import json
import os
from pathlib import Path

class AvailableItems:
    """
    Class for determining items available for craft based on character skills and equipment.
    
    This class analyzes character skills and current equipment to determine
    which items can be crafted. It considers skill requirements and filters
    out items that are already equipped or in inventory.
    """

    def __init__(self, skill_cutout: bool = True) -> None:
        """
        Initialize the AvailableItems analyzer with configuration.
        
        Args:
            skill_cutout: Whether to apply skill level filtering (default: True)
        """
        self.skills = ['weaponcrafting', 'gearcrafting', 'jewelrycrafting', 'cooking', 'mining', 'woodcutting', 'alchemy']
        self.items_data_path = Path('./memory/source_jsons/armor_weapon_db.json').resolve()
        self.no_items_message = 'No items currently available!'
        self.skill_cutout = skill_cutout
        with open(self.items_data_path) as f:
            self.items = json.load(f)

    @staticmethod
    def check_item(item_skills: dict, character_skills: dict, min_skill_level: int) -> bool:
        """
        Check if character meets the skill requirements for an item.
        
        This method verifies that the character has sufficient skill levels
        for all required skills of an item, considering the minimum skill level.
        
        Args:
            item_skills: Dictionary of skill requirements for the item
            character_skills: Dictionary of character's current skill levels
            min_skill_level: Minimum skill level threshold
            
        Returns:
            Boolean indicating whether the character can craft the item
        """
        condition_satisfied = True
        for skill_name, skill_value in item_skills.items():
            character_skill_value = character_skills[skill_name]
            if character_skill_value < skill_value or skill_value < min_skill_level:
                condition_satisfied = False
        return condition_satisfied

    def min_skill_level(self, skills: dict) -> int :
        """
        Calculate the minimum skill level for item filtering.
        
        This method determines the minimum skill level threshold based on
        the character's current skills. If skill_cutout is enabled, it
        applies additional filtering logic.
        
        Args:
            skills: Dictionary of character's current skill levels
            
        Returns:
            Integer representing the minimum skill level threshold
        """
        min_level = int(1e50)
        if not self.skill_cutout:
            return min_level
        for _, skill_level in skills.items():
            if skill_level < min_level:
                min_level = skill_level
        if min_level > 6:
            min_level -= 5
        return min_level

    @staticmethod
    def parse_equipment(character_equipment: dict) -> list:
        """
        Extract equipped item names from character equipment data.
        
        Args:
            character_equipment: Dictionary containing character equipment data
            
        Returns:
            List of equipped item names
        """
        current_equipment = []
        for slot in ['weapon_slot', 'shield_slot','helmet_slot','body_armor_slot', 'leg_armor_slot', 'boots_slot','ring1_slot', 'ring2_slot', 'amulet_slot']:
            equipment_code = character_equipment[slot]
            equipment_name = equipment_code.replace('_',' ').title()
            current_equipment.append(equipment_name)
        return current_equipment

    @staticmethod
    def parse_inventory(character_equipment: dict) -> list:
        """
        Extract item names from character inventory data.
        
        Args:
            character_equipment: Dictionary containing character inventory data
            
        Returns:
            List of item names in inventory
        """
        inventory = character_equipment['inventory']
        items_in_inventory = []
        for slot in inventory:
            item_name = slot['code']
            item_name = item_name.replace('_',' ').title()
            items_in_inventory.append(item_name)
        return items_in_inventory


    def get_items(self, character_skills: dict, character_state: dict) -> str:
        """
        Get list of available crafting items based on character state.
        
        This method analyzes the character's skills, equipment, and inventory
        to determine which items can be crafted. It filters out items that
        are already owned and applies skill requirements.
        
        Args:
            character_skills: Dictionary of character's current skill levels
            character_state: Dictionary containing character's current state
                           including equipment and inventory
                           
        Returns:
            String containing formatted list of available items with effects,
            or message indicating no items are available
        """
        available_items_names = []
        equipped_items = self.parse_equipment(character_state)
        equipped_items += self.parse_inventory(character_state)
        min_skill_level = self.min_skill_level(character_skills)
        for item_name, item_data in self.items.items():
            item_skills = item_data['skills']
            item_check_satisfy = self.check_item(item_skills, character_skills, min_skill_level)
            if item_check_satisfy and item_name not in equipped_items:
                available_items_names.append(f'- {item_name}:\n {item_data['effects']} \n')
        if len(available_items_names) == 0:
            return self.no_items_message
        available_items_names_text = ''.join(available_items_names)

        return available_items_names_text

