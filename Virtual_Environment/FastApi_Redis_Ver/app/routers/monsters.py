from typing import List, Annotated

from fastapi import APIRouter, Query, Path

from app.db import RedisDep
from app.routers import error_response
from app.routers.backend.monsters_redis import get_monsters_from_redis, get_monster_from_redis
from app.routers.backend.response_models import MonsterRedis

router = APIRouter()

@router.get(
    name="Get All Monsters",
    path='/monsters',
    tags=['Monsters'],
    response_model=List[MonsterRedis],
    description="Fetch monsters details.",
    response_description="Successfully fetched monsters details.",
    responses={
        404: {"description": "Monsters not found."}
    },
)
async def get_all_monsters(
        redis: RedisDep,
        drop: Annotated[
            str, Query(description="Item code of the drop.", regex=r'^[a-zA-Z0-9_-]+$', example="green_slimeball")
        ] = None,
        max_level: Annotated[
            int, Query(description="Monster maximum level.", ge=1)
        ] = None,
        min_level: Annotated[
            int, Query(description="Monster minimum level.", ge=1)
        ] = None,
):
    monsters = await get_monsters_from_redis(
        redis,
        drop=drop,
        max_level=max_level,
        min_level=min_level,
    )
    if not monsters:
        return error_response(404, "Monsters not found.")
    return monsters


@router.get(
    name="Get Monster",
    path="/monsters/{code}",
    tags=['Monsters'],
    response_model=MonsterRedis,
    description="Retrieve the details of a monster.",
    response_description="Successfully fetched monster.",
    responses={
        404: {"description": "Monster not found."}
    },
)
async def get_monster(
        redis: RedisDep,
        code: Annotated[
            str, Path(description="The code of the monster.", regex=r'^[a-zA-Z0-9_-]+$')
        ]
):
    monster = await get_monster_from_redis(redis, code)
    if not monster:
        return error_response(404, "Monster not found.")
    return monster
