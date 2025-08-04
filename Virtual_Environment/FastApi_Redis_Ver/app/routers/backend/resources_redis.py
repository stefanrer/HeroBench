import json
from typing import Optional, List

from app.db import Redis
from app.routers.backend.response_models import ResourceResponseRedis, ResourceDropResponseRedis

RESOURCE_KEY_PATTERN = "resource:{}"
RESOURCE_DROPS_KEY_PATTERN = "{}:drops"
DROP_CODE_INDEX_KEY_PATTERN = "resources:drop:{}"
RESOURCES_SKILL_INDEX_KEY_PATTERN = "resources:skill:{}"
RESOURCES_BY_LEVEL_INDEX_KEY_PATTERN = "resources:by_level"

async def load_resources_data(redis: Redis) -> bool:
    """Load resources from JSON into Redis"""
    with open('../Data/resources.json') as f:
        resources = json.load(f)
        async with redis.pipeline() as pipe:
            for resource in resources:
                resource_key = RESOURCE_KEY_PATTERN.format(resource['code'])
                await pipe.hset(resource_key, mapping={
                    "name": resource["name"],
                    "code": resource["code"],
                    "skill": resource["skill"],
                    "level": str(resource["level"])
                })

                # Store drops as regular set (no scores)
                for drop in resource["drops"]:
                    drops_key = RESOURCE_DROPS_KEY_PATTERN.format(resource_key)
                    await pipe.sadd(drops_key, json.dumps({
                        "code": drop["code"],
                        "rate": drop["rate"],
                        "min_quantity": drop["min_quantity"],
                        "max_quantity": drop["max_quantity"]
                    }))
                    # Create drop code index
                    await pipe.sadd(DROP_CODE_INDEX_KEY_PATTERN.format(drop['code']), resource["code"])

                # Create secondary indexes
                await pipe.sadd(RESOURCES_SKILL_INDEX_KEY_PATTERN.format(resource['skill']), resource["code"])
                await pipe.zadd(RESOURCES_BY_LEVEL_INDEX_KEY_PATTERN, {resource["code"]: resource["level"]})

            await pipe.execute()
            return True

async def get_resource_from_redis(redis: Redis, code: str) -> Optional[ResourceResponseRedis]:
    """Get single resource by code"""
    resource_key = RESOURCE_KEY_PATTERN.format(code)
    resource_data = await redis.hgetall(resource_key)
    if not resource_data:
        return None

    # Get drops
    drops = await redis.smembers(RESOURCE_DROPS_KEY_PATTERN.format(resource_key))
    parsed_drops = [
        ResourceDropResponseRedis(**json.loads(drop))
        for drop in drops
    ]

    return ResourceResponseRedis(
        **resource_data,
        drops=parsed_drops,
    )

async def get_resources_from_redis(
        redis: Redis,
        drop: Optional[str] = None,
        max_level: Optional[int] = None,
        min_level: Optional[int] = None,
        skill: Optional[str] = None
) -> List[ResourceResponseRedis]:
    if not any([drop, max_level, min_level, skill]):
        resource_codes = await redis.zrange(RESOURCES_BY_LEVEL_INDEX_KEY_PATTERN, 0, -1)
    else:
        """Get filtered resources"""
        filtered_codes = set()

        # Apply drop filter if specified
        if drop:
            filtered_codes.update(
                await redis.smembers(DROP_CODE_INDEX_KEY_PATTERN.format(drop))
            )

        # Apply skill filter if specified
        if skill:
            skill_codes = await redis.smembers(RESOURCES_SKILL_INDEX_KEY_PATTERN.format(skill))
            if filtered_codes:
                filtered_codes.intersection_update(skill_codes)
            else:
                filtered_codes.update(skill_codes)

        # Apply level range filter
        if min_level is not None or max_level is not None:
            level_codes = await redis.zrange(
                RESOURCES_BY_LEVEL_INDEX_KEY_PATTERN,
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
                    await pipe.zscore(RESOURCES_BY_LEVEL_INDEX_KEY_PATTERN, code)
                scores = await pipe.execute()

            # Pair codes with their levels and sort
            code_level_pairs = zip(filtered_codes, scores)
            resource_codes = [
                code for code, _ in sorted(code_level_pairs, key=lambda x: x[1])
            ]
        else:
            resource_codes = []

    if not resource_codes:
        return []

    # Fetch all matching resources
    async with redis.pipeline() as pipe:
        for code in resource_codes:
            resource_key = RESOURCE_KEY_PATTERN.format(code)
            await pipe.hgetall(resource_key)
            await pipe.smembers(RESOURCE_DROPS_KEY_PATTERN.format(resource_key))
        results = await pipe.execute()

    resources = []
    for i in range(0, len(results), 2):
        resource_data = results[i]
        drops_data = results[i + 1]

        if not resource_data:
            continue

        if drops_data:
            parsed_drops = [
                ResourceDropResponseRedis(**json.loads(drop))
                for drop in drops_data
            ]
        else:
            parsed_drops = []

        resources.append(ResourceResponseRedis(
            **resource_data,
            drops=parsed_drops,
        ))

    return resources