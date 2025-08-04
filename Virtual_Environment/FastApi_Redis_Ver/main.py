import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_redis, flush_redis, Redis, router as db_router
from app.routers import maps, resources, monsters, items, characters, actions
from app.routers.backend.characters_redis import load_base_character
from app.routers.backend.items_redis import load_items_data
from app.routers.backend.maps_redis import load_maps_data
from app.routers.backend.monsters_redis import load_monsters_data
from app.routers.backend.resources_redis import load_resources_data


@asynccontextmanager
async def redis_lifespan(app: FastAPI):
    """Simplified lifespan using db.py functions"""
    # Initialize and flush
    redis = await init_redis()
    await flush_redis(redis)

    # Load initial data if needed
    await load_initial_data(redis)

    # Store connection in app.state for optional use
    # app.state.redis = redis

    yield  # No shutdown logic as requested
    if redis:
        await redis.close()
app = FastAPI(lifespan=redis_lifespan)
app.include_router(maps.router)
app.include_router(resources.router)
app.include_router(monsters.router)
app.include_router(items.router)
app.include_router(characters.router)
app.include_router(db_router)
app.include_router(actions.router)

async def load_initial_data(redis: Redis):
    """Main initialization function that coordinates all data loading"""
    try:
        # Load all data components
        await load_maps_data(redis)  # Maps data
        await load_resources_data(redis) # Resources data
        await load_monsters_data(redis)
        await load_items_data(redis)
        await load_base_character(redis, 5)

        logging.info("All game data loaded successfully")
        print("All game data loaded successfully")
        return True
    except Exception as e:
        logging.error(f"Failed to load initial data: {e}")
        print(f"Failed to load initial data: {e}")
        raise
