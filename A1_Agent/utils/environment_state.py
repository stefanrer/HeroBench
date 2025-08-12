import os
from pathlib import Path
from env_api.actions_executors import CharacterInfo
from memory.available_items_craft import AvailableItems
from utils.state_parse import character_state_parse

class EnvironmentState:
    """
    Class for managing and providing comprehensive environment state information.
    
    This class aggregates character information, available crafting items,
    and map data to provide a complete view of the game environment state
    for agent decision-making.
    """

    def __init__(self, character_name: str) -> None:
        """
        Initialize the EnvironmentState with character and data sources.
        
        Args:
            character_name: Name of the character to track state for
        """
        self.character_info = CharacterInfo(character_name)
        self.available_items = AvailableItems(skill_cutout=True)
        self.maps = ''
        maps_path = Path('./memory/MAPS.txt').resolve()
        with open(maps_path, 'r') as f:
            self.maps = f.read()

    def get_environment_state(self, missing_items_text: str) -> dict:
        """
        Get the complete environment state for agent decision-making.
        
        This method combines character state, available crafting items,
        map information, and missing items to provide a comprehensive
        view of the current game environment.
        
        Args:
            missing_items_text: Text describing items that are missing from inventory
            
        Returns:
            Dictionary containing complete environment state with keys:
                - character_stats: Formatted character statistics
                - character_equipment: Current equipment information
                - character_inventory: Inventory contents
                - character_skills: Skill levels
                - skills_dict: Dictionary of skill levels
                - available_craft: Available crafting items or missing items text
                - map_content: Map information
        """
        character_state = self.character_info.action()
        character_parsed_state = character_state_parse(character_state)
        map_static = self.maps
        available_items = self.available_items.get_items(character_parsed_state['skills_dict'],character_state)
        if missing_items_text != '':
            character_parsed_state['available_craft'] = missing_items_text
        else:
            character_parsed_state['available_craft'] = available_items
        character_parsed_state['map_content'] = map_static
        return character_parsed_state

