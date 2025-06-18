"""
Prompts Module for Sapiens Engine

This module provides a collection of organized prompts for different dialogue types, 
voice styles, emotions, and more to be used throughout the Sapiens Engine.

Directory Structure:
- dialogue_types/ - Prompts for different dialogue types (debate, conversation, interview, etc.)
- voice_styles/ - Voice and tone style prompts (formal, casual, poetic, etc.)
- emotions/ - Emotion-focused prompts (happy, sad, angry, etc.)
- context/ - Context-aware prompting and conversation flow
- humor/ - Humor-related prompts and styles
- personality/ - Personality traits and character prompts
- system/ - System and general instruction prompts
- templates/ - Reusable prompt templates
- utils/ - Utility functions for prompt processing

Usage:
    from sapiens_engine.prompts import load_prompt

    # Load a debate moderator prompt
    moderator_prompt = load_prompt('debate', 'moderator')
    
    # Load with variable substitution
    opening_prompt = load_prompt('debate', 'opening', 
                                topic="AI Ethics",
                                pro_side=["Kant", "Aristotle"],
                                con_side=["Nietzsche"])
"""

import os
import yaml
import json
import logging
from pathlib import Path
from string import Template
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

# Base directory for prompts
PROMPTS_DIR = Path(__file__).parent

def load_prompt(category: str, prompt_name: str, **kwargs) -> Dict[str, str]:
    """
    Load a prompt from the appropriate category and fill in any variables.
    
    Args:
        category: The category of prompt (debate, emotion, voice_style, etc.)
        prompt_name: The specific prompt to load
        **kwargs: Variables to substitute in the prompt template
        
    Returns:
        Dict containing system_prompt and user_prompt keys
    """
    file_path = get_prompt_path(category, prompt_name)
    prompt_data = load_prompt_file(file_path)
    
    if not prompt_data:
        logger.warning(f"Prompt not found: {category}/{prompt_name}")
        return {"system_prompt": "", "user_prompt": ""}
    
    # Fill in template variables if any
    if kwargs:
        for key, value in prompt_data.items():
            if isinstance(value, str):
                template = Template(value)
                prompt_data[key] = template.safe_substitute(**kwargs)
    
    return prompt_data

def get_prompt_path(category: str, prompt_name: str) -> Path:
    """Get the file path for a prompt."""
    # Check if the category is a direct subdirectory
    if (PROMPTS_DIR / category).is_dir():
        base_path = PROMPTS_DIR / category
    # Or if it's within dialogue_types
    elif (PROMPTS_DIR / "dialogue_types" / category).is_dir():
        base_path = PROMPTS_DIR / "dialogue_types" / category
    else:
        # Default to the main prompts directory
        base_path = PROMPTS_DIR
    
    # Try different file extensions
    for ext in ['.yaml', '.yml', '.json']:
        file_path = base_path / f"{prompt_name}{ext}"
        if file_path.exists():
            return file_path
    
    # If no specific file found, look for a directory with an index file
    if (base_path / prompt_name).is_dir():
        for ext in ['.yaml', '.yml', '.json']:
            file_path = base_path / prompt_name / f"index{ext}"
            if file_path.exists():
                return file_path
    
    logger.warning(f"Could not find prompt file for {category}/{prompt_name}")
    return base_path / f"{prompt_name}.yaml"  # Return a default path even if it doesn't exist

def load_prompt_file(file_path: Path) -> Dict[str, Any]:
    """Load and parse a prompt file."""
    if not file_path.exists():
        logger.warning(f"Prompt file not found: {file_path}")
        return {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            if file_path.suffix in ['.yaml', '.yml']:
                return yaml.safe_load(file)
            elif file_path.suffix == '.json':
                return json.load(file)
            else:
                # Plain text file - assume it's just a prompt with no system message
                return {"user_prompt": file.read(), "system_prompt": ""}
    except Exception as e:
        logger.error(f"Error loading prompt file {file_path}: {e}")
        return {}

# Export public functions
__all__ = ['load_prompt', 'get_prompt_path', 'load_prompt_file']
