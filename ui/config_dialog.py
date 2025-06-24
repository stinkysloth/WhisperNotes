"""Configuration dialog for WhisperNotes."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QDialogButtonBox,
    QListWidget, QStackedWidget, QHBoxLayout, QWidget
)
from PySide6.QtCore import Qt, Signal
from typing import Optional, Dict, Any

class ConfigDialog(QDialog):
    """Main configuration dialog with sidebar navigation and tabbed content."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("WhisperNotes Settings")
        self.setMinimumSize(800, 600)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Initialize the UI components."""
        main_layout = QHBoxLayout(self)
        
        # Create sidebar
        self.sidebar = QListWidget()
        self.sidebar.setMaximumWidth(200)
        self.sidebar.setStyleSheet("""
            QListWidget {
                background-color: #f0f0f0;
                border: none;
                padding: 10px 0;
            }
            QListWidget::item {
                padding: 8px 16px;
                border: none;
            }
            QListWidget::item:selected {
                background-color: #e0e0e0;
                border-left: 3px solid #2196F3;
            }
        """)
        
        # Create content area
        self.content_stack = QStackedWidget()
        
        # Add tabs
        self.tabs = {}
        self._add_tab("general", "General")
        self._add_tab("note_types", "Note Types")
        
        # Connect sidebar selection to content stack
        self.sidebar.currentRowChanged.connect(self.content_stack.setCurrentIndex)
        
        # Add widgets to main layout
        main_layout.addWidget(self.sidebar, 1)
        main_layout.addWidget(self.content_stack, 3)
        
        # Add buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Apply | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self._apply_changes)
        
        layout = QVBoxLayout()
        layout.addLayout(main_layout)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def _add_tab(self, tab_id: str, name: str) -> QWidget:
        """Add a new tab to the configuration dialog.
        
        Args:
            tab_id: Unique identifier for the tab
            name: Display name for the tab
            
        Returns:
            The created tab widget
        """
        tab = QWidget()
        self.tabs[tab_id] = tab
        self.content_stack.addWidget(tab)
        self.sidebar.addItem(name)
        return tab
    
    def _apply_changes(self):
        """Apply configuration changes."""
        # TODO: Implement configuration save logic
        pass


class NoteTypeConfigDialog(QDialog):
    """Dialog for configuring a single note type."""
    
    def __init__(self, parent=None, note_type=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Note Type" if note_type else "New Note Type")
        self.setMinimumSize(600, 400)
        
        self.note_type = note_type or {}
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # TODO: Add note type configuration fields
        
        # Add buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addStretch()
        layout.addWidget(button_box)
    
    def get_note_type(self) -> Dict[str, Any]:
        """Get the configured note type data.
        
        Returns:
            Dictionary containing the note type configuration
        """
        # TODO: Return the configured note type data
        return self.note_type
