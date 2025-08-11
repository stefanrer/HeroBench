import random
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Path, Body
from sqlalchemy import false
from sqlmodel import Field, SQLModel, select

from app.db import SessionDep, CharacterLog, ActionType
from app.routers import error_response, error_info_response
from app.routers.characters import CharacterResponse, Character, InventorySlot, BlockedHitsResponse, ItemSlot
from app.routers.items import Item, ItemResponse
from app.routers.maps import MapResponse, Map, MapContentLink, MapContent, ContentType
from app.routers.monsters import Monster
from app.routers.resources import Resource

router = APIRouter()

class CharacterMovementDataResponse(SQLModel, ordered=True):
    destination: Annotated[MapResponse, Field(description="Destination details.")]
    character: Annotated[CharacterResponse, Field(description="Character details.")]


@router.post(
    name="Action Move",
    path="/my/{name}/action/move",
    tags=["My characters"],
    response_model=CharacterMovementDataResponse,
    description="Moves a character on the map using the map's X and Y position.",
    response_description="The character has moved successfully.",
    responses={
        404: {"description": "Map not found."},
        # 486: {"description": "An action is already in progress by your character."},
        490: {"description": "Character already at destination."},
        498: {"description": "Character not found."},
    },
)
async def action_move(
        session: SessionDep,
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
    character = session.exec(select(Character).filter_by(name=name)).first()
    if character:
        move_map = session.exec(select(Map).filter_by(x=x, y=y)).first()
        if move_map:
            if not (character.x == move_map.x and character.y == move_map.y):
                character.move_character(session, move_map.x, move_map.y)
                log = CharacterLog(character_name=character.name, action_type=ActionType.move,
                                   log=f"{character.name} moves to {move_map.x}, {move_map.y}.")
                session.add(log)
                session.commit()
                return CharacterMovementDataResponse(destination=move_map, character=character)
            else:
                return error_response(490, "Character already at destination.")
        else:
            return error_response(404, "Map not found.")
    else:
        return error_response(498, "Character not found.")


class EquipRequestResponse(SQLModel, ordered=True):
    slot: Annotated[ItemSlot, Field(description="Item slot.")]
    item: Annotated[ItemResponse, Field(description="Item details.")]
    character: Annotated[CharacterResponse, Field(description="Character details.")]


@router.post(
    name="Action Equip Item",
    path="/my/{name}/action/equip",
    tags=["My characters"],
    response_model=EquipRequestResponse,
    description="Equip an item on your character.",
    response_description="The item has been successfully equipped on your character.",
    responses={
        404: {"description": "Item not found."},
        472: {"description": "Item is not valid for this slot."},
        478: {"description": "Missing item or insufficient quantity."},
        # 485: {"description": "This item is already equipped."},
        # 486: {"description": "An action is already in progress by your character."},
        491: {"description": "Slot is not empty."},
        494: {"description": "Character can't equip more than 100 consumables in the same slot."},
        496: {"description": "Character level is insufficient."},
        498: {"description": "Character not found."},
    },
)
async def action_equip(
        session: SessionDep,
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
            int, Body(description="Item quantity. Applicable to consumables only.", ge=1, le=100)
        ] = None,
):
    character = session.exec(select(Character).filter_by(name=name)).first()
    if not character:
        return error_response(498, "Character not found.")

    slot_name = f"{slot.value}_slot"
    equip_slot_item_code = getattr(character, slot_name)

    if slot in [ItemSlot.consumable1, ItemSlot.consumable2]:  # consumable logic
        current_item = session.exec(select(Item).filter_by(code=code)).first()
        if not current_item:
            return error_response(404, "Item not found.")
        if character.level < current_item.level:
            return error_response(496, "Character level is insufficient.")

        if not character.item_fits_slot(current_item.type, slot.value):
            return error_response(472, "Item is not valid for this slot.")

        if not character.has_item_in_inventory(code=code):
            return error_response(478, "Missing item or insufficient quantity.")

        if current_item.code == equip_slot_item_code:
            slot_quantity = getattr(character, f"{slot_name}_quantity")
            if (slot_quantity + quantity) > 50:
                return error_response(494, "Character can't equip more than 50 consumables in the same slot.")
        character.equip_consumable(session, current_item.code, slot.value, quantity)
        log = CharacterLog(character_name=character.name, action_type=ActionType.equip_item,
                           log=f"The character {character.name} has equipped consumable {current_item.code} "
                               f"x{quantity} into slot {slot.value}.")
        session.add(log)
        session.commit()
        return EquipRequestResponse(slot=slot, item=current_item, character=character)

    if equip_slot_item_code != "":
        return error_response(491, "Slot is not empty.")

    current_item = session.exec(select(Item).filter_by(code=code)).first()
    if not current_item:
        return error_response(404, "Item not found.")
    if character.level < current_item.level:
        return error_response(496, "Character level is insufficient.")

    if not character.item_fits_slot(current_item.type, slot.value):
        return error_response(472, "Item is not valid for this slot.")

    if not character.has_item_in_inventory(code=code):
        return error_response(478, "Missing item or insufficient quantity.")

    character.equip_equipment(session, current_item, slot.value)
    log = CharacterLog(character_name=character.name, action_type=ActionType.equip_item,
                       log=f"The character {character.name} has equipped item {current_item.code} into slot {slot.value}.")
    session.add(log)
    session.commit()
    return EquipRequestResponse(slot=slot, item=current_item, character=character)


