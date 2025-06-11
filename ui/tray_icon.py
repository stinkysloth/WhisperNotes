"""
System tray icon for WhisperNotes.

This module provides the system tray icon and its menu functionality.
"""

import logging
import os
from typing import Optional, Callable, Dict, Any

from PySide6.QtCore import QObject, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QIcon, QAction, QSystemTrayIcon, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QMenu, QApplication

from core.constants import AppConstants

logger = logging.getLogger(__name__)

class TrayIcon(QSystemTrayIcon):
    """System tray icon for WhisperNotes."""
    
    # Signals
    show_window = Signal()
    hide_window = Signal()
    toggle_window = Signal()
    record_triggered = Signal()
    stop_triggered = Signal()
    journal_mode_toggled = Signal(bool)
    quit_triggered = Signal()
    
    def __init__(
        self,
        icon_path: Optional[str] = None,
        parent: Optional[QObject] = None
    ):
        """Initialize the system tray icon.
        
        Args:
            icon_path: Path to the icon file
            parent: Parent object
        """
        # Set default icon if not provided
        if icon_path is None or not os.path.exists(icon_path):
            icon_path = ":/icons/app.png"
        
        self.icon_base = QIcon(icon_path)
        self.recording_icon = self._create_recording_icon()
        
        # Initialize with base icon
        super().__init__(self.icon_base, parent)
        
        # State
        self.is_recording = False
        self.is_journal_mode = False
        self.is_visible = True
        self.recording_animation = False
        self.recording_animation_frame = 0
        
        # Create menu
        self.menu = QMenu()
        self._create_actions()
        self._update_menu()
        
        # Set context menu
        self.setContextMenu(self.menu)
        
        # Connect signals
        self.activated.connect(self._on_activated)
        self.messageClicked.connect(self._on_message_clicked)
        
        # Animation timer
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.setInterval(500)  # 0.5 second interval
        
        # Show the tray icon
        self.show()
    
    def _create_actions(self) -> None:
        """Create menu actions."""
        # Toggle window visibility
        self.toggle_window_action = QAction(
            "&Show/Hide",
            self,
            triggered=self.toggle_window.emit
        )
        
        # Record action
        self.record_action = QAction(
            "&Start Recording",
            self,
            triggered=self.record_triggered.emit
        )
        
        # Stop action
        self.stop_action = QAction(
            "S&top Recording",
            self,
            triggered=self.stop_triggered.emit
        )
        self.stop_action.setEnabled(False)
        
        # Toggle journal mode
        self.journal_mode_action = QAction(
            "&Journal Mode",
            self,
            checkable=True,
            toggled=self._on_journal_mode_toggled
        )
        
        # Quit action
        self.quit_action = QAction(
            "&Quit",
            self,
            triggered=self._on_quit_triggered
        )
    
    def _update_menu(self) -> None:
        """Update the context menu based on current state."""
        self.menu.clear()
        
        # Add actions to menu
        self.menu.addAction(self.toggle_window_action)
        self.menu.addSeparator()
        
        # Recording actions
        if not self.is_recording:
            self.menu.addAction(self.record_action)
        else:
            self.menu.addAction(self.stop_action)
        
        self.menu.addSeparator()
        
        # Journal mode
        self.journal_mode_action.setChecked(self.is_journal_mode)
        self.menu.addAction(self.journal_mode_action)
        
        self.menu.addSeparator()
        
        # Quit
        self.menu.addAction(self.quit_action)
    
    def _create_recording_icon(self) -> QIcon:
        """Create a recording indicator icon.
        
        Returns:
            QIcon: Icon with recording indicator
        """
        # Start with the base icon
        base_pixmap = self.icon_base.pixmap(64, 64)
        
        # Create a new pixmap to draw on
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        
        # Create a painter
        painter = QPainter(pixmap)
        
        try:
            # Draw the base icon
            painter.drawPixmap(0, 0, base_pixmap)
            
            # Draw a red recording indicator (circle in top-right corner)
            painter.setBrush(Qt.red)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(40, 8, 16, 16)
            
            return QIcon(pixmap)
            
        finally:
            painter.end()
    
    def set_recording_state(self, is_recording: bool) -> None:
        """Set the recording state.
        
        Args:
            is_recording: Whether recording is in progress
        """
        if self.is_recording == is_recording:
            return
            
        self.is_recording = is_recording
        
        # Update icon
        if is_recording:
            self.setIcon(self.recording_icon)
            self.animation_timer.start()
        else:
            self.animation_timer.stop()
            self.setIcon(self.icon_base)
        
        # Update menu
        self._update_menu()
        
        # Show notification
        if is_recording:
            self.showMessage(
                "Recording Started",
                "Click to stop recording",
                QSystemTrayIcon.Information,
                2000
            )
    
    def set_journal_mode(self, enabled: bool) -> None:
        """Set journal mode.
        
        Args:
            enabled: Whether journal mode is enabled
        """
        if self.is_journal_mode == enabled:
            return
            
        self.is_journal_mode = enabled
        self.journal_mode_action.setChecked(enabled)
        
        # Show notification
        mode = "Journal" if enabled else "Transcription"
        self.showMessage(
            f"{mode} Mode",
            f"Switched to {mode.lower()} mode",
            QSystemTrayIcon.Information,
            2000
        )
    
    def set_visible_state(self, is_visible: bool) -> None:
        """Set the window visibility state.
        
        Args:
            is_visible: Whether the main window is visible
        """
        self.is_visible = is_visible
        self._update_menu()
    
    @Slot()
    def _on_activated(self, reason):
        """Handle tray icon activation.
        
        Args:
            reason: The reason for activation
        """
        if reason == QSystemTrayIcon.Trigger:
            # Single click - toggle window
            self.toggle_window.emit()
        elif reason == QSystemTrayIcon.DoubleClick:
            # Double click - show window
            self.show_window.emit()
        elif reason == QSystemTrayIcon.MiddleClick:
            # Middle click - start/stop recording
            if self.is_recording:
                self.stop_triggered.emit()
            else:
                self.record_triggered.emit()
    
    @Slot()
    def _on_message_clicked(self):
        """Handle message click."""
        self.show_window.emit()
    
    @Slot(bool)
    def _on_journal_mode_toggled(self, checked: bool) -> None:
        """Handle journal mode toggle.
        
        Args:
            checked: Whether journal mode is checked
        """
        self.journal_mode_toggled.emit(checked)
    
    @Slot()
    def _on_quit_triggered(self) -> None:
        """Handle quit action."""
        # Stop any ongoing recording
        if self.is_recording:
            self.stop_triggered.emit()
            
        # Emit quit signal
        self.quit_triggered.emit()
    
    @Slot()
    def _update_animation(self) -> None:
        """Update recording animation."""
        if not self.is_recording:
            return
            
        # Toggle between two states for the recording indicator
        if self.recording_animation_frame % 2 == 0:
            self.setIcon(self.recording_icon)
        else:
            self.setIcon(self.icon_base)
            
        self.recording_animation_frame += 1
    
    def show_notification(self, title: str, message: str, timeout: int = 5000) -> None:
        """Show a notification message.
        
        Args:
            title: Notification title
            message: Notification message
            timeout: Timeout in milliseconds
        """
        self.showMessage(title, message, QSystemTrayIcon.Information, timeout)
    
    def show_error(self, title: str, message: str, timeout: int = 5000) -> None:
        """Show an error message.
        
        Args:
            title: Error title
            message: Error message
            timeout: Timeout in milliseconds
        """
        self.showMessage(title, message, QSystemTrayIcon.Critical, timeout)
    
    def close(self) -> None:
        """Clean up resources."""
        self.animation_timer.stop()
        super().hide()
        super().deleteLater()
