"""
Audio service for handling audio recording and playback.

This module provides the AudioService class which manages audio recording,
playback, and related functionality.
"""

import logging
import time
import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal, Slot, QMutex

from core.constants import AppConstants, RecordingState
from utils.audio_utils import save_audio

logger = logging.getLogger(__name__)

class AudioService(QObject):
    """Service for handling audio recording and playback."""
    
    # Signals
    recording_started = Signal()
    recording_stopped = Signal()
    recording_finished = Signal(object)  # audio_data
    error_occurred = Signal(str)         # error_message
    
    def __init__(self):
        """Initialize the audio service."""
        super().__init__()
        self.recording_thread = None
        self.recording_state = RecordingState.STOPPED
        self.audio_data = None
        self.sample_rate = AppConstants.SAMPLE_RATE
        self.mutex = QMutex()
        
    def start_recording(self) -> bool:
        """Start audio recording using QThread and RecordingWorker."""
        if self.recording_state != RecordingState.STOPPED:
            logger.warning("Recording already in progress")
            return False
        try:
            self.recording_state = RecordingState.RECORDING
            self.audio_data = []

            # Set up QThread and worker
            from PySide6.QtCore import QThread
            self.recording_thread = QThread()
            self.recording_worker = RecordingWorker(
                sample_rate=self.sample_rate,
                channels=1,
                chunk_size=AppConstants.CHUNK_SIZE,
                max_duration=AppConstants.MAX_RECORDING_DURATION
            )
            self.recording_worker.moveToThread(self.recording_thread)
            self.recording_thread.started.connect(self.recording_worker.run)
            self.recording_worker.finished.connect(self._on_recording_finished)
            self.recording_worker.finished.connect(self.recording_thread.quit)
            self.recording_worker.finished.connect(self.recording_worker.deleteLater)
            self.recording_thread.finished.connect(self.recording_thread.deleteLater)
            self.recording_worker.error.connect(self._on_recording_error)
            self.recording_worker.error.connect(self.recording_thread.quit)
            self.recording_worker.error.connect(self.recording_worker.deleteLater)
            self.recording_thread.finished.connect(self.recording_thread.deleteLater)

            self.recording_thread.start()
            self.recording_started.emit()
            logger.info("Recording started")
            return True
        except Exception as e:
            self.recording_state = RecordingState.STOPPED
            error_msg = f"Failed to start recording: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False

    
    def stop_recording(self) -> bool:
        """Stop the current recording."""
        if self.recording_state != RecordingState.RECORDING:
            return False
        try:
            if hasattr(self, 'recording_worker') and self.recording_worker:
                self.recording_worker.stop()
            if self.recording_thread and self.recording_thread.isRunning():
                self.recording_thread.quit()
                self.recording_thread.wait()
            self.recording_state = RecordingState.STOPPED
            logger.info("Recording stopped")
            return True
        except Exception as e:
            error_msg = f"Error stopping recording: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False

    
    def save_recording(self, file_path: str, format: str = "wav") -> bool:
        """Save the current recording to a file.
        
        Args:
            file_path: Path to save the recording to
            format: Audio format (wav, mp3, etc.)
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        if not self.audio_data or len(self.audio_data) == 0:
            logger.warning("No audio data to save")
            return False
            
        try:
            # Convert audio data to numpy array if needed
            audio_array = np.concatenate(self.audio_data) if len(self.audio_data) > 1 else self.audio_data[0]
            
            # Save the audio file
            save_audio_to_file(audio_array, self.sample_rate, file_path, format)
            logger.info(f"Audio saved to {file_path}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to save audio: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False
    
    def _on_recording_finished(self, audio_data):
        """Handle recording finished signal."""
        self.recording_state = RecordingState.STOPPED
        self.audio_data = [audio_data]  # Store as list for consistency
        self.recording_finished.emit(audio_data)
    
    def _on_recording_error(self, error_msg):
        """Handle recording error signal."""
        self.recording_state = RecordingState.STOPPED
        self.error_occurred.emit(error_msg)


from PySide6.QtCore import QObject, Signal, QThread

class RecordingWorker(QObject):
    """Worker object for recording audio, to be run in a QThread."""
    finished = Signal(object)  # audio_data
    error = Signal(str)

    def __init__(self, sample_rate=16000, channels=1, chunk_size=1024, max_duration=900.0):
        super().__init__()
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.max_duration = max_duration
        self.stop_flag = False
        self.audio_data = []

    def run(self):
        import sounddevice as sd
        import numpy as np
        import time
        try:
            self.audio_data = []
            start_time = time.time()
            def callback(indata, frames, time_info, status):
                if status:
                    logger.warning(f"Audio stream status: {status}")
                if self.stop_flag:
                    raise sd.CallbackStop()
                if time.time() - start_time > self.max_duration:
                    logger.warning("Maximum recording duration reached")
                    raise sd.CallbackStop()
                self.audio_data.append(indata.copy())
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=callback,
                blocksize=self.chunk_size
            ) as stream:
                logger.info("Audio stream started")
                while not self.stop_flag:
                    sd.sleep(100)
            if self.audio_data:
                audio_data = np.concatenate(self.audio_data)
                self.finished.emit(audio_data)
        except Exception as e:
            error_msg = f"Recording error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
    def stop(self):
        self.stop_flag = True
