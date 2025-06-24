"""
tray.py
-------
System tray icon, menu, and notification logic for WhisperNotes.

Responsibilities:
- Tray icon setup and teardown
- Menu actions (record, journal, quit, etc.)
- Notification display
"""

import logging
from PySide6.QtWidgets import (
    QSystemTrayIcon, QMenu, QMessageBox, QApplication,
    QFileDialog, QInputDialog
)
from PySide6.QtGui import QIcon, QPixmap, QAction, QActionGroup
from PySide6.QtCore import Qt, QTimer, Signal, QObject
import os
from pathlib import Path

class TrayManager:
    """
    Manages the system tray icon, menu, and notifications for WhisperNotes.

    Responsibilities:
    - Tray icon setup and teardown
    - Menu actions (record, journal, quit, settings, etc.)
    - Notification display
    """
    def __init__(
        self,
        app,
        parent,
        on_record,
        on_journal,
        on_quit,

        on_set_journal_dir=None,
        on_configure_templates=None,
        on_settings=None,
        on_import_audio=None
    ):
        """
        Initialize the tray manager.

        Args:
            app: The QApplication instance
            parent: The parent widget or main window
            on_record: Callback for record action
            on_journal: Callback for journal action
            on_quit: Callback for quit action
            on_set_journal_dir: Callback to set the journal directory (optional)
            on_configure_templates: Callback to configure templates (optional)
            on_settings: Generic callback for settings action (optional, for backward compatibility)
        """
        self.app = app
        self.parent = parent
        self.on_record = on_record
        self.on_journal = on_journal
        self.on_quit = on_quit

        self.on_set_journal_dir = on_set_journal_dir
        self.on_configure_templates = on_configure_templates
        self.on_settings = on_settings
        self.on_import_audio = on_import_audio
        self.tray_icon = None
        self._setup_tray()

    def _setup_tray(self):
        """
        Setup the system tray icon and menu, including advanced configuration actions.
        """
        try:
            logging.debug("Setting up system tray...")
            if not QApplication.instance():
                logging.error("No QApplication instance found!")
                return
            if not QSystemTrayIcon.isSystemTrayAvailable():
                logging.error("System tray is not available on this system")
                if QApplication.instance().topLevelWindows():
                    QMessageBox.critical(None, "Error", "System tray is not available on this system.")
                return
            if not self.tray_icon:
                self.tray_icon = QSystemTrayIcon(self.parent)

            # Diagnostic logging for icon path
            idle_icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.png')
            recording_icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.iconset', 'icon_32x32.png')
            logging.info(f"Tray icon idle path: {idle_icon_path}, exists: {os.path.exists(idle_icon_path)}")
            logging.info(f"Tray icon recording path: {recording_icon_path}, exists: {os.path.exists(recording_icon_path)}")
            try:
                self.tray_icon.setIcon(QIcon(idle_icon_path))
                logging.info("Tray icon set with idle icon.")
            except Exception as e:
                logging.error(f"Error setting tray icon: {e}", exc_info=True)

            menu = QMenu()

            # Log before showing tray icon
            logging.info("About to call tray_icon.show()...")
            
            # --- Main Actions ---
            record_action = menu.addAction("Start Recording")
            record_action.setShortcut("Ctrl+R")
            record_action.triggered.connect(self.on_record)
            
            journal_action = menu.addAction("Start Journal Entry")
            journal_action.setShortcut("Ctrl+J")
            journal_action.triggered.connect(self.on_journal)
            
            menu.addSeparator()
            
            # --- Note Types ---
            note_types_menu = QMenu("Note Types")
            
            # Add configured note types with their hotkeys
            if hasattr(self.parent, 'config') and hasattr(self.parent.config, 'note_types'):
                for note_type in self.parent.config.note_types:
                    # Accept both object and string note types for robustness
                    if hasattr(note_type, 'name'):
                        name = note_type.name
                        hotkey_str = getattr(note_type, 'hotkey', '') or ''
                    elif isinstance(note_type, str):
                        name = note_type
                        hotkey_str = ''
                    else:
                        name = str(note_type)
                        hotkey_str = ''
                    action = note_types_menu.addAction(f"{name} ({hotkey_str})")
                    action.setData(name)  # Store note type name for reference
                    action.triggered.connect(
                        lambda checked, name=name: self._on_select_note_type(name)
                    )
            else:
                no_types_action = note_types_menu.addAction("No note types configured")
                no_types_action.setEnabled(False)
            
            note_types_menu.addSeparator()
            
            # Add actions
            add_note_type_action = note_types_menu.addAction("+ Add New Note Type")
            add_note_type_action.triggered.connect(self._on_add_note_type)
            
            configure_note_type_action = note_types_menu.addAction("⚙️ Configure Note Types")
            configure_note_type_action.triggered.connect(self._on_configure_note_types)
            
            menu.addMenu(note_types_menu)
            menu.addSeparator()
            
            # --- Settings Menu ---
            settings_menu = QMenu("Settings")
            
            # Audio Settings
            audio_menu = QMenu("Audio", settings_menu)
            
            # Input Devices Submenu
            self.audio_device_menu = QMenu("Input Device", audio_menu)
            self._populate_audio_devices(self.audio_device_menu)
            audio_menu.addMenu(self.audio_device_menu)
            
            # Sample Rate Submenu
            self.sample_rate_menu = QMenu("Sample Rate", audio_menu)
            sample_rates = [
                (8000, "8000 Hz"),
                (16000, "16000 Hz"),
                (44100, "44100 Hz"),
                (48000, "48000 Hz")
            ]
            
            # Get current sample rate from settings or use default (16000)
            current_rate = 16000
            if hasattr(self.parent, 'settings') and self.parent.settings:
                current_rate = self.parent.settings.value("audio/sample_rate", 16000, type=int)
            
            # Create action group for exclusive selection
            sample_rate_group = QActionGroup(self.sample_rate_menu)
            sample_rate_group.setExclusive(True)
            
            for rate, label in sample_rates:
                action = self.sample_rate_menu.addAction(label)
                action.setCheckable(True)
                action.setChecked(rate == current_rate)
                action.triggered.connect(lambda checked, r=rate: self._on_select_sample_rate(r))
                sample_rate_group.addAction(action)
                
            audio_menu.addMenu(self.sample_rate_menu)
            
            # Add refresh devices action
            refresh_action = audio_menu.addAction("⟳ Refresh Audio Devices")
            refresh_action.triggered.connect(lambda: self._populate_audio_devices(self.audio_device_menu))
            
            settings_menu.addMenu(audio_menu)
            
            # Storage Settings
            storage_menu = QMenu("Storage", settings_menu)
            
            recordings_action = storage_menu.addAction("Recordings Folder")
            recordings_action.triggered.connect(lambda: self._on_set_recordings_folder())
            
            markdown_action = storage_menu.addAction("Markdown Output")
            markdown_action.triggered.connect(lambda: self._on_set_markdown_folder())
            
            journal_action = storage_menu.addAction("Journal Location")
            if self.on_set_journal_dir:
                journal_action.triggered.connect(self.on_set_journal_dir)
            else:
                journal_action.setEnabled(False)
                
            settings_menu.addMenu(storage_menu)
            
            # Templates
            if self.on_configure_templates:
                templates_action = settings_menu.addAction("Configure Templates")
                templates_action.triggered.connect(self.on_configure_templates)
            
            
            menu.addMenu(settings_menu)
            
            # Import Audio Files
            if self.on_import_audio:
                menu.addSeparator()
                import_action = menu.addAction("Import Audio Files...")
                import_action.triggered.connect(self.on_import_audio)
            
            # Quit
            menu.addSeparator()
            quit_action = menu.addAction("Quit")
            quit_action.setShortcut("Ctrl+Q")
            quit_action.triggered.connect(self.on_quit)

            self.tray_icon.setContextMenu(menu)
            self.update_icon(recording=False)
            if not self.tray_icon.isVisible():
                logging.debug("Showing tray icon...")
                self.tray_icon.show()
                QTimer.singleShot(1000, self.check_tray_visibility)
            logging.info("System tray setup complete")
        except Exception as e:
            logging.error(f"Error setting up system tray: {e}", exc_info=True)
    
    def _on_select_note_type(self, note_type_name):
        """Handle selection of a note type from the menu."""
        if hasattr(self.parent, 'on_note_type_selected'):
            self.parent.on_note_type_selected(note_type_name)
        else:
            logging.warning(f"No handler for note type selection: {note_type_name}")
    
    def _on_add_note_type(self):
        """Handle adding a new note type."""
        if hasattr(self.parent, 'show_config_dialog'):
            self.parent.show_config_dialog.emit()
            # TODO: Switch to note types tab in the config dialog
    
    def _on_configure_note_types(self):
        """Handle configuring note types."""
        # This will be connected to the configuration dialog when implemented
        if hasattr(self.parent, 'show_config_dialog'):
            self.parent.show_config_dialog.emit()
            # TODO: Switch to note types tab
    
    def _on_set_recordings_folder(self):
        """Open a dialog to select the recordings folder."""
        try:
            current_dir = str(Path.home())
            if hasattr(self.parent, 'settings') and self.parent.settings:
                current_dir = self.parent.settings.value("recordings_dir", current_dir)
            
            folder = QFileDialog.getExistingDirectory(
                None,
                "Select Recordings Folder",
                current_dir,
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )
            
            if folder:
                if hasattr(self.parent, 'settings') and self.parent.settings:
                    self.parent.settings.setValue("recordings_dir", folder)
                    self.show_notification(
                        "Settings Updated",
                        f"Recordings folder set to: {folder}",
                        QSystemTrayIcon.MessageIcon.Information
                    )
                    return True
            return False
        except Exception as e:
            logging.error(f"Error setting recordings folder: {e}", exc_info=True)
            self.show_notification(
                "Error",
                f"Failed to set recordings folder: {str(e)}",
                QSystemTrayIcon.MessageIcon.Critical
            )
            return False
    
    def _on_set_markdown_folder(self):
        """Open a dialog to select the markdown output folder."""
        try:
            current_dir = str(Path.home() / "Documents")
            if hasattr(self.parent, 'settings') and self.parent.settings:
                current_dir = self.parent.settings.value("markdown_dir", current_dir)
            
            folder = QFileDialog.getExistingDirectory(
                None,
                "Select Markdown Output Folder",
                current_dir,
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )
            
            if folder:
                if hasattr(self.parent, 'settings') and self.parent.settings:
                    self.parent.settings.setValue("markdown_dir", folder)
                    self.show_notification(
                        "Settings Updated",
                        f"Markdown output folder set to: {folder}",
                        QSystemTrayIcon.MessageIcon.Information
                    )
                    return True
            return False
        except Exception as e:
            logging.error(f"Error setting markdown folder: {e}", exc_info=True)
            self.show_notification(
                "Error",
                f"Failed to set markdown folder: {str(e)}",
                QSystemTrayIcon.MessageIcon.Critical
            )
            return False
            
    def _populate_audio_devices(self, menu):
        """Populate the audio devices menu with available input devices."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            input_devices = [d for d in devices if d['max_input_channels'] > 0]
            
            # Clear existing actions
            menu.clear()
            
            # Add default option
            default_action = menu.addAction("Default System Device")
            default_action.setCheckable(True)
            default_action.setChecked(True)
            default_action.triggered.connect(lambda: self._on_select_audio_device(None))
            
            menu.addSeparator()
            
            # Add available input devices
            for i, device in enumerate(input_devices):
                device_name = f"{device['name']} (Channels: {device['max_input_channels']}, " \
                            f"Rate: {device['default_samplerate']}Hz)"
                action = menu.addAction(device_name)
                action.setCheckable(True)
                action.setData(i)  # Store device index
                action.triggered.connect(lambda checked, idx=i: self._on_select_audio_device(idx))
                
        except ImportError:
            logging.warning("sounddevice module not available, using default audio device")
            action = menu.addAction("Default (sounddevice not installed)")
            action.setEnabled(False)
            
    def _on_select_audio_device(self, device_index):
        """Handle audio device selection."""
        try:
            if hasattr(self.parent, 'settings') and self.parent.settings:
                self.parent.settings.setValue("audio/device_index", device_index)
                self.show_notification(
                    "Audio Settings",
                    f"Audio input device updated",
                    QSystemTrayIcon.MessageIcon.Information
                )
                return True
            return False
        except Exception as e:
            logging.error(f"Error setting audio device: {e}", exc_info=True)
            self.show_notification(
                "Error",
                f"Failed to set audio device: {str(e)}",
                QSystemTrayIcon.MessageIcon.Critical
            )
            return False

    def update_icon(self, recording: bool):
        """
        Update the system tray icon based on recording status.
        Args:
            recording (bool): Whether the app is currently recording.
        """
        try:
            if self.tray_icon:
                if recording:
                    icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.iconset', 'icon_32x32.png')
                    self.tray_icon.setIcon(QIcon(icon_path))
                    self.tray_icon.setToolTip("WhisperNotes (Recording...)")
                else:
                    icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.png')
                    self.tray_icon.setIcon(QIcon(icon_path))
                    self.tray_icon.setToolTip("WhisperNotes (Idle)")
            else:
                logging.warning("update_icon called but tray_icon not yet initialized.")
        except Exception as e:
            logging.error(f"Error in update_icon: {e}", exc_info=True)

    def check_tray_visibility(self):
        """
        Check if the tray icon is visible and show an error if not.
        """
        if not self.tray_icon or not self.tray_icon.isVisible():
            logging.error("Failed to show system tray icon")
            if QApplication.instance().topLevelWindows():
                QMessageBox.critical(
                    None,
                    "Error",
                    "Failed to show system tray icon. Please check your system tray settings."
                )

    def show_notification(self, title: str, message: str, icon=QSystemTrayIcon.Information, msecs=3000):
        """
        Show a notification from the tray icon.
        Args:
            title (str): Notification title
            message (str): Notification message
            icon: QSystemTrayIcon.MessageIcon (default: Information)
            msecs (int): Duration in milliseconds
        """
        if self.tray_icon:
            self.tray_icon.showMessage(title, message, icon, msecs)
        else:
            logging.warning("Attempted to show notification but tray_icon is not initialized.")
