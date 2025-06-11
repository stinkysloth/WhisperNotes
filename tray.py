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
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QMessageBox, QApplication
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, QTimer

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
        on_edit_prompt=None,
        on_set_journal_dir=None,
        on_configure_templates=None,
        on_settings=None
    ):
        """
        Initialize the tray manager.

        Args:
            app: The QApplication instance
            parent: The parent widget or main window
            on_record: Callback for record action
            on_journal: Callback for journal action
            on_quit: Callback for quit action
            on_edit_prompt: Callback to edit the journaling summary prompt (optional)
            on_set_journal_dir: Callback to set the journal directory (optional)
            on_configure_templates: Callback to configure templates (optional)
            on_settings: Generic callback for settings action (optional, for backward compatibility)
        """
        self.app = app
        self.parent = parent
        self.on_record = on_record
        self.on_journal = on_journal
        self.on_quit = on_quit
        self.on_edit_prompt = on_edit_prompt
        self.on_set_journal_dir = on_set_journal_dir
        self.on_configure_templates = on_configure_templates
        self.on_settings = on_settings
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

            menu = QMenu()
            record_action = menu.addAction("Record")
            record_action.triggered.connect(self.on_record)
            journal_action = menu.addAction("Journal")
            journal_action.triggered.connect(self.on_journal)

            # --- Settings/Config submenu ---
            settings_menu = QMenu("Settings && Configuration")
            any_settings = False
            if self.on_edit_prompt:
                edit_prompt_action = settings_menu.addAction("Edit Summary Prompt...")
                edit_prompt_action.triggered.connect(self.on_edit_prompt)
                any_settings = True
            if self.on_set_journal_dir:
                set_journal_dir_action = settings_menu.addAction("Set Journal Directory...")
                set_journal_dir_action.triggered.connect(self.on_set_journal_dir)
                any_settings = True
            if self.on_configure_templates:
                config_templates_action = settings_menu.addAction("Configure Templates...")
                config_templates_action.triggered.connect(self.on_configure_templates)
                any_settings = True
            # Optionally add generic settings fallback
            if self.on_settings:
                generic_settings_action = settings_menu.addAction("Other Settings...")
                generic_settings_action.triggered.connect(self.on_settings)
                any_settings = True
            if any_settings:
                menu.addMenu(settings_menu)
            menu.addSeparator()
            quit_action = menu.addAction("Quit")
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

    def update_icon(self, recording: bool):
        """
        Update the system tray icon based on recording status.
        Args:
            recording (bool): Whether the app is currently recording.
        """
        try:
            pixmap = QPixmap(32, 32)
            if recording:
                pixmap.fill(Qt.GlobalColor.red)
                self.tray_icon.setToolTip("Voice Typer (Recording...)")
            else:
                pixmap.fill(Qt.GlobalColor.gray)
                self.tray_icon.setToolTip("Voice Typer (Idle)")
            if self.tray_icon:
                self.tray_icon.setIcon(QIcon(pixmap))
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
