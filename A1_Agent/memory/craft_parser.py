import json
import os

from memory.name_formater import name_formater
from pathlib import Path
class CraftParser:
    """
    Parser for analyzing crafting chains and item acquisition information.
    
    This class provides functionality to parse and analyze crafting recipes,
    item locations, and acquisition methods. It loads data from multiple
    JSON sources including items, maps, monsters, and resources.
    """

    def __init__(self) -> None:
        """
        Initialize the CraftParser with data from JSON files.
        
        Loads item, map, monster, and resource data from the source_jsons
        directory for use in crafting analysis.
        """
        base_path = Path('./memory/source_jsons').resolve()
        items_data_path =  base_path / 'items.json'
        maps_data_path = base_path / 'maps.json'
        monsters_data_path = base_path / 'monsters.json'
        resources_data_path = base_path /  'resources.json'

        with open(items_data_path, 'r') as data_file:
            self.items = json.load(data_file)

        with open(maps_data_path, 'r') as data_file:
            self.maps = json.load(data_file)

        with open(monsters_data_path, 'r') as data_file:
            self.monsters = json.load(data_file)

        with open(resources_data_path, 'r') as data_file:
            self.resources = json.load(data_file)

    def get_item_name(self, item_code: str) -> str:
        """
        Get the name of an item from its code.
        
        Args:
            item_code: The item code to look up
            
        Returns:
            The name of the item
        """
        for item in self.items:
            if item['code'] == item_code:
                return item['name']

    def get_item_acquisition_location(self,item_code: str,search_type: str, skill: str = '') -> tuple[int,int,str]:
        """
        Get the location where an item can be acquired.
        
        This method searches for the location where an item can be obtained
        based on the search type (workshop, monster, or resource).
        
        Args:
            item_code: The code of the item to find location for
            search_type: Type of search ('workshop', 'monster', or 'resource')
            skill: Required skill for workshop crafting (used when search_type is 'workshop')
            
        Returns:
            Tuple containing:
                - x: X coordinate of the acquisition location
                - y: Y coordinate of the acquisition location
                - source: Name of the source (workshop, monster name, or resource name)
                
        Raises:
            ValueError: If item location is not found
        """
        x = 0
        y = 0
        source = 'Unknown'
        if search_type == 'workshop':
            for tile in self.maps:
                if tile['content'] is not None:
                    if tile['content']['code'] == skill:
                        x = tile['x']
                        y = tile['y']
                        source = 'workshop'

        if search_type == 'monster':
            for monster in self.monsters:
                for drops in monster['drops']:
                    if drops['code'] == item_code:
                        monster_code = monster['code']
                        for tile in self.maps:
                            if tile['content'] is not None:
                                if tile['content']['code'] == monster_code:
                                    x = tile['x']
                                    y = tile['y']
                                    source = monster['name']

        if search_type == 'resource':
            for resource in self.resources:
                for drops in resource['drops']:
                    if drops['code'] == item_code:
                        resource_code = resource['code']
                        for tile in self.maps:
                            if tile['content'] is not None:
                                if tile['content']['code'] == resource_code:
                                    x = tile['x']
                                    y = tile['y']
                                    source = resource['name']
        if source == 'Unknown':  ValueError('Item location not found')
        return x,y,source

    @staticmethod
    def effects_text(effects: dict, item_name: str) -> str:
        """
        Format item effects into a readable text string.
        
        Args:
            effects: Dictionary containing item effects
            item_name: Name of the item for context
            
        Returns:
            Formatted string describing the item's effects
        """
        effects_text = f'Item {item_name} effects:'
        for effect in effects:
            effect_name = effect['name']
            effect_value = effect['value']
            effects_text += f'{name_formater(effect_name, effect_value)},'
        return effects_text

    def get_item_data(self, item_code: str) -> dict:
        """
        Get comprehensive data about an item including crafting requirements and location.
        
        This method searches through items, resources, and monsters to find
        complete information about how to acquire an item.
        
        Args:
            item_code: The code of the item to get data for
            
        Returns:
            Dictionary containing item information with keys:
                - item_name: Human-readable name of the item
                - item_type: Type of item ('raw resource', 'monster drop', or crafted)
                - item_subtype: Subtype of the item
                - item_acquisition_x: X coordinate where item can be acquired
                - item_acquisition_y: Y coordinate where item can be acquired
                - item_source: Source of the item (workshop, monster name, or resource name)
                - crafting_skill: Skills required to craft the item
                - crafting_skill_level: Skills levels required to craft the item
                - craft_components_codes_with_quant: List of required components with quantities
                - effects: Formatted text describing item effects
                
        Raises:
            ValueError: If item is not found in any data source
        """
        item_found = False
        item_name = 'Unknown'
        item_type = 'Unknown'
        item_subtype = 'Unknown'
        item_acquisition_x = 0
        item_acquisition_y = 0
        item_source = 'Unknown'
        crafting_skill = 'Unknown'
        crafting_skill_level = 0
        craft_components_codes_with_quant = []
        effects = ''
        item_name = self.get_item_name(item_code)

        if not item_found:
            for item in self.items:
                if item['code'] == item_code:
                    item_type = item['type']
                    item_subtype = item['subtype']
                    if 'effects' in item and len(effects)>0:
                        effects = self.effects_text(item['effects'], item['name'])
                    if item['craft'] is not None:
                        craft_data = item['craft']
                        crafting_skill = craft_data['skill']
                        crafting_skill_level = craft_data['level']
                        for craft_item in craft_data['items']:
                            craft_components_codes_with_quant.append([craft_item['code'],craft_item['quantity'],self.get_item_name(craft_item['code'])])
                    else:
                        continue

                    item_acquisition_x, item_acquisition_y, item_source = self.get_item_acquisition_location(item_code,
                                                                                                             search_type = 'workshop',
                                                                                                             skill = crafting_skill)
                    item_found = True

        if not item_found:
            for resource in self.resources:
                for resource_drop in resource['drops']:
                    if resource_drop['code'] == item_code:
                        item_type = 'raw resource'
                        item_subtype = 'raw resource'
                        crafting_skill = resource['skill']
                        crafting_skill_level = resource['level']
                        item_acquisition_x, item_acquisition_y, item_source = self.get_item_acquisition_location(item_code,
                                                                                                                 search_type = 'resource')
                        item_found = True

        if not item_found:
            for monster in self.monsters:
                for monster_drop in monster['drops']:
                    if monster_drop['code'] == item_code:
                        item_type = 'monster drop'
                        item_subtype = 'monster drop'
                        item_acquisition_x, item_acquisition_y, item_source = self.get_item_acquisition_location(item_code,
                                                                                                                 search_type = 'monster')
                        item_found = True
        if not item_found:  ValueError('Item not found')
        return {
            'item_name': item_name,
            'item_type': item_type,
            'item_subtype': item_subtype,
            'item_acquisition_x': item_acquisition_x,
            'item_acquisition_y': item_acquisition_y,
            'item_source': item_source,
            'crafting_skill': crafting_skill,
            'crafting_skill_level': crafting_skill_level,
            'craft_components_codes_with_quant': craft_components_codes_with_quant,
            'effects': effects
        }

    def parse(self, item_code: str) -> list:
        """
        Parse the complete crafting chain for an item.
        
        This method recursively analyzes all components required to craft
        an item, building a complete dependency tree of all required
        materials and their acquisition methods.
        
        Args:
            item_code: The code of the item to parse the crafting chain for
            
        Returns:
            List of dictionaries containing data for all items in the crafting chain,
            including the target item and all its required components
        """
        items = []
        next_parse_items = []
        target_item = self.get_item_data(item_code)
        items.append(target_item)
        for item in target_item['craft_components_codes_with_quant']:
            next_parse_items.append(item[0])

        nothing_to_parse = False
        while not nothing_to_parse:
            if len(next_parse_items) == 0:
                nothing_to_parse = True
                break

            new_next_parse_items = []
            for next_parse_item in next_parse_items:
                new_item_data = self.get_item_data(next_parse_item)
                items.append(new_item_data)
                for item in new_item_data['craft_components_codes_with_quant']:
                    new_next_parse_items.append(item[0])

            next_parse_items = new_next_parse_items

        return items

