import json
import math
import random
import re
from copy import deepcopy
from typing import Optional, List, Tuple

from app.db import Redis, create_log, ActionType
from app.routers.backend.characters_redis import CHARACTER_KEY_PATTERN, INVENTORY_KEY_PATTERN
from app.routers.backend.items_redis import get_item_from_redis
from app.routers.backend.response_models import CharacterResponseRedis, InventorySlotResponseRedis, \
    ResourceResponseRedis, DropResponseRedis, SkillInfoResponseRedis, ItemRedis, CraftItemRedis, FightResponseRedis, \
    MonsterRedis, ItemSlot, SimpleItemResponseRedis, BlockedHitsResponseRedis


BLOCKING_ENABLED: bool = False # TODO: Remove Blocks for Now
DROP_RATE_ENABLED: bool = False # TODO: Remove Drop rate for Now

async def update_character_redis(redis: Redis, character_name: str, changed_character: CharacterResponseRedis, initial_character: CharacterResponseRedis) -> bool:
    try:
        original_dict = initial_character.dict(exclude={"inventory"})
        changed_dict = changed_character.dict(exclude={"inventory"})
        changed_params = {
            k: v for k, v in changed_dict.items() if v != original_dict[k]
        }
        if not changed_params: # If nothing changed return
            return True
        character_key = CHARACTER_KEY_PATTERN.format(character_name)
        async with redis.pipeline(transaction=True) as pipe:
            await pipe.hset(character_key, mapping=changed_params)
            await pipe.execute()
            return True
    except Exception as e:
        print(e)
        return False

async def update_character_inventory_redis(
        redis: Redis,
        character_name: str,
        new_inventory: List[InventorySlotResponseRedis],
        old_inventory: List[InventorySlotResponseRedis] = None
)-> bool:
    if old_inventory == new_inventory:
        return True
    try:
        character_key = CHARACTER_KEY_PATTERN.format(character_name)
        inventory_key = INVENTORY_KEY_PATTERN.format(character_key)
        old_items = {item.code: item for item in (old_inventory or [])}
        async with redis.pipeline(transaction=True) as pipe:
            if not new_inventory:
                await pipe.delete(inventory_key)
            else:
                for new_item in new_inventory:
                    old_item = old_items.pop(new_item.code, None)
                    if not old_item or old_item.quantity != new_item.quantity or old_item.slot != new_item.slot:
                        await pipe.hset(
                            inventory_key,
                            new_item.code,
                            json.dumps({
                                "slot": new_item.slot,
                                "quantity": new_item.quantity
                            })
                        )
                if old_items.keys(): # If old keys remain delete from redis
                    await pipe.hdel(inventory_key, *old_items.keys())
            await pipe.execute()
            return True
    except Exception as e:
        print(e)
        return False

