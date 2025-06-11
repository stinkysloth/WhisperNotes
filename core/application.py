"""
Main application class for WhisperNotes.

This module contains the core application logic, orchestrating services and UI components.
"""

import logging
import sys
import os
from typing import Optional, Dict, Any

from PySide6.QtCore import QObject, QMutex, Signal, Slot
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon

# Import services
from services.audio_service import AudioService
from services.transcription_service import TranscriptionService
from services.journal_service import JournalService
from services.template_service import TemplateService

# Import UI components
from ui.tray import TrayManager
from ui.hotkeys import HotkeyManager

# Import utilities
from utils.platform_utils import get_platform_specific_utils

logger = logging.getLogger(__name__)


class WhisperNotes(QObject):
    """Main application class for WhisperNotes."""
    
    # Signals for cross-thread communication
    show_error_dialog = Signal(str, str)     # title, message
    show_info_dialog = Signal(str, str)      # title, message
    show_warning_dialog = Signal(str, str)   # title, message
    show_config_dialog = Signal()            # No args
    
    def __init__(self, app: QApplication):
        """Initialize the application."""
        super().__init__()
        self.app = app
        self.mutex = QMutex()
        self._setup_services()
        self._setup_ui()
        self._connect_signals()
        
    def _setup_services(self) -> None:
        """Initialize all service components."""
        self.audio_service = AudioService()
        self.transcription_service = TranscriptionService()
        self.journal_service = JournalService()
        self.template_service = TemplateService()
        
        # Platform-specific utilities
        self.platform_utils = get_platform_specific_utils()
        
    def _setup_ui(self) -> None:
        """Initialize UI components."""
        # Setup system tray
        self.tray_manager = TrayManager(
            app=self.app,
            parent=self,
            on_record=self.toggle_recording,
            on_journal=self.toggle_journal_mode,
            on_quit=self.quit,
            on_edit_prompt=self.prompt_edit_summary_prompt,
            on_set_journal_dir=self.prompt_set_journal_dir,
            on_configure_templates=self.show_template_config,
            on_import_audio=self.import_audio_files
        )
        
        # Setup hotkeys
        self.hotkey_manager = HotkeyManager(
            on_toggle_recording=self.toggle_recording,
            on_toggle_journal=self.toggle_journal_mode,
            on_quit=self.quit
        )
    
    def _connect_signals(self) -> None:
        """Connect all signals and slots."""
        # Connect dialog signals
        self.show_error_dialog.connect(self._show_error_dialog_slot)
        self.show_info_dialog.connect(self._show_info_dialog_slot)
        self.show_warning_dialog.connect(self._show_warning_dialog_slot)
        self.show_config_dialog.connect(self._show_config_dialog_slot)
        
        # Connect service signals
        self.audio_service.recording_finished.connect(self.handle_recording_finished)
        self.audio_service.error_occurred.connect(self.handle_error)
        
        self.transcription_service.transcription_ready.connect(self.handle_transcription)
        self.transcription_service.error_occurred.connect(self.handle_error)
    
    # Core application methods will be implemented here
    def toggle_recording(self) -> None:
        """Toggle audio recording."""
        raise NotImplementedError
    
    def toggle_journal_mode(self) -> None:
        """Toggle journaling mode."""
        raise NotImplementedError
    
    def quit(self) -> None:
        """Clean up and quit the application."""
        raise NotImplementedError
    
    # Additional methods will be implemented as we refactor
    # ...
    
    # Slot implementations
    @Slot(str, str)
    def _show_error_dialog_slot(self, title: str, message: str) -> None:
        """Show an error dialog."""
        QMessageBox.critical(None, title, message)
    
    @Slot(str, str)
    def _show_info_dialog_slot(self, title: str, message: str) -> None:
        """Show an information dialog."""
        QMessageBox.information(None, title, message)
    
    @Slot(str, str)
    def _show_warning_dialog_slot(self, title: str, message: str) -> None:
        """Show a warning dialog."""
        QMessageBox.warning(None, title, message)
    
    @Slot()
    def _show_config_dialog_slot(self) -> None:
        """Show the configuration dialog."""
        # Will be implemented when we refactor the config dialog
        pass
