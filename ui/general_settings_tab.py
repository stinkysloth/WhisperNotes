"""General settings tab for the configuration dialog."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
    QPushButton, QFileDialog
)
from PySide6.QtCore import Signal, Qt
from pathlib import Path

class GeneralSettingsTab(QWidget):
    """General settings tab for the configuration dialog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        
        # Recording settings group
        recording_group = QGroupBox("Recording Settings")
        recording_layout = QFormLayout()
        
        self.recording_device_combo = QComboBox()
        # TODO: Populate with available audio devices
        
        self.global_hotkey_edit = QLineEdit()
        self.global_hotkey_edit.setPlaceholderText("Press a key combination...")
        
        recording_layout.addRow("Recording Device:", self.recording_device_combo)
        recording_layout.addRow("Global Record Hotkey:", self.global_hotkey_edit)
        recording_group.setLayout(recording_layout)
        
        # Transcription settings group
        transcription_group = QGroupBox("Transcription Settings")
        transcription_layout = QFormLayout()
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        
        self.max_duration_spin = QSpinBox()
        self.max_duration_spin.setRange(1, 3600)  # 1 second to 1 hour
        self.max_duration_spin.setSuffix(" seconds")
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(30, 600)  # 30 seconds to 10 minutes
        self.timeout_spin.setSuffix(" seconds")
        
        transcription_layout.addRow("Model:", self.model_combo)
        transcription_layout.addRow("Max Recording Duration:", self.max_duration_spin)
        transcription_layout.addRow("Transcription Timeout:", self.timeout_spin)
        transcription_group.setLayout(transcription_layout)
        
        # Storage settings group
        storage_group = QGroupBox("Storage Settings")
        storage_layout = QFormLayout()
        
        self.default_journal_edit = QLineEdit()
        self.default_journal_edit.setReadOnly(True)
        browse_journal_btn = QPushButton("Browse...")
        browse_journal_btn.clicked.connect(self._browse_journal_dir)
        
        journal_layout = QHBoxLayout()
        journal_layout.addWidget(self.default_journal_edit)
        journal_layout.addWidget(browse_journal_btn)
        
        storage_layout.addRow("Default Journal Directory:", journal_layout)
        storage_group.setLayout(storage_layout)
        
        # Add all groups to main layout
        layout.addWidget(recording_group)
        layout.addWidget(transcription_group)
        layout.addWidget(storage_group)
        layout.addStretch()
    
    def _browse_journal_dir(self):
        """Open a directory dialog to select the journal directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Journal Directory",
            self.default_journal_edit.text() or str(Path.home())
        )
        if dir_path:
            self.default_journal_edit.setText(dir_path)
    
    def load_settings(self, settings):
        """Load settings into the UI.
        
        Args:
            settings: Dictionary containing the settings to load
        """
        # Recording settings
        if 'recording_device' in settings:
            index = self.recording_device_combo.findText(settings['recording_device'])
            if index >= 0:
                self.recording_device_combo.setCurrentIndex(index)
        
        if 'global_record_hotkey' in settings:
            self.global_hotkey_edit.setText(settings['global_record_hotkey'])
        
        # Transcription settings
        if 'ollama_model' in settings:
            index = self.model_combo.findText(settings['ollama_model'])
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
        
        if 'max_recording_duration' in settings:
            self.max_duration_spin.setValue(int(settings['max_recording_duration']))
        
        if 'transcription_timeout' in settings:
            self.timeout_spin.setValue(settings['transcription_timeout'])
        
        # Storage settings
        if 'default_journal_dir' in settings:
            self.default_journal_edit.setText(str(settings['default_journal_dir']))
    
    def get_settings(self):
        """Get the current settings from the UI.
        
        Returns:
            Dictionary containing the current settings
        """
        return {
            'recording_device': self.recording_device_combo.currentText(),
            'global_record_hotkey': self.global_hotkey_edit.text(),
            'ollama_model': self.model_combo.currentText(),
            'max_recording_duration': self.max_duration_spin.value(),
            'transcription_timeout': self.timeout_spin.value(),
            'default_journal_dir': self.default_journal_edit.text()
        }
