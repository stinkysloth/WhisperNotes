#!/usr/bin/env python3
"""
Journal Entry Preview Dialog for WhisperNotes application.
Provides a UI for previewing and editing journal entries before saving.
"""
import os
import logging
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QLineEdit, QComboBox, QCheckBox, QFileDialog,
    QGroupBox, QFormLayout, QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtGui import QIcon, QFont


class JournalPreviewDialog(QDialog):
    """
    Dialog for previewing and editing journal entries before saving.
    Allows editing summary and transcription, playing audio, and selecting save options.
    """
    
    def __init__(self, parent=None, entry_data: Dict[str, Any] = None, 
                 journal_dir: str = None, obsidian_vaults: Optional[Dict[str, str]] = None):
        """
        Initialize the journal preview dialog.
        
        Args:
            parent: Parent widget
            entry_data: Dictionary containing journal entry data
            journal_dir: Current journal directory
            obsidian_vaults: Dictionary of available Obsidian vaults {name: path}
        """
        super().__init__(parent)
        self.setWindowTitle("Journal Entry Preview")
        self.resize(800, 600)
        
        # Store entry data
        self.entry_data = entry_data or {}
        self.journal_dir = journal_dir
        self.obsidian_vaults = obsidian_vaults or {}
        
        # Setup audio player if audio file exists
        self.audio_player = None
        self.audio_output = None
        if self.entry_data.get('audio_file') and os.path.exists(self.entry_data.get('audio_file', '')):
            self.setup_audio_player()
        
        # Initialize UI
        self.init_ui()
        
        # Populate fields with entry data
        self.populate_fields()
    
    def setup_audio_player(self):
        """Set up the audio player for playback."""
        try:
            self.audio_player = QMediaPlayer()
            self.audio_output = QAudioOutput()
            self.audio_player.setAudioOutput(self.audio_output)
            
            # Set the source to the audio file
            audio_url = QUrl.fromLocalFile(self.entry_data['audio_file'])
            self.audio_player.setSource(audio_url)
            logging.info(f"Audio player set up with file: {self.entry_data['audio_file']}")
        except Exception as e:
            logging.error(f"Error setting up audio player: {e}")
            self.audio_player = None
    
    def init_ui(self):
        """Initialize the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Title section
        title_layout = QHBoxLayout()
        title_label = QLabel("Title:")
        self.title_edit = QLineEdit()
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.title_edit)
        main_layout.addLayout(title_layout)
        
        # Summary section
        summary_group = QGroupBox("Summary")
        summary_layout = QVBoxLayout()
        self.summary_edit = QTextEdit()
        self.summary_edit.setPlaceholderText("Summary of the journal entry")
        summary_layout.addWidget(self.summary_edit)
        summary_group.setLayout(summary_layout)
        main_layout.addWidget(summary_group)
        
        # Transcript section
        transcript_group = QGroupBox("Transcript")
        transcript_layout = QVBoxLayout()
        self.transcript_edit = QTextEdit()
        self.transcript_edit.setPlaceholderText("Full transcript of the recording")
        transcript_layout.addWidget(self.transcript_edit)
        transcript_group.setLayout(transcript_layout)
        main_layout.addWidget(transcript_group)
        
        # Audio playback section (if audio file exists)
        if self.audio_player:
            audio_group = QGroupBox("Audio Recording")
            audio_layout = QHBoxLayout()
            
            self.play_button = QPushButton("Play")
            self.play_button.clicked.connect(self.toggle_playback)
            audio_layout.addWidget(self.play_button)
            
            audio_group.setLayout(audio_layout)
            main_layout.addWidget(audio_group)
        
        # Save options section
        save_options_group = QGroupBox("Save Options")
        save_options_layout = QFormLayout()
        
        # Obsidian vault selection
        self.vault_combo = QComboBox()
        self.vault_combo.addItem("Default Journal Location", self.journal_dir)
        for name, path in self.obsidian_vaults.items():
            self.vault_combo.addItem(name, path)
        save_options_layout.addRow("Save Location:", self.vault_combo)
        
        # Custom folder selection
        folder_layout = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setReadOnly(True)
        self.folder_edit.setText(self.journal_dir)
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_folder)
        folder_layout.addWidget(self.folder_edit)
        folder_layout.addWidget(self.browse_button)
        save_options_layout.addRow("Custom Folder:", folder_layout)
        
        # Add to main list option
        self.add_to_list_checkbox = QCheckBox("Add to main journal list")
        self.add_to_list_checkbox.setChecked(True)
        save_options_layout.addRow("", self.add_to_list_checkbox)
        
        save_options_group.setLayout(save_options_layout)
        main_layout.addWidget(save_options_group)
        
        # Connect vault combo box signal
        self.vault_combo.currentIndexChanged.connect(self.update_folder_path)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | 
                                      QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
    
    def populate_fields(self):
        """Populate dialog fields with entry data."""
        # Generate title from timestamp
        if self.entry_data.get('timestamp'):
            self.title_edit.setText(f"Journal Entry - {self.entry_data.get('timestamp', '')}")
        
        # Set summary and transcript
        self.summary_edit.setText(self.entry_data.get('summary', ''))
        self.transcript_edit.setText(self.entry_data.get('formatted_text', 
                                                        self.entry_data.get('transcription', '')))
    
    def toggle_playback(self):
        """Toggle audio playback."""
        if not self.audio_player:
            return
            
        if self.audio_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.audio_player.pause()
            self.play_button.setText("Play")
        else:
            self.audio_player.play()
            self.play_button.setText("Pause")
    
    def browse_folder(self):
        """Open folder browser dialog."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder", self.folder_edit.text()
        )
        if folder:
            self.folder_edit.setText(folder)
            # Add custom folder to combo box if not already there
            found = False
            for i in range(self.vault_combo.count()):
                if self.vault_combo.itemData(i) == folder:
                    self.vault_combo.setCurrentIndex(i)
                    found = True
                    break
            
            if not found:
                self.vault_combo.addItem("Custom Folder", folder)
                self.vault_combo.setCurrentIndex(self.vault_combo.count() - 1)
    
    def update_folder_path(self, index):
        """Update folder path when vault selection changes."""
        selected_path = self.vault_combo.itemData(index)
        if selected_path:
            self.folder_edit.setText(selected_path)
    
    def get_updated_entry(self) -> Dict[str, Any]:
        """
        Get the updated entry data from the dialog.
        
        Returns:
            Dict containing updated entry data
        """
        # Update entry data with edited values
        updated_entry = self.entry_data.copy()
        updated_entry['title'] = self.title_edit.text()
        updated_entry['summary'] = self.summary_edit.toPlainText()
        updated_entry['formatted_text'] = self.transcript_edit.toPlainText()
        
        # Add save options
        updated_entry['save_location'] = self.folder_edit.text()
        updated_entry['add_to_list'] = self.add_to_list_checkbox.isChecked()
        
        return updated_entry