class CharacterUpdateRedis:
    def __init__(self, redis: Redis, character: CharacterResponseRedis) -> None:
        self.redis: Redis = redis
        self.character_name: str = character.name
        self.initial_character: CharacterResponseRedis = character
        self.changed_character: CharacterResponseRedis = deepcopy(self.initial_character)

    async def move_character(self, x, y):
        self.changed_character.x = x
        self.changed_character.y = y
        await create_log(self.redis, self.character_name, ActionType.move, f"{self.character_name} moves to {x}, {y}.")

    async def add_item(self, code: str, quantity: int):
        # Check if item already exists in inventory
        for slot in self.changed_character.inventory:
            if slot.code == code:
                slot.quantity += quantity
                return

        # If not, add new slot (slot number = index + 1)
        new_slot = InventorySlotResponseRedis(
            slot=len(self.changed_character.inventory) + 1,
            code=code,
            quantity=quantity
        )
        self.changed_character.inventory.append(new_slot)

    async def remove_item(self, code: str, quantity: int):
        # Find the slot containing the item
        for index, slot in enumerate(self.changed_character.inventory):
            if slot.code == code:
                # Reduce the quantity
                slot.quantity -= quantity
                if slot.quantity < 0:
                    raise ValueError(f"Item with code {code} quantity not enough for craft")

                # If quantity reaches zero or below, remove the slot
                if slot.quantity == 0:
                    self.changed_character.inventory.pop(index)
                    # Re-number remaining slots
                    for i, remaining_slot in enumerate(self.changed_character.inventory[index:], start=1):
                        remaining_slot.slot = i
                return

        raise ValueError(f"Item with code {code} not found in inventory")

    @staticmethod
    async def level_up_skill(skill_xp: int, skill_level: int, skill_max_xp: int):
        async def calculate_skill_max_xp(skill_current_level: int):
            """
            XP required to go from <level> to <level+1>.
            Starts at 150 for level 1→2, and increases by +10 each level.
            """
            return 150 + (skill_current_level - 1) * 10

        while skill_level < 40 and skill_xp >= skill_max_xp:
            skill_xp -= skill_max_xp
            skill_level += 1
            skill_max_xp = await calculate_skill_max_xp(skill_level)  # Use the new logarithmic formula for XP requirement
        return skill_xp, skill_level, skill_max_xp

    @staticmethod
    async def skill_xp_gain(action_level: int, character_skill_level: int, modifier: int = 1):
        """
        Always award 20 XP (×modifier), unless skill is >10 levels above the action.
        """
        if character_skill_level > action_level + 10:
            return 0
        return 50 * modifier

    async def increase_skill_xp(self, skill: str, action_level: int, modifier: int = 1):
        skill_xp = getattr(self.changed_character, f'{skill}_xp')
        skill_level = getattr(self.changed_character, f'{skill}_level')
        action_xp = await self.skill_xp_gain(action_level, skill_level, modifier)
        skill_max_xp = getattr(self.changed_character, f'{skill}_max_xp')
        skill_xp, skill_level, skill_max_xp = await self.level_up_skill(skill_xp + action_xp, skill_level, skill_max_xp)
        setattr(self.changed_character, f'{skill}_xp', skill_xp)
        setattr(self.changed_character, f'{skill}_level', skill_level)
        setattr(self.changed_character, f'{skill}_max_xp', skill_max_xp)
        return action_xp

    async def gather_resource(self, resource: ResourceResponseRedis, quantity: int, modifier: int = 1) ->Tuple[Optional[SkillInfoResponseRedis], bool]:
        try:
            items = []
            total_got_xp = 0
            for _ in range(quantity):
                total_got_xp += await self.increase_skill_xp(skill=resource.skill, action_level=resource.level, modifier=modifier)
            gather_cycles = quantity
            while gather_cycles > 0:
                for drop in resource.drops:
                    if DROP_RATE_ENABLED:
                        drop_chance = 1 / drop.rate
                        result = random.choices([None, 1], weights=[1 - drop_chance, drop_chance], k=1)[0]
                        if result:
                            item_quantity = random.randint(drop.min_quantity, drop.max_quantity)
                            await self.add_item(code=drop.code, quantity=item_quantity)
                            items.append(DropResponseRedis(code=drop.code, quantity=item_quantity))
                    else:
                        item_quantity = random.randint(drop.min_quantity, drop.max_quantity)
                        await self.add_item(code=drop.code, quantity=item_quantity)
                        items.append(DropResponseRedis(code=drop.code, quantity=item_quantity))
                gather_cycles -= 1

            skill_info = SkillInfoResponseRedis(skill=resource.skill , xp=total_got_xp, items=items)
            await create_log(self.redis, self.character_name, ActionType.gather,
                             f"{self.character_name} gather resource {resource.name} with the skill {resource.skill} x{quantity} times.")
            return skill_info, True
        except Exception as e:
            print(e)
            return None, False

    async def find_item_slot(self, code: str) -> Optional[InventorySlotResponseRedis]:
        return next((slot for slot in self.changed_character.inventory if slot.code == code), None)

    async def has_item_in_inventory(self, code: str) -> bool:
        inventory_item: Optional[InventorySlotResponseRedis] = await self.find_item_slot(code)
        if not inventory_item or inventory_item.quantity < 1:
            return False
        return True

    async def has_all_items_for_craft(self, needed_items_for_craft: List[CraftItemRedis], craft_quantity: int = 1) -> bool:
        inventory_items = {item.code: item for item in (self.changed_character.inventory or [])}
        for needed_item in needed_items_for_craft:
            inventory_item = inventory_items.get(needed_item.code)
            if not inventory_item or inventory_item.quantity < (needed_item.quantity * craft_quantity):
                return False
        return True

    async def craft_item(self, craft_item: ItemRedis, craft_quantity: int, modifier: int = 3) -> Tuple[Optional[SkillInfoResponseRedis], bool]:
        try:
            total_got_xp = 0
            for item in craft_item.craft.items:
                await self.remove_item(item.code, item.quantity * craft_quantity)
            for _ in range(craft_quantity):
                total_got_xp += await self.increase_skill_xp(skill=craft_item.craft.skill, action_level=craft_item.craft.level, modifier=modifier)
            await self.add_item(craft_item.code, craft_quantity)
            items = [DropResponseRedis(code=craft_item.code, quantity=craft_quantity)]
            skill_info = SkillInfoResponseRedis(skill=craft_item.craft.skill, xp=total_got_xp, items=items)
            await create_log(redis=self.redis, character_name=self.character_name, action=ActionType.craft, log=f"{self.character_name} crafts {craft_item.code} x{craft_quantity}.")
            return skill_info, True
        except Exception as e:
            print(e)
            return None, False

    @staticmethod
    async def level_up_character(xp, level, max_xp, hp):
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

    async def increase_battle_xp(self, monster_level: int, modifier: int = 1):
        action_xp = await self.skill_xp_gain(monster_level, self.changed_character.level, modifier)
        self.changed_character.xp, self.changed_character.level, self.changed_character.max_xp, self.changed_character.hp = await self.level_up_character(self.changed_character.xp + action_xp, self.changed_character.level, self.changed_character.max_xp, self.changed_character.hp)
        return action_xp

    async def fight_monster_simulation(self, monster: MonsterRedis):
        async def init_consumables():
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
                consumable_code = getattr(self.changed_character, slot)
                consumable_quantity = getattr(self.changed_character, f'{slot}_quantity')
                if consumable_code:
                    consumable_item: ItemRedis = await get_item_from_redis(redis=self.redis, code=consumable_code)
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
                                        setattr(self.changed_character, slot, "")
                                        setattr(self.changed_character, f'{slot}_quantity', 0)
                        else:
                            print(consumable_item, " - Not Implemented")
            return boost_stats, consumables
        async def initialize_elements(boost_stats):
            async def calculate_character_damage(element: str) -> int:
                base_attack = getattr(self.changed_character, f'attack_{element}')
                dmg = getattr(self.changed_character, f'dmg_{element}')
                dmg_boost = base_attack * ((dmg + boost_stats[f'dmg_{element}']) * 0.01)
                monster_res = getattr(monster, f'res_{element}')
                res_reduction = base_attack * (monster_res * 0.01)
                return base_attack + dmg_boost - res_reduction

            async def calculate_monster_damage(element: str) -> int:
                base_attack = getattr(monster, f'attack_{element}')
                character_res = getattr(self.changed_character, f'res_{element}')
                res_reduction = base_attack * (character_res * 0.01)
                return base_attack - res_reduction

            async def calculate_character_block_chance(element: str) -> float:
                res_value = getattr(self.changed_character, f'res_{element}')
                return (res_value / 10) / 100 if res_value > 0 else 0

            async def calculate_monster_block_chance(element: str) -> float:
                res_value = getattr(monster, f'res_{element}')
                return (res_value / 10) / 100 if res_value > 0 else 0

            elements = ["fire", "earth", "water", "air"]
            character_elements = {'damage': {}, 'block_chance': {}}
            monster_elements = {'damage': {}, 'block_chance': {}}

            for element in elements:
                if getattr(self.changed_character, f'attack_{element}') > 0:
                    character_elements['damage'][element] = await calculate_character_damage(element)
                if getattr(self.changed_character, f'res_{element}') > 0:
                    character_elements['block_chance'][element] = await calculate_character_block_chance(element)
                if getattr(monster, f'attack_{element}') > 0:
                    monster_elements['damage'][element] = await calculate_monster_damage(element)
                if getattr(monster, f'res_{element}') > 0:
                    monster_elements['block_chance'][element] = await calculate_monster_block_chance(element)

            return character_elements, monster_elements

        async def fight_cycle(consumables: list[dict], character_hp: int, monster_hp: int, logs: list[str], character_blocked_hits: BlockedHitsResponseRedis,
                              monster_blocked_hits: BlockedHitsResponseRedis, character_elements: dict, monster_elements: dict):
            async def use_restore_consumables(turn: int, character_hp: int, boost_hp: int):
                # Use restore items if HP is <= 50% each turn
                if character_hp < (self.changed_character.hp + boost_hp) / 2:
                    for consumable in consumables:
                        if consumable["quantity"] > 0:
                            character_hp += consumable["value"]
                            consumable["quantity"] -= 1
                            logs.append(f"Turn {turn}: Character used {consumable['name']} and restored {consumable['value']} hp.")
                return character_hp

            async def commit_consumables():
                for consumable in consumables:
                    quantity = consumable["quantity"]
                    setattr(self.changed_character, f'{consumable["slot"]}_quantity', quantity)
                    if quantity <= 0:
                        setattr(self.changed_character, f'{consumable["slot"]}', "")

            async def character_turn(turn: int, monster_hp: int):
                character_elemental_damage = character_elements["damage"]
                if character_elemental_damage:
                    monster_elemental_block_chance = monster_elements["block_chance"]
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

            async def monster_turn(turn: int, character_hp: int):
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
                character_hp = await use_restore_consumables(turn, character_hp, boost_stats["hp"])  # Use restore items if HP <= 50%
                monster_hp = await character_turn(turn, monster_hp)

                if monster_hp <= 0:
                    logs.append(f"Fight result: win. (Character HP: {self.changed_character.hp}, Monster HP: {0})")
                    got_xp = await self.increase_battle_xp(monster.level)
                    await commit_consumables()
                    return turn, logs, "win", got_xp

                character_hp = await monster_turn(turn, character_hp)
                if character_hp <= 0:
                    logs.append(f"Fight result: lose. (Character HP: {0}, Monster HP: {monster.hp})")
                    await self.move_character(0, 0)
                    await commit_consumables()
                    return turn, logs, "lose", 0

                turn += 1

            await commit_consumables()
            logs.append(f"Fight result: lose. (Character HP: {self.changed_character.hp}, Monster HP: {monster.hp})")
            return turn, logs, "lose", 0

        boost_stats, consumables = await init_consumables()  # Apply boosts before the fight
        character_hp = self.changed_character.hp + boost_stats["hp"]

        monster_hp = monster.hp
        logs = []
        monster_blocked_hits = BlockedHitsResponseRedis()
        character_blocked_hits = BlockedHitsResponseRedis()

        character_elements, monster_elements = await initialize_elements(boost_stats)
        return await fight_cycle(consumables, character_hp, monster_hp, logs, character_blocked_hits, monster_blocked_hits, character_elements, monster_elements)

    async def fight_monster(self, monster: MonsterRedis) -> Tuple[Optional[FightResponseRedis], bool]:
        try:
            turn, logs, result, got_xp = await self.fight_monster_simulation(monster)
            fight = FightResponseRedis(turns=turn, logs=logs, result=result)
            if result == "win":
                items = []
                drops = monster.drops
                for drop in drops:
                    if DROP_RATE_ENABLED:
                        drop_chance = 1 / drop.rate
                        result = random.choices([None, 1], weights=[1 - drop_chance, drop_chance], k=1)[0]
                        if result:
                            item_quantity = random.randint(drop.min_quantity, drop.max_quantity)
                            await self.add_item(drop.code, item_quantity)
                            items.append(DropResponseRedis(code=drop.code, quantity=item_quantity))
                    else:
                        item_quantity = random.randint(drop.min_quantity, drop.max_quantity)
                        await self.add_item(drop.code, item_quantity)
                        items.append(DropResponseRedis(code=drop.code, quantity=item_quantity))

                fight.drops = items
                fight.xp = got_xp
                await create_log(redis=self.redis, character_name=self.character_name, action=ActionType.fight,
                                   log=f"{self.character_name} won his fight against {monster.name}.")
            else:
                await create_log(redis=self.redis, character_name=self.character_name, action=ActionType.fight,
                                   log=f"{self.character_name} lost his fight against {monster.name}.")
            return fight, True
        except Exception as e:
            print(e)
            return None, False

    @staticmethod
    async def item_fits_slot(item_type, slot: ItemSlot) -> bool:
        async def slot_name_without_numerals() -> str:
            return re.sub(r'\d+', '', slot.value)

        return item_type == await slot_name_without_numerals()

    async def equip_consumable(self, item_code: str, slot: ItemSlot, quantity: int) -> bool:
        try:
            slot_name = f"{slot.value}_slot"
            await self.remove_item(item_code, quantity)
            setattr(self.changed_character, slot_name, item_code)
            existing_quantity = getattr(self.changed_character, f'{slot_name}_quantity')
            setattr(self.changed_character, f'{slot_name}_quantity', existing_quantity + quantity)
            await create_log(redis=self.redis, character_name=self.character_name, action=ActionType.equip_item,
                         log=f"The character {self.character_name} has equipped consumable {item_code} "
                             f"x{quantity} into slot {slot.value}.")
            return True
        except Exception as e:
            print(e)
            return False

    async def unequip_consumable(self, item_code: str, slot: ItemSlot, quantity: int) -> bool:
        try:
            slot_name = f"{slot.value}_slot"
            existing_quantity = getattr(self.changed_character, f'{slot_name}_quantity')
            setattr(self.changed_character, f'{slot_name}_quantity', existing_quantity - quantity)
            if existing_quantity - quantity == 0:
                setattr(self.changed_character, slot_name, "")
            await self.add_item(item_code, quantity)
            await create_log(redis=self.redis, character_name=self.character_name, action=ActionType.unequip_item,
                               log=f"The character {self.character_name} has unequipped consumable {item_code} in "
                                   f"quantity of {quantity} from slot {slot.value}.")
            return True
        except Exception as e:
            print(e)
            return False

    async def equip_equipment(self, item: ItemRedis, slot: ItemSlot, quantity: int = 1) -> bool:
        try:
            slot_name = f"{slot.value}_slot"
            await self.remove_item(item.code, quantity)
            setattr(self.changed_character, slot_name, item.code)
            await self.apply_equipment_stats(item)
            await create_log(redis=self.redis, character_name=self.character_name, action=ActionType.equip_item,
                             log=f"The character {self.character_name} has equipped item {item.code} into slot {slot.value}.")
            return True
        except Exception as e:
            print(e)
            return False

    async def unequip_equipment(self, item: ItemRedis, slot: ItemSlot, quantity: int = 1) -> bool:
        try:
            slot_name = f"{slot.value}_slot"
            await self.add_item(item.code, quantity)
            setattr(self.changed_character, slot_name, "")
            await self.unapply_equipment_stats(item)
            await create_log(redis=self.redis, character_name=self.character_name, action=ActionType.unequip_item,
                                   log=f"The character {self.character_name} has unequipped item {item.code} from slot {slot.value}.")
            return True
        except Exception as e:
            print(e)
            return False

    async def apply_equipment_stats(self, item: ItemRedis):
        for effect in item.effects:
            try:
                current = getattr(self.changed_character, effect.name)
                setattr(self.changed_character, effect.name, current + effect.value)
            except:
                print(f"Effect[{effect.name}] Not Implemented")

    async def unapply_equipment_stats(self, item: ItemRedis):
        for effect in item.effects:
            try:
                current = getattr(self.changed_character, effect.name)
                setattr(self.changed_character, effect.name, current - effect.value)
            except:
                print(f"Effect[{effect.name}] Not Implemented")

    async def remove_item_action(self, code, quantity) -> Tuple[Optional[SimpleItemResponseRedis], bool]:
        try:
            await self.remove_item(code, quantity)
            await create_log(redis=self.redis, character_name=self.character_name, action=ActionType.delete_item,
                       log=f"{self.character_name} deleted item {code} x{quantity}")
            return SimpleItemResponseRedis(code=code, quantity=quantity), True
        except Exception as e:
            print(e)
            return None, False

    async def give_item_to_recipient(self, code: str, quantity: int, recipient: 'CharacterUpdateRedis') -> Tuple[
        Optional[SimpleItemResponseRedis], bool]:
        try:
            await self.remove_item(code, quantity)
            await recipient.add_item(code, quantity)

            await create_log(redis=self.redis, character_name=self.character_name, action=ActionType.give_item,
                             log=f"{self.character_name} give item {code} x{quantity} to {recipient.character_name}")
            return SimpleItemResponseRedis(code=code, quantity=quantity), True
        except Exception as e:
            print(e)
            return None, False

    async def update_redis(self) -> bool:
        try:
            return (await update_character_redis(redis=self.redis, character_name=self.character_name, changed_character=self.changed_character, initial_character=self.initial_character) and
                    await update_character_inventory_redis(redis=self.redis, character_name=self.character_name, new_inventory=self.changed_character.inventory, old_inventory=self.initial_character.inventory))
        except Exception as e:
            print(e)
            return False

