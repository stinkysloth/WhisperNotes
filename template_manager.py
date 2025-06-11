#!/usr/bin/env python3
"""
Template Manager for WhisperNotes application.
Handles loading, saving, and applying templates for journal entries.
"""
import os
import re
import json
import logging
import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path


class TemplateManager:
    """
    Manages templates for journal entries.
    Handles loading templates from files, applying templates to entries,
    and saving user template configurations.
    """
    
    # Template variables that can be replaced
    VARIABLES = {
        "title": "Entry title",
        "summary": "AI-generated summary of the entry",
        "transcript": "Full transcript of the recording",
        "audio": "Link to the audio recording",
        "timestamp": "Date and time of the recording",
        "tags": "User-defined tags for the entry"
    }
    
    # Default template content
    DEFAULT_TEMPLATE = """# {title}

## Summary
{summary}

## Transcript
{transcript}

## Metadata
- **Date**: {timestamp}
- **Tags**: {tags}

{audio}
"""
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the TemplateManager.
        
        Args:
            templates_dir: Directory to store and load templates from.
                          If None, uses '~/Documents/Personal/WhisperNotes Templates/'.
        """
        # Set templates directory
        if templates_dir is None:
            home_dir = os.path.expanduser("~")
            self.templates_dir = os.path.join(home_dir, "Documents", "Personal", "WhisperNotes Templates")
        else:
            self.templates_dir = templates_dir
            
        # Ensure directory exists
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # Create default template if no templates exist
        self._create_default_template_if_needed()
        
        # Load available templates
        self.templates = self._load_templates()
        
        # Template configurations (hotkeys, save locations, etc.)
        self.template_configs = {}
        
    def _create_default_template_if_needed(self) -> None:
        """Create default template files if the templates directory is empty."""
        # Check if any .md files exist in the templates directory
        template_files = list(Path(self.templates_dir).glob("*.md"))
        
        if not template_files:
            # Create default template
            default_path = os.path.join(self.templates_dir, "Default Template.md")
            with open(default_path, 'w', encoding='utf-8') as f:
                f.write(self.DEFAULT_TEMPLATE)
            
            # Create meeting notes template
            meeting_path = os.path.join(self.templates_dir, "Meeting Notes.md")
            meeting_template = """# Meeting: {title}

## Summary
{summary}

## Discussion Points
{transcript}

## Action Items
- 

## Attendees
- 

## Date
{timestamp}

## Tags
{tags}

{audio}
"""
            with open(meeting_path, 'w', encoding='utf-8') as f:
                f.write(meeting_template)
                
            # Create quick note template
            quick_path = os.path.join(self.templates_dir, "Quick Note.md")
            quick_template = """# Quick Note: {title}

{transcript}

*Recorded on {timestamp}*

{audio}
"""
            with open(quick_path, 'w', encoding='utf-8') as f:
                f.write(quick_template)
                
            logging.info(f"Created default templates in {self.templates_dir}")
    
    def _load_templates(self) -> Dict[str, str]:
        """
        Load all template files from the templates directory.
        
        Returns:
            Dict mapping template names to file paths
        """
        templates = {}
        
        try:
            for file_path in Path(self.templates_dir).glob("*.md"):
                template_name = file_path.stem
                templates[template_name] = str(file_path)
                
            logging.info(f"Loaded {len(templates)} templates from {self.templates_dir}")
        except Exception as e:
            logging.error(f"Error loading templates: {e}")
            
        return templates
    
    def get_template_content(self, template_name: str) -> str:
        """
        Get the content of a template by name.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Template content as string
        """
        if template_name not in self.templates:
            logging.warning(f"Template '{template_name}' not found, using default")
            return self.DEFAULT_TEMPLATE
            
        try:
            with open(self.templates[template_name], 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logging.error(f"Error reading template '{template_name}': {e}")
            return self.DEFAULT_TEMPLATE
    
    def apply_template(self, template_name: str, entry_data: Dict[str, Any]) -> str:
        """
        Apply a template to a journal entry.
        
        Args:
            template_name: Name of the template to apply
            entry_data: Dictionary containing journal entry data
            
        Returns:
            Formatted entry content with template applied
        """
        # Get template content
        template_content = self.get_template_content(template_name)
        
        # Prepare variables for replacement
        variables = {
            "title": entry_data.get("title", f"Journal Entry - {entry_data.get('timestamp', '')}"),
            "summary": entry_data.get("summary", ""),
            "transcript": entry_data.get("formatted_text", entry_data.get("transcription", "")),
            "timestamp": entry_data.get("timestamp", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "tags": entry_data.get("tags", ""),
        }
        
        # Add audio link if available
        if entry_data.get("relative_audio_path"):
            variables["audio"] = f"🔊 [Listen to recording]({entry_data['relative_audio_path']})"
        else:
            variables["audio"] = ""
        
        # Apply template
        result = template_content
        for var_name, var_value in variables.items():
            placeholder = "{" + var_name + "}"
            result = result.replace(placeholder, str(var_value))
            
        return result
    
    def load_template_configs(self, config_data: Dict[str, Any]) -> None:
        """
        Load template configurations from settings.
        
        Args:
            config_data: Dictionary containing template configurations
        """
        self.template_configs = config_data or {}
    
    def save_template_config(self, template_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save configuration for a template.
        
        Args:
            template_name: Name of the template
            config: Configuration dictionary with hotkey, save_location, etc.
            
        Returns:
            Updated template configurations dictionary
        """
        self.template_configs[template_name] = config
        return self.template_configs
    
    def get_template_config(self, template_name: str) -> Dict[str, Any]:
        """
        Get configuration for a template.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Template configuration dictionary
        """
        return self.template_configs.get(template_name, {})
    
    def get_template_by_hotkey(self, hotkey_str: str) -> Optional[str]:
        """
        Find a template that matches the given hotkey.
        
        Args:
            hotkey_str: String representation of the hotkey
            
        Returns:
            Template name if found, None otherwise
        """
        for template_name, config in self.template_configs.items():
            if config.get("hotkey") == hotkey_str:
                return template_name
        return None
