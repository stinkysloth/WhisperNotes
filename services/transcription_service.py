"""
Transcription service for handling Whisper model loading and audio transcription.

This module provides the TranscriptionService class which manages the Whisper model
and handles audio transcription in a background thread.
"""

import logging
import os
import subprocess
import tempfile
import numpy as np
from typing import Optional, Dict, Any

from PySide6.QtCore import QObject, Signal, QThread, QMutex

from core.constants import AppConstants
from utils.audio_utils import convert_audio_to_wav

logger = logging.getLogger(__name__)

class TranscriptionService(QObject):
    """Service for handling audio transcription using Whisper."""
    
    # Signals
    model_loaded = Signal()
    transcription_started = Signal()
    transcription_finished = Signal(str)  # transcribed_text
    error_occurred = Signal(str)          # error_message
    
    def __init__(self, model_name: str = "base"):
        """Initialize the transcription service.
        
        Args:
            model_name: Name of the Whisper model to use (tiny, base, small, medium, large)
        """
        super().__init__()
        self.model_name = model_name
        self.model = None
        self.loading = False
        self.mutex = QMutex()
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the Whisper model in a background thread."""
        if self.loading or self.model is not None:
            return
            
        self.loading = True
        self.model_loader = ModelLoader(self.model_name)
        self.model_loader.finished.connect(self._on_model_loaded)
        self.model_loader.error.connect(self._on_model_error)
        
        # Start model loading in a separate thread
        self.model_thread = QThread()
        self.model_loader.moveToThread(self.model_thread)
        self.model_thread.started.connect(self.model_loader.run)
        self.model_thread.start()
        logger.info(f"Started loading Whisper model: {self.model_name}")
    
    def transcribe_audio(self, audio_data: np.ndarray, sample_rate: int) -> None:
        """Transcribe audio data in a background thread.
        
        Args:
            audio_data: Numpy array containing audio data
            sample_rate: Sample rate of the audio data
        """
        if self.model is None and not self.loading:
            error_msg = "Whisper model is not loaded"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return
            
        # Create a worker for the transcription
        self.transcription_worker = TranscriptionWorker(
            model_name=self.model_name,
            audio_data=audio_data,
            sample_rate=sample_rate
        )
        
        # Connect signals
        self.transcription_worker.transcription_ready.connect(self._on_transcription_ready)
        self.transcription_worker.error.connect(self._on_transcription_error)
        
        # Start transcription in a separate thread
        self.transcription_thread = QThread()
        self.transcription_worker.moveToThread(self.transcription_thread)
        self.transcription_thread.started.connect(self.transcription_worker.run)
        self.transcription_thread.start()
        
        self.transcription_started.emit()
        logger.info("Started audio transcription")
    
    def _on_model_loaded(self, model):
        """Handle successful model loading."""
        self.model = model
        self.loading = False
        logger.info(f"Whisper model loaded: {self.model_name}")
        self.model_loaded.emit()
    
    def _on_model_error(self, error_msg):
        """Handle model loading error."""
        self.loading = False
        logger.error(f"Failed to load Whisper model: {error_msg}")
        self.error_occurred.emit(f"Failed to load Whisper model: {error_msg}")
    
    def _on_transcription_ready(self, text):
        """Handle completed transcription."""
        logger.info("Transcription completed successfully")
        self.transcription_finished.emit(text)
    
    def _on_transcription_error(self, error_msg):
        """Handle transcription error."""
        logger.error(f"Transcription failed: {error_msg}")
        self.error_occurred.emit(f"Transcription failed: {error_msg}")


class ModelLoader(QObject):
    """Worker for loading the Whisper model in a background thread."""
    
    # Signals
    finished = Signal(object)  # loaded model
    error = Signal(str)        # error message
    
    def __init__(self, model_name: str = "base"):
        """Initialize the model loader.
        
        Args:
            model_name: Name of the Whisper model to load
        """
        super().__init__()
        self.model_name = model_name
    
    def run(self):
        """Load the Whisper model."""
        try:
            from faster_whisper import WhisperModel
            
            logger.info(f"Loading Whisper model: {self.model_name}")
            model = WhisperModel(
                self.model_name,
                device="auto",
                compute_type="int8"
            )
            
            # Test the model with a small audio buffer
            logger.debug("Testing model with empty audio")
            segments, _ = model.transcribe(
                np.zeros((16000,), dtype=np.float32),
                language="en"
            )
            list(segments)  # Force evaluation
            
            self.finished.emit(model)
            
        except Exception as e:
            error_msg = f"Failed to load Whisper model: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)


class TranscriptionWorker(QObject):
    """Worker for transcribing audio in a background thread."""
    
    # Signals
    finished = Signal()
    transcription_ready = Signal(str)  # transcribed text
    error = Signal(str)                # error message
    
    def __init__(self, model_name: str, audio_data: np.ndarray, sample_rate: int):
        """Initialize the transcription worker.
        
        Args:
            model_name: Name of the Whisper model to use
            audio_data: Numpy array containing audio data
            sample_rate: Sample rate of the audio data
        """
        super().__init__()
        self.model_name = model_name
        self.audio_data = audio_data
        self.sample_rate = sample_rate
        self._should_stop = False
    
    def run(self):
        """Run the transcription."""
        try:
            # Ensure audio is in the correct format
            if self.audio_data.dtype != np.float32:
                self.audio_data = self.audio_data.astype(np.float32) / 32768.0
            
            # Use faster-whisper for transcription
            from faster_whisper import WhisperModel
            
            logger.info(f"Starting transcription with model: {self.model_name}")
            model = WhisperModel(
                self.model_name,
                device="auto",
                compute_type="int8"
            )
            
            # Transcribe the audio
            segments, _ = model.transcribe(
                self.audio_data,
                language="en",
                beam_size=5,
                vad_filter=True
            )
            
            # Combine segments into a single text
            text = " ".join(segment.text for segment in segments)
            
            if self._should_stop:
                logger.info("Transcription was stopped")
                return
                
            logger.info("Transcription completed successfully")
            self.transcription_ready.emit(text.strip())
            
        except Exception as e:
            error_msg = f"Transcription failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error.emit(error_msg)
            
        finally:
            self.finished.emit()
    
    def request_stop(self):
        """Request the transcription to stop."""
        self._should_stop = True
        logger.info("Stopping transcription...")
