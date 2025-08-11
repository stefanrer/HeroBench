# Virtual Environment
![Virtual Enviroment Map](world_map.png "Virtual Enviroment Map")

## SQLite Version
Works slower, localy saves database in artifact.db file

## Redis Version
Works faster, needs Redis instance running on port 6379

---

# API CALLS Documentation

This document describes all available API calls for interacting with the virtual environment.

## Character Actions

### MOVE
Moves a character on the map.

**Path Params:**
- `name`: str - Character name

**Body Params:**
- `x`: int - Map X coordinate
- `y`: int - Map Y coordinate

**URL:** `POST /my/{name}/action/move`

**Response Codes:**
- 200: Character moved successfully
- 404: Map not found
- 490: Character already at destination
- 498: Character not found

---

### FIGHT
Starts a fight against a monster.

**Path Params:**
- `name`: str - Character name

**URL:** `POST /my/{name}/action/fight`

**Response Codes:**
- 200: Fight ended successfully
- 498: Character not found
- 598: Monster not found on this map

---

### EQUIP
Equips an item on your character.

**Path Params:**
- `name`: str - Character name

**Body Params:**
- `slot`: str - Equipment slot (weapon, shield, helmet, body_armor, leg_armor, boots, ring1, ring2, amulet, artifact1, artifact2, artifact3, consumable1, consumable2)
- `code`: str - Item code
- `quantity`: int (default=1) - Quantity (for consumables)

**URL:** `POST /my/{name}/action/equip`

**Response Codes:**
- 200: Item equipped successfully
- 404: Item not found
- 472: Invalid slot for item
- 478: Missing item/insufficient quantity
- 491: Slot not empty
- 494: Too many consumables (max 100)
- 496: Insufficient level
- 498: Character not found

---

### UNEQUIP
Unequips an item from your character.

**Params:**
- `name`: str - Character name
- `slot`: str - Equipment slot (weapon, shield, helmet, body_armor, leg_armor, boots, ring1, ring2, amulet, artifact1, artifact2, artifact3, consumable1, consumable2)
- `quantity`: int (default=1) - Quantity (for consumables)

**URL:** `POST /my/{name}/action/unequip`

**Response Codes:**
- 200: Item unequipped successfully
- 404: Item not found
- 478: Insufficient quantity
- 491: Slot is empty
- 498: Character not found

---

### GATHER
Harvests a resource on the character's map.

**PathParams:**
- `name`: str - Character name

**Body Params:**
- `quantity`: int (default=1) - Quantity to gather

**URL:** `POST /my/{name}/action/gathering`

**Response Codes:**
- 200: Resource gathered successfully
- 493: Insufficient skill level
- 498: Character not found
- 598: Resource not found on map

---

### CRAFT
Crafts an item (requires workshop).

**Path Params:**
- `name`: str - Character name

**Body Params:**
- `code`: str - Craft code
- `quantity`: int - Quantity to craft

**URL:** `POST /my/{name}/action/crafting`

**Response Codes:**
- 200: Item crafted successfully
- 404: Craft not found
- 498: Character not found
- 500: Crafting Error

** Crafting Error Example**
```json
{
  "error": {
    "code": 500,
    "message": {
      "errors": {
        "on_workshop_tile": false,
        "needed_skill_level": false,
        "enough_items_for_craft": false
      },
      "item": "gold_platebody",
      "workshop": {
        "needed": "(3, 1)",
        "current": "(0, 0)"
      },
      "skill_level": {
        "skill": "gearcrafting",
        "needed": 30,
        "current": 1
      },
      "missing_items": [
        {
          "code": "demon_horn",
          "needed": 2,
          "got": 0
        },
        {
          "code": "owlbear_hair",
          "needed": 3,
          "got": 0
        },
        {
          "code": "demoniac_dust",
          "needed": 4,
          "got": 0
        },
        {
          "code": "gold",
          "needed": 8,
          "got": 0
        },
        {
          "code": "red_cloth",
          "needed": 3,
          "got": 0
        }
      ]
    }
  }
}
```

---

### BUY_ITEM
Buy an item at the grand-exchange tile.

**Path Params:**
- `name`: str - Character name

**Body Params:**
- `code`: str - Item code
- `quantity`: int - Quantity to buy

**URL:** `POST /my/{name}/action/buy`

**Response Codes:**
- 200: Item bought successfully
- 404: Item not found
- 498: Character not found
- 598: Grand-exchange not found on this map

---

### DELETE_ITEM
Deletes an item from inventory.

**Path Params:**
- `name`: str - Character name

**Body Params:**
- `code`: str - Item code
- `quantity`: int - Quantity to delete

**URL:** `POST /my/{name}/action/delete`

**Response Codes:**
- 200: Item deleted successfully
- 478: Missing item/insufficient quantity
- 498: Character not found

