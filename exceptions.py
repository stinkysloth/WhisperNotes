"""Custom exceptions for the WhisperNotes application."""

class WhisperNotesError(Exception):
    """Base exception for all WhisperNotes exceptions."""
    pass

class AudioError(WhisperNotesError):
    """Base class for audio-related errors."""
    pass

class AudioRecordingError(AudioError):
    """Raised when there's an error during audio recording."""
    pass

class AudioSaveError(AudioError):
    """Raised when there's an error saving audio data."""
    pass

class AudioPlaybackError(AudioError):
    """Raised when there's an error during audio playback."""
    pass

class TranscriptionError(WhisperNotesError):
    """Raised when there's an error during transcription."""
    pass

class ModelError(WhisperNotesError):
    """Raised when there's an error with the AI model."""
    pass

class JournalingError(WhisperNotesError):
    """Raised when there's an error with journal operations."""
    pass

class FileSystemError(WhisperNotesError):
    """Raised when there's an error with file system operations."""
    pass

class ConfigurationError(WhisperNotesError):
    """Raised when there's an error with application configuration."""
    pass

def handle_error(error: Exception, context: str = "") -> str:
    """Handle an exception and return a user-friendly error message.
    
    Args:
        error: The exception that was raised
        context: Additional context about where the error occurred
        
    Returns:
        str: A user-friendly error message
    """
    import logging
    from PySide6.QtWidgets import QMessageBox
    
    # Log the error with stack trace
    logging.error(f"Error in {context or 'unknown context'}: {str(error)}", exc_info=True)
    
    # Generate user-friendly message based on error type
    if isinstance(error, AudioRecordingError):
        msg = "An error occurred while recording audio. Please check your microphone and try again."
    elif isinstance(error, AudioSaveError):
        msg = "Failed to save the audio file. Please check available disk space and permissions."
    elif isinstance(error, TranscriptionError):
        msg = "An error occurred during transcription. The audio might be too short or inaudible."
    elif isinstance(error, ModelError):
        msg = "An error occurred with the AI model. Please check your model configuration."
    elif isinstance(error, JournalingError):
        msg = "An error occurred while saving your journal entry. Your data might not have been saved."
    elif isinstance(error, FileSystemError):
        msg = "A file system error occurred. Please check disk space and permissions."
    elif isinstance(error, ConfigurationError):
        msg = "There's a problem with the application configuration. Please check your settings."
    else:
        msg = "An unexpected error occurred. Please try again later."
    
    # Do not show QMessageBox here; only return the message. GUI dialogs must be shown on the main thread.
    return msg
