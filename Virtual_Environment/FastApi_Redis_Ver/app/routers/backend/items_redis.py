import json
from typing import Optional, List

from app.db import Redis
from app.routers.backend.response_models import ItemRedis, ItemEffectRedis, CraftItemRedis, ItemCraftRedis

ITEM_KEY_PATTERN = "item:{}"
ITEMS_TYPE_INDEX_KEY_PATTERN = "items:type:{}"
ITEMS_NAME_INDEX_KEY_PATTERN = "items:name_index"
ITEMS_SUBTYPE_INDEX_KEY_PATTERN = "items:subtype:{}"
ITEMS_BY_LEVEL_INDEX_KEY_PATTERN = "items:by_level"
EFFECT_KEY_PATTERN = "{}:effects"
CRAFT_KEY_PATTERN = "{}:craft"
CRAFT_SKILL_INDEX_KEY_PATTERN = "items:craft_skill:{}"
CRAFT_ITEMS_KEY_PATTERN = "{}:items"
CRAFT_ITEM_INDEX_KEY_PATTERN = "items:craft_item:{}"

async def load_items_data(redis: Redis) -> bool:
    with open('../Data/items.json') as f:
        items_data = json.load(f)
        async with redis.pipeline() as pipe:
            for item_data in items_data:
                item_key = ITEM_KEY_PATTERN.format(item_data['code'])
                await pipe.hset(item_key, mapping={
                    "name": item_data["name"],
                    "code": item_data["code"],
                    "level": str(item_data["level"]),
                    "type": item_data["type"],
                    "subtype": item_data.get("subtype", ""),
                    "description": item_data.get("description", ""),
                })

                for effect in item_data['effects']:
                    effect_key = EFFECT_KEY_PATTERN.format(item_key)
                    await pipe.sadd(effect_key, json.dumps({
                        "name": effect["name"],
                        "value": str(effect["value"]),
                    }))

                # Index craft_material
                craft = item_data['craft']
                if craft:
                    craft_key = CRAFT_KEY_PATTERN.format(item_key)
                    await pipe.hset(craft_key, mapping={
                        "skill": craft["skill"],
                        "level": str(craft["level"]),
                        "quantity": str(craft["quantity"]),
                    })
                    # Create craft_skill index
                    await pipe.sadd(CRAFT_SKILL_INDEX_KEY_PATTERN.format(craft['skill']), item_data["code"])

                    for craft_item in craft["items"]:
                        craft_items_key = CRAFT_ITEMS_KEY_PATTERN.format(craft_key)
                        await pipe.sadd(craft_items_key, json.dumps({
                            "code": craft_item["code"],
                            "quantity": str(craft_item["quantity"]),
                        }))
                        # Create craft_item code index
                        await pipe.sadd(CRAFT_ITEM_INDEX_KEY_PATTERN.format(craft_item['code']), item_data["code"])

                # Create secondary indexes
                await pipe.sadd(ITEMS_TYPE_INDEX_KEY_PATTERN.format(item_data['type']), item_data["code"])
                await pipe.zadd(ITEMS_NAME_INDEX_KEY_PATTERN, {f"{item_data['name'].lower()}:{item_data['code']}": 0})  # Score 0, value format "name:code"
                await pipe.sadd(ITEMS_SUBTYPE_INDEX_KEY_PATTERN.format(item_data.get('subtype', '')), item_data["code"])
                await pipe.zadd(ITEMS_BY_LEVEL_INDEX_KEY_PATTERN, {item_data["code"]: item_data["level"]})

            await pipe.execute()
            return True

async def get_item_from_redis(redis: Redis, code: str) -> Optional[ItemRedis]:
    """Get single item by code"""
    item_key = ITEM_KEY_PATTERN.format(code)
    item_data = await redis.hgetall(item_key)
    if not item_data:
        return None
    # Get Effects
    effects = await redis.smembers(EFFECT_KEY_PATTERN.format(item_key))
    parsed_effects = [
        ItemEffectRedis(**json.loads(effect))
        for effect in effects
    ] if effects else []
    # Get Craft
    craft_key = CRAFT_KEY_PATTERN.format(item_key)
    craft = await redis.hgetall(craft_key)
    craft_items = await redis.smembers(CRAFT_ITEMS_KEY_PATTERN.format(craft_key))
    parsed_craft_items = [
        CraftItemRedis(**json.loads(item))
        for item in craft_items
    ] if craft else []
    parsed_craft = ItemCraftRedis(
        **craft,
        items=parsed_craft_items,
    ) if craft else None
    #
    return ItemRedis(
        **item_data,
        effects=parsed_effects,
        craft=parsed_craft,
    )

