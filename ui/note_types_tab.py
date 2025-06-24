"""Note types management tab for the configuration dialog."""
import os
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLabel, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from typing import List, Dict, Any, Optional, Callable

from .note_type_dialog import NoteTypeDialog

class NoteTypesTab(QWidget):
    """Tab for managing note types."""
    
    # Signal emitted when note types are updated
    note_types_updated = Signal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.note_types = []
        self._setup_ui()
        
        # Connect signals
        self.note_types_updated.connect(self._on_note_types_updated)
    
    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "Manage your note types below. Each type can have its own template, "
            "hotkey, and storage location."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Note types list
        self.note_types_list = QListWidget()
        self.note_types_list.setMinimumWidth(200)
        self.note_types_list.currentItemChanged.connect(self._on_note_type_selected)
        content_layout.addWidget(self.note_types_list)
        
        # Buttons
        btn_layout = QVBoxLayout()
        
        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self._add_note_type)
        
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self._edit_note_type)
        self.edit_btn.setEnabled(False)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_note_type)
        self.delete_btn.setEnabled(False)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        
        content_layout.addLayout(btn_layout)
        
        # Add to main layout
        layout.addLayout(content_layout)
    
    def load_note_types(self, note_types: List[Dict[str, Any]]):
        """Load note types into the list.
        
        Args:
            note_types: List of note type dictionaries
        """
        self.note_types = note_types
        self.note_types_list.clear()
        
        for note_type in note_types:
            self.note_types_list.addItem(note_type.get('name', 'Unnamed'))
    
    def get_note_types(self) -> List[Dict[str, Any]]:
        """Get the current list of note types.
        
        Returns:
            List of note type dictionaries
        """
        return self.note_types
    
    def _on_note_type_selected(self, current, previous):
        """Handle note type selection change."""
        is_selected = current is not None
        self.edit_btn.setEnabled(is_selected)
        self.delete_btn.setEnabled(is_selected)
    
    def _add_note_type(self):
        """Add a new note type."""
        try:
            dialog = NoteTypeDialog(self)
            if dialog.exec() == dialog.DialogCode.Accepted:
                new_note_type = dialog.get_note_type()
                # Generate a unique ID for the new note type
                new_note_type['id'] = f"note_type_{len(self.note_types) + 1}"
                self.note_types.append(new_note_type)
                self._update_note_types_list()
                self.note_types_updated.emit(self.note_types)
        except Exception as e:
            logging.error(f"Error adding note type: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to add note type: {str(e)}"
            )
    
    def _edit_note_type(self):
        """Edit the selected note type."""
        current_row = self.note_types_list.currentRow()
        if current_row >= 0 and current_row < len(self.note_types):
            try:
                note_type = self.note_types[current_row].copy()
                dialog = NoteTypeDialog(self, note_type)
                if dialog.exec() == dialog.DialogCode.Accepted:
                    updated_note_type = dialog.get_note_type()
                    # Preserve the ID
                    updated_note_type['id'] = note_type['id']
                    self.note_types[current_row] = updated_note_type
                    self._update_note_types_list()
                    self.note_types_updated.emit(self.note_types)
            except Exception as e:
                logging.error(f"Error editing note type: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to edit note type: {str(e)}"
                )
    
    def _delete_note_type(self):
        """Delete the selected note type."""
        current_row = self.note_types_list.currentRow()
        if current_row >= 0:
            try:
                note_name = self.note_types[current_row].get('name', 'this note type')
                reply = QMessageBox.question(
                    self,
                    'Confirm Deletion',
                    f'Are you sure you want to delete "{note_name}"?',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    del self.note_types[current_row]
                    self._update_note_types_list()
                    self.note_types_updated.emit(self.note_types)
            except Exception as e:
                logging.error(f"Error deleting note type: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete note type: {str(e)}"
                )
    
    def _update_note_types_list(self):
        """Update the note types list widget with current data."""
        self.note_types_list.clear()
        for note_type in self.note_types:
            self.note_types_list.addItem(note_type.get('name', 'Unnamed'))
    
    def _on_note_types_updated(self, note_types):
        """Handle note types update signal."""
        self.note_types = note_types
        self._update_note_types_list()
    
    def _export_note_type(self):
        """Export the selected note type to a file."""
        current_row = self.note_types_list.currentRow()
        if current_row >= 0:
            try:
                note_type = self.note_types[current_row]
                file_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Export Note Type",
                    f"{note_type.get('name', 'note_type')}.json",
                    "JSON Files (*.json)"
                )
                
                if file_path:
                    import json
                    with open(file_path, 'w') as f:
                        json.dump(note_type, f, indent=2)
            except Exception as e:
                logging.error(f"Error exporting note type: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to export note type: {str(e)}"
                )
    
    def _import_note_type(self):
        """Import a note type from a file."""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Import Note Type",
                "",
                "JSON Files (*.json)"
            )
            
            if file_path:
                import json
                with open(file_path, 'r') as f:
                    note_type = json.load(f)
                
                # Generate a new ID to avoid conflicts
                note_type['id'] = f"note_type_{len(self.note_types) + 1}"
                self.note_types.append(note_type)
                self._update_note_types_list()
                self.note_types_updated.emit(self.note_types)
        except Exception as e:
            logging.error(f"Error importing note type: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to import note type: {str(e)}"
            )
    
    def _duplicate_note_type(self):
        """Create a copy of the selected note type."""
        current_row = self.note_types_list.currentRow()
        if current_row >= 0:
            try:
                note_type = self.note_types[current_row].copy()
                # Generate a new ID and update the name
                note_type['id'] = f"note_type_{len(self.note_types) + 1}"
                note_type['name'] = f"{note_type.get('name', 'Copy')} (Copy)"
                
                # If there's a hotkey, clear it to avoid conflicts
                if 'hotkey' in note_type:
                    note_type['hotkey'] = None
                
                self.note_types.append(note_type)
                self._update_note_types_list()
                self.note_types_updated.emit(self.note_types)
            except Exception as e:
                logging.error(f"Error duplicating note type: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to duplicate note type: {str(e)}"
                )
    
    def _on_note_type_selected(self, current, previous):
        """Handle note type selection change."""
        is_selected = current is not None
        self.edit_btn.setEnabled(is_selected)
        self.delete_btn.setEnabled(is_selected)
        """Delete the selected note type."""
        current_row = self.note_types_list.currentRow()
        if current_row >= 0:
            reply = QMessageBox.question(
                self,
                'Delete Note Type',
                'Are you sure you want to delete this note type?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.note_types_list.takeItem(current_row)
                del self.note_types[current_row]
