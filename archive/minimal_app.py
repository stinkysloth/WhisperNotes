#!/usr/bin/env python3
import sys
import os
import logging
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QGuiApplication
from PySide6.QtCore import Qt, QTimer

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("minimal_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MinimalApp')

class MinimalApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.tray_icon = None
        self.setup_app()
        
    def setup_app(self):
        """Set up the application with system tray icon."""
        try:
            logger.info("Setting up application...")
            
            # Enable High DPI scaling
            QGuiApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
            QGuiApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
            
            # Check if system tray is available
            if not QSystemTrayIcon.isSystemTrayAvailable():
                logger.error("System tray is not available on this system")
                QMessageBox.critical(None, "Error", "System tray is not available on this system")
                sys.exit(1)
                
            logger.info("System tray is available")
            
            # Create the system tray icon
            self.create_tray_icon()
            
            # Show the tray icon
            if self.tray_icon:
                self.tray_icon.show()
                logger.info("Tray icon shown")
                
                # Show a notification to help locate the icon
                self.tray_icon.showMessage(
                    "Minimal App",
                    "Application is running in the system tray",
                    QSystemTrayIcon.Information,
                    3000
                )
                logger.info("Notification shown")
            
        except Exception as e:
            logger.error(f"Error setting up application: {e}", exc_info=True)
            QMessageBox.critical(None, "Error", f"Failed to set up application: {e}")
            sys.exit(1)
    
    def create_tray_icon(self):
        """Create the system tray icon with menu."""
        try:
            logger.info("Creating tray icon...")
            
            # Create a simple colored circle icon
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(Qt.red)
            painter.setPen(Qt.black)
            painter.drawEllipse(4, 4, 24, 24)
            painter.end()
            
            # Save the icon for debugging
            icon_path = os.path.expanduser("~/minimal_app_icon.png")
            pixmap.save(icon_path)
            logger.info(f"Icon saved to {icon_path}")
            
            # Create the tray icon
            self.tray_icon = QSystemTrayIcon(QIcon(pixmap), self.app)
            self.tray_icon.setToolTip("Minimal App")
            
            # Create the context menu
            menu = QMenu()
            
            # Add a test action
            test_action = menu.addAction("Test Action")
            test_action.triggered.connect(self.on_test_action)
            
            # Add a quit action
            quit_action = menu.addAction("Quit")
            quit_action.triggered.connect(self.quit_app)
            
            # Set the context menu
            self.tray_icon.setContextMenu(menu)
            
            logger.info("Tray icon created successfully")
            
        except Exception as e:
            logger.error(f"Error creating tray icon: {e}", exc_info=True)
            raise
    
    def on_test_action(self):
        """Handle test action from the tray menu."""
        logger.info("Test action triggered")
        QMessageBox.information(None, "Test", "Test action triggered!")
    
    def quit_app(self):
        """Quit the application."""
        logger.info("Quitting application...")
        self.app.quit()
    
    def run(self):
        """Run the application."""
        logger.info("Starting application...")
        return self.app.exec()

if __name__ == "__main__":
    try:
        app = MinimalApp()
        sys.exit(app.run())
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        QMessageBox.critical(None, "Fatal Error", f"The application encountered a fatal error: {e}")
        sys.exit(1)
