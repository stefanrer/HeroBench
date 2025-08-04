from typing import Annotated

from fastapi import APIRouter, Query, Path

from app.db import RedisDep
from app.routers import error_response
from app.routers.backend.items_redis import get_items_from_redis, get_item_from_redis
from app.routers.backend.response_models import ItemRedis

router = APIRouter()

@router.get(
    name="Get All Items",
    path="/items",
    tags=["Items"],
    response_model=list[ItemRedis],
    description="Fetch items details.",
    response_description="Fetch items details.",
    responses={
        404: {"description": "Items not found."}
    },
)
async def get_all_items(
        redis: RedisDep,
        craft_material: Annotated[
            str, Query(description="Item code of items used as material for crafting.", pattern=r'^[a-zA-Z0-9_-]+$')
        ] = None,
        craft_skill: Annotated[
            str, Query(description="Skill to craft items.")
        ] = None,
        max_level: Annotated[
            int, Query(description="Maximum level items.", ge=1)
        ] = None,
        min_level: Annotated[
            int, Query(description="Minimum level items.", ge=1)
        ] = None,
        name: Annotated[
            str, Query(description="Name of the item.", pattern=r'^[a-zA-Z0-9_ -]+$')
        ] = None,
        type: Annotated[
            str, Query(description="Type of items.")
        ] = None,
):
    items = await get_items_from_redis(redis, craft_material, craft_skill, max_level, min_level, name, type)
    if not items:
        return error_response(404, "Items not found.")
    return items


@router.get(
    name="Get Item",
    path="/items/{code}",
    tags=["Items"],
    response_model=ItemRedis,
    description="Retrieve the details of a item.",
    response_description="Successfully fetched item.",
    responses={
        404: {"description": "Item not found."}
    },
)
async def get_item(
    redis: RedisDep,
    code: Annotated[
        str, Path(description="The code of the item.", pattern=r'^[a-zA-Z0-9_-]+$')
    ]
):
    item = await get_item_from_redis(redis=redis, code=code)
    if not item:
        return error_response(404, "Item not found.")
    return item



