import json
import os
from pathlib import Path
from memory.craft_parser import CraftParser, to_text
BASE_PATH = Path('./memory/source_jsons').resolve()
MONSTERS_DATA_JSON_PATH = BASE_PATH / 'monsters.json'
ITEMS_DATA_JSON_PATH = BASE_PATH / 'items.json'
ITEMS_DATA_JSON = None
MONSTERS_DATA_JSON = None

with open(MONSTERS_DATA_JSON_PATH, 'r') as json_file:
    MONSTERS_DATA = json.load(json_file)
with open(ITEMS_DATA_JSON_PATH, 'r') as json_file:
    ITEMS_DATA = json.load(json_file)

def entity_description_generator(entity_name: str, quantity: int = 1) -> str:
    """
    Generate description for an entity (item or monster) by name.
    
    This function searches through both items and monsters data to find
    a matching entity and generates an appropriate description. It first
    checks items, then monsters, and returns a fallback message if
    no match is found.
    
    Args:
        entity_name: Name of the entity to describe
        quantity: Quantity of the entity (default: 1)
        
    Returns:
        String containing the entity description or fallback message
    """
    for item_candidate in ITEMS_DATA:
        if item_candidate['name'] == entity_name:
            return item_desc_generator(entity_name, quantity)
    for monster_candidate in MONSTERS_DATA:
        if monster_candidate['name'] == entity_name:
            return monster_desc_generator(entity_name)

    return f'No information about {entity_name}. Ignore this entity.'

def item_desc_generator(item_name: str, quantity: int = 1) -> str:
    """
    Generate detailed description for an item including crafting information.
    
    This function uses the CraftParser to get detailed information about
    an item, including its crafting requirements, location, and effects.
    It handles cases where item information is not available.
    
    Args:
        item_name: Name of the item to describe
        quantity: Quantity of the item (default: 1)
        
    Returns:
        String containing detailed item description and crafting information
    """
    craft_parser = CraftParser()
    item_code = item_name.lower().replace(' ', '_')
    item_data = craft_parser.parse(item_code)
    item_desc = to_text(item_data)[0]
    if item_data[0]['item_name'] is None:
        item_json = {'Error' : f'No information about item {item_name}, check if item name spelled correctly.'}
    else:
        item_json = item_to_json(item_data,item_data[0]['item_name'], quantity = quantity)
    if item_desc == '':
        item_desc = f'No information about item {item_name}, check if item name spelled correctly.'
    return item_desc

def get_monster_json(monster_name: str) -> dict:
    """
    Retrieve monster data from the monsters JSON file.
    
    Args:
        monster_name: Name of the monster to retrieve data for
        
    Returns:
        Dictionary containing monster data or empty dict if not found
    """
    monster_path = Path('./memory/source_jsons/monsters.json').resolve()
    with open(monster_path, 'r') as f:
        monster_json = json.load(f)
        for monster in monster_json:
            if monster['name'] == monster_name:
                return monster

    return {}

def item_to_json(crafting_chain: list, name: str, quantity: int = 1) -> dict:
    """
    Convert item crafting chain data to structured JSON format.
    
    This function takes crafting chain data and converts it into a structured
    JSON format that includes item information, location, requirements,
    and crafting details.
    
    Args:
        crafting_chain: List of crafting chain data
        name: Name of the target item
        quantity: Quantity of the item (default: 1)
        
    Returns:
        Dictionary containing structured item information with keys:
            - name: Item name
            - location: Acquisition location coordinates
            - action: How to obtain the item (crafted, gathered, collected)
            - quantity: Item quantity (omitted if < 1)
            - requires: List of required resources
            - source: Source of the item (workshop, resource location, monster)
    """
    item = None
    for candidate in crafting_chain:
        if candidate['item_name'] == name:
            item = candidate
            break
    name = item['item_name'].replace("'",'"')
    location = {"x": item['item_acquisition_x'], "y": item['item_acquisition_y']}
    action = ''
    source = ''
    if item['item_source'] == 'workshop':
        action = "crafted"
        source = "workshop"
    if item['item_type'] == 'raw resource':
        action = f"gathered"
        source = f'{item['item_source']}'
    if item['item_type'] == 'monster drop':
        action = f"collected"
        source = f"monster {item['item_source']}"

    required_resources = [item_to_json(crafting_chain, res[2], res[1]) for res in item['craft_components_codes_with_quant'] ]

    item_json = {
        "name": name,
        "location": location,
        "action": action,
        "quantity": quantity,
        "requires": required_resources,
        "source": source
    }

    if quantity < 1:
        _ = item_json.pop('quantity')

    return item_json

def monster_desc_generator(monster_name: str) -> str:
    """
    Generate detailed description for a monster including stats and abilities.
    
    This function retrieves monster data and formats it into a human-readable
    description including level, health points, attack values, and resistances.
    
    Args:
        monster_name: Name of the monster to describe
        
    Returns:
        String containing formatted monster description with stats
    """
    monster_data = get_monster_json(monster_name)
    monster_description = f''' 
Monster: {monster_data['name']}
Level: {monster_data['level']}
HP: {monster_data['hp']}
Attack:
    - Fire damage: {monster_data['attack_fire']} points
    - Earth damage: {monster_data['attack_earth']} points
    - Water damage: {monster_data['attack_water']} points
    - Air damage: {monster_data['attack_air']} points
Defence:
    - Fire resistance: {monster_data['attack_fire']} percent
    - Earth resistance: {monster_data['attack_earth']} percent
    - Water resistance: {monster_data['attack_water']} percent
    - Air resistance: {monster_data['attack_air']} percent
'''
    return monster_description
