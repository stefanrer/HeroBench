from typing import List, Annotated

from fastapi import APIRouter, Query, Path

from app.db import RedisDep
from app.routers import error_response
from app.routers.backend.resources_redis import get_resources_from_redis, get_resource_from_redis
from app.routers.backend.response_models import ResourceResponseRedis

router = APIRouter()

@router.get(
    name="Get All Resources",
    path='/resources',
    tags=['Resources'],
    response_model=List[ResourceResponseRedis],
    description="Fetch resources details.",
    response_description="Successfully fetched resources details.",
    responses={
        404: {"description": "Resources not found."}
    },
)
async def get_all_resources(
        redis: RedisDep,
        drop: Annotated[
            str, Query(description="Item code of the drop.", regex=r'^[a-zA-Z0-9_-]+$', example="copper_ore")
        ] = None,
        max_level: Annotated[
            int, Query(description="Skill maximum level.", ge=1)
        ] = None,
        min_level: Annotated[
            int, Query(description="Skill minimum level.", ge=1)
        ] = None,
        skill: Annotated[
            str, Query(description="The code of the skill.")
        ] = None,
):
    resources = await get_resources_from_redis(
        redis=redis,
        drop=drop,
        max_level=max_level,
        min_level=min_level,
        skill=skill
    )

    if not resources:
        return error_response(404, "Resources not found.")
    return resources


@router.get(
    name="Get Resource",
    path="/resources/{code}",
    tags=['Resources'],
    response_model=ResourceResponseRedis,
    description="Retrieve the details of a resource.",
    response_description="Successfully fetched resource.",
    responses={
        404: {"description": "Resource not found."}
    },
)
async def get_resource(
        redis: RedisDep,
        code: Annotated[
            str, Path(description="The code of the resource.", regex=r'^[a-zA-Z0-9_-]+$', example="copper_rocks")
        ]
):
    resource = await get_resource_from_redis(redis, code)
    if not resource:
        return error_response(404, "Resource not found.")
    return resource