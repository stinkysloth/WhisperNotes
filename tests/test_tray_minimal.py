import sys
import os
import platform
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QGuiApplication
from PySide6.QtCore import Qt

# Print debug information
print("Python executable:", sys.executable)
print("Python version:", sys.version)
print("Platform:", platform.platform())
print("Current working directory:", os.getcwd())
print("Environment:")
for var in ["QT_DEBUG_PLUGINS", "QT_LOGGING_RULES", "QT_QUICK_BACKEND"]:
    print(f"  {var}: {os.environ.get(var, 'Not set')}")

# Set QT_LOGGING_RULES to see Qt debug messages
os.environ["QT_LOGGING_RULES"] = "qt.qpa.*=true"

def create_test_app():
    # Enable high DPI scaling
    QGuiApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QGuiApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    # Create application instance
    app = QApplication(sys.argv)
    print("QApplication created")
    
    # Check if system tray is available
    print("Checking if system tray is available...")
    if not QSystemTrayIcon.isSystemTrayAvailable():
        error_msg = "System tray is not available on this system"
        print(error_msg)
        QMessageBox.critical(None, "Error", error_msg)
        sys.exit(1)
    print("System tray is available")
    
    # Create a simple red circle icon
    try:
        print("Creating icon...")
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(255, 0, 0))  # Red circle
        painter.setPen(QColor(0, 0, 0))  # Black border
        painter.drawEllipse(4, 4, 24, 24)  # Draw a circle
        painter.end()
        
        # Save the icon for debugging
        icon_path = os.path.join(os.path.expanduser("~"), "tray_icon_debug.png")
        pixmap.save(icon_path)
        print(f"Icon saved to {icon_path}")
        
        # Create tray icon
        print("Creating system tray icon...")
        tray_icon = QSystemTrayIcon(QIcon(pixmap), app)
        tray_icon.setToolTip("Test Tray Icon")
        print("System tray icon created")
    except Exception as e:
        print(f"Error creating icon: {e}")
        # Try with a simple text icon as fallback
        try:
            print("Trying fallback icon...")
            tray_icon = QSystemTrayIcon()
            tray_icon.showMessage("Test", "Using fallback icon", QSystemTrayIcon.Information, 2000)
            print("Fallback icon created")
        except Exception as e2:
            print(f"Fallback icon failed: {e2}")
            QMessageBox.critical(None, "Error", f"Failed to create system tray icon: {e}\n{e2}")
            sys.exit(1)
    
    # Create menu
    try:
        print("Creating menu...")
        menu = QMenu()
        test_action = menu.addAction("Test Action")
        test_action.triggered.connect(lambda: print("Test action triggered"))
        menu.addSeparator()
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(app.quit)
        
        # Set the menu
        print("Setting context menu...")
        tray_icon.setContextMenu(menu)
        print("Context menu set")
        
        # Show the tray icon
        print("Showing tray icon...")
        tray_icon.show()
        print("Tray icon show() called")
        
        # Show a message to help locate the icon
        tray_icon.showMessage(
            "WhisperNotes",
            "Application is running in the system tray",
            QSystemTrayIcon.Information,
            3000
        )
        print("Notification shown")
        
        print("Tray icon should be visible now")
        print("If you don't see the icon, check the menu bar at the top of the screen")
        print("On macOS, some applications might appear in the 'extras' section of the menu bar")
        
    except Exception as e:
        print(f"Error setting up menu: {e}")
        QMessageBox.critical(None, "Error", f"Failed to set up menu: {e}")
        sys.exit(1)
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    create_test_app()
