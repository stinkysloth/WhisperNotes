#!/usr/bin/env python3

"""
WhisperNotes Main Application Module


This module implements the main application logic for WhisperNotes, a cross-platform (macOS, Windows, Linux) desktop voice journaling and note-taking app using PySide6 (Qt), Whisper ASR, and system tray integration.

Key Responsibilities:
---------------------
- Application entry point and event loop
- System tray icon, actions, and notifications
- Global hotkey registration (Cmd+Shift+R/J, Cmd+Q)
- Audio recording and transcription using Whisper
- Journaling integration and clipboard management
- Thread-safe communication via Qt signals/slots
- Robust error handling and resource cleanup

Architecture & Structure:
------------------------
- Platform-specific clipboard and accessibility support
- Worker threads for recording, transcription, and model loading
- Main `WhisperNotes` class orchestrates UI, hotkeys, and threading
- Modular fallback logic for missing dependencies (journaling, exceptions)
- Mutex-protected critical sections for thread safety
- Modular cleanup helpers for graceful shutdown

Constraints & Developer Notes:
-----------------------------
- Requires PySide6, pynput, sounddevice, librosa, and Whisper
- On macOS, terminal/Python must have Accessibility permissions for hotkeys
- All UI and signal/slot connections must be made from the main Qt thread
- File should be split into smaller modules if it exceeds 500 lines (see refactor plan at bottom)
- See README.md for setup, permissions, and troubleshooting

"""
import os
import sys
import time
import platform
from PySide6.QtCore import QObject, Signal, Slot, QThread, QTimer, QMutex, QStandardPaths, QSettings, QFile, QIODevice, QByteArray, QBuffer, QMimeData, QCoreApplication, Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QSystemTrayIcon, QMenu, QStyle, QInputDialog, QLineEdit, QDialog, QVBoxLayout, QLabel, QPushButton, QDialogButtonBox, QTextEdit, QComboBox, QFormLayout, QHBoxLayout, QSpinBox, QCheckBox, QGroupBox, QProgressDialog, QProgressBar
print("Main process Python executable:", sys.executable)

# Import platform-specific modules for auto-paste
if sys.platform == 'darwin':  # macOS
    import Quartz
    from AppKit import NSApplication, NSApp
    from PySide6.QtCore import QTimer
elif sys.platform == 'win32':  # Windows
    import win32clipboard
    import win32con
    import win32gui
    import win32api
    import win32process
    import win32ui
    from ctypes import wintypes
    import ctypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    from pywinauto import Application
    import uiautomation as auto
else:  # Linux
    import subprocess
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, Gdk, GdkX11  # noqa: F401
    import Xlib.display
    import Xlib.XK
    import Xlib.X
    import Xlib.ext.xtest
    import Xlib.error
import logging
import tempfile
import subprocess
import platform
from core.constants import RecordingState
import numpy as np
import sounddevice as sd
import soundfile as sf
import webbrowser
import threading
import queue
import shutil
import datetime
import uuid
import re
import io
import csv
import json
from pathlib import Path

# Local imports
from core.settings_manager import SettingsManager
from models.config import NoteTypeConfig, StorageConfig
from template_manager import TemplateManager
from tray import TrayManager
from typing import Optional, Dict, List, Any, Tuple, Union, Callable, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import importlib
import importlib.util
from urllib.parse import urlparse, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
import requests
from pydub import AudioSegment
from pydub.utils import mediainfo

# Local imports
try:
    from .hotkeys import HotkeyManager
except ImportError:
    from hotkeys import HotkeyManager
    class AudioSaveError(Exception): pass
    class TranscriptionError(Exception): pass
    class ModelError(Exception): pass
    class JournalingError(Exception): pass
    class FileSystemError(Exception): pass
    class ConfigurationError(Exception): pass
    
    def handle_error(error: Exception, context: str = "") -> str:
        logging.error(f"Error in {context or 'unknown context'}: {str(error)}\n{traceback.format_exc()}")
        return f"An error occurred: {str(error)}"

# Import journaling module
try:
    from journaling import JournalingManager
