from typing import Annotated

from fastapi import APIRouter, Query, Path

from app.db import RedisDep
from app.routers import error_response
from app.routers.backend.maps_redis import get_maps_from_redis, get_map_from_redis
from app.routers.backend.response_models import MapRedis

router = APIRouter()

@router.get(
    name="Get All Maps",
    path="/maps",
    tags=["Maps"],
    response_model=list[MapRedis],
    description="Fetch maps details.",
    response_description="Successfully fetched maps details.",
    responses={
        404: {"description": "Maps not found."}
    }
)
async def get_all_maps(
    redis: RedisDep,
    content_code: Annotated[
        str | None, Query(description="Content code on the map.", regex=r'^[a-zA-Z0-9_-]+$')
    ] = None,
    content_type: Annotated[
        str  | None, Query(description="Type of content on the map.")
    ] = None
):
    maps = await get_maps_from_redis(
        redis,
        content_code=content_code,
        content_type=content_type,
    )
    if not maps:
        return error_response(404, "Maps not found.")
    return maps


@router.get(
    name="Get Map",
    path="/maps/{x}/{y}",
    tags=["Maps"],
    response_model=MapRedis,
    description="Retrieve the details of a map.",
    response_description="Successfully fetched map.",
    responses={
        404: {"description": "Map not found."}
    }
)
async def get_map(
        redis: RedisDep,
        x: Annotated[int, Path(description="The position x of the map.")],
        y: Annotated[int, Path(description="The position y of the map.")]
):
    map_tile = await get_map_from_redis(redis, x, y)
    if not map_tile:
        return error_response(404, "Map not found.")
    return map_tile


