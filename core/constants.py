"""
Application-wide constants for WhisperNotes.
"""
import sys
from enum import Enum

class AppConstants:
    """Application constants."""
    APP_NAME = "WhisperNotes"
    VERSION = "1.0.0"
    ORGANIZATION = "WhisperNotes"
    
    # Default paths
    DEFAULT_JOURNAL_DIR = "~/Documents/Personal/Audio Journal"
    DEFAULT_OUTPUT_FILE = "~/Documents/WhisperNotesTranscriptions.md"
    
    # Audio settings
    SAMPLE_RATE = 16000  # Hz
    CHANNELS = 1  # Mono
    CHUNK_SIZE = 1024
    
    # Recording settings
    MAX_RECORDING_DURATION = 900  # 15 minutes in seconds
    
    # Hotkey defaults (platform-specific)
    if sys.platform == 'darwin':
        DEFAULT_RECORD_HOTKEY = "cmd+shift+r"
        DEFAULT_JOURNAL_HOTKEY = "cmd+shift+j"
        DEFAULT_QUIT_HOTKEY = "cmd+q"
    else:  # Windows/Linux
        DEFAULT_RECORD_HOTKEY = "ctrl+shift+r"
        DEFAULT_JOURNAL_HOTKEY = "ctrl+shift+j"
        DEFAULT_QUIT_HOTKEY = "ctrl+q"

class RecordingState(Enum):
    """Recording state enumeration."""
    STOPPED = 0
    RECORDING = 1
    PROCESSING = 2

class JournalMode(Enum):
    """Journal mode enumeration."""
    NORMAL = 0
    JOURNAL = 1
