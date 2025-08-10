from enum import Enum
from typing import Optional, List, Annotated

from pydantic import BaseModel, Field


# Maps
class MapContentRedis(BaseModel):
    type: str
    code: str

class MapRedis(BaseModel):
    name: str
    skin: str
    x: int
    y: int
    content: Optional[MapContentRedis] = None

# Resources
class ResourceDropResponseRedis(BaseModel):
    code: str
    rate: int
    min_quantity: int
    max_quantity: int

class ResourceResponseRedis(BaseModel):
    name: str
    code: str
    skill: str
    level: int
    drops: Optional[List[ResourceDropResponseRedis]] = None

# Monsters
class MonsterDropRedis(BaseModel):
    code: str
    rate: int
    min_quantity: int
    max_quantity: int

class MonsterRedis(BaseModel):
    name: str
    code: str
    level: int
    hp: int
    attack_fire: int
    attack_earth: int
    attack_water: int
    attack_air: int
    res_fire: int
    res_earth: int
    res_water: int
    res_air: int
    min_gold: int
    max_gold: int
    drops: Optional[List[MonsterDropRedis]]

# Characters
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

class InventorySlotResponseRedis(BaseModel):
    slot: Annotated[int, Field(description="Inventory slot identifier.")]
    code: Annotated[str, Field(description="required Item code.")]
    quantity: Annotated[int, Field(description="required Quantity in the slot.")]

class CharacterResponseRedis(BaseModel):
    name: Annotated[str, Field(description="Name of the character.")] = "string"
    skin: Annotated[str, Field(description="Character skin code.")] = "men1"
    level: Annotated[int, Field(description="Combat level.")] = 1
    xp: Annotated[int, Field(description="The current xp level of the combat level.")] = 0
    max_xp: Annotated[int, Field(description="XP required to level up the character.")] = 150

    mining_level: Annotated[int, Field(description="Mining level.")] = 1
    mining_xp: Annotated[int, Field(description="The current xp level of the Mining skill.")] = 0
    mining_max_xp: Annotated[int, Field(description="Mining XP required to level up the skill.")] = 150

    woodcutting_level: Annotated[int, Field(description="Woodcutting level.")] = 1
    woodcutting_xp: Annotated[int, Field(description="The current xp level of the Woodcutting skill.")] = 0
    woodcutting_max_xp: Annotated[int, Field(description="Woodcutting XP required to level up the skill.")] = 150

    fishing_level: Annotated[int, Field(description="Fishing level.")] = 1
    fishing_xp: Annotated[int, Field(description="The current xp level of the Fishing skill.")] = 0
    fishing_max_xp: Annotated[int, Field(description="Fishing XP required to level up the skill.")] = 150

    weaponcrafting_level: Annotated[int, Field(description="Weaponcrafting level.")] = 1
    weaponcrafting_xp: Annotated[int, Field(description="The current xp level of the Weaponcrafting skill.")] = 0
    weaponcrafting_max_xp: Annotated[int, Field(description="Weaponcrafting XP required to level up the skill.")] = 150

    gearcrafting_level: Annotated[int, Field(description="Gearcrafting level.")] = 1
    gearcrafting_xp: Annotated[int, Field(description="The current xp level of the Gearcrafting skill.")] = 0
    gearcrafting_max_xp: Annotated[int, Field(description="Gearcrafting XP required to level up the skill.")] = 150

    jewelrycrafting_level: Annotated[int, Field(description="Jewelrycrafting level.")] = 1
    jewelrycrafting_xp: Annotated[int, Field(description="The current xp level of the Jewelrycrafting skill.")] = 0
    jewelrycrafting_max_xp: Annotated[int, Field(description="Jewelrycrafting XP required to level up the skill.")] = 150

    cooking_level: Annotated[int, Field(description="Cooking level.")] = 1
    cooking_xp: Annotated[int, Field(description="The current xp level of the Cooking skill.")] = 0
    cooking_max_xp: Annotated[int, Field(description="Cooking XP required to level up the skill.")] = 150

    hp: Annotated[int, Field(description="Character HP.")] = 120

    attack_fire: Annotated[int, Field(description="Fire attack.")] = 0
    attack_earth: Annotated[int, Field(description="Earth attack.")] = 0
    attack_water: Annotated[int, Field(description="Water attack.")] = 0
    attack_air: Annotated[int, Field(description="Air attack.")] = 0

    dmg_fire: Annotated[int, Field(description="% Fire damage.")] = 0
    dmg_earth: Annotated[int, Field(description="% Earth damage.")] = 0
    dmg_water: Annotated[int, Field(description="% Water damage.")] = 0
    dmg_air: Annotated[int, Field(description="% Air damage.")] = 0

    res_fire: Annotated[int, Field(description="% Fire resistance.")] = 0
    res_earth: Annotated[int, Field(description="% Earth resistance.")] = 0
    res_water: Annotated[int, Field(description="% Water resistance.")] = 0
    res_air: Annotated[int, Field(description="% Air resistance.")] = 0

    x: Annotated[int, Field(description="Character x coordinate.")] = 0
    y: Annotated[int, Field(description="Character y coordinate.")] = 0

    weapon_slot: Annotated[str, Field(description="Weapon slot.")] = ""
    shield_slot: Annotated[str, Field(description="Shield slot.")] = ""
    helmet_slot: Annotated[str, Field(description="Helmet slot.")] = ""
    body_armor_slot: Annotated[str, Field(description="Body armor slot.")] = ""
    leg_armor_slot: Annotated[str, Field(description="Leg armor slot.")] = ""
    boots_slot: Annotated[str, Field(description="Boots slot.")] = ""
    ring1_slot: Annotated[str, Field(description="Ring 1 slot.")] = ""
    ring2_slot: Annotated[str, Field(description="Ring 2 slot.")] = ""
    amulet_slot: Annotated[str, Field(description="Amulet slot.")] = ""
    artifact1_slot: Annotated[str, Field(description="Artifact 1 slot.")] = ""
    artifact2_slot: Annotated[str, Field(description="Artifact 2 slot.")] = ""
    artifact3_slot: Annotated[str, Field(description="Artifact 3 slot.")] = ""

    consumable1_slot: Annotated[str, Field(description="Consumable 1 slot.")] = ""
    consumable1_slot_quantity: Annotated[int, Field(description="Consumable 1 quantity.")] = 0
    consumable2_slot: Annotated[str, Field(description="Consumable 2 slot.")] = ""
    consumable2_slot_quantity: Annotated[int, Field(description="Consumable 2 quantity.")] = 0

    inventory: Annotated[List[InventorySlotResponseRedis], Field(description="List of inventory slots.")] = []

