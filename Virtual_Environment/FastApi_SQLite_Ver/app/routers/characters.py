import json
import math
import random
import re
from enum import Enum
from typing import Annotated, Dict

from fastapi import APIRouter, Depends, Path, Body
from sqlmodel import Field, Relationship, Session, SQLModel, select

from app.db import SessionDep, CharacterLog, ActionType
from app.routers import error_response
from app.routers.items import CraftItem, Craft
from app.routers.items import Item
from app.routers.monsters import Monster

BLOCKING_ENABLED: bool = False 

class BlockedHitsResponse(SQLModel, ordered=True):
    fire: Annotated[int, Field(description="The amount of fire hits blocked.", default=0)]
    earth: Annotated[int, Field(description="The amount of earth hits blocked.", default=0)]
    water: Annotated[int, Field(description="The amount of water hits blocked.", default=0)]
    air: Annotated[int, Field(description="The amount of air hits blocked.", default=0)]
    total: Annotated[int, Field(description="The amount of total hits blocked.", default=0)]


class ItemSlot(str, Enum):
    weapon = "weapon"
    shield = "shield"
    helmet = "helmet"
    body_armor = "body_armor"
    leg_armor = "leg_armor"
    boots = "boots"
    ring1 = "ring1"
    ring2 = "ring2"
    amulet = "amulet"
    artifact1 = "artifact1"
    artifact2 = "artifact2"
    artifact3 = "artifact3"
    consumable1 = "consumable1"
    consumable2 = "consumable2"


class Skin(str, Enum):
    men1 = "men1"
    men2 = "men2"
    men3 = "men3"
    women1 = "women1"
    women2 = "women2"
    women3 = "women3"


with open("app/Data/items.json") as j_file:
    check_items = [item['code'] for item in json.load(j_file)]
# print(check_items)

router = APIRouter()

def calculate_skill_max_xp(level: int) -> int:
    return 150 + (level - 1) * 10

class CharacterInventoryLink(SQLModel, table=True):
    character_id: int | None = Field(default=None, foreign_key="character.id", primary_key=True)
    inventory_id: int | None = Field(default=None, foreign_key="inventoryslot.id", primary_key=True)


