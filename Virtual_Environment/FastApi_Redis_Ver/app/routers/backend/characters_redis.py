import json
import random
from typing import Optional, List, Dict

from app.db import Redis, create_log, ActionType
from app.routers.backend.response_models import InventorySlotResponseRedis, CharacterResponseRedis

with open("../Data/items.json") as j_file:
    check_items = [item['code'] for item in json.load(j_file)]

CHARACTER_KEY_PATTERN = "character:{}"
CHARACTERS_KEY_PATTERN = "characters"
INVENTORY_KEY_PATTERN = "{}:inventory"

skins = ["men1", "men2", "men3", "women1", "women2", "women3"]

async def get_character_inventory(redis: Redis, inventory_key: str) -> Optional[List[InventorySlotResponseRedis]]:
    # Get Inventory
    inventory = await redis.hgetall(inventory_key)
    parsed_inventory = [
        InventorySlotResponseRedis(slot=slot_num, code=inventory_slot,
                                   quantity=json.loads(inventory[inventory_slot])["quantity"])
        for slot_num, inventory_slot in enumerate(inventory, 1)
    ]
    return parsed_inventory


async def create_character_redis(redis: Redis, name: str, skin: str) -> Optional[CharacterResponseRedis]:
    try:
        async with redis.pipeline(transaction=True) as pipe:
            character_key = CHARACTER_KEY_PATTERN.format(name)
            new_character = CharacterResponseRedis(
                name=name,
                skin=skin,
                weapon_slot="wooden_stick",
                attack_earth=4
            )
            await redis.hset(character_key, mapping=new_character.dict(exclude={"inventory"}))
            await redis.sadd(CHARACTERS_KEY_PATTERN, name) # Add character name to set of character names for later use
            await pipe.execute()
            await create_log(redis, name, ActionType.create_character, f"Successfully created character - {name}.")
            return new_character
    except Exception as e:
        print(e)
        return None

async def create_custom_character_redis(redis: Redis, name: str, skin: str, char_data: Dict) -> Optional[CharacterResponseRedis]:
    try:
        async with redis.pipeline(transaction=True) as pipe:
            character_key = CHARACTER_KEY_PATTERN.format(name)
            inventory_key = INVENTORY_KEY_PATTERN.format(character_key)
            new_character = CharacterResponseRedis(
                name=name,
                skin=skin,
                **{key: value for key, value in char_data.items() if key != 'inventory'},
            )
            await redis.hset(character_key, mapping=new_character.dict(exclude={"inventory"}))
            if 'inventory' in char_data:
                for inventory_slot in char_data['inventory']:
                    inventory_slot = InventorySlotResponseRedis(**inventory_slot)
                    await pipe.hset(inventory_key, inventory_slot.code, json.dumps({
                        "quantity": inventory_slot.quantity,
                    }))
            await redis.sadd(CHARACTERS_KEY_PATTERN, name)  # Add character name to set of character names for later use
            await pipe.execute()
            new_character.inventory = char_data['inventory'] if 'inventory' in char_data else []
            await create_log(redis, name, ActionType.create_custom_character, f"Successfully created custom character - {new_character.name}.")
            return new_character
    except Exception as e:
        print(e)
        return None

async def delete_character_redis(redis: Redis, name: str) -> Optional[CharacterResponseRedis]:
    try:
        async with redis.pipeline(transaction=True) as pipe:
            character_key = CHARACTER_KEY_PATTERN.format(name)
            inventory_key = INVENTORY_KEY_PATTERN.format(character_key)
            character_data = await redis.hgetall(character_key)
            if not character_data:
                return None
            await redis.delete(character_key)
            inventory_data = await get_character_inventory(redis, inventory_key)
            if inventory_data:
                await redis.delete(inventory_key)
            else:
                inventory_data = []
            await redis.srem(CHARACTERS_KEY_PATTERN, name)
            await pipe.execute()
            await create_log(redis=redis, character_name=name, action=ActionType.delete_character,
                                   log=f"Successfully deleted character - {name}.")
            return CharacterResponseRedis(
                **character_data,
                inventory=inventory_data
            )
    except Exception as e:
        print(e)
        return None

async def get_character_redis(redis: Redis, name: str) -> Optional[CharacterResponseRedis]:
    """Get single character by name"""
    try:
        character_key = CHARACTER_KEY_PATTERN.format(name)
        inventory_key = INVENTORY_KEY_PATTERN.format(character_key)
        character_data = await redis.hgetall(character_key)
        if not character_data:
            return None

        parsed_inventory = await get_character_inventory(redis, inventory_key)
        return CharacterResponseRedis(
            **character_data,
            inventory=parsed_inventory
        )
    except Exception as e:
        print(e)
        return None

async def get_all_characters_redis(redis: Redis) -> Optional[List[CharacterResponseRedis]]:
    all_character_names = await redis.smembers(CHARACTERS_KEY_PATTERN)
    characters_data = [await get_character_redis(redis, character_name)
        for character_name in all_character_names
    ]
    return characters_data

async def load_base_character(redis: Redis, amount: int) -> bool:
    for n in range(1, amount + 1):
        name = f"character_{n}"
        skin = random.choice(skins)
        await create_character_redis(redis, name, skin)
    return True