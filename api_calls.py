from typing import Dict

import requests


# Character Actions

def buy(name: str, code: str, quantity: int = 1) -> tuple[int, dict]:
    """
    Buy an item at the grand-exchange tile.

    :param name: str    Character name.
    :param code: str    Item code.
    :param quantity: int  Quantity to buy.

    :return: (status_code, response_json)
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/my/{name}/action/buy"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "code": code,
        "quantity": quantity
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.status_code, response.json()


def move(name: str, x: int, y: int) -> tuple[int, dict]:
    """
    Moves a character on the map using the map's X and Y position.

    :param name: str
        Name of your character.
    :param x: int
        The x coordinate of the destination.
    :param y: int
        The y coordinate of the destination.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: The character has moved successfully.
        404: Map not found.
        490: Character already at destination.
        498: Character not found.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/my/{name}/action/move"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "x": x,
        "y": y
    }

    response = requests.post(url, json=payload, headers=headers)

    return response.status_code, response.json()


def fight(name: str) -> tuple[int, dict]:
    """
    Start a fight against a monster on the character's map.

    :param name: str
        Name of your character.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: The fight ended successfully.
        498: Character not found.
        598: Monster not found on this map.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/my/{name}/action/fight"

    response = requests.post(url)

    return response.status_code, response.json()


def equip(name: str, slot: str, code: str, quantity: int = 1) -> tuple[int, dict]:
    """
    Equip an item on your character.

    :param name: str
        Name of your character.
    :param slot: str
        Item slot. Allowed values: 'weapon', 'shield', 'helmet', 'body_armor', 'leg_armor', 'boots',
         'ring1', 'ring2', 'amulet', 'artifact1', 'artifact2', 'artifact3', 'consumable1' or 'consumable2'.
    :param code: str
        Item code.
    :param quantity: int, optional (default = 1)
        Item quantity. Applicable to consumables only.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: The item has been successfully equipped on your character.
        404: Item not found.
        472: Item is not valid for this slot.
        478: Missing item or insufficient quantity.
        491: Slot is not empty.
        494: Character can't equip more than 100 consumables in the same slot.
        496: Character level is insufficient.
        498: Character not found.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/my/{name}/action/equip"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "slot": slot,
        "code": code,
        "quantity": quantity
    }

    response = requests.post(url, json=payload, headers=headers)

    return response.status_code, response.json()


def unequip(name: str, slot: str, quantity: int = 1) -> tuple[int, dict]:
    """
    Unequip an item on your character.

    :param name: str
        Name of your character.
    :param slot: str
        Item slot. Allowed values: 'weapon', 'shield', 'helmet', 'body_armor', 'leg_armor', 'boots',
         'ring1', 'ring2', 'amulet', 'artifact1', 'artifact2', 'artifact3', 'consumable1' or 'consumable2'.
    :param quantity: int, optional (default = 1)
        Item quantity. Applicable to consumables only.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: The item has been successfully unequipped and added in his inventory.
        404: Item not found.
        478: Insufficient quantity of the equipped item.
        491: Slot is empty.
        498: Character not found.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/my/{name}/action/unequip"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "slot": slot,
        "quantity": quantity
    }

    response = requests.post(url, json=payload, headers=headers)

    return response.status_code, response.json()


def gather(name: str, quantity: int = 1) -> tuple[int, dict]:
    """
    Harvest a resource on the character's map.

    :param quantity:
        Quantity of items to gather.
    :param name: str
        Name of your character.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: The resource has been successfully gathered.
        493: Not skill level required.
        498: Character not found.
        598: Resource not found on this map.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/my/{name}/action/gathering"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = quantity

    response = requests.post(url, json=payload, headers=headers)

    return response.status_code, response.json()


