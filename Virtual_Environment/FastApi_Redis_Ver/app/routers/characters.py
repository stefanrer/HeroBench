from typing import List, Annotated, Dict

from fastapi import APIRouter, Path, Body

from app.db import RedisDep
from app.routers import error_response
from app.routers.backend.characters_redis import get_character_redis, get_all_characters_redis, create_character_redis, \
    create_custom_character_redis, delete_character_redis
from app.routers.backend.response_models import CharacterResponseRedis

router = APIRouter()

@router.get(
    name="Get Character",
    path="/characters/{name}",
    tags=["Characters"],
    response_model=CharacterResponseRedis,
    response_description="Successfully fetched character.",
    description="Retrieve the details of a character.",
    responses={
        404: {"description": "Character not found."}
    },
)
async def get_character(
        redis: RedisDep,
        name: Annotated[
            str, Path(description="The character name.", regex=r'^[a-zA-Z0-9_-]+$')
        ]
):
    character = await get_character_redis(redis, name)
    if not character:
        return error_response(404, "Character not found.")
    return character


@router.get(
    name="Get All Characters",
    path="/characters",
    tags=["Characters"],
    response_model=List[CharacterResponseRedis],
    description="Fetch characters details.",
    response_description="Successfully fetched characters details.",
    responses={
        404: {"description": "No Characters."}
    }
)
async def get_all_characters(
    redis: RedisDep,
):
    characters = await get_all_characters_redis(redis)
    if not characters:
        return error_response(404, "No Characters.")
    return characters

@router.post(
    name="Create Character",
    path="/characters/create",
    tags=["Characters"],
    response_model=CharacterResponseRedis,
    response_description="Successfully created character.",
    description="Create new character",
    responses={
        # 404: {"description": "Can't create new character."},
        494: {"description": "Name already used."},
    }
)
async def create_character(
    redis: RedisDep,
    name: Annotated[
        str, Body(description="Your desired character name.", max_length=64, regex=r'^[a-zA-Z0-9_-]+$')
    ],
    skin: Annotated[
        str, Body(description="Your desired skin.")
    ],
):
    character_key = f"characters:{name}"
    if await redis.exists(character_key):
        return error_response(494, "Name already used.")
    new_character = await create_character_redis(redis, name, skin)
    return new_character


@router.post(
    name="Create Custom Character",
    path="/characters/create_custom",
    tags=["Characters"],
    response_model=CharacterResponseRedis,
    response_description="Successfully created custom character.",
    description="Create new custom character",
    responses={
        494: {"description": "Name already used."},
        498: {"description": "Wrong Json."},
    }
)
async def create_custom_character(
        redis: RedisDep,
        name: Annotated[
            str, Body(description="Your desired character name.", max_length=64, regex=r'^[a-zA-Z0-9_-]+$')
        ],
        skin: Annotated[
            str, Body(description="Your desired skin.")
        ],
        char_data: Annotated[
            Dict, Body(description="Your desired character data.")
        ]
):
    character_key = f"characters:{name}"
    if await redis.exists(character_key):
        return error_response(494, "Name already used.")
    new_character = await create_custom_character_redis(redis, name, skin, char_data)
    if not new_character:
        return error_response(498, "Wrong Json.")
    return new_character


@router.post(
    name="Delete Character",
    path="/characters/delete",
    tags=["Characters"],
    response_model=CharacterResponseRedis,
    response_description="Successfully deleted character.",
    description="Delete character",
    responses={
        # 404: {"description": "Can't delete character."},
        498: {"description": "Character not found."}
    }
)
async def delete_character(
        redis: RedisDep,
        name: Annotated[
            str, Body(description="Character name.", max_length=64, regex=r'^[a-zA-Z0-9_-]+$')
        ],
):
    character = await delete_character_redis(redis, name)
    if not character:
        return error_response(498, "Character not found.")
    return character


