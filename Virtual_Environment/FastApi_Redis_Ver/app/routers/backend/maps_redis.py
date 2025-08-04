import json
from typing import Optional, List

from app.db import Redis
from app.routers.backend.response_models import MapRedis

MAP_KEY_PATTERN = "map:{}:{}"
MAPS_CONTENT_TYPE_INDEX_KEY_PATTERN = "maps:content_type:{}"
MAPS_CONTENT_CODE_INDEX_KEY_PATTERN = "maps:content_code:{}"

async def load_maps_data(redis: Redis) -> bool:
    """Load maps from JSON into Redis"""
    with open("../Data/maps.json") as file:
        maps = json.load(file)
        async with redis.pipeline() as pipe:
            for map_data in maps:
                map_key = MAP_KEY_PATTERN.format(map_data['x'], map_data['y'])
                await pipe.hset(map_key, mapping={
                    "name": map_data["name"],
                    "skin": map_data["skin"],
                    "x": str(map_data["x"]),
                    "y": str(map_data["y"]),
                    "content": json.dumps(map_data["content"]),
                })

                if map_data.get("content"):
                    content = map_data["content"]
                    # Create secondary indexes
                    await pipe.sadd(MAPS_CONTENT_TYPE_INDEX_KEY_PATTERN.format(content['type']), map_key)
                    await pipe.sadd(MAPS_CONTENT_CODE_INDEX_KEY_PATTERN.format(content['code']), map_key)

            await pipe.execute()
            return True

async def get_map_from_redis(redis: Redis, x: int, y: int) -> Optional[MapRedis]:
    """Get single map by coordinates"""
    map_key = MAP_KEY_PATTERN.format(x, y)
    data = await redis.hgetall(map_key)
    if not data:
        return None

    # Reconstruct content if exists
    if data.get("content"):
        data["content"] = json.loads(data["content"])

    return MapRedis(**data)

async def get_maps_from_redis(
        redis: Redis,
        content_code: Optional[str] = None,
        content_type: Optional[str] = None
) -> List[MapRedis]:
    """Get filtered maps (warning: Redis isn't great at complex queries)"""
    maps = []
    if not any([content_code, content_type]):
        map_keys = await redis.keys("map:*:*")
    else:
        sets_to_intersect = []
        if content_code:
            sets_to_intersect.append(await redis.smembers(MAPS_CONTENT_CODE_INDEX_KEY_PATTERN.format(content_code)))
        if content_type:
            sets_to_intersect.append(await redis.smembers(MAPS_CONTENT_TYPE_INDEX_KEY_PATTERN.format(content_type)))

        map_keys = list(set.intersection(*sets_to_intersect)) if len(sets_to_intersect) > 1 else sets_to_intersect[0]
    async with redis.pipeline() as pipe:
        for key in map_keys:
            await pipe.hgetall(key)
        results = await pipe.execute()

    for data in results:
        if not data:
            continue

        # Process content
        if data.get("content"):
            data["content"] = json.loads(data["content"])

        map_obj = MapRedis(**data)

        maps.append(map_obj)

    return maps