"""Tests for the SettingsManager class."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.config import AppConfig, NoteTypeConfig, StorageConfig, GeneralConfig
from core.settings_manager import SettingsManager

class TestSettingsManager(unittest.TestCase):
    """Test cases for SettingsManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_config_path = Path(self.temp_dir.name) / "test_config.json"
        self.settings = SettingsManager(self.test_config_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def test_initialization_creates_default_config(self):
        """Test that initialization creates a default config if none exists."""
        self.assertIsInstance(self.settings.config, AppConfig)
        self.assertTrue(self.test_config_path.exists())
    
    def test_load_existing_config(self):
        """Test loading an existing config file."""
        # Create a test config file with some test data
        test_config = AppConfig(
            general=GeneralConfig(
                ollama_model="test-model",
                global_record_hotkey="ctrl+alt+r"
            )
        )
        
        # Save the test config
        with open(self.test_config_path, 'w') as f:
            config_data = test_config.model_dump(mode='json')
            json.dump(config_data, f, indent=2)
        
        # Create a new settings manager that should load the existing config
        settings = SettingsManager(self.test_config_path)
        
        # Verify the loaded config matches the test data
        self.assertEqual(settings.config.general.ollama_model, "test-model")
        self.assertEqual(settings.config.general.global_record_hotkey, "ctrl+alt+r")
    
    def test_save_note_type(self):
        """Test saving a note type."""
        note_type = NoteTypeConfig(
            name="Test Note",
            hotkey="ctrl+alt+t",
            summary_prompt="Summarize this",
            template="# {{title}}\n{{transcription}}"
        )
        
        # Save the note type
        self.assertTrue(self.settings.save_note_type(note_type))
        
        # Verify it was added to the in-memory config
        self.assertIn(note_type.id, self.settings.config.note_types)
        
        # Verify the note type data matches
        saved_note = self.settings.config.note_types[note_type.id]
        self.assertEqual(saved_note.name, "Test Note")
        self.assertEqual(saved_note.hotkey, "ctrl+alt+t")
        
        # Save the config to disk
        self.settings._save_config()
        
        # Reload settings to verify it was saved to disk
        new_settings = SettingsManager(self.test_config_path)
        self.assertIn(note_type.id, new_settings.config.note_types)
        saved_note = new_settings.config.note_types[note_type.id]
        self.assertEqual(saved_note.name, "Test Note")
        self.assertEqual(saved_note.hotkey, "ctrl+alt+t")
    
    def test_delete_note_type(self):
        """Test deleting a note type."""
        note_type = NoteTypeConfig(name="Test Note")
        self.settings.save_note_type(note_type)
        
        self.assertTrue(self.settings.delete_note_type(note_type.id))
        self.assertNotIn(note_type.id, self.settings.config.note_types)
    
    def test_update_general_settings(self):
        """Test updating general settings."""
        new_settings = {
            "ollama_model": "whisper-large",
            "global_record_hotkey": "ctrl+shift+space"
        }
        
        self.assertTrue(self.settings.update_general_settings(**new_settings))
        
        # Check that the settings were updated
        for key, value in new_settings.items():
            self.assertEqual(getattr(self.settings.config.general, key), value)
    
    def test_handle_corrupted_config(self):
        """Test handling of a corrupted config file."""
        # Create a corrupted config file
        with open(self.test_config_path, 'w') as f:
            f.write('{invalid json}')
        
        # This should not raise an exception
        settings = SettingsManager(self.test_config_path)
        self.assertIsInstance(settings.config, AppConfig)
        
        # A backup should be created
        backup_file = self.test_config_path.with_suffix('.bak')
        self.assertTrue(backup_file.exists())

if __name__ == '__main__':
    unittest.main()