def craft(name: str, code: str, quantity: int) -> tuple[int, dict]:
    """
    Crafting an item. The character must be on a map with a workshop.

    :param name: str
        Name of your character.
    :param code: str
        Craft code.
    :param quantity: int
        Quantity of items to craft.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: The item was successfully crafted.
        404: Craft not found.
        478: Missing item or insufficient quantity.
        493: Not skill level required.
        498: Character not found.
        598: Workshop not found on this map.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/my/{name}/action/crafting"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "code": code,
        "quantity": quantity
    }

    response = requests.post(url, json=payload, headers=headers)

    return response.status_code, response.json()


def delete_item(name: str, code: str, quantity: int) -> tuple[int, dict]:
    """
    Delete an item from your character's inventory.

    :param name: str
        Name of your character.
    :param code: str
        Item code.
    :param quantity: int
        Item quantity.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: Item successfully deleted from your character.
        478: Missing item or insufficient quantity.
        498: Character not found.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/my/{name}/action/delete"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "code": code,
        "quantity": quantity
    }

    response = requests.post(url, json=payload, headers=headers)

    return response.status_code, response.json()


def give_item(name: str, recipient: str, code: str, quantity: int) -> tuple[int, dict]:
    """
    Gives recipient a quantity of an item from your character's inventory.

    :param name: str
        Name of your character.
    :param recipient: str
        Recipient name.
    :param code: str
        Item code.
    :param quantity: int
        Item quantity.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: Item successfully Given to recipient.
        478: Missing item or insufficient quantity.
        498: Character not found.
        598: Recipient not found.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/my/{name}/action/give"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "recipient": recipient,
        "code": code,
        "quantity": quantity
    }

    response = requests.post(url, json=payload, headers=headers)
    print(response)

    return response.status_code, response.json()


# Maps
def get_all_maps(content_code: str = None, content_type: str = None) -> tuple[int, dict]:
    """
    Fetch maps details.

    :param content_code: str, optional
        Content code on the map.
    :param content_type: str, optional
        Type of content on the map. Available values: 'monster', 'resource', 'workshop', 'bank',
         'grand_exchange', 'tasks_master'.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: Successfully fetched maps details.
        404: Maps not found.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/maps"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    querystring = {
        "content_code": content_code,
        "content_type": content_type,
    }

    response = requests.get(url, headers=headers, params=querystring)

    return response.status_code, response.json()


def get_map(x: int, y: int) -> tuple[int, dict]:
    """
    Retrieve the details of a map.

    :param x: int
        The position x of the map.
    :param y: int
        The position y of the map.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: Successfully fetched map.
        404: Map not found.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/maps/{x}/{y}"

    response = requests.get(url)

    return response.status_code, response.json()


# Resources
def get_all_resources(drop: str = None, max_level: int = None, min_level: int = None, skill: str = None) -> tuple[int, dict]:
    """
    Fetch resources details.

    :param drop: str, optional
        Item code of the drop.
    :param max_level: int, optional
        Skill maximum level.
    :param min_level: int, optional
        Skill minimum level.
    :param skill: str, optional
        The code of the skill. Allowed values: 'mining', 'woodcutting', 'fishing'.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: Successfully fetched resources details.
        404: Resources not found.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/resources"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    querystring = {
        "drop": drop,
        "max_level": max_level,
        "min_level": min_level,
        "skill": skill,
    }

    response = requests.get(url, headers=headers, params=querystring)

    return response.status_code, response.json()


def get_resource(code: str) -> tuple[int, dict]:
    """
    Retrieve the details of a resource.

    :param code: str
        The code of the resource.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: Successfully fetched resource.
        404: Resource not found.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/resources/{code}"

    response = requests.get(url)

    return response.status_code, response.json()


# Monsters
def get_all_monsters(drop: str = None, max_level: int = None, min_level: int = None) -> tuple[int, dict]:
    """
    Fetch monsters details.

    :param drop: str, optional
        Item code of the drop.
    :param max_level: int, optional
        Monster maximum level.
    :param min_level: int, optional
        Monster minimum level.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: Successfully fetched monsters details.
        404: Monsters not found.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/monsters"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    querystring = {
        "drop": drop,
        "max_level": max_level,
        "min_level": min_level,
    }

    response = requests.get(url, headers=headers, params=querystring)

    return response.status_code, response.json()