except ImportError:
    # Fallback if journaling.py is not found
    class JournalingManager:
        def __init__(self, *args, **kwargs):
            pass
        def create_journal_entry(self, *args, **kwargs):
            return {'error': 'Journaling not available'}

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more verbose output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("whisper_notes.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('WhisperNotes')
logger.info("Logging system initialized")

# Modern service-based architecture
from services.audio_service import AudioService
from services.transcription_service import TranscriptionService

class WhisperNotes(QObject):
    """Main application class for WhisperNotes."""

    # Signals to safely show dialogs from main thread
    show_error_dialog = Signal(str, str)
    show_info_dialog = Signal(str, str)
    show_warning_dialog = Signal(str, str)
    show_config_dialog = Signal()

    """
    Main application class for WhisperNotes.

    Orchestrates the system tray, hotkeys, audio recording, transcription,
    journaling, and thread management. Handles all user interactions and
    coordinates between UI and background workers. Entry point for the app logic.

    Args:
        app (QApplication): The main Qt application instance.

    Constraints:
        - All UI and signal/slot connections must be made from the main Qt thread.
        - Platform-specific permissions may be required (see README).
    """
    toggle_recording_signal = Signal()
    toggle_journal_signal = Signal()
    quit_signal = Signal()
    
    def __init__(self, app):
        super().__init__()

        # Modern services
        self.audio_service = AudioService()
        self.transcription_service = TranscriptionService()

        # Connect service signals
        self.audio_service.recording_finished.connect(self._on_recording_finished)
        self.audio_service.error_occurred.connect(self.handle_error)
        self.transcription_service.transcription_finished.connect(self._on_transcription_finished)
        self.transcription_service.error_occurred.connect(self.handle_error)
 

        # Connect dialog signals to slots
        self.show_error_dialog.connect(self._show_error_dialog_slot)
        self.show_info_dialog.connect(self._show_info_dialog_slot)
        self.show_warning_dialog.connect(self._show_warning_dialog_slot)
        self.show_config_dialog.connect(self._show_config_dialog_slot)

        self.app = app
        self.model = None
        self.last_recording_time = 0
        self.mutex = QMutex()  # For thread safety
        self.hotkey_active = False
        self.pressed_keys = set()
        self.journaling_mode = False  # Track if we're in journaling mode
        self.is_recording = False  # Track recording state
        self.auto_paste_enabled = True  # Enable auto-paste by default
 
        
        # Initialize platform-specific settings
        self._init_platform_specific()
        


        # Initialize platform-specific settings
        self._init_platform_specific()
        
        # Initialize the new SettingsManager
        self.settings_manager = SettingsManager()
        self.config = self.settings_manager.config
        
        # Initialize TemplateManager
        templates_dir = os.path.join(os.path.expanduser('~'), '.whispernotes', 'templates')
        os.makedirs(templates_dir, exist_ok=True)
        self.template_manager = TemplateManager(templates_dir)
        
        # Template system - now using NoteTypeConfig from settings
        self.note_types = {}
        self.active_note_type = None
        
        # Define toggle_recording method
        self.toggle_recording = self._toggle_recording
        
        # Set up tray manager EARLY so it's always available for hotkey callbacks
        logging.info("Setting up TrayManager in __init__ (early)")
        self.tray_manager = TrayManager(
            app=self.app,
            parent=self,
            on_record=self.toggle_recording,
            on_journal=self.toggle_journal_mode,
            on_quit=self.quit,
            on_set_journal_dir=self.prompt_set_journal_dir,
            on_configure_templates=self.open_config_dialog,
            on_settings=self.open_config_dialog,
            on_import_audio=self.import_audio_files
        )

        # Initialize HotkeyManager first
        logging.info("Setting up HotkeyManager in __init__")
        self.hotkey_manager = HotkeyManager(
            on_toggle_recording=self.toggle_recording,
            on_toggle_journal=self.toggle_journal_mode,
            on_quit=self.quit
        )

        # Now register hotkeys for note types
        self._register_note_type_hotkeys()

        # Define tray dialog handler before tray setup
        def open_config_dialog():
            """
            Open the configuration dialog to set the journal directory. (Stub implementation)
            """
            self._show_config_dialog_slot()

        # Legacy QSettings for backward compatibility
        self.legacy_settings = QSettings("WhisperNotes", "WhisperNotes")
        
        # Migrate settings from QSettings to the new config if needed
        self._migrate_legacy_settings()
        
        # Initialize journaling manager with directory and prompt from config
        journal_dir = Path(self.config.general.default_journal_dir)
        summary_prompt = self.config.general.default_summary_prompt
        
        # Create journal directory if it doesn't exist
        journal_dir.mkdir(parents=True, exist_ok=True)
        
        self.journal_manager = JournalingManager(
            output_dir=str(journal_dir),
            summary_prompt=summary_prompt
        )
        logging.info(f"Using journal directory: {journal_dir}")
        
        self.toggle_recording_signal.connect(self.toggle_recording)
        self.toggle_journal_signal.connect(self.toggle_journal_mode)
        self.quit_signal.connect(self.quit)


        self.setup_watchdog()

        # Connect dialog signals to slots
        self.show_error_dialog.connect(self._show_error_dialog_slot)
        self.show_info_dialog.connect(self._show_info_dialog_slot)
        self.show_warning_dialog.connect(self._show_warning_dialog_slot)
        self.show_config_dialog.connect(self._show_config_dialog_slot)

    def _toggle_recording(self):
        """Toggle recording state using AudioService."""
        logging.info("[SLOT ENTRY] toggle_recording() called. is_recording=%s", self.is_recording)
        if self.is_recording:
            self.audio_service.stop_recording()
            self.is_recording = False
            if hasattr(self, 'tray_manager'):
                self.tray_manager.update_icon(False)
        else:
            started = self.audio_service.start_recording()
            if started:
                self.is_recording = True
                self.last_recording_time = time.time()
                if hasattr(self, 'tray_manager'):
                    self.tray_manager.update_icon(True)

    def toggle_journal_mode(self):
        """Toggle journaling mode on/off and update tray icon."""
        self.journaling_mode = not self.journaling_mode
        logging.info(f"Journaling mode toggled: {self.journaling_mode}")
        if hasattr(self, 'tray_manager'):
            self.tray_manager.update_icon(self.is_recording, journaling=self.journaling_mode)

    def prompt_set_journal_dir(self):
        """Stub for setting the journal directory from the tray menu."""
        logging.info("prompt_set_journal_dir called from tray (stub implementation)")
        self._show_config_dialog_slot()

    def open_config_dialog(self):
        """Open the configuration dialog from the tray menu."""
        logging.info("open_config_dialog called from tray")
        self.show_config_dialog.emit()

    def import_audio_files(self):
        """Stub for importing audio files from the tray menu."""
        logging.info("import_audio_files called from tray (stub implementation)")
        # TODO: Implement audio file import dialog
        pass

        """Toggle journaling mode on/off and update tray icon."""
        self.journaling_mode = not self.journaling_mode
        logging.info(f"Journaling mode toggled: {self.journaling_mode}")
        if hasattr(self, 'tray_manager'):
            self.tray_manager.update_icon(self.is_recording, journaling=self.journaling_mode)

        """Toggle recording state using AudioService."""
        logging.info("[SLOT ENTRY] toggle_recording() called. is_recording=%s", self.is_recording)
        if self.is_recording:
            self.audio_service.stop_recording()
            self.is_recording = False
            if hasattr(self, 'tray_manager'):
                self.tray_manager.update_icon(False)
        else:
            started = self.audio_service.start_recording()
            if started:
                self.is_recording = True
                if hasattr(self, 'tray_manager'):
                    self.tray_manager.update_icon(True)

    def _init_platform_specific(self):
        """Initialize platform-specific settings and modules."""
        if sys.platform == 'darwin':  # macOS
            # Initialize NSApplication for macOS accessibility
            self.nsapp = NSApplication.sharedApplication()
        elif sys.platform == 'win32':  # Windows
            # Initialize Windows-specific settings
            self._init_windows()
        # Linux initialization handled in the paste method
        
    def _init_windows(self):
        """Initialize Windows-specific settings."""
        # Ensure the process is DPI aware for high-DPI displays
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)  # Process DPI aware
        except:
            pass  # Not critical if this fails
    
    def paste_at_cursor(self, text):
        """
        Paste text at the current cursor position in the active window.
        
        Args:
            text: The text to paste
            
        Returns:
            bool: True if successful, False otherwise
        """
        logging.info(f"[Paste] paste_at_cursor called with text: {text[:50]}...")
        if not text or not self.auto_paste_enabled:
            logging.info("[Paste] Skipping paste: no text or auto_paste disabled.")
            return False
        try:
            if sys.platform == 'darwin':  # macOS
                return self._paste_macos(text)
            elif sys.platform == 'win32':  # Windows
                return self._paste_windows(text)
            else:  # Linux
                return self._paste_linux(text)
        except Exception as e:
            logging.error(f"Error pasting text at cursor: {e}")
            return False
    
    def _paste_macos(self, text):
        """Paste text at cursor position on macOS. Tries Quartz event simulation, falls back to AppleScript if needed."""
        try:
            logging.info("[Paste] Starting macOS paste routine (Quartz)")
            # Save current clipboard content
            old_clipboard = QApplication.clipboard()
            old_text = old_clipboard.text()
            logging.info(f"[Paste] Old clipboard text: {old_text[:50]}...")
            
            # Set new text to clipboard
            old_clipboard.setText(text)
            logging.info(f"[Paste] Set clipboard to: {text[:50]}...")
            
            # Try Quartz event simulation
            try:
                import time
                logging.info("[Paste] Getting NSApplication.sharedApplication()")
                system_events = Quartz.NSApplication.sharedApplication()
                logging.info(f"[Paste] system_events: {system_events}")
                logging.info("[Paste] Creating event source")
                source = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateCombinedSessionState)
                # Press Cmd down
                logging.info("[Paste] Press Cmd down")
                cmd_down = Quartz.CGEventCreateKeyboardEvent(source, 0x37, True)
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, cmd_down)
                time.sleep(0.05)
                # Press V down
                logging.info("[Paste] Press V down")
                v_down = Quartz.CGEventCreateKeyboardEvent(source, 0x09, True)
                Quartz.CGEventSetFlags(v_down, Quartz.kCGEventFlagMaskCommand)
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, v_down)
                time.sleep(0.05)
                # Release V
                logging.info("[Paste] Release V")
                v_up = Quartz.CGEventCreateKeyboardEvent(source, 0x09, False)
                Quartz.CGEventSetFlags(v_up, Quartz.kCGEventFlagMaskCommand)
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, v_up)
                time.sleep(0.05)
                # Release Cmd
                logging.info("[Paste] Release Cmd")
                cmd_up = Quartz.CGEventCreateKeyboardEvent(source, 0x37, False)
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, cmd_up)
                time.sleep(0.05)
                logging.info("[Paste] Quartz paste routine complete")
                # Restore old clipboard after a short delay
                QTimer.singleShot(1000, lambda: old_clipboard.setText(old_text))
                return True
            except Exception as quartz_e:
                logging.error(f"[Paste] Quartz paste error: {quartz_e}. Attempting AppleScript fallback.")
                # Try AppleScript fallback
                import subprocess
                try:
                    # AppleScript to paste (Cmd+V) in frontmost app
                    script = 'tell application "System Events" to keystroke "v" using command down'
                    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
                    if result.returncode == 0:
                        logging.info("[Paste] AppleScript fallback paste succeeded.")
                        QTimer.singleShot(1000, lambda: old_clipboard.setText(old_text))
                        return True
                    else:
                        logging.error(f"[Paste] AppleScript fallback failed: {result.stderr}")
                except Exception as apple_e:
                    logging.error(f"[Paste] AppleScript fallback error: {apple_e}")
            # Restore clipboard even if all pastes fail
            QTimer.singleShot(1000, lambda: old_clipboard.setText(old_text))
            return False
        except Exception as e:
            logging.error(f"macOS paste error (outer): {e}")
            return False
    
    def _paste_windows(self, text):
        """Paste text at cursor position on Windows."""
        try:
            # Save current clipboard content
            win32clipboard.OpenClipboard()
            try:
                old_data = win32clipboard.GetClipboardData()
            except:
                old_data = None
            win32clipboard.CloseClipboard()
            
            # Set new text to clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            
            # Get the foreground window
            hwnd = user32.GetForegroundWindow()
            
            # Send Ctrl+V to paste
            user32.keybd_event(0x11, 0, 0, 0)  # Ctrl down
            user32.keybd_event(0x56, 0, 0, 0)  # V down
            user32.keybd_event(0x56, 0, 2, 0)  # V up
            user32.keybd_event(0x11, 0, 2, 0)  # Ctrl up
            
            # Restore old clipboard after a short delay
            def restore_clipboard():
                try:
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    if old_data is not None:
                        win32clipboard.SetClipboardText(old_data, win32con.CF_UNICODETEXT)
                    win32clipboard.CloseClipboard()
                except:
                    pass
                    
            QTimer.singleShot(1000, restore_clipboard)
            
            return True
            
        except Exception as e:
            logging.error(f"Windows paste error: {e}")
            return False
    
    def _paste_linux(self, text):
        """Paste text at cursor position on Linux."""
        try:
            # Save current clipboard content
            old_clipboard = QApplication.clipboard()
            old_text = old_clipboard.text()
            
            # Set new text to clipboard
            old_clipboard.setText(text)
            
            # Get display and root window
            display = Xlib.display.Display()
            root = display.screen().root
            
            # Get the current focus window
            current_focus = display.get_input_focus().focus
            
            # Create the key press event
            keycode = display.keysym_to_keycode(Xlib.XK.string_to_keysym('v'))
            
            # Press Control
            Xlib.ext.xtest.fake_input(display, Xlib.X.KeyPress, 37, Xlib.X.CurrentTime, current_focus, 0, 0, 0)
            
            # Press V
            Xlib.ext.xtest.fake_input(display, Xlib.X.KeyPress, keycode, Xlib.X.CurrentTime, current_focus, 0, 0, 0)
            
            # Release V
            Xlib.ext.xtest.fake_input(display, Xlib.X.KeyRelease, keycode, Xlib.X.CurrentTime, current_focus, 0, 0, 0)
            
            # Release Control
            Xlib.ext.xtest.fake_input(display, Xlib.X.KeyRelease, 37, Xlib.X.CurrentTime, current_focus, 0, 0, 0)
            
            display.sync()
            display.close()
            
            # Restore old clipboard after a short delay
            QTimer.singleShot(1000, lambda: old_clipboard.setText(old_text))
            
            return True
            
        except Exception as e:
            logging.error(f"Linux paste error: {e}")
            return False
        
        # Initialize QSettings for persistent output file path
        self.settings = QSettings("WhisperNotes", "WhisperNotes")
        if not self.settings.contains("output_file"):
            documents_path = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
            default_output = os.path.join(documents_path, "WhisperNotesTranscriptions.md")
            self.settings.setValue("output_file", default_output)
        logging.info(f"Output Markdown file initialized to: {self.settings.value('output_file')}")
        
 
        # Initialize journaling manager with directory and prompts from settings if available
        journal_dir = self.settings.value("journal_dir")
        summary_prompt = self.settings.value("summary_prompt")
        format_prompt = self.settings.value("format_prompt")

        # Initialize journaling manager with directory and prompt from settings if available
        journal_dir = self.settings.value("journal_dir")
        summary_prompt = self.settings.value("summary_prompt")
        
        if journal_dir and os.path.isdir(journal_dir):
            self.journal_manager = JournalingManager(output_dir=journal_dir, summary_prompt=summary_prompt)
            logging.info(f"Using journal directory from settings: {journal_dir}")
        else:
            # Use default directory
            home_dir = os.path.expanduser("~")
            default_journal_dir = os.path.join(home_dir, "Documents", "Personal", "Audio Journal")
            self.journal_manager = JournalingManager(output_dir=default_journal_dir, summary_prompt=summary_prompt)
            logging.info(f"Using default journal directory: {default_journal_dir}")
            # Save the default to settings
            self.settings.setValue("journal_dir", default_journal_dir)
 
            
        # Set format prompt if available
        if format_prompt:
            self.journal_manager.set_format_prompt(format_prompt)
        
        self.toggle_recording_signal.connect(self.toggle_recording)
        self.toggle_journal_signal.connect(self.toggle_journal_mode)
        self.quit_signal.connect(self.quit)


        self.setup_tray()
        self.setup_hotkeys()
        self.setup_watchdog()
    

        
    def setup_watchdog(self):
        """Setup a watchdog timer to periodically check the application state."""
        self.watchdog_timer = QTimer(self)
        self.watchdog_timer.timeout.connect(self.check_application_state)
        self.watchdog_timer.start(1000)  # Check every second
    
    def check_application_state(self):
        """Check the application state and ensure everything is responsive."""
        # Check if recording has timed out
        if self.is_recording and self.audio_service and self.audio_service.recording_state == RecordingState.RECORDING and hasattr(self, 'last_recording_time'):
            elapsed = time.time() - self.last_recording_time
            # Get max duration from config, with a 2-second buffer for safety
            max_duration = getattr(self.config.general, 'max_recording_duration', 900.0) + 2.0
            if elapsed > max_duration:
                logging.warning(f"Recording timeout detected ({elapsed:.1f}s > {max_duration-2.0}s). Forcing stop.")
                self.stop_recording()
    

    def _on_transcription_finished(self, text):
        """
        Handle the transcription finished signal from TranscriptionService.

        Args:
            text (str): The transcribed text
        """
        logging.info(f"[Transcription] Finished: {text[:100]}...")
        self.transcribed_text = text
        # Always attempt to paste at cursor after transcription
        logging.info("[Transcription] Calling paste_at_cursor after transcription finished...")
        paste_result = self.paste_at_cursor(text)
        logging.info(f"[Transcription] paste_at_cursor returned: {paste_result}")
        # Clear audio data after handling transcription
        if hasattr(self, '_clear_audio_data'):
            self._clear_audio_data()
            logging.info("[Transcription] Cleared audio data after transcription.")

    def _on_recording_finished(self, audio_data):
        """
        Handle the recorded audio data from AudioService and start transcription.
        Args:
            audio_data: The recorded audio data as a numpy array
        """
        if audio_data is None or len(audio_data) == 0:
            logging.warning("No audio data to process.")
            if hasattr(self, 'tray_manager'):
                self.tray_manager.update_icon(False)
            return
        self.audio_data = audio_data
        logging.info(f"Recording finished, audio data shape: {getattr(audio_data, 'shape', 'unknown')}")
        self.is_recording = False
        if hasattr(self, 'tray_manager'):
            self.tray_manager.update_icon(False)
            self.active_note_type = None
            
        try:
            # Start transcription using TranscriptionService
            logging.info("Starting transcription for recorded audio...")
            self.transcription_service.transcribe_audio(self.audio_data, self.audio_service.sample_rate)
        except Exception as e:
            error_msg = handle_error(e, "transcription start")
            try:
                if hasattr(self, 'tray_manager') and hasattr(self.tray_manager, 'tray_icon'):
                    self.tray_manager.tray_icon.showMessage(
                        "Transcription Error",
                        error_msg,
                        QSystemTrayIcon.MessageIcon.Critical,
                        5000
                    )
            except Exception as ui_error:
                logging.error(f"Failed to show error message: {ui_error}")
            self.show_error_dialog.emit("Transcription Error", error_msg)
            logging.error(f"Error in starting transcription: {error_msg}")
            raise

        # Journal entry creation and other post-recording logic here
        # ...

    @Slot(str)
    def start_recording(self):
        """Start the recording thread."""
        if self.is_recording:
            logging.info("Already recording, nothing to start")
            return
            
        logging.info("Starting recording...")
        self.is_recording = True
        self.last_recording_time = time.time()
        
        # Update UI immediately on the main thread
        if hasattr(self, 'toggle_action'):
            self.toggle_action.setText("Stop Recording")
            
        # Update icon through update_icon method which already has safeguards
        if hasattr(self, 'tray_manager') and self.tray_manager:
            self.tray_manager.update_icon(True)
        
        # Start recording via AudioService
        self.audio_service.start_recording()
    
    def stop_recording(self):
        """Stop the recording thread."""
        if not self.is_recording:
            logging.info("Not recording, nothing to stop")
            return
            
        logging.info("Stopping recording...")
        self.is_recording = False
        
        # Update UI immediately on the main thread
        if hasattr(self, 'toggle_action'):
            self.toggle_action.setText("Start Recording")
            
        # Update tray icon and tooltip through tray_manager if it exists
        if hasattr(self, 'tray_manager') and self.tray_manager:
            self.tray_manager.update_icon(False)
        
        # Stop recording via AudioService
        self.audio_service.stop_recording()
    
    def handle_error(self, error_msg):
        """Handle errors from the worker thread."""
        logging.error(f"Error: {error_msg}")

        # Check if tray_icon exists before using it
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.showMessage("Error", error_msg, QSystemTrayIcon.MessageIcon.Critical)
            
        # Still try to stop recording if possible
        self.stop_recording()
    
    def _clear_transcriber_references(self):
        """
        Clean up and remove references to the transcriber worker.
        This is called when the worker has finished and is being deleted.
        """
        try:
            if not hasattr(self, 'transcriber') or self.transcriber is None:
                return
                
            logging.info("Cleaning up transcriber worker references")
            
            # Store reference and clear immediately to prevent reentrancy
            transcriber = self.transcriber
            self.transcriber = None
            
            # If the transcriber is already deleted, just return
            try:
                if isinstance(transcriber, QObject) and not transcriber.isWidgetType():
                    try:
                        # Safely disconnect signals if they exist
                        signal_names = ['error', 'finished', 'transcription_ready']
                        for signal_name in signal_names:
                            try:
                                if hasattr(transcriber, signal_name):
                                    signal = getattr(transcriber, signal_name, None)
                                    if signal is not None and hasattr(signal, 'disconnect'):
                                        try:
                                            signal.disconnect()
                                        except (RuntimeError, TypeError) as e:
                                            # Signal might be already disconnected or invalid
                                            logging.debug(f"Error disconnecting {signal_name} signal: {e}")
                            except Exception as e:
                                logging.warning(f"Error checking {signal_name} signal: {e}")
                        
                        # Request stop if the transcriber is still running
                        if hasattr(transcriber, 'request_stop'):
                            try:
                                transcriber.request_stop()
                            except Exception as e:
                                logging.warning(f"Error requesting stop on transcriber: {e}")
                        
                        # Schedule the transcriber for deletion if it's a QObject
                        if isinstance(transcriber, QObject):
                            transcriber.deleteLater()
                        
                        logging.debug("Transcriber worker references cleared")
                        
                    except Exception as e:
                        logging.error(f"Error during transcriber cleanup: {e}", exc_info=True)
                else:
                    logging.debug("Transcriber worker already deleted, skipping cleanup")
                    
            except Exception as e:
                logging.error(f"Error checking if transcriber is deleted: {e}")
                
        except Exception as e:
            logging.error(f"Unexpected error in _clear_transcriber_references: {e}", exc_info=True)

    def _clear_transcription_thread_references(self):
        """
        Clean up and remove references to the transcription thread.
        This is called when the thread has finished and is being deleted.
        """
        try:
            # Early return if no thread exists
            if not hasattr(self, 'transcription_thread') or self.transcription_thread is None:
                return
                
            logging.info("Cleaning up transcription thread references")
            
            # Store reference and clear immediately to prevent reentrancy
            thread = self.transcription_thread
            self.transcription_thread = None
            
            # If the thread is already deleted, just return
            if not isinstance(thread, QObject) or thread.thread() is None:
                logging.debug("Thread already deleted or invalid, skipping cleanup")
                return
            
            try:
                # Safely disconnect signals if they exist
                self._disconnect_thread_signals(thread)
                
                # Request stop if possible
                if hasattr(self, 'transcriber') and self.transcriber is not None:
                    try:
                        # Check if transcriber is valid and has request_stop method
                        if (isinstance(self.transcriber, QObject) and 
                            hasattr(self.transcriber, 'request_stop') and 
                            callable(getattr(self.transcriber, 'request_stop'))):
                            self.transcriber.request_stop()
                    except Exception as e:
                        logging.warning(f"Error requesting stop on transcriber: {e}")
                
                # Ensure the thread is properly terminated
                if thread.isRunning():
                    logging.warning("Transcription thread still running during cleanup")
                    
                    # First try to quit gracefully
                    thread.quit()
                    if not thread.wait(2000):  # Wait up to 2 seconds
                        logging.warning("Thread did not exit gracefully, terminating...")
                        try:
                            thread.terminate()
                            if not thread.wait(1000):  # Give it 1 more second
                                logging.error("Failed to terminate transcription thread")
                        except Exception as e:
                            logging.error(f"Error terminating thread: {e}")
                
                # Schedule the thread for deletion if it's still valid
                if isinstance(thread, QObject) and thread.thread() is not None:
                    try:
                        thread.deleteLater()
                    except Exception as e:
                        logging.error(f"Error scheduling thread for deletion: {e}")
                
                # Clear any remaining references
                if hasattr(self, 'transcriber') and self.transcriber is not None:
                    self.transcriber = None
                
                logging.debug("Transcription thread references cleared")
                
            except Exception as e:
                logging.error(f"Error during transcription thread cleanup: {e}", exc_info=True)
                
        except Exception as e:
            logging.error(f"Unexpected error in _clear_transcription_thread_references: {e}", exc_info=True)
            
    def _disconnect_thread_signals(self, thread):
        """Safely disconnect signals from a thread."""
        if not thread:
            return
            
        signal_names = ['started', 'finished', 'error', 'transcription_ready']
        
        for signal_name in signal_names:
            try:
                if hasattr(thread, signal_name):
                    signal = getattr(thread, signal_name)
                    if signal:
                        try:
                            signal.disconnect()
                        except (RuntimeError, TypeError) as e:
                            # Signal might be already disconnected or invalid
                            logging.debug(f"Error disconnecting {signal_name} signal: {e}")
            except Exception as e:
                logging.warning(f"Error checking {signal_name} signal: {e}")

        # Error handling is done by the caller
    
    @Slot(str, str)
    def _show_error_dialog_slot(self, title, msg):
        QMessageBox.critical(None, title, msg)

    @Slot(str, str)
    def _show_info_dialog_slot(self, title, msg):
        QMessageBox.information(None, title, msg)

    @Slot(str, str)
    def _show_warning_dialog_slot(self, title, msg):
        QMessageBox.warning(None, title, msg)

    @Slot()
    def _show_config_dialog_slot(self):
        try:
            # Import the ConfigDialog here to avoid circular imports
            from ui.config_dialog import ConfigDialog
            from ui.general_settings_tab import GeneralSettingsTab
            from ui.note_types_tab import NoteTypesTab
            
            dialog = ConfigDialog()
            
            # Add tabs to the dialog
            general_tab = GeneralSettingsTab()
            note_types_tab = NoteTypesTab()
            
            # Load current settings
            general_settings = {
                'recording_device': self.config.general.recording_device,
                'global_record_hotkey': self.config.general.global_record_hotkey,
                'ollama_model': self.config.general.ollama_model,
                'max_recording_duration': self.config.general.max_recording_duration,
                'transcription_timeout': self.config.general.transcription_timeout,
                'default_journal_dir': str(self.config.general.default_journal_dir)
            }
            general_tab.load_settings(general_settings)
            
            # Load note types
            note_types = [
                {
                    'id': nt.id,
                    'name': nt.name,
                    'hotkey': nt.hotkey,
                    'storage': {
                        'audio_path': str(nt.storage.audio_path) if nt.storage.audio_path else None,
                        'markdown_path': str(nt.storage.markdown_path) if nt.storage.markdown_path else None,
                        'use_default': nt.storage.use_default
                    },
                    'summary_prompt': nt.summary_prompt,
                    'template': nt.template
                }
                for nt in self.config.note_types.values()
            ]
            note_types_tab.load_note_types(note_types)
            
            # Add tabs to the dialog
            dialog.content_stack.addWidget(general_tab)
            dialog.content_stack.addWidget(note_types_tab)
            
            # Show the dialog
            result = dialog.exec()
            
            if result == QDialog.DialogCode.Accepted:
                # Save settings
                new_settings = general_tab.get_settings()
                self.config.general.recording_device = new_settings['recording_device']
                self.config.general.global_record_hotkey = new_settings['global_record_hotkey']
                self.config.general.ollama_model = new_settings['ollama_model']
                self.config.general.max_recording_duration = new_settings['max_recording_duration']
                self.config.general.transcription_timeout = new_settings['transcription_timeout']
                self.config.general.default_journal_dir = Path(new_settings['default_journal_dir'])
                
                # Save note types
                note_types_data = note_types_tab.get_note_types()
                
                # Convert to NoteTypeConfig objects
                from models.config import NoteTypeConfig, StorageConfig
                
                # Clear existing note types
                self.config.note_types.clear()
                
                # Add new note types
                for nt_data in note_types_data:
                    storage_data = nt_data.get('storage', {})
                    storage_config = StorageConfig(
                        audio_path=Path(storage_data.get('audio_path', '')),
                        markdown_path=Path(storage_data.get('markdown_path', '')),
                        use_default=storage_data.get('use_default', True)
                    )
                    
                    note_type = NoteTypeConfig(
                        id=nt_data.get('id', f"note_type_{len(self.config.note_types) + 1}"),
                        name=nt_data['name'],
                        hotkey=nt_data.get('hotkey'),
                        storage=storage_config,
                        summary_prompt=nt_data.get('summary_prompt', ''),
                        template=nt_data.get('template', '')
                    )
                    
                    self.config.note_types[note_type.id] = note_type
                
                # Save the config
                self.settings_manager._save_config()
                
                # Update hotkeys if they changed
                self._register_note_type_hotkeys()
                
                # Show success message
                QMessageBox.information(
                    None,
                    "Settings Saved",
                    "Configuration has been saved successfully.",
                    QMessageBox.Ok
                )
                
        except Exception as e:
            logging.error(f"Error showing config dialog: {e}", exc_info=True)
            self.show_error_dialog.emit("Configuration Error", f"Failed to open configuration dialog: {str(e)}")
    
    def _migrate_legacy_settings(self):
        """
        Migrate settings from the legacy QSettings to the new configuration system.
        This ensures a smooth transition for existing users.
        """
        # Only migrate if we don't have any note types yet
        if not self.config.note_types and self.legacy_settings.contains("output_file"):
            try:
                # Migrate journal directory
                journal_dir = self.legacy_settings.value("journal_dir")
                if journal_dir and os.path.isdir(journal_dir):
                    self.config.general.default_journal_dir = journal_dir
                
                # Migrate summary prompt
                summary_prompt = self.legacy_settings.value("summary_prompt")
                if summary_prompt:
                    self.config.general.default_summary_prompt = summary_prompt
                
                # Create a default note type from legacy settings
                default_note = NoteTypeConfig(
                    name="Default Note",
                    hotkey=self.legacy_settings.value("record_hotkey", "ctrl+alt+r"),
                    summary_prompt=summary_prompt or "",
                    storage=StorageConfig(
                        audio_path=Path(journal_dir or ".") / "audio",
                        markdown_path=Path(journal_dir or ".")
                    ),
                    template="# {{title}}\n{{transcription}}\n\n{{summary_detailed}}"
                )
                
                # Save the default note type
                self.settings_manager.save_note_type(default_note)
                
                # Save the updated config
                self.settings_manager._save_config()
                
                logging.info("Successfully migrated legacy settings to new configuration system")
                
            except Exception as e:
                logging.error(f"Error migrating legacy settings: {e}")
    
    def _register_note_type_hotkeys(self):
        """
        Register hotkeys for all configured note types.
        """
        # First unregister any existing template hotkeys
        if hasattr(self, '_unregister_all_template_hotkeys'):
            self._unregister_all_template_hotkeys()
        
        # Register hotkeys for each note type
        for note_id, note_type in self.config.note_types.items():
            if note_type.hotkey:
                try:
                    self.hotkey_manager.register_template_hotkey(
                        note_type.hotkey,
                        note_type.name,
                        lambda nt_id=note_id: self._on_note_type_hotkey(nt_id)
                    )
                    logging.debug(f"Registered hotkey {note_type.hotkey} for note type {note_type.name}")
                except Exception as e:
                    logging.error(f"Failed to register hotkey {note_type.hotkey} for note type {note_type.name}: {e}")
    
    def _on_note_type_hotkey(self, note_type_id):
        """
        Handle hotkey press for a specific note type.
        
        Args:
            note_type_id: ID of the note type to activate
        """
        if note_type_id in self.config.note_types:
            self.active_note_type = self.config.note_types[note_type_id]
            logging.info(f"Activated note type: {self.active_note_type.name}")
            self.toggle_recording()
        else:
            logging.warning(f"Note type with ID {note_type_id} not found")
            
    def _load_template_configs(self):
        """
        Load template configurations from settings and register hotkeys.
        """
        if not hasattr(self, 'settings') or not self.settings:
            logging.warning("Settings not initialized, cannot load template configurations")
            return
            
        config_str = self.settings.value("template_configs")
        if config_str:
            try:
                template_configs = json.loads(config_str)
                self.template_manager.load_template_configs(template_configs)
                self._register_template_hotkeys(template_configs)
                logging.info(f"Loaded {len(template_configs)} template configurations from settings")
            except json.JSONDecodeError:
                logging.error("Failed to parse template configurations from settings")
                
    def _update_template_hotkeys(self):
        """
        Update template hotkeys based on current template configurations.
        """
        # Get current template configurations
        template_configs = self.template_manager.template_configs
        
        # Unregister all existing template hotkeys
        self._unregister_all_template_hotkeys()
        
        # Register new template hotkeys
        self._register_template_hotkeys(template_configs)
        
    def _register_template_hotkeys(self, template_configs):
        """
        Register hotkeys for templates based on their configurations.
        
        Args:
            template_configs: Dictionary of template configurations
        """
        for template_name, config in template_configs.items():
            hotkey = config.get("hotkey")
            if hotkey and hotkey.strip():
                # Register the hotkey with the hotkey manager
                success = self.hotkey_manager.register_template_hotkey(
                    hotkey_str=hotkey.strip(),
                    template_name=template_name,
                    callback=self._on_template_hotkey
                )
                if success:
                    logging.info(f"Registered hotkey '{hotkey}' for template '{template_name}'")
                else:
                    logging.warning(f"Failed to register hotkey '{hotkey}' for template '{template_name}'")
                    
    def _unregister_all_template_hotkeys(self):
        """
        Unregister all template hotkeys.
        """
        # Get current template configurations
        template_configs = self.template_manager.template_configs
        
        # Unregister each hotkey
        for template_name, config in template_configs.items():
            hotkey = config.get("hotkey")
            if hotkey and hotkey.strip():
                self.hotkey_manager.unregister_template_hotkey(hotkey.strip())
                
    def _on_template_hotkey(self, template_name):
        """
        Handle template hotkey press.
        
        Args:
            template_name: Name of the template to use
        """
        logging.info(f"Template hotkey pressed for template: {template_name}")
        
        # Check if we're already recording
        if self.is_recording:
            logging.warning("Cannot start template recording while already recording")
            self.tray_manager.show_message(
                "Recording in Progress",
                "Please finish the current recording before using a template.",
                QSystemTrayIcon.MessageIcon.Warning
            )
            return
            
        # Start recording with the selected template
        self.journaling_mode = True
        self._set_active_template(template_name)
        self.toggle_recording()
        
    def _set_active_template(self, template_name):
        """
        Set the active template for the next journal entry.
        
        Args:
            template_name: Name of the template to use
        """
        if not hasattr(self, 'journal_manager') or not self.journal_manager:
            logging.error("Journal manager not initialized, cannot set active template")
            return
            
        # Store the template name in the journal manager
        self.journal_manager.active_template = template_name
        
        # Get template configuration
        template_config = self.template_manager.get_template_config(template_name)
        
        # Set custom save location if specified
        if template_config and "save_location" in template_config and template_config["save_location"]:
            self.journal_manager.custom_output_dir = template_config["save_location"]
        else:
            self.journal_manager.custom_output_dir = None
            
        # Set custom tags if specified
        if template_config and "tags" in template_config:
            self.journal_manager.custom_tags = template_config["tags"]
        else:
            self.journal_manager.custom_tags = None
            
        logging.info(f"Set active template to '{template_name}'")

    def quit(self):
        try:
            logging.info("Quitting application...")
            self.stop_recording() # This should ideally wait for the recording thread to finish.

            # Stop watchdog timer
            if hasattr(self, 'watchdog_timer'):
                self.watchdog_timer.stop()

            # Cleanup transcription thread if running
            try:
                if hasattr(self, 'transcription_thread') and self.transcription_thread and self.transcription_thread.isRunning():
                    logging.info("Requesting transcription worker to stop and waiting for thread to finish...")
                    if hasattr(self, 'transcriber') and self.transcriber: # self.transcriber is the QObject worker
                        self.transcriber.request_stop() # New method
                    
                    self.transcription_thread.quit() # Ask event loop to stop (harmless if no event loop)
                    if not self.transcription_thread.wait(5000): # Increased timeout
                        logging.warning("Transcription thread did not finish in time.")
                        # self.transcription_thread.terminate() # Avoid if possible, can lead to instability
            except RuntimeError as e:
                logging.warning(f"RuntimeError during transcription thread cleanup: {e}")
            except Exception as e:
                logging.error(f"Unexpected error during transcription thread cleanup: {e}", exc_info=True)

            # Recording thread cleanup is now handled by AudioService; legacy code removed.

            # Cleanup model loader thread if running
            try:
                if hasattr(self, 'model_thread') and self.model_thread and self.model_thread.isRunning():
                    logging.info("Waiting for model loader thread to finish...")
                    # ModelLoader.run() is blocking; no easy stop. quit() is a hint if it had an event loop.
                    self.model_thread.quit()
                    if not self.model_thread.wait(5000): # Increased timeout
                        logging.warning("Model loader thread did not finish in time.")
            except RuntimeError as e:
                logging.warning(f"RuntimeError during model loader thread cleanup: {e}")
            except Exception as e:
                logging.error(f"Unexpected error during model loader thread cleanup: {e}", exc_info=True)

            # Cleanup hotkey listener
            if hasattr(self, 'listener'):
                logging.info("Stopping hotkey listener...")
                self.listener.stop()
                try:
                    # Attempt to join the listener thread to ensure it exits cleanly
                    # This might block, so use with caution or make listener a QThread
                    # For pynput, listener.stop() is usually sufficient and join isn't always exposed/needed this way.
                    if hasattr(self.listener, 'join') and callable(self.listener.join):
                         self.listener.join() # Remove timeout=1.0
                except Exception as e:
                    logging.warning(f"Error joining hotkey listener thread: {e}")

            logging.info("All cleanup attempts finished. Quitting QCoreApplication.")
            QCoreApplication.instance().quit()

        except Exception as e:
            logging.error(f"Error during quit: {e}", exc_info=True)
            QCoreApplication.instance().quit() # Ensure quit is called even if an error occurs in cleanup



if __name__ == "__main__":
    # Handle multiprocessing in frozen applications
    import multiprocessing
    if getattr(sys, 'frozen', False):
        multiprocessing.freeze_support()
    
    # Create the Qt Application
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Set application attributes for better macOS integration
    if sys.platform == 'darwin':  # macOS specific
        from Foundation import NSBundle
        # Set the bundle name to show in the menu bar
        bundle = NSBundle.mainBundle()
        if bundle:
            info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
            if info:
                info['CFBundleName'] = 'WhisperNotes'
    
 
    # Create the main application with error handling and logging
    try:
        logger.info("Instantiating WhisperNotes...")
        whisper_notes = WhisperNotes(app)
        logger.info("WhisperNotes instantiated successfully.")
    except Exception as e:
        logger.exception("Exception during WhisperNotes instantiation: %s", e)
        import traceback
        print("Exception during WhisperNotes instantiation:")
        print(traceback.format_exc())
        sys.exit(1)

    # On macOS, we need to ensure the application is properly activated
    if sys.platform == 'darwin':
        from AppKit import NSApp
        NSApp.activateIgnoringOtherApps_(True)
    
    # Start the event loop
    sys.exit(app.exec())