class InventorySlot(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    slot: int = Field(description="Inventory slot identifier.")
    code: str = Field(description="required Item code.", index=True)
    quantity: int = Field(description="required Quantity in the slot.", ge=1)

    character: "Character" = Relationship(back_populates="inventory", link_model=CharacterInventoryLink)

class Character(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(description="Name of the character.", max_length=12, min_length=3, regex=r'^[a-zA-Z0-9_-]+$',
                      unique=True, default="string", index=True)
    skin: Skin = Field(description="Character skin code.", default=Skin.men1)
    level: int = Field(description="Combat level.", default=1, ge=1)
    xp: int = Field(description="The current xp level of the combat level.", default=0, ge=0)
    max_xp: int = Field(description="XP required to level up the character.", default=150)

    def increase_battle_xp(self, session: Session, monster_level: int, modifier: int = 1):
        action_xp = self.skill_xp_gain(monster_level, self.level, modifier)
        self.xp, self.level, self.max_xp, self.hp = self.level_up_character(self.xp + action_xp, self.level, self.max_xp, self.hp)
        session.add(self)
        session.commit()
        return action_xp

    @staticmethod
    def level_up_character(xp, level, max_xp, hp):
        def calculate_skill_max_xp():
            base_xp = 100
            xp_increase = int(base_xp * math.log2(level) * ((level // 10) + 1))
            xp_increase = (xp_increase // 50) * 50 + 150  # Round up
            return xp_increase

        while level < 40 and xp >= max_xp:
            xp -= max_xp
            level += 1
            hp += 5
            if level <= 40:
                max_xp = calculate_skill_max_xp()  # logic to increase XP requirement
        return xp, level, max_xp, hp
    # achievements_points: int = Field(description="Achievements points.", default=0)
    # gold: int = Field(description="The numbers of gold on this character.", default=0)
    # speed: int = Field(description="*Not available, on the roadmap. Character movement speed.", default=0)

    mining_level: int = Field(description="Mining level.", default=1, ge=1)
    mining_xp: int = Field(description="The current xp level of the Mining skill.", default=0, ge=0)
    mining_max_xp: int = Field(description="Mining XP required to level up the skill.", default=150, ge=0)

    woodcutting_level: int = Field(description="Woodcutting level.", default=1, ge=1)
    woodcutting_xp: int = Field(description="The current xp level of the Woodcutting skill.", default=0, ge=0)
    woodcutting_max_xp: int = Field(description="Woodcutting XP required to level up the skill.", default=150, ge=0)

    fishing_level: int = Field(description="Fishing level.", default=1, ge=1)
    fishing_xp: int = Field(description="The current xp level of the Fishing skill.", default=0, ge=0)
    fishing_max_xp: int = Field(description="Fishing XP required to level up the skill.", default=150, ge=0)

    weaponcrafting_level: int = Field(description="Weaponcrafting level.", default=1, ge=1)
    weaponcrafting_xp: int = Field(description="The current xp level of the Weaponcrafting skill.", default=0, ge=0)
    weaponcrafting_max_xp: int = Field(description="Weaponcrafting XP required to level up the skill.", default=150, ge=0)

    gearcrafting_level: int = Field(description="Gearcrafting level.", default=1, ge=1)
    gearcrafting_xp: int = Field(description="The current xp level of the Gearcrafting skill.", default=0, ge=0)
    gearcrafting_max_xp: int = Field(description="Gearcrafting XP required to level up the skill.", default=150, ge=0)

    jewelrycrafting_level: int = Field(description="Jewelrycrafting level.", default=1, ge=1)
    jewelrycrafting_xp: int = Field(description="The current xp level of the Jewelrycrafting skill.", default=0, ge=0)
    jewelrycrafting_max_xp: int = Field(description="Jewelrycrafting XP required to level up the skill.", default=150, ge=0)

    cooking_level: int = Field(description="Cooking level.", default=1, ge=1)
    cooking_xp: int = Field(description="The current xp level of the Cooking skill.", default=0, ge=0)
    cooking_max_xp: int = Field(description="Cooking XP required to level up the skill.", default=150, ge=0)

    @staticmethod
    def skill_xp_gain(action_level: int, character_skill_level: int, modifier: int = 1) -> int:
        if character_skill_level > action_level + 10:
            return 0
        return 50 * modifier

    def increase_skill_xp(self, session: Session, skill: str, action_level: int, modifier: int = 1) -> int:
        current_xp = getattr(self, f"{skill}_xp")
        current_level = getattr(self, f"{skill}_level")
        xp_gain = self.skill_xp_gain(action_level, current_level, modifier)
        new_xp = current_xp + xp_gain
        new_xp, new_lv, new_thr = self.level_up_skill(new_xp, current_level, getattr(self, f"{skill}_max_xp"))
        setattr(self, f"{skill}_xp",      new_xp)
        setattr(self, f"{skill}_level",   new_lv)
        setattr(self, f"{skill}_max_xp",  new_thr)
        session.add(self)
        session.commit()
        return xp_gain

    @staticmethod
    def level_up_skill(xp: int, level: int, threshold: int) -> tuple[int,int,int]:
        while level < 40 and xp >= threshold:
            xp -= threshold
            level += 1
            threshold = calculate_skill_max_xp(level)
        return xp, level, threshold

    hp: int = Field(description="Character HP.", default=120)

    # haste: int = Field(description="*Character Haste. Increase speed attack (reduce fight cooldown)", default=0)
    # critical_strike: int = Field(description="*Not available, on the roadmap. Character Critical Strike. Critical strikes increase the attack's damage.")
    # stamina: int = Field(description="*Not available, on the roadmap. Regenerates life at the start of each turn.")

    attack_fire: int = Field(description="Fire attack.", default=0)
    attack_earth: int = Field(description="Earth attack.", default=0)
    attack_water: int = Field(description="Water attack.", default=0)
    attack_air: int = Field(description="Air attack.", default=0)

    dmg_fire: int = Field(description="% Fire damage.", default=0)
    dmg_earth: int = Field(description="% Earth damage.", default=0)
    dmg_water: int = Field(description="% Water damage.", default=0)
    dmg_air: int = Field(description="% Air damage.", default=0)

    res_fire: int = Field(description="% Fire resistance.", default=0)
    res_earth: int = Field(description="% Earth resistance.", default=0)
    res_water: int = Field(description="% Water resistance.", default=0)
    res_air: int = Field(description="% Air resistance.", default=0)

    def fight_monster(self, session: Session, monster: Monster):
        def init_consumables():
            boost_stats = {
                'hp': 0,
                'dmg_fire': 0,
                'dmg_earth': 0,
                'dmg_water': 0,
                'dmg_air': 0,
                # etc
            }
            consumables = []
            for slot in ['consumable1_slot', 'consumable2_slot']:
                consumable_code = getattr(self, slot)
                consumable_quantity = getattr(self, f'{slot}_quantity')
                if consumable_code:
                    consumable_item: Item = session.exec(select(Item).filter_by(code=consumable_code)).first()
                    if consumable_item:
                        if consumable_item.subtype == 'restore':
                            consumables.append({"slot": slot, "name": consumable_item.name,
                                                "quantity": consumable_quantity, "value": consumable_item.effects[0].value})
                        elif consumable_item.subtype == 'boost':
                            for effect in consumable_item.effects:
                                if effect.name.startswith("boost_"):
                                    boost_stats[effect.name.split('boost_')[1]] += effect.value
                                    consumable_quantity -= 1
                                    if consumable_quantity <= 0:  # set to 0 if quantity reaches the 0
                                        setattr(self, slot, "")
                                        setattr(self, f'{slot}_quantity', 0)
                        else:
                            print(consumable_item, " - Not Implemented")


            return boost_stats, consumables

        def initialize_elements(boost_stats):
            def calculate_character_damage(element: str) -> float:
                base_attack = getattr(self, f'attack_{element}')
                dmg = getattr(self, f'dmg_{element}')
                dmg_boost = base_attack * ((dmg + boost_stats[f'dmg_{element}']) * 0.01)
                monster_res = getattr(monster, f'res_{element}')
                res_reduction = base_attack * (monster_res * 0.01)
                return base_attack + dmg_boost - res_reduction

            def calculate_monster_damage(element: str) -> float:
                base_attack = getattr(monster, f'attack_{element}')
                character_res = getattr(self, f'res_{element}')
                res_reduction = base_attack * (character_res * 0.01)
                return base_attack - res_reduction

            def calculate_character_block_chance(element: str) -> float:
                res_value = getattr(self, f'res_{element}')
                return (res_value / 10) / 100 if res_value > 0 else 0

            def calculate_monster_block_chance(element: str) -> float:
                res_value = getattr(monster, f'res_{element}')
                return (res_value / 10) / 100 if res_value > 0 else 0

            elements = ["fire", "earth", "water", "air"]
            character_elements = {'damage': {}, 'block_chance': {}}
            monster_elements = {'damage': {}, 'block_chance': {}}

            for element in elements:
                if getattr(self, f'attack_{element}') > 0:
                    character_elements['damage'][element] = calculate_character_damage(element)
                if getattr(self, f'res_{element}') > 0:
                    character_elements['block_chance'][element] = calculate_character_block_chance(element)
                if getattr(monster, f'attack_{element}') > 0:
                    monster_elements['damage'][element] = calculate_monster_damage(element)
                if getattr(monster, f'res_{element}') > 0:
                    monster_elements['block_chance'][element] = calculate_monster_block_chance(element)

            return character_elements, monster_elements

        def fight_cycle(consumables: list[dict], character_hp: int, monster_hp: int, logs: list[str], character_blocked_hits: BlockedHitsResponse,
                              monster_blocked_hits: BlockedHitsResponse, character_elements: dict, monster_elements: dict):
            def use_restore_consumables(turn: int, character_hp: int, boost_hp: int):
                # Use restore items if HP is <= 50% each turn
                if character_hp < (self.hp + boost_hp) / 2:
                    for consumable in consumables:
                        if consumable["quantity"] > 0:
                            character_hp += consumable["value"]
                            consumable["quantity"] -= 1
                            logs.append(f"Turn {turn}: Character used {consumable['name']} and restored {consumable['value']} hp.")
                return character_hp

            def commit_consumables():
                for consumable in consumables:
                    quantity = consumable["quantity"]
                    setattr(self, f'{consumable["slot"]}_quantity', quantity)
                    if quantity <= 0:
                        setattr(self, f'{consumable["slot"]}', "")
                    session.add(self)
                    session.commit()

            def character_turn(turn: int, monster_hp: int):
                character_elemental_damage = character_elements["damage"]
                if character_elemental_damage:
                    monster_elemental_block_chance = monster_elements["block_chance"]
                    # print(monster_elemental_block_chance)
                    for element in character_elemental_damage:
                        if BLOCKING_ENABLED and element in monster_elemental_block_chance:
                            block = random.choices([None, 1], weights=[1 - monster_elemental_block_chance[element],
                                                                       monster_elemental_block_chance[element]], k=1)[0]
                            if block:
                                blocked_hits = getattr(monster_blocked_hits, element)
                                setattr(monster_blocked_hits, element, blocked_hits + 1)
                                monster_blocked_hits.total += 1
                                logs.append(f"Turn {turn}: The monster blocked {element} attack.")
                                continue

                        damage = character_elemental_damage[element]
                        monster_hp -= damage
                        logs.append(f"Turn {turn}: The character used {element} attack and dealt {damage} damage.")
                else:
                    logs.append(f"Turn {turn}: The character dealt {0} damage.")
                return monster_hp

            def monster_turn(turn: int, character_hp: int):
                monster_elemental_damage = monster_elements["damage"]
                if monster_elemental_damage:
                    character_elemental_block_chance = character_elements["block_chance"]
                    for element in monster_elemental_damage:
                        if BLOCKING_ENABLED and element in character_elemental_block_chance:
                            block = random.choices([None, 1], weights=[1 - character_elemental_block_chance[element],
                                                                       character_elemental_block_chance[element]], k=1)[0]
                            if block:
                                blocked_hits = getattr(character_blocked_hits, element)
                                setattr(character_blocked_hits, element, blocked_hits + 1)
                                character_blocked_hits.total += 1
                                logs.append(f"Turn {turn}: The character blocked {element} attack.")
                                continue

                        damage = monster_elemental_damage[element]
                        character_hp -= damage
                        logs.append(f"Turn {turn}: The monster used {element} attack and dealt {damage} damage.")
                else:
                    logs.append(f"Turn {turn}: The monster dealt {0} damage.")
                return character_hp

            turn = 1
            while turn < 50:  # Limit to 100 turns(50 since 50 for player and 50 for monster)
                character_hp = use_restore_consumables(turn, character_hp, boost_stats["hp"])  # Use restore items if HP <= 50%
                monster_hp = character_turn(turn, monster_hp)

                if monster_hp <= 0:
                    logs.append(f"Fight result: win. (Character HP: {self.hp}, Monster HP: {0})")
                    got_xp = self.increase_battle_xp(session, monster.level)
                    commit_consumables()
                    return self, turn, logs, "win", got_xp, monster_blocked_hits, character_blocked_hits

                character_hp = monster_turn(turn, character_hp)
                if character_hp <= 0:
                    logs.append(f"Fight result: lose. (Character HP: {0}, Monster HP: {monster.hp})")
                    self.move_character(session, 0, 0)
                    commit_consumables()
                    return self, turn, logs, "lose", 0, monster_blocked_hits, character_blocked_hits

                turn += 1

            commit_consumables()
            logs.append(f"Fight result: lose. (Character HP: {self.hp}, Monster HP: {monster.hp})")
            return self, turn, logs, "lose", 0, monster_blocked_hits, character_blocked_hits

        boost_stats, consumables = init_consumables()  # Apply boosts before the fight
        character_hp = self.hp + boost_stats["hp"]

        monster_hp = monster.hp
        logs = []
        monster_blocked_hits = BlockedHitsResponse()
        character_blocked_hits = BlockedHitsResponse()

        character_elements, monster_elements = initialize_elements(boost_stats)
        return fight_cycle(consumables, character_hp, monster_hp, logs, character_blocked_hits, monster_blocked_hits, character_elements, monster_elements)

    x: int = Field(description="Character x coordinate.", default=0)
    y: int = Field(description="Character y coordinate.", default=0)

    def move_character(self, session: Session, x: int, y: int) -> "Character":
        self.x, self.y = x, y
        session.add(self)
        session.commit()
        return self

    # cooldown: int = Field(description="Cooldown in seconds.")
    # cooldown_expiration: datetime | None = Field(description="Datetime Cooldown expiration.")

    weapon_slot: str = Field(description="Weapon slot.", default="")
    shield_slot: str = Field(description="Shield slot.", default="")
    helmet_slot: str = Field(description="Helmet slot.", default="")
    body_armor_slot: str = Field(description="Body armor slot.", default="")
    leg_armor_slot: str = Field(description="Leg armor slot.", default="")
    boots_slot: str = Field(description="Boots slot.", default="")
    ring1_slot: str = Field(description="Ring 1 slot.", default="")
    ring2_slot: str = Field(description="Ring 2 slot.", default="")
    amulet_slot: str = Field(description="Amulet slot.", default="")
    artifact1_slot: str = Field(description="Artifact 1 slot.", default="")
    artifact2_slot: str = Field(description="Artifact 2 slot.", default="")
    artifact3_slot: str = Field(description="Artifact 3 slot.", default="")

    def equip_equipment(self, session: Session, item: Item, slot_type: str, quantity: int = 1):
        slot_name = f"{slot_type}_slot"
        self.remove_item(session, item.code, quantity)
        setattr(self, slot_name, item.code)
        self.apply_equipment_stats(item)
        session.add(self)
        session.commit()

    def unequip_equipment(self, session: Session, item: Item, slot_type: str, quantity: int = 1):
        slot_name = f"{slot_type}_slot"
        self.add_item(session, item.code, quantity)
        setattr(self, slot_name, "")
        self.unapply_equipment_stats(item)
        session.add(self)
        session.commit()

    def apply_equipment_stats(self, item: Item):
        for effect in item.effects:
            try:
                current = getattr(self, effect.name)
                setattr(self, effect.name, current + effect.value)
            except:
                print(f"Effect[{effect.name}] Not Implemented")

    def unapply_equipment_stats(self, item: Item):
        for effect in item.effects:
            try:
                current = getattr(self, effect.name)
                setattr(self, effect.name, current - effect.value)
            except:
                print(f"Effect[{effect.name}] Not Implemented")

    consumable1_slot: str = Field(description="Consumable 1 slot.", default="")
    consumable1_slot_quantity: int = Field(description="Consumable 1 quantity.", ge=0, default=0)
    consumable2_slot: str = Field(description="Consumable 2 slot.", default="")
    consumable2_slot_quantity: int = Field(description="Consumable 2 quantity.", ge=0, default=0)

    def equip_consumable(self, session: Session, item_code: str, slot_type: str, quantity: int):
        slot_name = f"{slot_type}_slot"
        self.remove_item(session, item_code, quantity)
        setattr(self, slot_name, item_code)
        existing_quantity = getattr(self, f'{slot_name}_quantity')
        setattr(self, f'{slot_name}_quantity', existing_quantity + quantity)
        session.add(self)
        session.commit()

    def unequip_consumable(self, session: Session, item_code: str, slot_type: str, quantity: int):
        slot_name = f"{slot_type}_slot"
        existing_quantity = getattr(self, f'{slot_name}_quantity')
        setattr(self, f'{slot_name}_quantity', existing_quantity - quantity)
        if existing_quantity - quantity == 0:
            setattr(self, slot_name, "")
        self.add_item(session, item_code, quantity)
        session.add(self)
        session.commit()

    @staticmethod
    def item_fits_slot(item_type, slot_name) -> bool:
        def slot_name_without_numerals() -> str:
            return re.sub(r'\d+', '', slot_name)
        return item_type == slot_name_without_numerals()

    # task: str = Field(description="Task in progress.")
    # task_type: str = Field(description="Task type.")
    # task_progress: int = Field(description="Task progression.")
    # task_total: int = Field(description="Task total objective.")

    # inventory_max_items: int = Field(description="Inventory max items.")
    inventory: list[InventorySlot] | None = Relationship(back_populates="character", link_model=CharacterInventoryLink)

    def has_item_in_inventory(self, code: str) -> bool:
        inventory_item = next((slot for slot in self.inventory if slot.code == code), None)
        if not inventory_item or inventory_item.quantity < 1:
            return False
        return True

    def has_all_items_for_craft(self, needed_items_for_craft: list[CraftItem], craft_quantity: int = 1) -> bool:
        for item in needed_items_for_craft:
            inventory_item = next((slot for slot in self.inventory if slot.code == item.code),
                                  None)
            if not inventory_item or inventory_item.quantity < (item.quantity * craft_quantity):
                return False
        return True

    def get_missing_items_for_craft(self, needed_items_for_craft: list[CraftItem], craft_quantity: int = 1):
        missing_items_for_craft = []
        for item in needed_items_for_craft:
            inventory_item = next((slot for slot in self.inventory if slot.code == item.code),
                                  None)
            if not inventory_item: # Append full quantity if item not in inventory
                missing_items_for_craft.append({"code": item.code, "needed": (item.quantity * craft_quantity), "got": 0})
            elif inventory_item.quantity < (item.quantity * craft_quantity): # append missing quantity
                missing_items_for_craft.append({"code": item.code, "needed": (item.quantity * craft_quantity), "got": (item.quantity * craft_quantity) - inventory_item.quantity})
        return missing_items_for_craft

    def craft_items(self, session: Session, craft: Craft, needed_items_for_craft: list[CraftItem], craft_code: str, craft_quantity: int = 1) -> int:
        for item in needed_items_for_craft:
            self.remove_item(session, item.code, item.quantity * craft_quantity)
        self.add_item(session, craft_code, craft_quantity)
        got_xp = 0
        for _ in range(craft_quantity):
            got_xp += self.increase_skill_xp(session, craft.skill.value, craft.level, 3)
        return got_xp

    def sort_inventory(self, session: Session) -> None:
        slots = session.exec(
            select(InventorySlot).where(InventorySlot.character == self).order_by(InventorySlot.slot)).all()
        for index, slot in enumerate(slots):
            slot.slot = index
        session.commit()

    def add_item(self, session: Session, item_code: str, quantity: int) -> None:
        # print(f"Adding item {item_code}")
        # Find existing slot with the same item code
        slot = session.exec(
            select(InventorySlot).where(InventorySlot.character == self, InventorySlot.code == item_code)
        ).first()
        if slot:
            # Update quantity if the item already exists
            slot.quantity += quantity
        else:
            # Find the next available slot number
            slot_number = len(self.inventory) if self.inventory else 0
            # Create a new slot with the item
            slot = InventorySlot(slot=slot_number, code=item_code, quantity=quantity)
            self.inventory.append(slot)
            session.add(slot)
            self.sort_inventory(session)
        session.commit()

    def remove_item(self, session: Session, item_code: str, quantity: int) -> None:
        # print(f"Removing item {item_code}")
        # Find existing slot with the same item code
        slot = session.exec(
            select(InventorySlot).where(InventorySlot.character == self, InventorySlot.code == item_code)).first()
        if slot:
            # Decrease quantity or remove the slot if quantity reaches 0
            slot.quantity -= quantity
            if slot.quantity <= 0:
                self.inventory.remove(slot)
                session.delete(slot)
                self.sort_inventory(session)
            session.commit()


class InventorySlotResponse(SQLModel, ordered=True):
    slot: Annotated[int, Field(description="Inventory slot identifier.")]
    code: Annotated[str, Field(description="required Item code.")]
    quantity: Annotated[int, Field(description="required Quantity in the slot.")]


class CharacterResponse(SQLModel, ordered=True):
    name: Annotated[str, Field(description="Name of the character.")]
    skin: Annotated[Skin, Field(description="Character skin code.")]
    level: Annotated[int, Field(description="Combat level.")]
    xp: Annotated[int, Field(description="The current xp level of the combat level.")]
    max_xp: Annotated[int, Field(description="XP required to level up the character.")]

    mining_level: Annotated[int, Field(description="Mining level.")]
    mining_xp: Annotated[int, Field(description="The current xp level of the Mining skill.")]
    mining_max_xp: Annotated[int, Field(description="Mining XP required to level up the skill.")]

    woodcutting_level: Annotated[int, Field(description="Woodcutting level.")]
    woodcutting_xp: Annotated[int, Field(description="The current xp level of the Woodcutting skill.")]
    woodcutting_max_xp: Annotated[int, Field(description="Woodcutting XP required to level up the skill.")]

    fishing_level: Annotated[int, Field(description="Fishing level.")]
    fishing_xp: Annotated[int, Field(description="The current xp level of the Fishing skill.")]
    fishing_max_xp: Annotated[int, Field(description="Fishing XP required to level up the skill.")]

    weaponcrafting_level: Annotated[int, Field(description="Weaponcrafting level.")]
    weaponcrafting_xp: Annotated[int, Field(description="The current xp level of the Weaponcrafting skill.")]
    weaponcrafting_max_xp: Annotated[int, Field(description="Weaponcrafting XP required to level up the skill.")]

    gearcrafting_level: Annotated[int, Field(description="Gearcrafting level.")]
    gearcrafting_xp: Annotated[int, Field(description="The current xp level of the Gearcrafting skill.")]
    gearcrafting_max_xp: Annotated[int, Field(description="Gearcrafting XP required to level up the skill.")]

    jewelrycrafting_level: Annotated[int, Field(description="Jewelrycrafting level.")]
    jewelrycrafting_xp: Annotated[int, Field(description="The current xp level of the Jewelrycrafting skill.")]
    jewelrycrafting_max_xp: Annotated[int, Field(description="Jewelrycrafting XP required to level up the skill.")]

    cooking_level: Annotated[int, Field(description="Cooking level.")]
    cooking_xp: Annotated[int, Field(description="The current xp level of the Cooking skill.")]
    cooking_max_xp: Annotated[int, Field(description="Cooking XP required to level up the skill.")]

    hp: Annotated[int, Field(description="Character HP.")]

    attack_fire: Annotated[int, Field(description="Fire attack.")]
    attack_earth: Annotated[int, Field(description="Earth attack.")]
    attack_water: Annotated[int, Field(description="Water attack.")]
    attack_air: Annotated[int, Field(description="Air attack.")]

    dmg_fire: Annotated[int, Field(description="% Fire damage.")]
    dmg_earth: Annotated[int, Field(description="% Earth damage.")]
    dmg_water: Annotated[int, Field(description="% Water damage.")]
    dmg_air: Annotated[int, Field(description="% Air damage.")]

    res_fire: Annotated[int, Field(description="% Fire resistance.")]
    res_earth: Annotated[int, Field(description="% Earth resistance.")]
    res_water: Annotated[int, Field(description="% Water resistance.")]
    res_air: Annotated[int, Field(description="% Air resistance.")]

    x: Annotated[int, Field(description="Character x coordinate.")]
    y: Annotated[int, Field(description="Character y coordinate.")]

    weapon_slot: Annotated[str, Field(description="Weapon slot.")]
    shield_slot: Annotated[str, Field(description="Shield slot.")]
    helmet_slot: Annotated[str, Field(description="Helmet slot.")]
    body_armor_slot: Annotated[str, Field(description="Body armor slot.")]
    leg_armor_slot: Annotated[str, Field(description="Leg armor slot.")]
    boots_slot: Annotated[str, Field(description="Boots slot.")]
    ring1_slot: Annotated[str, Field(description="Ring 1 slot.")]
    ring2_slot: Annotated[str, Field(description="Ring 2 slot.")]
    amulet_slot: Annotated[str, Field(description="Amulet slot.")]
    artifact1_slot: Annotated[str, Field(description="Artifact 1 slot.")]
    artifact2_slot: Annotated[str, Field(description="Artifact 2 slot.")]
    artifact3_slot: Annotated[str, Field(description="Artifact 3 slot.")]

    consumable1_slot: Annotated[str, Field(description="Consumable 1 slot.")]
    consumable1_slot_quantity: Annotated[int, Field(description="Consumable 1 quantity.")]
    consumable2_slot: Annotated[str, Field(description="Consumable 2 slot.")]
    consumable2_slot_quantity: Annotated[int, Field(description="Consumable 2 quantity.")]

    inventory: Annotated[list[InventorySlotResponse], Field(description="List of inventory slots.")]


def load_base_character(session: Session, amount: int):
    for n in range(1, amount + 1):
        name = f"character_{n}"
        skin = random.choice(list(Skin))
        new_character = Character(name=name, skin=skin, weapon_slot="wooden_stick", attack_earth=4)
        session.add(new_character)
        session.commit()
        session.refresh(new_character)
    return True


@router.post(
    name="Create Character",
    path="/characters/create",
    tags=["Characters"],
    response_model=CharacterResponse,
    response_description="Successfully created character.",
    description="Create new character",
    responses={
        # 404: {"description": "Can't create new character."},
        494: {"description": "Name already used."},
    }
)
async def create_character(
        session: SessionDep,
        name: Annotated[
            str, Body(description="Your desired character name.", min_length=3, max_length=12, regex=r'^[a-zA-Z0-9_-]+$')
        ],
        skin: Annotated[
            Skin, Body(description="Your desired skin.")
        ],
):
    if session.exec(select(Character).filter_by(name=name)).first():
        return error_response(494, "Name already used.")
    else:
        new_character = Character(name=name, skin=skin, weapon_slot="wooden_stick", attack_earth=4)
        session.add(new_character)
        log = CharacterLog(character_name=new_character.name, action_type=ActionType.create_character,
                           log=f"Successfully created character - {new_character.name}.")
        session.add(log)
        session.commit()
        # session.refresh(new_character)
        return new_character

@router.post(
    name="Create Custom Character",
    path="/characters/create_custom",
    tags=["Characters"],
    response_model=CharacterResponse,
    response_description="Successfully created custom character.",
    description="Create new custom character",
    responses={
        494: {"description": "Name already used."},
        498: {"description": "Wrong Json."},
    }
)
async def create_custom_character(
        session: SessionDep,
        name: Annotated[
            str, Body(description="Your desired character name.", min_length=3, max_length=12, regex=r'^[a-zA-Z0-9_-]+$')
        ],
        skin: Annotated[
            Skin, Body(description="Your desired skin.")
        ],
        char_data: Annotated[
            Dict, Body(description="Your desired character data.")
        ]
):
    # Check if the character name is already taken
    if session.exec(select(Character).filter_by(name=name)).first():
        return error_response(494, "Name already used.")

    try:
        # Create the new character using the data from the dictionary
        new_character = Character(
            name=name,
            skin=skin,
            **{key: value for key, value in char_data.items() if key != 'inventory'}
        )

        if 'inventory' in char_data:
            for item in char_data['inventory']:
                if item['code'] in check_items and item['quantity'] > 0:
                    new_character.add_item(session, item['code'], item['quantity'])
                else:
                    print(f"Item[{item['code']}] Not Implemented or quantity less or 0")

        # Add the new character to the session
        session.add(new_character)

        # Log the creation of the character
        log = CharacterLog(
            character_name=new_character.name,
            action_type=ActionType.create_custom_character,
            log=f"Successfully created custom character - {new_character.name}."
        )
        session.add(log)

        # Commit the session to save the changes
        session.commit()

        # Return the newly created character
        return new_character
    except:
        return error_response(498, "Wrong Json.")


@router.post(
    name="Delete Character",
    path="/characters/delete",
    tags=["Characters"],
    response_model=CharacterResponse,
    response_description="Successfully deleted character.",
    description="Delete character",
    responses={
        # 404: {"description": "Can't delete character."},
        498: {"description": "Character not found."}
    }
)
async def delete_character(
        session: SessionDep,
        name: Annotated[
            str, Body(description="Character name.", min_length=3, max_length=12, regex=r'^[a-zA-Z0-9_-]+$')
        ],
):
    character = session.exec(select(Character).filter_by(name=name)).first()
    if character:
        session.delete(character)
        log = CharacterLog(character_name=character.name, action_type=ActionType.delete_character,
                           log=f"Successfully deleted character - {character.name}.")
        session.add(log)
        session.commit()
        return character
    else:
        return error_response(498, "Character not found.")


@router.get(
    name="Get All Characters",
    path="/characters",
    tags=["Characters"],
    response_model=list[CharacterResponse],
    description="Fetch characters details.",
    response_description="Successfully fetched characters details.",
    responses={
        404: {"description": "No Characters."}
    }
)
async def get_all_characters(
        session: SessionDep,
):
    query = select(Character)
    characters = session.exec(query).all()
    if not characters:
        return error_response(404, "No Characters.")
    return characters


@router.get(
    name="Get Character",
    path="/characters/{name}",
    tags=["Characters"],
    response_model=CharacterResponse,
    response_description="Successfully fetched character.",
    description="Retrieve the details of a character.",
    responses={
        404: {"description": "Character not found."}
    },
)
async def get_character(
        session: SessionDep,
        name: Annotated[
            str, Path(description="The character name.", regex=r'^[a-zA-Z0-9_-]+$')
        ]
):
    character = session.exec(select(Character).where(Character.name == name)).first()
    if not character:
        return error_response(404, "Character not found.")
    return character


class CharacterLogResponse(SQLModel, ordered=True):
    character_name: Annotated[str, Field(description="character name")]
    action_type: Annotated[ActionType, Field(description="action type")]
    log: Annotated[str, Field(description="log of the performed action")]


@router.get(
    name="Get Logs",
    path="/logs/{amount}",
    tags=["Logs"],
    response_model=list[CharacterLogResponse],
    response_description="Successfully fetched logs.",
    description="Retrieve the last N logs.",
    responses={
        404: {"description": "No logs found."},
    }
)
async def get_logs(
        session: SessionDep,
        amount: Annotated[
            int, Path(description="Last N Logs.", ge=1)
        ],
):
    query = select(CharacterLog).order_by(CharacterLog.id.desc()).limit(amount)
    logs = session.exec(query).all()
    if not logs:
        raise error_response(status_code=404, message="No logs found")
    return logs


@router.get(
    name="Get Character Logs",
    path="/logs/{amount}/{name}",
    tags=["Logs"],
    response_model=list[CharacterLogResponse],
    response_description="Successfully fetched character logs.",
    description="Retrieve the last N logs for a specific character",
    responses={
        404: {"description": "No logs found for this character"},
    }
)
async def get_character_logs(
        session: SessionDep,
        name: Annotated[
            str, Path(description="Name of your character.", regex=r'^[a-zA-Z0-9_-]+$')
        ],
        amount: Annotated[
            int, Path(description="Last N Logs.", ge=1)
        ],
):
    query = select(CharacterLog).where(CharacterLog.character_name == name).order_by(CharacterLog.id.desc()).limit(amount)
    logs = session.exec(query).all()
    if not logs:
        raise error_response(status_code=404, message=f"No logs found for character {name}")
    return logs