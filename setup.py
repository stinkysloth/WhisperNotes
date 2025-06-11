"""
Setup file for creating a macOS application bundle with py2app.
"""
import os
from setuptools import setup

APP = ['whisper_notes.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': [
        'PySide6', 'whisper', 'sounddevice', 'pynput', 'numpy', 'librosa',
        'soundfile', 'pydub', 'torch', 'transformers', 'sentencepiece',
        'tqdm', 'requests', 'urllib3', 'chardet', 'idna', 'certifi',
        'pyobjc', 'AppKit', 'Foundation', 'Quartz'
    ],
    'excludes': ['tkinter'],
    'plist': {
        'CFBundleName': 'WhisperNotes',
        'CFBundleDisplayName': 'WhisperNotes',
        'CFBundleIdentifier': 'com.whispernotes.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': '© 2025 WhisperNotes',
        'LSUIElement': True,  # Makes the app run without showing in the dock
    },
    'iconfile': 'assets/icon.icns' if os.path.exists('assets/icon.icns') else None,
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