def get_monster(code: str) -> tuple[int, dict]:
    """
    Retrieve the details of a monster.

    :param code: str
        The code of the monster.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: Successfully fetched monster.
        404: Monster not found.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/monsters/{code}"

    response = requests.get(url)

    return response.status_code, response.json()


# Items
def get_all_items(craft_material: str = None, craft_skill: str = None, max_level: int = None, min_level: int = None,
                  name: str = None, type: str = None) -> tuple[int, dict]:
    """
    Fetch items details.

    :param craft_material: str, optional
        Item code of items used as material for crafting.
    :param craft_skill: str, optional
        Skill to craft items. Allowed values: 'weaponcrafting', 'gearcrafting', 'jewelrycrafting', 'cooking',
         'woodcutting', 'mining'.
    :param max_level: int, optional
        Maximum level items.
    :param min_level: int, optional
        Minimum level items.
    :param name: str, optional
        Name of the item.
    :param type: str, optional
        Type of items. Available values: 'weapon', 'body_armor', 'resource', 'leg_armor', 'helmet', 'boots', 'shield',
         'amulet', 'ring', 'artifact', 'consumable', 'currency'.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: Fetch items details.
        404: Items not found.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/items"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    querystring = {
        "craft_material": craft_material,
        "craft_skill": craft_skill,
        "max_level": max_level,
        "min_level": min_level,
        "name": name,
        "type": type
    }

    response = requests.get(url, headers=headers, params=querystring)

    return response.status_code, response.json()


def get_item(code: str) -> tuple[int, dict]:
    """
    Retrieve the details of an item.

    :param code: str
        The code of the item.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: Successfully fetched item.
        404: Item not found.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/items/{code}"

    response = requests.get(url)

    return response.status_code, response.json()


# Characters
def create_character(name: str, skin: str) -> tuple[int, dict]:
    """
    Create a new character on your account.

    :param name: str
        Your desired character name. Must be unique. Must be between 3 and 12 characters long.
    :param skin: str
        Your desired skin. Allowed values: 'men1', 'men2', 'men3', 'women1', 'women2', 'women3'.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: Successfully created character.
        494: Name already used.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/characters/create"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "name": name,
        "skin": skin
    }

    response = requests.post(url, json=payload, headers=headers)

    return response.status_code, response.json()


def create_custom_character(name: str, skin: str, char_data: Dict) -> tuple[int, dict]:
    """
    Create a new custom character on your account.

    :param name: str
        Your desired character name. Must be unique. Must be between 3 and 12 characters long.
    :param skin: str
        Your desired skin. Allowed values: 'men1', 'men2', 'men3', 'women1', 'women2', 'women3'.
    :param char_data: Dict

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: Successfully created character.
        494: Name already used.
        498: Wrong json.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/characters/create_custom"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "name": name,
        "skin": skin,
        "char_data": char_data
    }

    response = requests.post(url, json=payload, headers=headers)

    return response.status_code, response.json()


def delete_character(name: str) -> tuple[int, dict]:
    """
    Delete a character from your account.

    :param name: str
        Character name. Must be between 3 and 12 characters long.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: Successfully deleted character.
        498: Character not found.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/characters/delete"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = name

    response = requests.post(url, json=payload, headers=headers)

    return response.status_code, response.json()


def get_all_characters() -> tuple[int, dict]:
    """
    Fetch details of all characters.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: Successfully fetched characters details.
        404: No characters found.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/characters"

    response = requests.get(url)

    return response.status_code, response.json()


def get_character(name: str) -> tuple[int, dict]:
    """
    Retrieve the details of a character.

    :param name: str
        The character name.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: Successfully fetched character.
        404: Character not found.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/characters/{name}"

    response = requests.get(url)

    return response.status_code, response.json()


# Logs
def get_logs(amount: int = 100) -> tuple[int, dict]:
    """
    Retrieve the last N logs.

    :param amount: int
        Last N Logs.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: Successfully fetched logs.
        404: No logs found.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/logs/{amount}"

    response = requests.get(url)

    return response.status_code, response.json()


def get_character_logs(name: str, amount: int = 100) -> tuple[int, dict]:
    """
    Retrieve the last N logs for a specific character.

    :param name: str
        Name of the character.
    :param amount: int
        Last N Logs.

    :return: tuple[int, dict]
        A tuple containing the status_code and response body (a JSON object as a dictionary).

    response codes:
        200: Successfully fetched logs.
        404: No logs found for this character.
    """
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/logs/{amount}/{name}"

    response = requests.get(url)

    return response.status_code, response.json()

