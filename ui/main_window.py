"""
Main application window for WhisperNotes.

This module contains the main application window implementation.
"""

import logging
from typing import Optional, Dict, Any

from PySide6.QtCore import Qt, QSize, Signal, Slot
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QStatusBar, QLabel, QPushButton, QToolBar, QSizePolicy
)
from PySide6.QtGui import QAction, QIcon, QKeySequence

from core.constants import AppConstants
from services.audio_service import AudioService
from services.journal_service import JournalService
from services.template_service import TemplateService
from services.transcription_service import TranscriptionService
from .widgets.audio_meter import AudioMeter
from .widgets.transcription_view import TranscriptionView
from .widgets.journal_editor import JournalEditor

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """Main application window for WhisperNotes."""
    
    # Signals
    recording_started = Signal()
    recording_stopped = Signal()
    journal_mode_toggled = Signal(bool)  # True if journal mode is enabled
    
    def __init__(
        self,
        audio_service: AudioService,
        journal_service: JournalService,
        template_service: TemplateService,
        transcription_service: TranscriptionService,
        parent: Optional[QWidget] = None
    ):
        """Initialize the main window.
        
        Args:
            audio_service: Audio service instance
            journal_service: Journal service instance
            template_service: Template service instance
            transcription_service: Transcription service instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Store services
        self.audio_service = audio_service
        self.journal_service = journal_service
        self.template_service = template_service
        self.transcription_service = transcription_service
        
        # UI state
        self.is_recording = False
        self.is_journal_mode = False
        
        # Initialize UI
        self._init_ui()
        self._connect_signals()
        
        # Update UI state
        self._update_ui_state()
    
    def _init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle(f"{AppConstants.APP_NAME} {AppConstants.APP_VERSION}")
        self.setMinimumSize(800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create toolbar
        self._create_toolbar()
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self._create_transcription_tab()
        self._create_journal_tab()
        
        # Create status bar
        self._create_status_bar()
        
        # Set initial tab
        self.tab_widget.setCurrentIndex(0)
    
    def _create_toolbar(self) -> None:
        """Create the main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Record action
        self.record_action = QAction(
            QIcon(":/icons/record.png"),
            "&Record",
            self,
            shortcut=QKeySequence("Ctrl+R"),
            triggered=self.toggle_recording
        )
        
        # Stop action
        self.stop_action = QAction(
            QIcon(":/icons/stop.png"),
            "S&top",
            self,
            shortcut=QKeySequence("Ctrl+."),
            triggered=self.stop_recording
        )
        self.stop_action.setEnabled(False)
        
        # Toggle journal mode action
        self.journal_mode_action = QAction(
            QIcon(":/icons/journal.png"),
            "&Journal Mode",
            self,
            checkable=True,
            toggled=self.toggle_journal_mode
        )
        
        # Add actions to toolbar
        toolbar.addAction(self.record_action)
        toolbar.addAction(self.stop_action)
        toolbar.addSeparator()
        toolbar.addAction(self.journal_mode_action)
        
        # Add stretch to push other items to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        
        # Audio level meter
        self.audio_meter = AudioMeter()
        toolbar.addWidget(self.audio_meter)
    
    def _create_transcription_tab(self) -> None:
        """Create the transcription tab."""
        self.transcription_view = TranscriptionView()
        self.tab_widget.addTab(self.transcription_view, "&Transcription")
    
    def _create_journal_tab(self) -> None:
        """Create the journal tab."""
        self.journal_editor = JournalEditor(self.journal_service, self.template_service)
        self.tab_widget.addTab(self.journal_editor, "&Journal")
    
    def _create_status_bar(self) -> None:
        """Create the status bar."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # Status labels
        self.recording_status = QLabel("Ready")
        self.model_status = QLabel("Model: Not Loaded")
        self.mode_status = QLabel("Mode: Transcription")
        
        # Add widgets to status bar
        status_bar.addWidget(self.recording_status)
        status_bar.addPermanentWidget(self.model_status)
        status_bar.addPermanentWidget(self.mode_status)
    
    def _connect_signals(self) -> None:
        """Connect signals and slots."""
        # Audio service signals
        self.audio_service.recording_started.connect(self._on_recording_started)
        self.audio_service.recording_stopped.connect(self._on_recording_stopped)
        self.audio_service.audio_level_updated.connect(self._on_audio_level_updated)
        self.audio_service.error_occurred.connect(self._on_audio_error)
        
        # Transcription service signals
        self.transcription_service.transcription_started.connect(self._on_transcription_started)
        self.transcription_service.transcription_finished.connect(self._on_transcription_finished)
        self.transcription_service.error_occurred.connect(self._on_transcription_error)
        
        # Journal service signals
        self.journal_service.entry_created.connect(self._on_journal_entry_created)
        self.journal_service.error_occurred.connect(self._on_journal_error)
        
        # Template service signals
        self.template_service.template_added.connect(self._on_template_updated)
        self.template_service.template_updated.connect(self._on_template_updated)
        self.template_service.template_deleted.connect(self._on_template_updated)
    
    def _update_ui_state(self) -> None:
        """Update the UI state based on current mode and status."""
        # Update recording actions
        self.record_action.setEnabled(not self.is_recording)
        self.stop_action.setEnabled(self.is_recording)
        
        # Update journal mode action
        self.journal_mode_action.setChecked(self.is_journal_mode)
        
        # Update status bar
        if self.is_recording:
            self.recording_status.setText("Recording...")
        else:
            self.recording_status.setText("Ready")
        
        self.mode_status.setText(f"Mode: {'Journal' if self.is_journal_mode else 'Transcription'}")
    
    # Public slots
    @Slot()
    def toggle_recording(self) -> None:
        """Toggle recording state."""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    @Slot()
    def start_recording(self) -> None:
        """Start audio recording."""
        logger.info("Starting recording...")
        self.audio_service.start_recording()
    
    @Slot()
    def stop_recording(self) -> None:
        """Stop audio recording and process the recorded audio."""
        logger.info("Stopping recording...")
        self.audio_service.stop_recording()
    
    @Slot(bool)
    def toggle_journal_mode(self, enabled: bool) -> None:
        """Toggle journal mode.
        
        Args:
            enabled: Whether journal mode should be enabled
        """
        logger.info(f"{'Enabling' if enabled else 'Disabling'} journal mode")
        self.is_journal_mode = enabled
        self.journal_mode_toggled.emit(enabled)
        self._update_ui_state()
    
    # Signal handlers
    @Slot()
    def _on_recording_started(self) -> None:
        """Handle recording started signal."""
        logger.info("Recording started")
        self.is_recording = True
        self._update_ui_state()
        self.recording_started.emit()
    
    @Slot()
    def _on_recording_stopped(self) -> None:
        """Handle recording stopped signal."""
        logger.info("Recording stopped")
        self.is_recording = False
        self._update_ui_state()
        self.recording_stopped.emit()
    
    @Slot(float)
    def _on_audio_level_updated(self, level: float) -> None:
        """Update audio level meter.
        
        Args:
            level: Current audio level (0.0 to 1.0)
        """
        self.audio_meter.set_level(level)
    
    @Slot(str)
    def _on_audio_error(self, error_msg: str) -> None:
        """Handle audio error signal.
        
        Args:
            error_msg: Error message
        """
        logger.error(f"Audio error: {error_msg}")
        self.statusBar().showMessage(f"Error: {error_msg}", 5000)
    
    @Slot()
    def _on_transcription_started(self) -> None:
        """Handle transcription started signal."""
        logger.info("Transcription started")
        self.statusBar().showMessage("Transcribing...")
    
    @Slot(str)
    def _on_transcription_finished(self, text: str) -> None:
        """Handle transcription finished signal.
        
        Args:
            text: Transcribed text
        """
        logger.info("Transcription finished")
        self.statusBar().showMessage("Transcription complete", 3000)
        
        if self.is_journal_mode:
            # Add to journal
            self.journal_editor.add_content(text)
        else:
            # Show in transcription view
            self.transcription_view.append_text(text)
    
    @Slot(str)
    def _on_transcription_error(self, error_msg: str) -> None:
        """Handle transcription error signal.
        
        Args:
            error_msg: Error message
        """
        logger.error(f"Transcription error: {error_msg}")
        self.statusBar().showMessage(f"Transcription error: {error_msg}", 5000)
    
    @Slot(dict)
    def _on_journal_entry_created(self, entry: Dict[str, Any]) -> None:
        """Handle journal entry created signal.
        
        Args:
            entry: Created journal entry data
        """
        logger.info(f"Journal entry created: {entry.get('id')}")
        self.statusBar().showMessage(f"Journal entry saved: {entry.get('title')}", 3000)
    
    @Slot(str)
    def _on_journal_error(self, error_msg: str) -> None:
        """Handle journal error signal.
        
        Args:
            error_msg: Error message
        """
        logger.error(f"Journal error: {error_msg}")
        self.statusBar().showMessage(f"Journal error: {error_msg}", 5000)
    
    @Slot()
    def _on_template_updated(self, *args) -> None:
        """Handle template updated signal."""
        logger.info("Templates updated")
        # Refresh the journal editor to show updated templates
        self.journal_editor.refresh_templates()
    
    def closeEvent(self, event) -> None:
        """Handle window close event."""
        # Stop any ongoing recording
        if self.is_recording:
            self.stop_recording()
        
        # Save window state
        # TODO: Save window geometry and state
        
        # Accept the close event
        event.accept()
