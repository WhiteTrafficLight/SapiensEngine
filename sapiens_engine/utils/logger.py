import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

class SimulationLogger:
    """
    Logger for the philosophical simulation
    """
    
    def __init__(self, log_dir: str, log_level: str = "info"):
        """
        Initialize the simulation logger
        
        Args:
            log_dir: Directory where logs will be stored
            log_level: Logging level (debug, info, warning, error, critical)
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Convert string log level to logging constant
        level_map = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL
        }
        log_level_value = level_map.get(log_level.lower(), logging.INFO)
        
        # Set up the root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level_value)
        
        # Clear any existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        # Create a file handler
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"simulation_{timestamp}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        
        # Create a console handler
        console_handler = logging.StreamHandler()
        
        # Set the log level for both handlers
        file_handler.setLevel(log_level_value)
        console_handler.setLevel(log_level_value)
        
        # Create a formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add the handlers to the root logger
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        self.logger = root_logger
        self.log_file = log_file
        
    def debug(self, message: str):
        """Log a debug message"""
        self.logger.debug(message)
        
    def info(self, message: str):
        """Log an info message"""
        self.logger.info(message)
        
    def warning(self, message: str):
        """Log a warning message"""
        self.logger.warning(message)
        
    def error(self, message: str):
        """Log an error message"""
        self.logger.error(message)
        
    def critical(self, message: str):
        """Log a critical message"""
        self.logger.critical(message)
        
    def log_dialogue(self, dialogue: Dict[str, Any], level: str = "info"):
        """
        Log a dialogue exchange
        
        Args:
            dialogue: Dictionary containing dialogue information
            level: Log level for the message
        """
        if level.lower() == "debug":
            log_method = self.debug
        elif level.lower() == "info":
            log_method = self.info
        elif level.lower() == "warning":
            log_method = self.warning
        elif level.lower() == "error":
            log_method = self.error
        elif level.lower() == "critical":
            log_method = self.critical
        else:
            log_method = self.info
            
        # Log the dialogue in a formatted way
        log_method(f"Dialogue on topic: {dialogue.get('topic', 'Unknown')}")
        
        for exchange in dialogue.get("exchanges", []):
            speaker = exchange.get("speaker", "Unknown")
            content = exchange.get("content", "")
            log_method(f"  {speaker}: {content}")
            
        log_method(f"End of dialogue")
        
    def get_log_file_path(self) -> str:
        """Get the path to the current log file"""
        return self.log_file 
 