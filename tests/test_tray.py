#!/usr/bin/env python3
import sys
import os
import platform
import logging
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QStyle, QMessageBox
from PySide6.QtGui import QIcon, QPixmap, QColor, QGuiApplication
from PySide6.QtCore import QSize, Qt, QTimer

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TestTray')

def create_placeholder_icon():
    # Create a simple colored icon as a fallback
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(65, 105, 225))  # Royal Blue square as a placeholder
    return QIcon(pixmap)

def main():
    logger.info("Starting application...")
    logger.info(f"Python {platform.python_version()} on {platform.system()} {platform.release()}")
    
    try:
        from PySide6 import __version__ as pyside_version
        logger.info(f"PySide6 version: {pyside_version}")
    except ImportError as e:
        logger.error(f"Could not get PySide6 version: {e}")
    
    # Create the application
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    app.setQuitOnLastWindowClosed(False)
    logger.info("Application instance created")
    
    # Check if system tray is available
    if not QSystemTrayIcon.isSystemTrayAvailable():
        error_msg = "System tray is not available on this system!"
        logger.error(error_msg)
        QMessageBox.critical(None, "Error", error_msg)
        return 1
    
    logger.info("System tray is available")
    
    # Create the tray icon
    try:
        tray_icon = QSystemTrayIcon()
        logger.info("Tray icon created")
    except Exception as e:
        error_msg = f"Failed to create system tray icon: {e}"
        logger.error(error_msg, exc_info=True)
        QMessageBox.critical(None, "Error", error_msg)
        return 1
    
    # Set a simple icon that should work on all platforms
    icon_set = False
    
    # Try different icon sources
    icon_sources = [
        # Try built-in icons first
        lambda: app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon),
        lambda: app.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon),
        lambda: app.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon),
        # Then try a simple colored icon
        create_placeholder_icon,
    ]
    
    for icon_source in icon_sources:
        try:
            icon = icon_source() if callable(icon_source) else icon_source
            if not icon.isNull():
                tray_icon.setIcon(icon)
                logger.info(f"Successfully set icon from {icon_source.__name__ if callable(icon_source) else 'source'}")
                icon_set = True
                break
        except Exception as e:
            logger.warning(f"Could not set icon from source: {e}")
    
    if not icon_set:
        error_msg = "Failed to set any icon for the system tray"
        logger.error(error_msg)
        QMessageBox.critical(None, "Error", error_msg)
        return 1
    
    try:
        # Create a simple menu
        menu = QMenu()
        
        # Add a quit action
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(app.quit)
        
        # Set the menu and show the tray icon
        tray_icon.setContextMenu(menu)
        logger.info("Context menu created and set")
        
        # Show the tray icon
        tray_icon.show()
        logger.info("Tray icon shown")
        
        # Show a message
        tray_icon.showMessage(
            "Test",
            "System tray is working!",
            QSystemTrayIcon.Information,
            3000  # 3 seconds
        )
        logger.info("Test message shown")
        
        # Set up a timer to check if the icon is visible
        def check_icon_visibility():
            if not tray_icon.isVisible():
                logger.error("Tray icon is not visible!")
                QMessageBox.critical(None, "Error", "Tray icon is not visible. Please check your system tray settings.")
            else:
                logger.info("Tray icon is visible")
        
        # Check after a short delay
        QTimer.singleShot(2000, check_icon_visibility)
        
    except Exception as e:
        error_msg = f"Error setting up tray menu: {e}"
        logger.error(error_msg, exc_info=True)
        QMessageBox.critical(None, "Error", error_msg)
        return 1
    
    try:
        logger.info("Starting application event loop")
        return app.exec()
    except Exception as e:
        logger.critical(f"Critical error in application: {e}", exc_info=True)
        return 1
    finally:
        logger.info("Application shutting down")

if __name__ == "__main__":
    sys.exit(main())
