"""
Minimal setup file for creating a macOS application bundle with py2app.
"""
import os
from setuptools import setup

APP = ['whisper_notes.py']
DATA_FILES = [
    ('assets', ['assets/icon.icns']),  # Include the icon file
]

# Minimal configuration to avoid recursion errors
OPTIONS = {
    'argv_emulation': False,
    'packages': [],  # Start with no packages, let py2app find them
    'includes': [],  # Start with no explicit includes
    'excludes': [
        'tkinter', 'PyQt5', 'PyQt6', 'PySide2', 'matplotlib', 'scipy',
        'pandas', 'sklearn', 'IPython', 'jupyter', 'notebook', 'pytest',
        'unittest', 'pydoc', 'doctest', 'pdb', 'setuptools', 'pip',
        'wheel', 'virtualenv', 'venv', 'distutils', 'ensurepip', 'Cython'
    ],
    'plist': {
        'CFBundleName': 'WhisperNotes',
        'CFBundleDisplayName': 'WhisperNotes',
        'CFBundleIdentifier': 'com.whispernotes.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': '© 2025 WhisperNotes',
        'LSUIElement': True,  # Makes the app run without showing in the dock
        'NSMicrophoneUsageDescription': 'WhisperNotes needs access to your microphone for voice recording.',
        'NSSpeechRecognitionUsageDescription': 'WhisperNotes needs access to speech recognition for transcribing your voice.',
    },
    'iconfile': 'assets/icon.icns' if os.path.exists('assets/icon.icns') else None,
    'optimize': 1,
    'semi_standalone': True,
    'strip': True,
    'site_packages': True,  # Try with site-packages included
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