# Items
class ItemEffectRedis(BaseModel):
    name: str
    value: int

class CraftItemRedis(BaseModel):
    code: str
    quantity: int

class ItemCraftRedis(BaseModel):
    skill: str
    level: int
    items: List[CraftItemRedis]
    quantity: int

class ItemRedis(BaseModel):
    name: str
    code: str
    level: int
    type: str
    subtype: str
    description: str
    effects: List[ItemEffectRedis] = []
    craft: Optional[ItemCraftRedis] = None

# Endpoints
class CharacterMovementDataResponseRedis(BaseModel):
    destination: Annotated[MapRedis, Field(description="Destination details.")]
    character: Annotated[CharacterResponseRedis, Field(description="Character details.")]

class DropResponseRedis(BaseModel):
    code: Annotated[str, Field(description="The code of the item.")]
    quantity: Annotated[int, Field(description="The quantity of the item.")]

class SkillInfoResponseRedis(BaseModel):
    skill: Annotated[str, Field(description="The Skill used")]
    xp: Annotated[int, Field(description="The amount of xp gained.")]
    items: Annotated[List[DropResponseRedis], Field(description="Items received.")]

class SkillResponseRedis(BaseModel):
    details: Annotated[SkillInfoResponseRedis, Field(description="Skill details.")]
    character: Annotated[CharacterResponseRedis, Field(description="Character details.")]

class FightResult(str, Enum):
    win = "win"
    lose = "lose"

class BlockedHitsResponseRedis(BaseModel):
    fire: Annotated[int, Field(description="The amount of fire hits blocked.")] = 0
    earth: Annotated[int, Field(description="The amount of earth hits blocked.")] = 0
    water: Annotated[int, Field(description="The amount of water hits blocked.")] = 0
    air: Annotated[int, Field(description="The amount of air hits blocked.")] = 0
    total: Annotated[int, Field(description="The amount of total hits blocked.")] = 0

class FightResponseRedis(BaseModel):
    result: Annotated[FightResult, Field(description="The result of the fight.")] = FightResult.win
    xp: Annotated[int,  Field(description="The amount of xp gained by the fight.")] = 0
    drops: Annotated[list[DropResponseRedis], Field(description="The items dropped by the fight.")] = []
    turns: Annotated[int, Field(description="Numbers of the turns of the combat.")] = 0
    logs: Annotated[list[str], Field(description="The fight logs.")] = []

class CharacterFightDataRedis(BaseModel):
    fight: Annotated[FightResponseRedis, Field(description="Fight details.")]
    character: Annotated[CharacterResponseRedis, Field(description="Character details.")]

class CharacterFightsDataRedis(BaseModel):
    fights: Annotated[List[FightResponseRedis], Field(description="Fight details.")]
    character: Annotated[CharacterResponseRedis, Field(description="Character details.")]

class EquipRequestResponseRedis(BaseModel):
    slot: Annotated[ItemSlot, Field(description="Item slot.")]
    item: Annotated[ItemRedis, Field(description="Item details.")]
    character: Annotated[CharacterResponseRedis, Field(description="Character details.")]

class SimpleItemResponseRedis(BaseModel):
    code: Annotated[str, Field(description="The code of the item.")]
    quantity: Annotated[int, Field(description="The quantity of the item.")]

class BuyResponseRedis(BaseModel):
    item: Annotated[SimpleItemResponseRedis, Field(description="Item details.")]
    character: Annotated[CharacterResponseRedis, Field(description="Character details.")]

class DeleteItemResponseRedis(BaseModel):
    item: Annotated[SimpleItemResponseRedis, Field(description="Item details.")]
    character: Annotated[CharacterResponseRedis, Field(description="Character details.")]

class GivenItemResponseRedis(BaseModel):
    item: Annotated[SimpleItemResponseRedis, Field(description="Item details.")]
    character: Annotated[CharacterResponseRedis, Field(description="Character details.")]
    recipient: Annotated[CharacterResponseRedis, Field(description="Recipient details.")]