import os
import yaml
from typing import Dict, Any, List, Optional

class ConfigLoader:
    """Loads and manages configuration from YAML files"""
    
    def __init__(self, config_dir: str = None):
        """
        Initialize the config loader
        
        Args:
            config_dir: Directory where config files are located. Defaults to 'config/'
        """
        self.config_dir = config_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        self.config_cache = {}
        
    def load_config(self, config_name: str) -> Dict[str, Any]:
        """
        Load a configuration file by name
        
        Args:
            config_name: Name of the config file without extension
            
        Returns:
            Dict containing the configuration
        """
        if config_name in self.config_cache:
            return self.config_cache[config_name]
            
        config_path = os.path.join(self.config_dir, f"{config_name}.yaml")
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        self.config_cache[config_name] = config
        return config
        
    def get_main_config(self) -> Dict[str, Any]:
        """Returns the main configuration"""
        return self.load_config("config")
        
    def get_npcs_config(self) -> Dict[str, Any]:
        """Returns the NPCs configuration"""
        return self.load_config("npcs")
        
    def get_npc_by_id(self, npc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get NPC configuration by ID
        
        Args:
            npc_id: The ID of the NPC to retrieve
            
        Returns:
            Dict containing the NPC configuration or None if not found
        """
        npcs_config = self.get_npcs_config()
        for npc in npcs_config.get("npcs", []):
            if npc.get("id") == npc_id:
                return npc
        return None
        
    def get_all_npcs(self) -> List[Dict[str, Any]]:
        """Returns all NPC configurations"""
        return self.get_npcs_config().get("npcs", []) 
 