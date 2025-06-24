"""Settings management for WhisperNotes application."""
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Optional, List

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.config import AppConfig, NoteTypeConfig

logger = logging.getLogger(__name__)

class SettingsManager:
    """Manages application settings and configurations."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the settings manager.
        
        Args:
            config_path: Path to the configuration file. If not provided, uses default location.
        """
        self.config_path = config_path or self.get_default_config_path()
        self.config: Optional[AppConfig] = None
        self._load_config()
    
    @staticmethod
    def get_default_config_path() -> Path:
        """Get the default configuration file path.
        
        Returns:
            Path to the default configuration file.
        """
        config_dir = Path.home() / ".config" / "whisper-notes"
        return config_dir / "config.json"
    
    def _load_config(self):
        """Load the configuration from disk or create a default one."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Use model_validate to create the model from the dict
                    self.config = AppConfig.model_validate(data)
                    logger.info(f"Loaded config from {self.config_path}")
            else:
                self.config = AppConfig()
                self._save_config()
                logger.info("Created default config")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            # Create a backup of corrupted config
            if self.config_path.exists():
                backup = self.config_path.with_suffix('.bak')
                self.config_path.rename(backup)
                logger.warning(f"Backed up corrupted config to {backup}")
            self.config = AppConfig()
            self._save_config()
    
    def _save_config(self):
        """Save the current configuration to disk."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                # Convert the model to a dictionary with json_encoders
                config_dict = self.config.model_dump(mode='json')
                json.dump(
                    config_dict,
                    f,
                    indent=2,
                    ensure_ascii=False
                )
            logger.debug(f"Saved config to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            raise
    
    # Note Type Management
    
    def get_note_type(self, note_type_id: str) -> Optional[NoteTypeConfig]:
        """Get a note type by ID.
        
        Args:
            note_type_id: The ID of the note type to retrieve.
            
        Returns:
            The NoteTypeConfig if found, None otherwise.
        """
        return self.config.note_types.get(note_type_id)
    
    def get_all_note_types(self) -> List[NoteTypeConfig]:
        """Get all note types.
        
        Returns:
            A list of all note types.
        """
        return list(self.config.note_types.values())
    
    def save_note_type(self, note_type: NoteTypeConfig) -> bool:
        """Save or update a note type.
        
        Args:
            note_type: The note type to save.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            self.config.note_types[note_type.id] = note_type
            self._save_config()
            logger.info(f"Saved note type: {note_type.name} ({note_type.id})")
            return True
        except Exception as e:
            logger.error(f"Error saving note type: {e}")
            return False
    
    def delete_note_type(self, note_type_id: str) -> bool:
        """Delete a note type by ID.
        
        Args:
            note_type_id: The ID of the note type to delete.
            
        Returns:
            True if deleted, False if not found or error.
        """
        if note_type_id in self.config.note_types:
            try:
                del self.config.note_types[note_type_id]
                self._save_config()
                logger.info(f"Deleted note type: {note_type_id}")
                return True
            except Exception as e:
                logger.error(f"Error deleting note type: {e}")
        return False
    
    # General Settings
    
    def update_general_settings(self, **kwargs) -> bool:
        """Update general settings.
        
        Args:
            **kwargs: Settings to update.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            for key, value in kwargs.items():
                if hasattr(self.config.general, key):
                    setattr(self.config.general, key, value)
            self._save_config()
            logger.info("Updated general settings")
            return True
        except Exception as e:
            logger.error(f"Error updating general settings: {e}")
            return False