@router.post(
    name="Action Unequip Item",
    path="/my/{name}/action/unequip",
    tags=["My characters"],
    response_model=EquipRequestResponse,
    description="Unequip an item on your character.",
    response_description="The item has been successfully unequipped and added in his inventory.",
    responses={
        404: {"description": "Item not found."},
        478: {"description": "Insufficient quantity of the equipped item."},
        # 486: {"description": "An action is already in progress by your character."},
        491: {"description": "Slot is empty."},
        498: {"description": "Character not found."},
    },
)
async def action_unequip(
        session: SessionDep,
        name: Annotated[
            str, Path(description="Name of your character.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
        slot: Annotated[
            ItemSlot, Body(description="Item slot.", example=ItemSlot.weapon.value)
        ],
        quantity: Annotated[
            int, Body(description="Item quantity. Applicable to consumables only.", ge=1, le=100)
        ] = None,
):
    character = session.exec(select(Character).filter_by(name=name)).first()
    if not character:
        return error_response(498, "Character not found.")

    slot_name = f"{slot.value}_slot"
    equip_slot_item_code = getattr(character, slot_name)
    if equip_slot_item_code == "":
        return error_response(491, "Slot is empty.")
    current_item = session.exec(select(Item).filter_by(code=equip_slot_item_code)).first()
    if not current_item:
        return error_response(404, "Item not found.")
    if slot in [ItemSlot.consumable1, ItemSlot.consumable2]:  # consumable logic
        equiped_quantity = getattr(character, f'{slot_name}_quantity')
        if equiped_quantity < quantity:
            return error_response(478, "Insufficient quantity of the equipped item.")
        character.unequip_consumable(session, current_item.code, slot.value, quantity)
        log = CharacterLog(character_name=character.name, action_type=ActionType.unequip_item,
                           log=f"The character {character.name} has unequipped consumable {current_item.code} in "
                               f"quantity of {quantity} from slot {slot.value}.")
        session.add(log)
        session.commit()
        return EquipRequestResponse(slot=slot, item=current_item, character=character)
    character.unequip_equipment(session, current_item, slot.value)
    log = CharacterLog(character_name=character.name, action_type=ActionType.unequip_item,
                       log=f"The character {character.name} has unequipped item {current_item.code} from slot {slot.value}.")
    session.add(log)
    session.commit()
    return EquipRequestResponse(slot=slot, item=current_item, character=character)


class DropResponse(SQLModel, ordered=True):
    code: Annotated[str, Field(description="The code of the item.")]
    quantity: Annotated[int, Field(description="The quantity of the item.")]


class FightResult(str, Enum):
    win = "win"
    lose = "lose"


# TODO: Add gold drop if needed in future
class FightResponse(SQLModel, ordered=True):
    result: Annotated[FightResult, Field(description="The result of the fight.", default=FightResult.win)]
    xp: Annotated[int,  Field(description="The amount of xp gained by the fight.", default=0)]
    # gold: Annotated[int, Field(description="The amount of gold gained by the fight.")]
    drops: Annotated[list[DropResponse], Field(description="The items dropped by the fight.", default=[])]
    turns: Annotated[int, Field(description="Numbers of the turns of the combat.", default=0)]
    monster_blocked_hits: Annotated[BlockedHitsResponse, Field(description="The amount of blocked hits by the monster.", default=BlockedHitsResponse())]
    player_blocked_hits: Annotated[BlockedHitsResponse, Field(description="The amount of blocked hits by the player.", default=BlockedHitsResponse())]
    logs: Annotated[list[str], Field(description="The fight logs.", default=[])]


class CharacterFightData(SQLModel, ordered=True):
    fight: Annotated[FightResponse, Field(description="Fight details.")]
    character: Annotated[CharacterResponse, Field(description="Character details.")]


@router.post(
    name="Action Fight",
    path="/my/{name}/action/fight",
    tags=["My characters"],
    response_model=CharacterFightData,
    description="Start a fight against a monster on the character's map.",
    response_description="The fight ended successfully.",
    responses={
        # 486: {"description": "An action is already in progress by your character."},
        498: {"description": "Character not found."},
        598: {"description": "Monster not found on this map."}
    },
)
async def action_fight(
        session: SessionDep,
        name: Annotated[
            str, Path(description="Name of your character.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
):
    character = session.exec(select(Character).filter_by(name=name)).first()
    if character:
        current_map = session.exec(select(Map).filter_by(x=character.x, y=character.y)).first()
        if current_map and current_map.content and current_map.content.type == "monster":
            current_monster = session.exec(select(Monster).filter_by(code=current_map.content.code)).first()
            character, turn, logs, result, got_xp, monster_blocks, character_blocks = character.fight_monster(session, current_monster)
            fight = FightResponse(turns=turn, monster_blocked_hits=monster_blocks, player_blocked_hits=character_blocks,
                                  logs=logs, result=result)
            if result == "win":
                items = []
                drops = current_monster.drops
                for drop in drops:
                    # drop_chance = 1 / drop.rate
                    drop_chance = 1  # remove drop_chance for now
                    result = random.choices([None, 1], weights=[1 - drop_chance, drop_chance], k=1)[0]
                    if result:
                        quantity = random.randint(drop.min_quantity, drop.max_quantity)
                        character.add_item(session, drop.code, quantity)
                        items.append(DropResponse(code=drop.code, quantity=quantity))
                fight.drops = items
                fight.xp = got_xp
                log = CharacterLog(character_name=character.name, action_type=ActionType.fight,
                                   log=f"{character.name} win his fight against {current_monster.name}.")
            else:
                log = CharacterLog(character_name=character.name, action_type=ActionType.fight,
                                   log=f"{character.name} lost his fight against {current_monster.name}.")
            session.add(log)
            session.commit()
            return CharacterFightData(fight=fight, character=character)
        else:
            return error_response(598, "Monster not found on this map.")
    else:
        return error_response(498, "Character not found.")


class SkillInfoResponse(SQLModel, ordered=True):
    xp: Annotated[int, Field(description="The amount of xp gained.")]
    items: Annotated[list[DropResponse], Field(description="Items received.")]


class SkillDataResponse(SQLModel, ordered=True):
    details: Annotated[SkillInfoResponse, Field(description="Skill details.")]
    character: Annotated[CharacterResponse, Field(description="Character details.")]


@router.post(
    name="Action Gathering",
    path="/my/{name}/action/gathering",
    tags=["My characters"],
    response_model=SkillDataResponse,
    description="Harvest a resource on the character's map.",
    response_description="The resource has been successfully gathered.",
    responses={
        # 486: {"description": "An action is already in progress by your character."},
        493: {"description": "Not skill level required."},
        498: {"description": "Character not found."},
        598: {"description": "Resource not found on this map."}
    },
)
async def action_gathering(
        session: SessionDep,
        name: Annotated[
            str, Path(description="Name of your character.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
        quantity: Annotated[
            int, Body(description="Quantity of items to gather.", ge=1)
        ],
):
    character = session.exec(select(Character).filter_by(name=name)).first()
    if character:
        current_map = session.exec(select(Map).filter_by(x=character.x, y=character.y)).first()
        if current_map and current_map.content and current_map.content.type == "resource":
            current_resource = session.exec(select(Resource).filter_by(code=current_map.content.code)).first()
            needed_skill = current_resource.skill.value
            # print(needed_skill)
            character_skill_level = getattr(character, f'{needed_skill}_level')
            if character_skill_level >= current_resource.level:
                items = []
                drops = current_resource.drops
                total_got_xp = 0
                gather_cycles = quantity
                while gather_cycles > 0:
                    for drop in drops:
                        # drop_chance = 1 / drop.rate
                        drop_chance = 1 # TODO: remove drop_chance for now
                        result = random.choices([None, 1], weights=[1 - drop_chance, drop_chance], k=1)[0]
                        if result:
                            item_quantity = random.randint(drop.min_quantity, drop.max_quantity)
                            character.add_item(session, drop.code, item_quantity)
                            items.append(DropResponse(code=drop.code, quantity=item_quantity))
                    got_xp = character.increase_skill_xp(session, needed_skill, current_resource.level)
                    total_got_xp += got_xp
                    gather_cycles -= 1
                skill_info = SkillInfoResponse(xp=total_got_xp, items=items)
                drop_codes = [drop.code for drop in drops]
                drop_codes_str = ', '.join(drop_codes)
                log = CharacterLog(
                    character_name=character.name, 
                    action_type=ActionType.gather,
                    log=f"{character.name} gathered resources {drop_codes_str} with the skill {needed_skill} x{quantity} times."
                )
                session.add(log)
                session.commit()
                return SkillDataResponse(details=skill_info, character=character)
            else:
                return error_response(493, "Not skill level required.")
        else:
            return error_response(598, "Resource not found on this map.")
    else:
        return error_response(498, "Character not found.")


@router.post(
    name="Action Crafting",
    path="/my/{name}/action/crafting",
    tags=["My characters"],
    response_model=SkillDataResponse,
    description="Crafting an item. The character must be on a map with a workshop.",
    response_description="The item was successfully crafted.",
    responses={
        404: {"description": "Craft not found."},
        478: {"description": "Missing item or insufficient quantity."},
        # 486: {"description": "An action is already in progress by your character."},
        493: {"description": "Not skill level required."},
        498: {"description": "Character not found."},
        500: {"description": "Crafting Error."},
        598: {"description": "Workshop not found on this map."}
    },
)
async def action_crafting(
        session: SessionDep,
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
    character = session.exec(select(Character).filter_by(name=name)).first()
    if not character:  # Check character exist
        return error_response(498, "Character not found.")
    current_craft = session.exec(select(Item).filter_by(code=code)).first()
    if not current_craft or not current_craft.craft:  # Check if item has craft
        return error_response(404, "Craft not found.")

    # Can checks
    current_map = session.exec(select(Map).filter_by(x=character.x, y=character.y)).first()
    if not current_map or not current_map.content or current_map.content.type != "workshop" or current_map.content.code != current_craft.craft.skill:  # Check for workshop on current map
        correct_map = (session.exec( # select the correct workshop map tile
            select(Map)
            .join(MapContentLink, Map.id == MapContentLink.map_id)
            .join(MapContent, MapContentLink.map_content_id == MapContent.id)
            .where(MapContent.type == ContentType.workshop)
            .where(MapContent.code == current_craft.craft.skill)
        ).first())
    else:
        correct_map = current_map
        on_workshop_tile = True

    character_skill_level = getattr(character, f'{current_craft.craft.skill.value}_level')
    if character_skill_level < current_craft.craft.level:  # Check character passed skill level check
    #     return error_info_response(493, info)
        pass
    else:
        needed_skill_level = True

    needed_items_for_craft = current_craft.craft.items
    # if not character.inventory:   # check if character inventory empty or has enough items to craft
    #     return error_response(478, "Missing item or insufficient quantity.")
    if not character.has_all_items_for_craft(needed_items_for_craft, quantity):
    #     return error_info_response(478, info)
        pass
    else:
        enough_items_for_craft = True

    if on_workshop_tile and needed_skill_level and enough_items_for_craft:
        xp_got = character.craft_items(session, current_craft.craft, needed_items_for_craft, code, quantity)
        items = [DropResponse(code=code, quantity=quantity)]
        skill_info = SkillInfoResponse(xp=xp_got, items=items)
        log = CharacterLog(character_name=character.name, action_type=ActionType.craft,
                           log=f"{character.name} crafts {code} x{quantity}.")
        session.add(log)
        session.commit()
        return SkillDataResponse(details=skill_info, character=character)
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
            "skill": current_craft.craft.skill.value,
            "needed": current_craft.craft.level,
            "current": character_skill_level
        }
        error_missing_items = character.get_missing_items_for_craft(needed_items_for_craft, quantity)
        info = {
            "errors": errors,
            "workshop": error_workshop,
            "skill_level": error_skill_level,
            "missing_items": error_missing_items
        }
        log_text = f"{character.name} failed to craft {code} x{quantity}."
        if not on_workshop_tile:
            log_text += f" On wrong map tile: {error_workshop}."
        if not needed_skill_level:
            log_text += f" Needed skill level: {error_skill_level}."
        if not enough_items_for_craft:
            log_text += f" Missing items: {error_missing_items}."

        log = CharacterLog(character_name=character.name, action_type=ActionType.craft,
                           log=log_text)
        session.add(log)
        session.commit()
        return error_info_response(500, info)


class SimpleItemResponse(SQLModel, ordered=True):
    code: Annotated[str, Field(description="The code of the item.")]
    quantity: Annotated[int, Field(description="The quantity of the item.")]

class BuyResponse(SQLModel, ordered=True):
    item: Annotated[SimpleItemResponse, Field(description="Item purchased.")]
    character: Annotated[CharacterResponse, Field(description="Character state after purchase.")]


@router.post(
    name="Action Buy Item",
    path="/my/{name}/action/buy",
    tags=["My characters"],
    response_model=BuyResponse,
    description="Buy an item at a grand-exchange tile.",
    response_description="Item successfully purchased and added to inventory.",
    responses={
        404: {"description": "Item not found."},
        498: {"description": "Character not found."},
        598: {"description": "Grand-exchange not found on this map."},
    },
)
async def action_buy(
        session: SessionDep,
        name: Annotated[str, Path(description="Name of your character.", regex=r'^[a-zA-Z0-9_-]+$')],
        code: Annotated[str, Body(description="Item code.", regex=r'^[a-zA-Z0-9_-]+$')],
        quantity: Annotated[int, Body(description="Quantity to buy.", ge=1)] = 1,
):
    character = session.exec(select(Character).filter_by(name=name)).first()
    if not character:
        return error_response(498, "Character not found.")

    current_map = session.exec(select(Map).filter_by(x=character.x, y=character.y)).first()
    if not current_map or not current_map.content or current_map.content.type != "grand_exchange":
        return error_response(598, "Grand-exchange not found on this map.")

    item = session.exec(select(Item).filter_by(code=code)).first()
    if not item:
        return error_response(404, "Item not found.")

    character.add_item(session, item.code, quantity)

    log = CharacterLog(character_name=character.name,
                       action_type=ActionType.buy_item,
                       log=f"{character.name} purchased {item.code} x{quantity}.")
    session.add(log)
    session.commit()

    return BuyResponse(
        item=SimpleItemResponse(code=item.code, quantity=quantity),
        character=character
    )


class DeleteItemResponse(SQLModel, ordered=True):
    item: Annotated[SimpleItemResponse, Field(description="Item details.")]
    character: Annotated[CharacterResponse, Field(description="Character details.")]


@router.post(
    name="Action Delete Item",
    path="/my/{name}/action/delete",
    tags=["My characters"],
    response_model=DeleteItemResponse,
    description="Delete an item from your character's inventory.",
    response_description="Item successfully deleted from your character.",
    responses={
        478: {"description": "Missing item or insufficient quantity."},
        # 486: {"description": "An action is already in progress by your character."},
        498: {"description": "Character not found."},
    },
)
async def action_delete(
        session: SessionDep,
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
    character = session.exec(select(Character).filter_by(name=name)).first()
    if character:
        inventory_slot = session.exec(select(InventorySlot).where(InventorySlot.code == code)).first()
        if inventory_slot:
            if quantity <= inventory_slot.quantity:
                character.remove_item(session, code, quantity)
                log = CharacterLog(character_name=character.name, action_type=ActionType.delete_item,
                                   log=f"{character.name} deleted item {code} x{quantity}")
                session.add(log)
                session.commit()
                return DeleteItemResponse(item=SimpleItemResponse(code=code, quantity=quantity), character=character)
            else:
                return error_response(478, "Missing item or insufficient quantity.")
        else:
            return error_response(478, "Missing item or insufficient quantity.")
    else:
        return error_response(498, "Character not found.")


class GivenItemResponse(SQLModel, ordered=True):
    item: Annotated[SimpleItemResponse, Field(description="Item details.")]
    character: Annotated[CharacterResponse, Field(description="Character details.")]
    recipient: Annotated[CharacterResponse, Field(description="Recipient details.")]

@router.post(
    name="Action Give Item",
    path="/my/{name}/action/give",
    tags=["My characters"],
    response_model=GivenItemResponse,
    description="Give Item to another Character.",
    response_description="The item has been successfully Given to the recipient.",
    responses={
        478: {"description": "Insufficient quantity of the item in character inventory."},
        # 486: {"description": "An action is already in progress by your character."},
        498: {"description": "Character not found."},
        598: {"description": "Recipient not found."},
    },
)
async def action_give(
        session: SessionDep,
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
    character: Character = session.exec(select(Character).filter_by(name=name)).first()
    if character:
        recipient: Character = session.exec(select(Character).filter_by(name=recipient)).first()
        if recipient:
            if character.inventory:
                inventory_slot = session.exec(select(InventorySlot).where(InventorySlot.code == code)).first()
                if inventory_slot:
                    if quantity <= inventory_slot.quantity:
                        character.remove_item(session, code, quantity)
                        recipient.add_item(session, code, quantity)
                        log = CharacterLog(character_name=character.name, action_type=ActionType.give_item,
                                           log=f"{character.name} give item {code} x{quantity} to {recipient.name}")
                        session.add(log)
                        session.commit()
                        return GivenItemResponse(item=SimpleItemResponse(code=code, quantity=quantity),
                                                  character=character, recipient=recipient)
                    else:
                        return error_response(478, "Missing item or insufficient quantity.")
                else:
                    return error_response(478, "Missing item or insufficient quantity.")
            else:
                return error_response(478, "Missing item or insufficient quantity.")
        else:
            return error_response(598, "Recipient not found.")
    else:
        return error_response(498, "Character not found.")