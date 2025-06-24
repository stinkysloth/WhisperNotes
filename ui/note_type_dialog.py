"""Dialog for creating and editing note types."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QLabel, QFileDialog, QTextEdit, QComboBox,
    QGroupBox, QCheckBox, QMessageBox, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal, Slot
from pathlib import Path
from typing import Dict, Any, Optional, Callable

class StorageConfigWidget(QGroupBox):
    """Widget for configuring storage settings for a note type."""
    
    def __init__(self, parent=None):
        super().__init__("Storage Settings", parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        # Use default storage checkbox
        self.use_default_checkbox = QCheckBox("Use default storage locations")
        self.use_default_checkbox.setChecked(True)
        self.use_default_checkbox.toggled.connect(self._on_use_default_toggled)
        layout.addWidget(self.use_default_checkbox)
        
        # Audio path
        self.audio_path_edit = QLineEdit()
        self.audio_path_edit.setReadOnly(True)
        self.audio_browse_btn = QPushButton("Browse...")
        self.audio_browse_btn.clicked.connect(self._browse_audio_path)
        
        audio_layout = QHBoxLayout()
        audio_layout.addWidget(self.audio_path_edit)
        audio_layout.addWidget(self.audio_browse_btn)
        
        # Markdown path
        self.markdown_path_edit = QLineEdit()
        self.markdown_path_edit.setReadOnly(True)
        self.markdown_browse_btn = QPushButton("Browse...")
        self.markdown_browse_btn.clicked.connect(self._browse_markdown_path)
        
        markdown_layout = QHBoxLayout()
        markdown_layout.addWidget(self.markdown_path_edit)
        markdown_layout.addWidget(self.markdown_browse_btn)
        
        # Add to form layout
        form_layout.addRow("Audio Files:", audio_layout)
        form_layout.addRow("Markdown Files:", markdown_layout)
        
        layout.addLayout(form_layout)
        self.setLayout(layout)
        
        # Initial state
        self._on_use_default_toggled(True)
    
    def _on_use_default_toggled(self, checked):
        """Enable/disable path editing based on the use default checkbox."""
        self.audio_path_edit.setEnabled(not checked)
        self.audio_browse_btn.setEnabled(not checked)
        self.markdown_path_edit.setEnabled(not checked)
        self.markdown_browse_btn.setEnabled(not checked)
    
    def _browse_audio_path(self):
        """Open a directory dialog to select the audio path."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Audio Storage Directory",
            self.audio_path_edit.text() or str(Path.home())
        )
        if dir_path:
            self.audio_path_edit.setText(dir_path)
    
    def _browse_markdown_path(self):
        """Open a directory dialog to select the markdown path."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Markdown Storage Directory",
            self.markdown_path_edit.text() or str(Path.home())
        )
        if dir_path:
            self.markdown_path_edit.setText(dir_path)
    
    def get_storage_config(self) -> Dict[str, Any]:
        """Get the current storage configuration.
        
        Returns:
            Dictionary containing the storage configuration
        """
        return {
            'use_default': self.use_default_checkbox.isChecked(),
            'audio_path': self.audio_path_edit.text() or None,
            'markdown_path': self.markdown_path_edit.text() or None
        }
    
    def set_storage_config(self, config: Dict[str, Any]):
        """Set the storage configuration.
        
        Args:
            config: Dictionary containing the storage configuration
        """
        self.use_default_checkbox.setChecked(config.get('use_default', True))
        self.audio_path_edit.setText(str(config.get('audio_path', '')))
        self.markdown_path_edit.setText(str(config.get('markdown_path', '')))


class HotkeyCaptureWidget(QLineEdit):
    """Widget for capturing hotkey combinations."""
    
    hotkey_captured = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Press a key combination...")
        self.setAlignment(Qt.AlignCenter)
        self._current_keys = set()
    
    def keyPressEvent(self, event):
        """Handle key press events to capture the hotkey."""
        key = event.key()
        modifiers = event.modifiers()
        
        # Ignore modifier keys by themselves
        if key in (Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta):
            return
        
        # Build the key combination string
        keys = []
        if modifiers & Qt.ShiftModifier:
            keys.append("Shift")
        if modifiers & Qt.ControlModifier:
            keys.append("Ctrl")
        if modifiers & Qt.AltModifier:
            keys.append("Alt")
        if modifiers & Qt.MetaModifier:
            keys.append("Meta")
        
        # Add the key itself (if not a modifier)
        key_name = self._get_key_name(key)
        if key_name and key_name not in keys:
            keys.append(key_name)
        
        if keys:
            hotkey = "+".join(keys)
            self.setText(hotkey)
            self.hotkey_captured.emit(hotkey)
    
    def _get_key_name(self, key):
        """Get the name of a key."""
        if Qt.Key_A <= key <= Qt.Key_Z:
            return chr(key).upper()
        elif Qt.Key_0 <= key <= Qt.Key_9:
            return chr(key)
        elif key == Qt.Key_Space:
            return "Space"
        elif key == Qt.Key_Return:
            return "Return"
        elif key == Qt.Key_Enter:
            return "Enter"
        elif key == Qt.Key_Backspace:
            return "Backspace"
        elif key == Qt.Key_Tab:
            return "Tab"
        elif key == Qt.Key_Escape:
            return "Escape"
        elif Qt.Key_F1 <= key <= Qt.Key_F35:
            return f"F{key - Qt.Key_F1 + 1}"
        return None
    
    def keyReleaseEvent(self, event):
        """Ignore key release events."""
        pass


class NoteTypeDialog(QDialog):
    """Dialog for creating and editing note types."""
    
    def __init__(self, parent=None, note_type=None):
        """Initialize the dialog.
        
        Args:
            parent: Parent widget
            note_type: Optional note type data to edit
        """
        super().__init__(parent)
        self.note_type = note_type or {}
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize the UI components."""
        self.setWindowTitle("Edit Note Type" if self.note_type else "New Note Type")
        self.setMinimumSize(600, 600)
        
        layout = QVBoxLayout()
        
        # Basic info group
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Meeting, Lecture, Personal")
        
        self.hotkey_edit = HotkeyCaptureWidget()
        
        basic_layout.addRow("Name*:", self.name_edit)
        basic_layout.addRow("Hotkey:", self.hotkey_edit)
        basic_group.setLayout(basic_layout)
        
        # Storage settings
        self.storage_widget = StorageConfigWidget()
        
        # Summary prompt
        prompt_group = QGroupBox("Summary Prompt")
        prompt_layout = QVBoxLayout()
        
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText(
            "Enter a prompt that will be used to generate a summary of the transcription. "
            "You can use the following placeholders: {transcription}, {date}, {time}, {duration}"
        )
        self.prompt_edit.setMinimumHeight(80)
        
        prompt_layout.addWidget(self.prompt_edit)
        prompt_group.setLayout(prompt_layout)
        
        # Template
        template_group = QGroupBox("Template")
        template_layout = QVBoxLayout()
        
        self.template_edit = QTextEdit()
        self.template_edit.setPlaceholderText(
            "Enter the markdown template for this note type. You can use the following placeholders:\n"
            "- {title}: Title of the note\n"
            "- {date}: Current date\n"
            "- {time}: Current time\n"
            "- {datetime}: Current date and time\n"
            "- {duration}: Duration of the recording\n"
            "- {summary_detailed}: Detailed summary\n"
            "- {summary_brief}: Brief summary\n"
            "- {transcription}: Full transcription text"
        )
        template_layout.addWidget(self.template_edit)
        template_group.setLayout(template_layout)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._validate_and_accept)
        button_box.rejected.connect(self.reject)
        
        # Add widgets to main layout
        layout.addWidget(basic_group)
        layout.addWidget(self.storage_widget)
        layout.addWidget(prompt_group)
        layout.addWidget(template_group)
        layout.addStretch()
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # Load note type data if editing
        if self.note_type:
            self._load_note_type()
    
    def _load_note_type(self):
        """Load note type data into the form."""
        if not self.note_type:
            return
            
        self.name_edit.setText(self.note_type.get('name', ''))
        self.hotkey_edit.setText(self.note_type.get('hotkey', ''))
        self.prompt_edit.setPlainText(self.note_type.get('summary_prompt', ''))
        self.template_edit.setPlainText(self.note_type.get('template', ''))
        
        # Load storage settings
        storage_config = self.note_type.get('storage', {})
        self.storage_widget.set_storage_config(storage_config)
    
    def _validate_and_accept(self):
        """Validate the form and accept if valid."""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter a name for the note type.")
            return
        
        self.accept()
    
    def get_note_type(self) -> Dict[str, Any]:
        """Get the note type data from the form.
        
        Returns:
            Dictionary containing the note type configuration
        """
        return {
            'name': self.name_edit.text().strip(),
            'hotkey': self.hotkey_edit.text().strip() or None,
            'storage': self.storage_widget.get_storage_config(),
            'summary_prompt': self.prompt_edit.toPlainText().strip(),
            'template': self.template_edit.toPlainText().strip()
        }