---

### GIVE_ITEM
Gives an item to another character.

**Path Params:**
- `name`: str - Character name

**Body Params:**
- `recipient`: str - Recipient name
- `code`: str - Item code
- `quantity`: int - Quantity to give

**URL:** `POST /my/{name}/action/give`

**Response Codes:**
- 200: Item given successfully
- 478: Missing item/insufficient quantity
- 498: Character not found
- 598: Recipient not found

---

## Maps

### get_all_maps
Fetches all maps details.

**Body Params:**
- `content_code`: str (optional) - Content code
- `content_type`: str (optional) - Content type (monster, resource, workshop, etc)

**URL:** `GET /maps`

**Response Codes:**
- 200: Maps fetched successfully
- 404: Maps not found

---

### get_map
Retrieves details of a specific map.

**Path Params:**
- `x`: int - Map X coordinate
- `y`: int - Map Y coordinate

**URL:** `GET /maps/{x}/{y}`

**Response Codes:**
- 200: Map fetched successfully
- 404: Map not found

---

## Resources

### get_all_resources
Fetches all resources details.

**Body Params:**
- `drop`: str (optional) - Item code of drop
- `max_level`: int (optional) - Max skill level
- `min_level`: int (optional) - Min skill level
- `skill`: str (optional) - Skill code (woodcutting, fishing, mining, etc)

**URL:** `GET /resources`

**Response Codes:**
- 200: Resources fetched successfully
- 404: Resources not found

---

### get_resource
Retrieves details of a specific resource.

**Path Params:**
- `code`: str - Resource code

**URL:** `GET /resources/{code}`

**Response Codes:**
- 200: Resource fetched successfully
- 404: Resource not found

---

## Monsters

### get_all_monsters
Fetches all monsters details.

**Body Params:**
- `drop`: str (optional) - Item code of drop
- `max_level`: int (optional) - Max level
- `min_level`: int (optional) - Min level

**URL:** `GET /monsters`

**Response Codes:**
- 200: Monsters fetched successfully
- 404: Monsters not found

---

### get_monster
Retrieves details of a specific monster.

**Path Params:**
- `code`: str - Monster code

**URL:** `GET /monsters/{code}`

**Response Codes:**
- 200: Monster fetched successfully
- 404: Monster not found

---

## Items

### get_all_items
Fetches all items details.

**Body Params:**
- `craft_material`: str (optional) - Material item code
- `craft_skill`: str (optional) - Crafting skill (cooking, weaponcrafting, gearcrafting, mining, jewelrycrafting, woodcutting, etc)
- `max_level`: int (optional) - Max level
- `min_level`: int (optional) - Min level
- `name`: str (optional) - Item name
- `type`: str (optional) - Item type

**URL:** `GET /items`

**Response Codes:**
- 200: Items fetched successfully
- 404: Items not found

---

### get_item
Retrieves details of a specific item.

**Path Params:**
- `code`: str - Item code

**URL:** `GET /items/{code}`

**Response Codes:**
- 200: Item fetched successfully
- 404: Item not found

---

## Characters

### create_character
Creates a new character.

**Body Params:**
- `name`: str - Character name (3-12 chars, unique)
- `skin`: str - Skin type

**URL:** `POST /characters/create`

**Response Codes:**
- 200: Character created successfully
- 494: Name already used

---

### create_custom_character
Creates a custom character.

**Body Params:**
- `name`: str - Character name
- `skin`: str - Skin type
- `char_data`: Dict - Custom character data

**URL:** `POST /characters/create_custom`

**Response Codes:**
- 200: Character created successfully
- 494: Name already used
- 498: Invalid JSON data

---

### delete_character
Deletes a character.

**Body Params:**
- `name`: str - Character name

**URL:** `POST /characters/delete`

**Response Codes:**
- 200: Character deleted successfully
- 498: Character not found

---

### get_all_characters
Fetches all characters.

**URL:** `GET /characters`

**Response Codes:**
- 200: Characters fetched successfully
- 404: No characters found

---

### get_character
Retrieves details of a specific character.

**Path Params:**
- `name`: str - Character name

**URL:** `GET /characters/{name}`

**Response Codes:**
- 200: Character fetched successfully
- 404: Character not found

---

## Logs

### get_logs
Retrieves the last N logs.

**Path Params:**
- `amount`: int (default=100) - Number of logs

**URL:** `GET /logs/{amount}`

**Response Codes:**
- 200: Logs fetched successfully
- 404: No logs found

---

### get_character_logs
Retrieves logs for a specific character.

**Path Params:**
- `name`: str - Character name
- `amount`: int (default=100) - Number of logs

**URL:** `GET /logs/{amount}/{name}`

**Response Codes:**
- 200: Logs fetched successfully
- 404: No logs found for character