async def prefix_search_sorted_set(redis: Redis, prefix: str):
    prefix = prefix.lower()
    results = await redis.zrange(
        name=ITEMS_NAME_INDEX_KEY_PATTERN,
        start=f"[{prefix}",
        end=f"[{prefix}\xff",  # \xff ensures we get all matches
        bylex=True,
    )
    return {code.split(":", 1)[1] for code in results if ":" in code}

async def get_items_from_redis(
        redis: Redis,
        craft_material: Optional[str] = None,
        craft_skill: Optional[str] = None,
        max_level: Optional[int] = None,
        min_level: Optional[int] = None,
        name: Optional[str] = None,
        item_type: Optional[str] = None,
) -> List[ItemRedis]:
    if not any([craft_material, craft_skill, max_level, min_level, name, item_type]):
        item_codes = await redis.zrange(ITEMS_BY_LEVEL_INDEX_KEY_PATTERN, 0, -1)
    else:
        """Get filtered items"""
        filtered_codes = set()

        # Apply craft item filter if specified
        if craft_material:
            filtered_codes.update(
                await redis.smembers(CRAFT_ITEM_INDEX_KEY_PATTERN.format(craft_material))
            )

        # Apply craft skill filter if specified
        if craft_skill:
            skill_codes = await redis.smembers(CRAFT_SKILL_INDEX_KEY_PATTERN.format(craft_skill))
            if filtered_codes:
                filtered_codes.intersection_update(skill_codes)
            else:
                filtered_codes.update(skill_codes)

        # Apply level range filter if specified
        if min_level is not None or max_level is not None:
            level_codes = await redis.zrange(
                name=ITEMS_BY_LEVEL_INDEX_KEY_PATTERN,
                start=min_level or "-inf",
                end=max_level or "+inf",
                byscore=True,
            )
            if filtered_codes:
                filtered_codes.intersection_update(level_codes)
            else:
                filtered_codes.update(level_codes)

        # Apply name filter if specified
        if name:
            name_codes = await prefix_search_sorted_set(redis, name)
            if filtered_codes:
                filtered_codes.intersection_update(name_codes)
            else:
                filtered_codes.update(name_codes)

        # Apply type filter if specified
        if item_type:
            type_codes = await redis.smembers(ITEMS_TYPE_INDEX_KEY_PATTERN.format(item_type))
            if filtered_codes:
                filtered_codes.intersection_update(type_codes)
            else:
                filtered_codes.update(type_codes)

        # Sort the filtered results by level
        if filtered_codes:
            async with redis.pipeline() as pipe:
                for code in filtered_codes:
                    await pipe.zscore(ITEMS_BY_LEVEL_INDEX_KEY_PATTERN, code)
                scores = await pipe.execute()

            # Pair codes with their levels and sort
            code_level_pairs = zip(filtered_codes, scores)
            item_codes = [
                code for code, _ in sorted(code_level_pairs, key=lambda x: x[1])
            ]
        else:
            item_codes = []

    if not item_codes:
        return []

    # Fetch all matching items
    async with redis.pipeline() as pipe:
        for code in item_codes:
            item_key = ITEM_KEY_PATTERN.format(code)
            await pipe.hgetall(item_key)
            await pipe.smembers(EFFECT_KEY_PATTERN.format(item_key))
            craft_key = CRAFT_KEY_PATTERN.format(item_key)
            await pipe.hgetall(craft_key)
            await pipe.smembers(CRAFT_ITEMS_KEY_PATTERN.format(craft_key))
        results = await pipe.execute()
    items = []
    for i in range(0, len(results), 4):
        item_data, effects, craft, craft_items = results[i:i+4]

        if not item_data:
            continue
        #
        if effects:
            parsed_effects = [
                ItemEffectRedis(**json.loads(effect))
                for effect in effects
            ]
        else:
            parsed_effects = []
        if craft:
            parsed_craft_items = [
                CraftItemRedis(**json.loads(item))
                for item in craft_items
            ]
            parsed_craft = ItemCraftRedis(
                **craft,
                items=parsed_craft_items,
            )
        else:
            parsed_craft = None
        #
        item = ItemRedis(
            **item_data,
            effects=parsed_effects,
            craft=parsed_craft,
        )
        items.append(item)

    return items