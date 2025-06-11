#!/usr/bin/env python3
"""
Template Configuration Dialog for WhisperNotes application.
Provides a UI for configuring templates and their associated hotkeys.
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QLineEdit, QComboBox, QFileDialog, QListWidget,
    QGroupBox, QFormLayout, QDialogButtonBox, QMessageBox,
    QListWidgetItem, QWidget, QCheckBox
)
from PySide6.QtCore import Qt, QSettings, Signal, Slot
from PySide6.QtGui import QIcon, QFont


from PySide6.QtCore import Signal, Slot

class TemplateConfigDialog(QDialog):
    """
    Dialog for configuring templates and their associated hotkeys.
    Allows selecting templates, configuring hotkeys, and setting save locations.
    """

    dialog_signal = Signal(str, str, str)  # type, title, message (e.g. 'warning', 'info', 'error')

    def __init__(self, parent=None, template_manager=None, settings=None):
        super().__init__(parent)
        self.dialog_signal.connect(self._show_dialog_slot)
        self.setWindowTitle("Template Configuration")
        # ... rest of __init__ ...
        self.resize(800, 600)
        
        self.template_manager = template_manager
        self.settings = settings
        
        # Load template configurations from settings
        self.template_configs = {}
        self._load_configs()
        
        # Initialize UI
        self.init_ui()
        
        # Populate template list
        self.populate_template_list()
    
    def _load_configs(self):
        """Load template configurations from settings."""
        if self.settings:
            config_str = self.settings.value("template_configs")
            if config_str:
                try:
                    self.template_configs = json.loads(config_str)
                    if self.template_manager:
                        self.template_manager.load_template_configs(self.template_configs)
                except json.JSONDecodeError:
                    logging.error("Failed to parse template configurations from settings")
    
    def init_ui(self):
        """Initialize the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Templates directory section
        dir_layout = QHBoxLayout()
        dir_label = QLabel("Templates Directory:")
        self.dir_edit = QLineEdit()
        self.dir_edit.setReadOnly(True)
        if self.template_manager:
            self.dir_edit.setText(self.template_manager.templates_dir)
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_templates_dir)
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.dir_edit)
        dir_layout.addWidget(self.browse_button)
        main_layout.addLayout(dir_layout)
        
        # Split view: template list on left, configuration on right
        split_layout = QHBoxLayout()
        
        # Template list section
        template_list_group = QGroupBox("Available Templates")
        template_list_layout = QVBoxLayout()
        self.template_list = QListWidget()
        self.template_list.currentItemChanged.connect(self.on_template_selected)
        template_list_layout.addWidget(self.template_list)
        
        # Add buttons for template management
        template_buttons_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_templates)
        self.open_folder_button = QPushButton("Open Templates Folder")
        self.open_folder_button.clicked.connect(self.open_templates_folder)
        template_buttons_layout.addWidget(self.refresh_button)
        template_buttons_layout.addWidget(self.open_folder_button)
        template_list_layout.addLayout(template_buttons_layout)
        
        template_list_group.setLayout(template_list_layout)
        split_layout.addWidget(template_list_group, 1)
        
        # Template configuration section
        config_group = QGroupBox("Template Configuration")
        config_layout = QFormLayout()
        
        # Template name (read-only)
        self.template_name_edit = QLineEdit()
        self.template_name_edit.setReadOnly(True)
        config_layout.addRow("Template Name:", self.template_name_edit)
        
        # Hotkey configuration
        self.hotkey_edit = QLineEdit()
        self.hotkey_edit.setPlaceholderText("e.g., cmd+shift+t")
        config_layout.addRow("Hotkey:", self.hotkey_edit)
        
        # Save location
        save_location_layout = QHBoxLayout()
        self.save_location_edit = QLineEdit()
        self.save_location_edit.setReadOnly(True)
        self.save_location_browse = QPushButton("Browse...")
        self.save_location_browse.clicked.connect(self.browse_save_location)
        save_location_layout.addWidget(self.save_location_edit)
        save_location_layout.addWidget(self.save_location_browse)
        config_layout.addRow("Save Location:", save_location_layout)
        
        # Tags
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("e.g., work, meeting, notes")
        config_layout.addRow("Default Tags:", self.tags_edit)
        
        # Add to main list option
        self.add_to_list_checkbox = QCheckBox("Add to main journal list")
        self.add_to_list_checkbox.setChecked(True)
        config_layout.addRow("", self.add_to_list_checkbox)
        
        # Template preview
        self.template_preview = QTextEdit()
        self.template_preview.setReadOnly(True)
        self.template_preview.setPlaceholderText("Select a template to see its content")
        config_layout.addRow("Template Preview:", self.template_preview)
        
        # Save button for this template config
        self.save_config_button = QPushButton("Save Configuration")
        self.save_config_button.clicked.connect(self.save_template_config)
        config_layout.addRow("", self.save_config_button)
        
        config_group.setLayout(config_layout)
        split_layout.addWidget(config_group, 2)
        
        main_layout.addLayout(split_layout)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
    
    def populate_template_list(self):
        """Populate the list of available templates."""
        if not self.template_manager:
            return
            
        self.template_list.clear()
        
        for template_name in sorted(self.template_manager.templates.keys()):
            item = QListWidgetItem(template_name)
            # Store the template path as item data
            item.setData(Qt.ItemDataRole.UserRole, self.template_manager.templates[template_name])
            self.template_list.addItem(item)
    
    def on_template_selected(self, current, previous):
        """Handle template selection."""
        if not current:
            return
            
        template_name = current.text()
        template_path = current.data(Qt.ItemDataRole.UserRole)
        
        # Update template name field
        self.template_name_edit.setText(template_name)
        
        # Load template configuration if exists
        config = self.template_configs.get(template_name, {})
        
        # Update UI with configuration
        self.hotkey_edit.setText(config.get("hotkey", ""))
        self.save_location_edit.setText(config.get("save_location", ""))
        self.tags_edit.setText(config.get("tags", ""))
        self.add_to_list_checkbox.setChecked(config.get("add_to_list", True))
        
        # Update template preview
        if self.template_manager:
            template_content = self.template_manager.get_template_content(template_name)
            self.template_preview.setText(template_content)
    
    def browse_templates_dir(self):
        """Browse for templates directory."""
        if not self.template_manager:
            return
            
        current_dir = self.dir_edit.text() or os.path.expanduser("~")
        new_dir = QFileDialog.getExistingDirectory(
            self, "Select Templates Directory", current_dir
        )
        
        if new_dir:
            # Update template manager
            self.template_manager.templates_dir = new_dir
            self.dir_edit.setText(new_dir)
            
            # Reload templates
            self.template_manager.templates = self.template_manager._load_templates()
            self.populate_template_list()
            
            # Save to settings
            if self.settings:
                self.settings.setValue("templates_dir", new_dir)
    
    def browse_save_location(self):
        """Browse for save location."""
        current_dir = self.save_location_edit.text() or os.path.expanduser("~")
        new_dir = QFileDialog.getExistingDirectory(
            self, "Select Save Location", current_dir
        )
        
        if new_dir:
            self.save_location_edit.setText(new_dir)
    
    def save_template_config(self):
        """Save the current template configuration."""
        if not self.template_manager:
            return
            
        current_item = self.template_list.currentItem()
        if not current_item:
            self.dialog_signal.emit('warning', "No Template Selected", "Please select a template to configure.")
            return
            
        template_name = current_item.text()
        
        # Create configuration
        config = {
            "hotkey": self.hotkey_edit.text().strip(),
            "save_location": self.save_location_edit.text(),
            "tags": self.tags_edit.text(),
            "add_to_list": self.add_to_list_checkbox.isChecked()
        }
        
        # Validate hotkey
        if config["hotkey"]:
            # Check if this hotkey is already used by another template
            existing_template = self.template_manager.get_template_by_hotkey(config["hotkey"])
            if existing_template and existing_template != template_name:
                result = self.dialog_signal.emit('question', "Hotkey Already Assigned", 
                    f"The hotkey '{config['hotkey']}' is already assigned to template '{existing_template}'.\n\n"
                    f"Do you want to reassign it to '{template_name}'?")
                # This dialog is modal and must be shown on the main thread; keep as is for now.
                if result != QMessageBox.StandardButton.Yes:
                    return
        
        # Save configuration
        self.template_configs = self.template_manager.save_template_config(template_name, config)
        
        # Save to settings
        if self.settings:
            self.settings.setValue("template_configs", json.dumps(self.template_configs))
        
        self.dialog_signal.emit('info', "Configuration Saved", f"Configuration for template '{template_name}' has been saved.")
    
    def refresh_templates(self):
        """Refresh the list of available templates."""
        if self.template_manager:
            self.template_manager.templates = self.template_manager._load_templates()
            self.populate_template_list()
    
    def open_templates_folder(self):
        """Open the templates folder in the file explorer."""
        if not self.template_manager:
            return
            
        import subprocess
        import platform
        
        try:
            folder_path = self.template_manager.templates_dir
            
            if platform.system() == "Windows":
                os.startfile(folder_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", folder_path])
            else:  # Linux
                subprocess.call(["xdg-open", folder_path])
                
        except Exception as e:
            logging.error(f"Error opening templates folder: {e}")
            self.dialog_signal.emit('warning', "Error", f"Could not open templates folder: {e}")
    
    def get_template_configs(self):
        """Get the current template configurations."""
        return self.template_configs