def item_to_text(item_data: dict) -> str:
    """
    Convert item data to formatted text description.
    
    This function creates a human-readable description of an item including
    its acquisition method, location, required resources, and effects.
    
    Args:
        item_data: Dictionary containing item information from get_item_data()
        
    Returns:
        Formatted string describing the item and how to acquire it
    """
    item_text_head = ''
    item_name = item_data['item_name']
    x_pos = item_data['item_acquisition_x']
    y_pos = item_data['item_acquisition_y']
    item_source = item_data['item_source']

    if item_data['item_source'] == 'workshop':
        item_text_head = f'{item_name} \nItem "{item_name}" crafted at location X = {x_pos}, Y = {y_pos}. \nRequired resources: '

    elif item_data['item_type'] == 'raw resource':
        item_text_head = f'{item_name} \nItem "{item_name}" gathered at location X = {x_pos}, Y = {y_pos}. \nItem source: "{item_source}" '

    elif item_data['item_type'] == 'monster drop':
        item_text_head = f'{item_name} \nItem "{item_name}" collected at location X = {x_pos}, Y = {y_pos}. \nDrops from monster: "{item_source}" '
    else:
        item_text_head = f"{item_name} \nThis item can't be acquired from game world"
    text_main = ''

    for item in item_data['craft_components_codes_with_quant']:
        text_main += f'{item[1]} items "{item[2]}", \n'

    text_full = item_text_head + text_main
    if 'effects' in item_data:
        text_full += f"\n{item_data['effects']}"
    return text_full

def to_text(items: list) -> tuple[str,str]:
    """
    Convert a list of items to formatted text descriptions and skill requirements.
    
    This function processes a list of item data and generates both a
    comprehensive text description of all items and a summary of required skills.
    
    Args:
        items: List of item data dictionaries from parse() method
        
    Returns:
        Tuple containing:
            - item_text: Formatted text describing all items and their acquisition methods
            - skills_text: Formatted text listing required skills and their levels
    """
    item_text = ''
    skills = {}
    for item in items:
        item_text += item_to_text(item)
        skill = item['crafting_skill']
        skill_level = item['crafting_skill_level']
        if skill != 'Unknown':
            if skill not in skills.keys():
                skills[skill] = skill_level
            else:
                if skills[skill] < skill_level:
                    skills[skill] = skill_level
    skills_text = ''
    if len(skills.keys()) > 0:
        for skill in skills.keys():
            skills_text += f'Skill "{skill}" (level {skills[skill]})\n'

    return item_text, skills_text

