import json
import logging
import time
from enum import Enum
from typing import Annotated, AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.routers import error_response

GLOBAL_LOGS_KEY_PATTERN = "logs:global"
CHARACTER_LOGS_KEY_PATTERN = "logs:{}"


class ActionType(str, Enum):
    create_character = "create_character"
    create_custom_character = "create_custom_character"
    delete_character = "delete_character"
    move = "move"
    equip_item = "equip_item"
    unequip_item = "unequip_item"
    fight = "fight"
    gather = "gather"
    craft = "craft"
    delete_item = "delete_item"
    give_item = "give_item"
    buy_item = "buy_item"


class LogRedis(BaseModel):
    character_name: Annotated[str, Field(description="character name")]
    action_type: Annotated[ActionType, Field(description="action type")]
    log: Annotated[str, Field(description="log of the performed action")]
    timestamp: Annotated[float, Field(default_factory=time.time)]


async def get_redis() -> AsyncGenerator[Redis, None]:
    """
    Dependency for route handlers (unchanged from your original)
    Creates new connection per request
    """
    redis = await init_redis()
    try:
        yield redis
    finally:
        await redis.close()

async def init_redis() -> Redis:
    """Initialize and return a Redis connection with automatic cleanup"""
    redis = Redis.from_url("redis://localhost:6379", decode_responses=True)
    try:
        # Verify connection
        if not await redis.ping():
            raise ConnectionError("Failed to connect to Redis")
        logging.info("Redis connection established")
        return redis
    except Exception as e:
        logging.error(f"Redis connection failed: {e}")
        await redis.close()
        raise

async def flush_redis(redis: Redis) -> None:
    """Clear all data in Redis (like rm_db)"""
    await redis.flushdb()
    logging.info("Redis database flushed")


async def create_log(redis: Redis, character_name: str, action: ActionType, log: str) -> LogRedis:
    log = LogRedis(
        character_name=character_name,
        action_type=action,
        log=log,
        timestamp=time.time(),
    )
    async with redis.pipeline(transaction=True) as pipe:
        log_json = json.dumps(log.dict())
        # Add to global logs
        await redis.zadd(
            GLOBAL_LOGS_KEY_PATTERN,
            {log_json: log.timestamp}
        )
        await redis.zadd(
            CHARACTER_LOGS_KEY_PATTERN.format(character_name),
            {log_json: log.timestamp}
        )
        await pipe.execute()
    return log

RedisDep = Annotated[Redis, Depends(get_redis)]

router = APIRouter()


async def get_all_logs_redis(redis: Redis, amount: int) -> Optional[List[LogRedis]]:
    results = await redis.zrange(GLOBAL_LOGS_KEY_PATTERN, start=0, end=amount-1, desc=True)
    logs: List[LogRedis] = [LogRedis(**json.loads(log)) for log in results]
    return logs

async def get_character_logs_redis(redis: Redis, amount: int, character_name: str) -> Optional[List[LogRedis]]:
    results = await redis.zrange(CHARACTER_LOGS_KEY_PATTERN.format(character_name), start=0, end=amount-1, desc=True)
    logs: List[LogRedis] = [LogRedis(**json.loads(log)) for log in results]
    return logs


@router.get(
    name="Get Logs",
    path="/logs/{amount}",
    tags=["Logs"],
    response_model=List[LogRedis],
    response_description="Successfully fetched logs.",
    description="Retrieve the last N logs.",
    responses={
        404: {"description": "No logs found."},
    }
)
async def get_logs(
        redis: RedisDep,
        amount: Annotated[
            int, Path(description="Last N Logs.", ge=1)
        ],
):
    logs = await get_all_logs_redis(redis, amount)
    if not logs:
        raise error_response(status_code=404, message="No logs found")
    return logs


@router.get(
    name="Get Character Logs",
    path="/logs/{amount}/{name}",
    tags=["Logs"],
    response_model=List[LogRedis],
    response_description="Successfully fetched character logs.",
    description="Retrieve the last N logs for a specific character",
    responses={
        404: {"description": "No logs found for this character"},
    }
)
async def get_character_logs(
        redis: RedisDep,
        name: Annotated[
            str, Path(description="Name of your character.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
        amount: Annotated[
            int, Path(description="Last N Logs.", ge=1)
        ],
):
    logs = await get_character_logs_redis(redis, amount, name)
    if not logs:
        raise error_response(status_code=404, message=f"No logs found for character {name}")
    return logs