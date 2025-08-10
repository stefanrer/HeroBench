from typing import Optional, Annotated, List

from fastapi import APIRouter, Path, Body

from app.db import RedisDep
from app.routers import error_response, error_info_response
from app.routers.backend.actions_redis import CharacterUpdateRedis
from app.routers.backend.maps_redis import get_correct_map_from_redis
from app.routers.backend.monsters_redis import get_monster_from_redis
from app.routers.backend.response_models import CharacterResponseRedis, CharacterMovementDataResponseRedis, \
    SkillResponseRedis, CharacterFightDataRedis, ItemRedis, MonsterRedis, EquipRequestResponseRedis, ItemSlot, \
    DeleteItemResponseRedis, InventorySlotResponseRedis, GivenItemResponseRedis, CharacterFightsDataRedis, \
    FightResponseRedis, BuyResponseRedis, SimpleItemResponseRedis
from app.routers.characters import get_character_redis
from app.routers.items import get_item_from_redis
from app.routers.maps import MapRedis, get_map_from_redis
from app.routers.resources import ResourceResponseRedis, get_resource_from_redis

router = APIRouter()

@router.post(
    name="Action Move",
    path="/my/{name}/action/move",
    tags=["My characters"],
    response_model=CharacterMovementDataResponseRedis,
    description="Moves a character on the map using the map's X and Y position.",
    response_description="The character has moved successfully.",
    responses={
        404: {"description": "Map not found."},
        486: {"description": "Redis Error."},
        490: {"description": "Character already at destination."},
        498: {"description": "Character not found."},
    },
)
async def action_move(
        redis: RedisDep,
        name: Annotated[
            str, Path(description="Name of your character.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
        x: Annotated[
            int, Body(description="The x coordinate of the destination.")
        ],
        y: Annotated[
            int, Body(description="The y coordinate of the destination.")
        ],
):
    character: Optional[CharacterResponseRedis] = await get_character_redis(redis, name)
    if not character:
        return error_response(498, "Character not found.")

    move_map: Optional[MapRedis] = await get_map_from_redis(redis, x, y)
    if not move_map:
        return error_response(404, "Map not found.")

    if character.x == move_map.x and character.y == move_map.y:
        return error_response(490, "Character already at destination.")

    update_redis = CharacterUpdateRedis(redis, character)
    await update_redis.move_character(x, y)

    if not await update_redis.update_redis():
        return error_response(486, "Redis Error.")

    return CharacterMovementDataResponseRedis(destination=move_map, character=update_redis.changed_character)


@router.post(
    name="Action Gathering",
    path="/my/{name}/action/gathering",
    tags=["My characters"],
    response_model=SkillResponseRedis,
    description="Harvest a resource on the character's map.",
    response_description="The resource has been successfully gathered.",
    responses={
        404: {"description": "Resource not found."},
        486: {"description": "Redis Error."},
        493: {"description": "Not skill level required."},
        498: {"description": "Character not found."},
        598: {"description": "Resource not found on this map."}
    },
)
async def action_gathering(
        redis: RedisDep,
        name: Annotated[
            str, Path(description="Name of your character.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
        quantity: Annotated[
            int, Body(description="Quantity of items to gather.", ge=1)
        ],
):
    character: Optional[CharacterResponseRedis] = await get_character_redis(redis, name)
    if not character:
        return error_response(498, "Character not found.")

    current_map: Optional[MapRedis] = await get_map_from_redis(redis, character.x, character.y)
    if not current_map or not current_map.content or not current_map.content.type == "resource":
        return error_response(598, "Resource not found on this map.")

    current_resource: Optional[ResourceResponseRedis] = await get_resource_from_redis(redis=redis, code=current_map.content.code)
    if not current_resource:
        return error_response(404, "Resource not found.")

    needed_skill = current_resource.skill
    character_skill_level = getattr(character, f'{needed_skill}_level')

    if character_skill_level < current_resource.level:
        return error_response(493, "Not skill level required.")

    update_redis = CharacterUpdateRedis(redis, character)
    skill_info, gathered = await update_redis.gather_resource(current_resource, quantity, 1)

    if not gathered or not await update_redis.update_redis():
        return error_response(486, "Redis Error.")

    return SkillResponseRedis(details=skill_info, character=update_redis.changed_character)


@router.post(
    name="Action Crafting",
    path="/my/{name}/action/crafting",
    tags=["My characters"],
    response_model=SkillResponseRedis,
    description="Crafting an item. The character must be on a map with a workshop.",
    response_description="The item was successfully crafted.",
    responses={
        404: {"description": "Craft not found."},
        478: {"description": "Missing item or insufficient quantity."},
        486: {"description": "An action is already in progress by your character."},
        493: {"description": "Not skill level required."},
        498: {"description": "Character not found."},
        500: {"description": "Crafting Error."},
        598: {"description": "Workshop not found on this map."}
    },
)
async def action_crafting(
        redis: RedisDep,
        name: Annotated[
            str, Path(description="Name of your character.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
        code: Annotated[
            str, Body(description="Craft code.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
        quantity: Annotated[
            int, Body(description="Quantity of items to craft.", ge=1)
        ],
):
    on_workshop_tile = False
    needed_skill_level = False
    enough_items_for_craft = False


    # Must checks
    character: Optional[CharacterResponseRedis] = await get_character_redis(redis, name)
    if not character:
        return error_response(498, "Character not found.")

    current_craft: Optional[ItemRedis] = await get_item_from_redis(redis, code)
    if not current_craft or not current_craft.craft:
        return error_response(404, "Craft not found.")

    # Can checks
    current_map: Optional[MapRedis] = await get_map_from_redis(redis, character.x, character.y)
    if not current_map or not current_map.content or not current_map.content.type == "workshop" or current_map.content.code != current_craft.craft.skill:
        correct_map = await get_correct_map_from_redis(redis, content_type="workshop", content_code=current_craft.craft.skill)
        # return error_response(598, "Workshop not found on this map.")
    else:
        correct_map = current_map
        on_workshop_tile = True

    character_skill_level = getattr(character, f'{current_craft.craft.skill}_level')
    if character_skill_level < current_craft.craft.level:
        # return error_response(493, "Not skill level required.")
        pass
    else:
        needed_skill_level = True

    needed_items_for_craft = current_craft.craft.items

    update_redis = CharacterUpdateRedis(redis, character)

    if not character.inventory or not await update_redis.has_all_items_for_craft(needed_items_for_craft, quantity):  # check if character inventory empty or has enough items to craft
        # return error_response(478, "Missing item or insufficient quantity.")
        pass
    else:
        enough_items_for_craft = True

    if on_workshop_tile and needed_skill_level and enough_items_for_craft:
        skill_info, crafted = await update_redis.craft_item(current_craft, quantity)
        if not crafted or not await update_redis.update_redis():
            return error_response(486, "Redis Error.")

        return SkillResponseRedis(details=skill_info, character=update_redis.changed_character)
    else:
        errors = {
            "on_workshop_tile": on_workshop_tile,
            "needed_skill_level": needed_skill_level,
            "enough_items_for_craft": enough_items_for_craft,
        }
        error_workshop = {
            "needed": f"({correct_map.x}, {correct_map.y})",
            "current": f"({current_map.x}, {current_map.y})",
        }
        error_skill_level = {
            "skill": current_craft.craft.skill,
            "needed": current_craft.craft.level,
            "current": character_skill_level
        }
        error_missing_items = await update_redis.get_missing_items_for_craft(needed_items_for_craft, quantity)
        info = {
            "errors": errors,
            "item": current_craft.code,
            "workshop": error_workshop,
            "skill_level": error_skill_level,
            "missing_items": error_missing_items
        }
        log_text = f"{update_redis.changed_character.name} failed to craft {code} x{quantity}."
        if not on_workshop_tile:
            log_text += f" On wrong map tile: {error_workshop}."
        if not needed_skill_level:
            log_text += f" Needed skill level: {error_skill_level}."
        if not enough_items_for_craft:
            log_text += f" Missing items: {error_missing_items}."

        await update_redis.add_craft_failure_log(log_text)

        return error_info_response(500, info)


@router.post(
    name="Action Buy Item",
    path="/my/{name}/action/buy",
    tags=["My characters"],
    response_model=BuyResponseRedis,
    description="Buy an item at a grand-exchange tile.",
    response_description="Item successfully purchased and added to inventory.",
    responses={
        404: {"description": "Item not found."},
        486: {"description": "Redis Error."},
        498: {"description": "Character not found."},
        598: {"description": "Grand-exchange not found on this map."},
    },
)
async def action_buy(
        redis: RedisDep,
        name: Annotated[
            str, Path(description="Name of your character.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
        code: Annotated[
            str, Body(description="Item code.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
        quantity: Annotated[
            int, Body(description="Quantity of items to buy.", ge=1)
        ] = 1,
):
    character: Optional[CharacterResponseRedis] = await get_character_redis(redis, name)
    if not character:
        return error_response(498, "Character not found.")

    current_map: Optional[MapRedis] = await get_map_from_redis(redis, character.x, character.y)
    if not current_map or not current_map.content or not current_map.content.type == "grand_exchange":
        return error_response(598, "Grand-exchange not found on this map.")

    current_item: Optional[ItemRedis] = await get_item_from_redis(redis, code)
    if not current_item:
        return error_response(404, "Item not found.")

    update_redis = CharacterUpdateRedis(redis, character)
    bought = await update_redis.buy_item(current_item, quantity)

    if not bought or not await update_redis.update_redis():
        return error_response(486, "Redis Error.")

    return BuyResponseRedis(
        item=SimpleItemResponseRedis(code=current_item.code, quantity=quantity),
        character=update_redis.changed_character
    )


@router.post(
    name="Action Fight",
    path="/my/{name}/action/fight",
    tags=["My characters"],
    response_model=CharacterFightDataRedis,
    description="Start a fight against a monster on the character's map.",
    response_description="The fight ended successfully.",
    responses={
        404: {"description": "Monster not found."},
        486: {"description": "Redis Error."},
        498: {"description": "Character not found."},
        598: {"description": "Monster not found on this map."}
    },
)
async def action_fight(
        redis: RedisDep,
        name: Annotated[
            str, Path(description="Name of your character.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
):
    character: Optional[CharacterResponseRedis] = await get_character_redis(redis, name)
    if not character:
        return error_response(498, "Character not found.")

    current_map: Optional[MapRedis] = await get_map_from_redis(redis, character.x, character.y)
    if not current_map or not current_map.content or not current_map.content.type == "monster":
        return error_response(598, "Monster not found on this map.")

    current_monster: Optional[MonsterRedis] = await get_monster_from_redis(redis, current_map.content.code)
    if not current_monster:
        return error_response(404, "Monster not found.")

    update_redis = CharacterUpdateRedis(redis, character)
    fight_response, fought = await update_redis.fight_monster(current_monster)

    if not fought or not await update_redis.update_redis():
        return error_response(486, "Redis Error.")

    return CharacterFightDataRedis(fight=fight_response, character=update_redis.changed_character)


@router.post(
    name="Action Fight Multiple",
    path="/my/{name}/action/fight/{quantity}",
    tags=["My characters"],
    response_model=CharacterFightsDataRedis,
    description="Start a fight against a quantity of monsters on the character's map.",
    response_description="The fights ended successfully.",
    responses={
        404: {"description": "Monster not found."},
        486: {"description": "Redis Error."},
        498: {"description": "Character not found."},
        598: {"description": "Monster not found on this map."}
    },
)
async def action_fight_multiple(
        redis: RedisDep,
        name: Annotated[
            str, Path(description="Name of your character.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
        quantity: Annotated[
            int, Path(description="Quantity of monsters to fight.", ge=1)
        ],
):
    character: Optional[CharacterResponseRedis] = await get_character_redis(redis, name)
    if not character:
        return error_response(498, "Character not found.")

    current_map: Optional[MapRedis] = await get_map_from_redis(redis, character.x, character.y)
    if not current_map or not current_map.content or not current_map.content.type == "monster":
        return error_response(598, "Monster not found on this map.")

    current_monster: Optional[MonsterRedis] = await get_monster_from_redis(redis, current_map.content.code)
    if not current_monster:
        return error_response(404, "Monster not found.")

    fight_responses: List[FightResponseRedis] = []
    update_redis = CharacterUpdateRedis(redis, character)
    while quantity > 0:

        fight_response, fought = await update_redis.fight_monster(current_monster)

        if not fought:
            return error_response(486, "Redis Error.")

        fight_responses.append(fight_response)

        quantity -= 1

    if not await update_redis.update_redis():
        return error_response(486, "Redis Error.")

    return CharacterFightsDataRedis(fights=fight_responses, character=update_redis.changed_character)


@router.post(
    name="Action Equip Item",
    path="/my/{name}/action/equip",
    tags=["My characters"],
    response_model=EquipRequestResponseRedis,
    description="Equip an item on your character.",
    response_description="The item has been successfully equipped on your character.",
    responses={
        404: {"description": "Item not found."},
        472: {"description": "Item is not valid for this slot."},
        478: {"description": "Missing item or insufficient quantity."},
        # 485: {"description": "This item is already equipped."},
        486: {"description": "Redis Error."},
        491: {"description": "Slot is not empty."},
        496: {"description": "Character level is insufficient."},
        498: {"description": "Character not found."},
    },
)
async def action_equip(
        redis: RedisDep,
        name: Annotated[
            str, Path(description="Name of your character.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
        slot: Annotated[
            ItemSlot, Body(description="Item slot.", example=ItemSlot.weapon.value)
        ],
        code: Annotated[
            str, Body(description="Item code.", regex=r'^[a-zA-Z0-9_-]+$', example='copper_dagger')
        ],
        quantity: Annotated[
            int, Body(description="Item quantity. Applicable to consumables only.", ge=1)
        ] = None,
):
    character: Optional[CharacterResponseRedis] = await get_character_redis(redis, name)
    if not character:
        return error_response(498, "Character not found.")

    slot_name = f"{slot.value}_slot"
    equip_slot_item_code = getattr(character, slot_name)

    current_item: Optional[ItemRedis] = await get_item_from_redis(redis, code)
    if not current_item:
        return error_response(404, "Item not found.")

    update_redis = CharacterUpdateRedis(redis=redis, character=character)

    if slot in [ItemSlot.consumable1, ItemSlot.consumable2]:  # consumable logic
        if character.level < current_item.level:
            return error_response(496, "Character level is insufficient.")

        if not await update_redis.item_fits_slot(current_item.type, slot):
            return error_response(472, "Item is not valid for this slot.")

        if not await update_redis.has_item_in_inventory(code=code):
            return error_response(478, "Missing item or insufficient quantity.")

        if current_item.code != equip_slot_item_code and equip_slot_item_code != "":
            return error_response(491, "Slot is not empty.")

        # slot_quantity = getattr(update_redis.changed_character, f"{slot_name}_quantity")
        # if (slot_quantity + quantity) > 50:
        #     return error_response(494, "Character can't equip more than 50 consumables in the same slot.")

        equipped = await update_redis.equip_consumable(current_item.code, slot, quantity)
        if not equipped or not await update_redis.update_redis():
            return error_response(486, "Redis Error.")

        return EquipRequestResponseRedis(slot=slot, item=current_item, character=update_redis.changed_character)

    if equip_slot_item_code != "":
        return error_response(491, "Slot is not empty.")

    if character.level < current_item.level:
        return error_response(496, "Character level is insufficient.")

    if not await update_redis.item_fits_slot(current_item.type, slot):
        return error_response(472, "Item is not valid for this slot.")

    if not await update_redis.has_item_in_inventory(code=code):
        return error_response(478, "Missing item or insufficient quantity.")

    equipped = await update_redis.equip_equipment(current_item, slot)
    if not equipped or not await update_redis.update_redis():
        return error_response(486, "Redis Error.")

    return EquipRequestResponseRedis(slot=slot, item=current_item, character=update_redis.changed_character)

@router.post(
    name="Action Unequip Item",
    path="/my/{name}/action/unequip",
    tags=["My characters"],
    response_model=EquipRequestResponseRedis,
    description="Unequip an item on your character.",
    response_description="The item has been successfully unequipped and added in his inventory.",
    responses={
        404: {"description": "Item not found."},
        478: {"description": "Insufficient quantity of the equipped item."},
        486: {"description": "Redis Error."},
        491: {"description": "Slot is empty."},
        498: {"description": "Character not found."},
    },
)
async def action_unequip(
        redis: RedisDep,
        name: Annotated[
            str, Path(description="Name of your character.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
        slot: Annotated[
            ItemSlot, Body(description="Item slot.", example=ItemSlot.weapon.value)
        ],
        quantity: Annotated[
            int, Body(description="Item quantity. Applicable to consumables only.", ge=1)
        ] = None,
):
    character: Optional[CharacterResponseRedis] = await get_character_redis(redis, name)
    if not character:
        return error_response(498, "Character not found.")

    slot_name = f"{slot.value}_slot"
    equip_slot_item_code = getattr(character, slot_name)
    if equip_slot_item_code == "":
        return error_response(491, "Slot is empty.")

    current_item: Optional[ItemRedis] = await get_item_from_redis(redis, equip_slot_item_code)
    if not current_item:
        return error_response(404, "Item not found.")

    update_redis = CharacterUpdateRedis(redis=redis, character=character)

    if slot in [ItemSlot.consumable1, ItemSlot.consumable2]:  # consumable logic
        equipped_quantity = getattr(update_redis.changed_character, f'{slot_name}_quantity')
        if equipped_quantity < quantity:
            return error_response(478, "Insufficient quantity of the equipped item.")

        unequipped = await update_redis.unequip_consumable(current_item.code, slot, quantity)
        if not unequipped or not await update_redis.update_redis():
            return error_response(486, "Redis Error.")

        return EquipRequestResponseRedis(slot=slot, item=current_item, character=update_redis.changed_character)

    unequipped = await update_redis.unequip_equipment(current_item, slot)
    if not unequipped or not await update_redis.update_redis():
        return error_response(486, "Redis Error.")

    return EquipRequestResponseRedis(slot=slot, item=current_item, character=update_redis.changed_character)

@router.post(
    name="Action Delete Item",
    path="/my/{name}/action/delete",
    tags=["My characters"],
    response_model=DeleteItemResponseRedis,
    description="Delete an item from your character's inventory.",
    response_description="Item successfully deleted from your character.",
    responses={
        478: {"description": "Missing item or insufficient quantity."},
        486: {"description": "Redis Error."},
        498: {"description": "Character not found."},
    },
)
async def action_delete(
        redis: RedisDep,
        name: Annotated[
            str, Path(description="Name of your character.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
        code: Annotated[
            str, Body(description="Item code.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
        quantity: Annotated[
            int, Body(description="Item quantity.", ge=1)
        ],
):
    character: Optional[CharacterResponseRedis] = await get_character_redis(redis, name)
    if not character:
        return error_response(498, "Character not found.")

    update_redis = CharacterUpdateRedis(redis=redis, character=character)

    inventory_slot: InventorySlotResponseRedis = await update_redis.find_item_slot(code)
    if not inventory_slot:
        return error_response(478, "Missing item or insufficient quantity.")

    if quantity > inventory_slot.quantity:
        return error_response(478, "Missing item or insufficient quantity.")
    item_response, removed = await update_redis.remove_item_action(code, quantity)
    if not removed or not await update_redis.update_redis():
        return error_response(486, "Redis Error.")

    return DeleteItemResponseRedis(item=item_response, character=update_redis.changed_character)


@router.post(
    name="Action Give Item",
    path="/my/{name}/action/give",
    tags=["My characters"],
    response_model=GivenItemResponseRedis,
    description="Give Item to another Character.",
    response_description="The item has been successfully Given to the recipient.",
    responses={
        478: {"description": "Insufficient quantity of the item in character inventory."},
        486: {"description": "Redis Error."},
        498: {"description": "Character not found."},
        598: {"description": "Recipient not found."},
    },
)
async def action_give(
        redis: RedisDep,
        name: Annotated[
            str, Path(description="Name of your character.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
        recipient: Annotated[
            str, Body(description="Recipient name.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
        code: Annotated[
            str, Body(description="Item code.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
        quantity: Annotated[
            int, Body(description="Item quantity.", ge=1)
        ],
):
    character: Optional[CharacterResponseRedis] = await get_character_redis(redis, name)
    if not character:
        return error_response(498, "Character not found.")

    recipient: Optional[CharacterResponseRedis] = await get_character_redis(redis, recipient)
    if not recipient:
        return error_response(598, "Recipient not found.")

    update_redis_character = CharacterUpdateRedis(redis=redis, character=character)
    update_redis_recipient = CharacterUpdateRedis(redis=redis, character=recipient)

    if not update_redis_character.changed_character.inventory:
        return error_response(478, "Missing item or insufficient quantity.")

    inventory_slot: Optional[InventorySlotResponseRedis] = await update_redis_character.find_item_slot(code)
    if not inventory_slot:
        return error_response(478, "Missing item or insufficient quantity.")

    if quantity > inventory_slot.quantity:
        return error_response(478, "Missing item or insufficient quantity.")

    item_response, given = await update_redis_character.give_item_to_recipient(code, quantity, update_redis_recipient)
    if not given or not await update_redis_character.update_redis() or not await update_redis_recipient.update_redis():
        return error_response(486, "Redis Error.")

    return GivenItemResponseRedis(item=item_response, character=update_redis_character.changed_character, recipient=update_redis_recipient.changed_character)