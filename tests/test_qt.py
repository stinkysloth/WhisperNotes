#!/usr/bin/env python3
import sys
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

def main():
    print("Creating QApplication...")
    app = QApplication(sys.argv)
    
    print("Creating main window...")
    window = QWidget()
    window.setWindowTitle("Test Window")
    
    layout = QVBoxLayout()
    label = QLabel("If you can see this, PySide6 is working!")
    layout.addWidget(label)
    window.setLayout(layout)
    
    print("Showing window...")
    window.show()
    
    print("Starting event loop...")
    sys.exit(app.exec())

if __name__ == "__main__":
    print("Starting test script...")
    main()
