import json
from typing import Optional, List

from app.db import Redis
from app.routers.backend.response_models import MonsterRedis, MonsterDropRedis

MONSTER_KEY_PATTERN = "monster:{}"
MONSTER_DROPS_KEY_PATTERN = "{}:drops"
DROP_CODE_INDEX_KEY_PATTERN = "monsters:drop:{}"
MONSTERS_BY_LEVEL_INDEX_KEY_PATTERN = "monsters:by_level"

async def load_monsters_data(redis: Redis) -> bool:
    with open('../Data/monsters.json') as f:
        monsters = json.load(f)
        async with redis.pipeline() as pipe:
            for monster in monsters:
                monster_key = MONSTER_KEY_PATTERN.format(monster['code'])
                await pipe.hset(monster_key, mapping={
                    "name": monster['name'],
                    "code": monster['code'],
                    "level": str(monster['level']),
                    "hp": str(monster['hp']),
                    "attack_fire": str(monster['attack_fire']),
                    "attack_earth": str(monster['attack_earth']),
                    "attack_water": str(monster['attack_water']),
                    "attack_air": str(monster['attack_air']),
                    "res_fire": str(monster['res_fire']),
                    "res_earth": str(monster['res_earth']),
                    "res_water": str(monster['res_water']),
                    "res_air": str(monster['res_air']),
                    "min_gold": str(monster['min_gold']),
                    "max_gold": str(monster['max_gold']),
                })

                # Store drops as regular set (no scores)
                for drop in monster['drops']:
                    monster_drops_key = MONSTER_DROPS_KEY_PATTERN.format(monster_key)
                    await pipe.sadd(monster_drops_key, json.dumps({
                        "code": drop["code"],
                        "rate": drop["rate"],
                        "min_quantity": drop["min_quantity"],
                        "max_quantity": drop["max_quantity"]
                    }))
                    # Create drop code index
                    await pipe.sadd(DROP_CODE_INDEX_KEY_PATTERN.format(drop['code']), monster["code"])

                # Create secondary indexes
                await pipe.zadd(MONSTERS_BY_LEVEL_INDEX_KEY_PATTERN, {monster["code"]: monster["level"]})

            await pipe.execute()
            return True

async def get_monster_from_redis(redis: Redis, code: str) -> Optional[MonsterRedis]:
    """Get single monster by code"""
    monster_key = MONSTER_KEY_PATTERN.format(code)
    monster_data = await redis.hgetall(monster_key)
    if not monster_data:
        return None

    # Get drops
    monster_drops_key = MONSTER_DROPS_KEY_PATTERN.format(monster_key)
    drops = await redis.smembers(monster_drops_key)
    parsed_drops = [
        MonsterDropRedis(**json.loads(drop))
        for drop in drops
    ]

    return MonsterRedis(
        **monster_data,
        drops=parsed_drops,
    )

async def get_monsters_from_redis(redis: Redis, drop: Optional[str] = None, max_level: Optional[int] = None, min_level: Optional[int] = None) -> Optional[List[MonsterRedis]]:
    if not any([drop, min_level, max_level]):
        monster_codes = await redis.zrange(MONSTERS_BY_LEVEL_INDEX_KEY_PATTERN, 0, -1)
    else:
        """Get filtered monsters"""
        filtered_codes = set()

        # Apply drop filter if specified
        if drop:
            filtered_codes.update(
                await redis.smembers(DROP_CODE_INDEX_KEY_PATTERN.format(drop))
            )
        # Apply level range filter
        if min_level is not None or max_level is not None:
            level_codes = await redis.zrange(
                MONSTERS_BY_LEVEL_INDEX_KEY_PATTERN,
                start=min_level or "-inf",
                end=max_level or "+inf",
                byscore=True,
            )
            if filtered_codes:
                filtered_codes.intersection_update(level_codes)
            else:
                filtered_codes.update(level_codes)

        # Sort the filtered results by level
        if filtered_codes:
            async with redis.pipeline() as pipe:
                for code in filtered_codes:
                    await pipe.zscore(MONSTERS_BY_LEVEL_INDEX_KEY_PATTERN, code)
                scores = await pipe.execute()

            # Pair codes with their levels and sort
            code_level_pairs = zip(filtered_codes, scores)
            monster_codes = [
                code for code, _ in sorted(code_level_pairs, key=lambda x: x[1])
            ]
        else:
            monster_codes = []

    if not monster_codes:
        return []

    # Fetch all matching resources
    pipeline = redis.pipeline()
    for code in monster_codes:
        monster_key = MONSTER_KEY_PATTERN.format(code)
        await pipeline.hgetall(monster_key)
        await pipeline.smembers(MONSTER_DROPS_KEY_PATTERN.format(monster_key))
    results = await pipeline.execute()

    resources = []
    for i in range(0, len(results), 2):
        resource_data = results[i]
        drops_data = results[i + 1]

        if not resource_data:
            continue

        parsed_drops = [
            MonsterDropRedis(**json.loads(drop))
            for drop in drops_data
        ]

        resources.append(MonsterRedis(
            **resource_data,
            drops=parsed_drops,
        ))

    return resources