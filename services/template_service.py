"""
Template service for managing journal entry templates.

This module provides the TemplateService class which handles the creation,
management, and application of markdown templates for journal entries.
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QMutex

from core.constants import AppConstants
from utils.file_utils import ensure_directory_exists

logger = logging.getLogger(__name__)

class TemplateService(QObject):
    """Service for managing journal entry templates."""
    
    # Signals
    templates_loaded = Signal()
    template_added = Signal(dict)        # template data
    template_updated = Signal(dict)      # template data
    template_deleted = Signal(str)       # template_id
    error_occurred = Signal(str)         # error_message
    
    def __init__(self, config_dir: Optional[str] = None):
        """Initialize the template service.
        
        Args:
            config_dir: Optional directory to store template configurations.
                      If not provided, a default will be used.
        """
        super().__init__()
        self.config_dir = config_dir or os.path.join(
            os.path.expanduser("~"),
            ".config",
            AppConstants.ORGANIZATION.lower()
        )
        self.templates_file = os.path.join(self.config_dir, "templates.json")
        self.templates = {}
        self.active_template = None
        self.mutex = QMutex()
        self._ensure_config_dir()
        self.load_templates()
    
    def _ensure_config_dir(self) -> None:
        """Ensure the configuration directory exists."""
        try:
            ensure_directory_exists(self.config_dir)
            logger.info(f"Using template config directory: {self.config_dir}")
        except Exception as e:
            error_msg = f"Failed to create config directory: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
    
    def load_templates(self) -> bool:
        """Load templates from the configuration file.
        
        Returns:
            bool: True if templates were loaded successfully, False otherwise
        """
        if not os.path.exists(self.templates_file):
            logger.info("No templates file found, using default templates")
            self._create_default_templates()
            return True
            
        try:
            with open(self.templates_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.templates = data.get('templates', {})
            self.active_template = data.get('active_template')
            
            logger.info(f"Loaded {len(self.templates)} templates from {self.templates_file}")
            self.templates_loaded.emit()
            return True
            
        except Exception as e:
            error_msg = f"Failed to load templates: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False
    
    def _create_default_templates(self) -> None:
        """Create default templates if none exist."""
        default_templates = {
            "default": {
                "id": "default",
                "name": "Default",
                "content": "# {title}\n\n{content}",
                "hotkey": "",
                "created_at": self._current_timestamp(),
                "updated_at": self._current_timestamp()
            },
            "meeting": {
                "id": "meeting",
                "name": "Meeting Notes",
                "content": "# Meeting Notes: {title}\n\n**Date:** {date:%Y-%m-%d}\n**Time:** {time:%H:%M}\n**Attendees:** \n\n## Agenda\n\n## Discussion Points\n\n## Decisions\n\n## Action Items\n- [ ] ",
                "hotkey": "",
                "created_at": self._current_timestamp(),
                "updated_at": self._current_timestamp()
            },
            "journal": {
                "id": "journal",
                "name": "Journal Entry",
                "content": "# {title}\n\n**Date:** {date:%Y-%m-%d}  
**Time:** {time:%H:%M}  \n\n## What happened today?\n\n## How do I feel about it?\n\n## What am I grateful for?\n\n## What did I learn?\n\n## Tomorrow's Goals\n- [ ] ",
                "hotkey": "",
                "created_at": self._current_timestamp(),
                "updated_at": self._current_timestamp()
            }
        }
        
        self.templates = default_templates
        self.save_templates()
    
    def save_templates(self) -> bool:
        """Save templates to the configuration file.
        
        Returns:
            bool: True if templates were saved successfully, False otherwise
        """
        try:
            data = {
                'templates': self.templates,
                'active_template': self.active_template,
                'version': '1.0'
            }
            
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.templates)} templates to {self.templates_file}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to save templates: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a template by ID.
        
        Args:
            template_id: ID of the template to retrieve
            
        Returns:
            Dict containing the template data, or None if not found
        """
        return self.templates.get(template_id)
    
    def get_all_templates(self) -> List[Dict[str, Any]]:
        """Get all templates.
        
        Returns:
            List of template dictionaries, sorted by name
        """
        return sorted(
            list(self.templates.values()),
            key=lambda x: x.get('name', '').lower()
        )
    
    def add_template(self, template_data: Dict[str, Any]) -> bool:
        """Add a new template.
        
        Args:
            template_data: Dictionary containing template data
            
        Returns:
            bool: True if template was added successfully, False otherwise
        """
        try:
            template_id = template_data.get('id')
            if not template_id:
                template_id = self._generate_template_id(template_data.get('name', ''))
            
            if template_id in self.templates:
                error_msg = f"Template with ID '{template_id}' already exists"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                return False
            
            template = {
                'id': template_id,
                'name': template_data.get('name', 'Untitled Template'),
                'content': template_data.get('content', ''),
                'hotkey': template_data.get('hotkey', ''),
                'created_at': self._current_timestamp(),
                'updated_at': self._current_timestamp()
            }
            
            self.templates[template_id] = template
            
            if not self.active_template:
                self.active_template = template_id
            
            if self.save_templates():
                self.template_added.emit(template)
                return True
            return False
            
        except Exception as e:
            error_msg = f"Failed to add template: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False
    
    def update_template(self, template_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing template.
        
        Args:
            template_id: ID of the template to update
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        if template_id not in self.templates:
            error_msg = f"Template with ID '{template_id}' not found"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
            
        try:
            template = self.templates[template_id].copy()
            
            # Update fields
            for key, value in updates.items():
                if key in ['id', 'created_at']:
                    continue  # Don't allow updating these fields
                if key in template:
                    template[key] = value
            
            template['updated_at'] = self._current_timestamp()
            self.templates[template_id] = template
            
            if self.save_templates():
                self.template_updated.emit(template)
                return True
            return False
            
        except Exception as e:
            error_msg = f"Failed to update template: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template.
        
        Args:
            template_id: ID of the template to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        if template_id not in self.templates:
            return False
            
        try:
            # Don't allow deleting the default template
            if template_id == 'default':
                error_msg = "Cannot delete the default template"
                logger.warning(error_msg)
                self.error_occurred.emit(error_msg)
                return False
            
            # If the active template is being deleted, set a new active template
            if self.active_template == template_id:
                # Find another template to make active
                other_templates = [tid for tid in self.templates if tid != template_id]
                self.active_template = other_templates[0] if other_templates else None
            
            del self.templates[template_id]
            
            if self.save_templates():
                self.template_deleted.emit(template_id)
                return True
            return False
            
        except Exception as e:
            error_msg = f"Failed to delete template: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False
    
    def set_active_template(self, template_id: str) -> bool:
        """Set the active template.
        
        Args:
            template_id: ID of the template to set as active
            
        Returns:
            bool: True if active template was set successfully, False otherwise
        """
        if template_id not in self.templates:
            error_msg = f"Template with ID '{template_id}' not found"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
            
        self.active_template = template_id
        return self.save_templates()
    
    def get_active_template(self) -> Optional[Dict[str, Any]]:
        """Get the active template.
        
        Returns:
            Dict containing the active template data, or None if no active template
        """
        if not self.active_template:
            return None
        return self.templates.get(self.active_template)
    
    def apply_template(self, template_id: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Apply a template with the given context.
        
        Args:
            template_id: ID of the template to apply
            context: Dictionary of template variables
            
        Returns:
            str: Rendered template content
        """
        template = self.get_template(template_id)
        if not template:
            error_msg = f"Template with ID '{template_id}' not found"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return ""
        
        try:
            from datetime import datetime
            
            # Default context
            ctx = {
                'title': 'Untitled',
                'content': '',
                'date': datetime.now(),
                'time': datetime.now(),
                **(context or {})
            }
            
            # Apply template formatting
            content = template['content']
            
            # Simple string formatting (can be enhanced with a template engine)
            try:
                return content.format(**ctx)
            except KeyError as e:
                error_msg = f"Missing template variable: {str(e)}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                return content
                
        except Exception as e:
            error_msg = f"Failed to apply template: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return ""
    
    def _generate_template_id(self, name: str) -> str:
        """Generate a template ID from a name.
        
        Args:
            name: Template name
            
        Returns:
            str: Generated template ID
        """
        import re
        import time
        
        # Convert to lowercase and replace spaces with underscores
        template_id = name.lower().replace(' ', '_')
        
        # Remove invalid characters
        template_id = re.sub(r'[^a-z0-9_]', '', template_id)
        
        # Ensure ID is unique
        if template_id in self.templates:
            template_id = f"{template_id}_{int(time.time())}"
        
        return template_id
    
    @staticmethod
    def _current_timestamp() -> str:
        """Get the current timestamp as an ISO format string.
        
        Returns:
            str: Current timestamp in ISO format
        """
        from datetime import datetime
        return datetime.now().isoformat()
