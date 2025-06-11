#!/usr/bin/env python3
"""
Test script for the WhisperNotes template system.
This script tests the template manager and template configuration dialog.
"""
import os
import sys
import json
import logging
import argparse
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import template system
try:
    from template_manager import TemplateManager
    from template_config_dialog import TemplateConfigDialog
except ImportError as e:
    logging.error(f"Failed to import template system modules: {e}")
    sys.exit(1)

def test_template_manager():
    """Test the TemplateManager class functionality."""
    logging.info("Testing TemplateManager...")
    
    # Create a template manager with default settings
    template_manager = TemplateManager()
    
    # Log available templates
    templates = template_manager.templates
    logging.info(f"Found {len(templates)} templates:")
    for name, path in templates.items():
        logging.info(f"  - {name}: {path}")
    
    # Test template content retrieval
    if templates:
        first_template = next(iter(templates.keys()))
        content = template_manager.get_template_content(first_template)
        logging.info(f"Template '{first_template}' content sample: {content[:100]}...")
    
    # Test template application with sample data
    sample_entry = {
        "title": "Test Entry",
        "summary": "This is a test summary for template application.",
        "transcription": "This is a test transcription with some content that should be formatted according to the template.",
        "timestamp": "2025-06-02 16:30:00",
        "tags": "test, template, sample"
    }
    
    if templates:
        first_template = next(iter(templates.keys()))
        formatted = template_manager.apply_template(first_template, sample_entry)
        logging.info(f"Applied template '{first_template}' to sample entry:")
        logging.info(formatted)
    
    # Test template configuration
    config = {
        "hotkey": "cmd+shift+t",
        "save_location": os.path.expanduser("~/Desktop/Template Test"),
        "tags": "template, test",
        "add_to_list": True
    }
    
    if templates:
        first_template = next(iter(templates.keys()))
        template_manager.save_template_config(first_template, config)
        retrieved_config = template_manager.get_template_config(first_template)
        logging.info(f"Saved and retrieved config for '{first_template}':")
        logging.info(f"  - Config: {retrieved_config}")
    
    # Test hotkey lookup
    if templates:
        template_name = template_manager.get_template_by_hotkey("cmd+shift+t")
        logging.info(f"Template with hotkey 'cmd+shift+t': {template_name}")
    
    logging.info("TemplateManager tests completed.")
    return template_manager

def test_template_dialog(template_manager):
    """Test the TemplateConfigDialog."""
    logging.info("Testing TemplateConfigDialog...")
    
    # Create QApplication instance
    app = QApplication(sys.argv)
    
    # Create settings
    settings = QSettings("WhisperNotes", "TestTemplateSystem")
    
    # Create and show dialog
    dialog = TemplateConfigDialog(
        parent=None,
        template_manager=template_manager,
        settings=settings
    )
    
    # Show dialog (this will block until dialog is closed)
    logging.info("Showing template configuration dialog. Close the dialog to continue.")
    result = dialog.exec()
    
    # Check result
    if result:
        logging.info("Dialog was accepted.")
    else:
        logging.info("Dialog was rejected or closed.")
    
    # Get updated configurations
    configs = dialog.get_template_configs()
    logging.info(f"Template configurations after dialog: {json.dumps(configs, indent=2)}")
    
    logging.info("TemplateConfigDialog test completed.")
    
    return app.exec()

def main():
    """Main function to run the tests."""
    parser = argparse.ArgumentParser(description="Test the WhisperNotes template system")
    parser.add_argument("--manager-only", action="store_true", help="Only test the template manager, not the dialog")
    args = parser.parse_args()
    
    # Test template manager
    template_manager = test_template_manager()
    
    # Test dialog if not in manager-only mode
    if not args.manager_only:
        return test_template_dialog(template_manager)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
