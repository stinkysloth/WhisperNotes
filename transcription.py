"""
transcription.py
---------------
Model loading and transcription threading logic for WhisperNotes.

Responsibilities:
- ModelLoader class
- TranscriptionWorker class
- Whisper model loading and error handling
"""

# Qt and threading dependencies
import logging
from PySide6.QtCore import QObject, Signal

# Error handling dependencies (assume these are available in the main app)
try:
    from exceptions import TranscriptionError, ModelError
except ImportError:
    class TranscriptionError(Exception): pass
    class ModelError(Exception): pass

class ModelLoader(QObject):
    """
    Worker for loading the Whisper model in a background thread.

    This class is responsible for asynchronously loading the Whisper ASR model
    to avoid blocking the main UI thread. Signals are emitted on success or error.

    Args:
        model_name (str): Name of the Whisper model to load (default: "base").
    """
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, model_name="base"):
        """
        Initialize the model loader.

        Args:
            model_name (str): Name of the Whisper model to load.
        """
        super().__init__()
        self.model_name = model_name

    def run(self):
        """
        Load the Whisper model and emit the finished signal.

        Emits:
            finished(model): When the model is loaded successfully.
            error(str): If an error occurs during loading.
        """
        try:
            logging.info("Loading Whisper model...")
            from faster_whisper import WhisperModel
            # Map model names to faster-whisper compatible names if needed
            model_name_map = {
                "tiny": "tiny",
                "base": "base",
                "small": "small",
                "medium": "medium",
                "large": "large",
                "large-v2": "large-v2",
                "large-v3": "large-v3"
            }
            # Use mapped name or original if not in map
            model_name = model_name_map.get(self.model_name, self.model_name)
            # Load the model with faster-whisper
            model = WhisperModel(model_name, device="cpu", compute_type="int8")
            logging.info("Whisper model loaded using faster-whisper")
            self.finished.emit(model)
        except Exception as e:
            error_msg = f"Error loading Whisper model: {e}"
            logging.error(error_msg, exc_info=True)
            self.error.emit(error_msg)


class TranscriptionWorker(QObject):
    """
    Worker for transcribing audio with Whisper via an external subprocess.

    This class manages audio transcription in a background thread, using an
    external process for isolation and reliability. Emits signals for completion,
    errors, and result delivery. Designed for use with Qt threading.

    Args:
        model_name (str): Name of the Whisper model to use.
        audio_data (np.ndarray): Audio data to transcribe.

    Constraints:
        - Should be run in a QThread.
        - Emits Qt signals for thread-safe communication.
    """
    finished = Signal()
    transcription_ready = Signal(str)
    error = Signal(str)

    def __init__(self, model_name, audio_data):
        """
        Initialize the transcription worker.

        Args:
            model_name (str): Name of the Whisper model to use.
            audio_data (np.ndarray): Audio data to transcribe.
        """
        super().__init__()
        self.model_name = model_name
        self.audio_data = audio_data
        self.timeout = 120 # Timeout for subprocess in seconds
        self._should_stop = False
        self.process = None
        logging.debug(f"TranscriptionWorker initialized for model {self.model_name}")

    def request_stop(self):
        logging.info("TranscriptionWorker: Stop requested.")
        self._should_stop = True
        if self.process and self.process.poll() is None: # If process exists and is running
            logging.info("TranscriptionWorker: Terminating active subprocess due to stop request.")
            try:
                self.process.kill()
                self.process.wait(timeout=2) # Give it a moment to die
            except Exception as e:
                logging.warning(f"TranscriptionWorker: Error killing subprocess: {e}")
        self.process = None # Ensure process handle is cleared

    def run(self):
        logging.info("[TranscriptionWorker] RUN METHOD ENTERED (topmost line).")
        import numpy as np
        import soundfile as sf
        import tempfile
        import subprocess
        import json
        import os
        import sys
        import traceback

        try:
            logging.getLogger().handlers[0].flush()
            if self._should_stop:
                logging.info("[TranscriptionWorker] Aborting _do_transcription at start: stop requested.")
                return
            with tempfile.TemporaryDirectory() as tmpdir:
                logging.info(f"[TranscriptionWorker] Created tempdir: {tmpdir}")
                audio_path = os.path.join(tmpdir, "audio.wav")
                result_path = os.path.join(tmpdir, "result.json")
                try:
                    logging.info(f"[TranscriptionWorker] Saving audio to {audio_path}")
                    if self.audio_data.dtype != np.float32:
                        audio_float32 = self.audio_data.astype(np.float32)
                    else:
                        audio_float32 = self.audio_data
                    max_val = np.max(np.abs(audio_float32))
                    if max_val > 1.0:
                        audio_float32 /= max_val
                    sf.write(audio_path, audio_float32, samplerate=16000, subtype='PCM_16')
                    logging.info(f"[TranscriptionWorker] Audio saved to {audio_path}")
                except Exception as e:
                    logging.error(f"[TranscriptionWorker] Error saving audio: {e}")
                    self.error.emit(f"Error saving audio: {e}")
                    return
                if self._should_stop:
                    logging.info("[TranscriptionWorker] Stop requested after saving audio, aborting.")
                    return
                try:
                    # Use faster-whisper directly in-process instead of subprocess
                    logging.info("[TranscriptionWorker] Transcribing with faster-whisper")
                    from faster_whisper import WhisperModel
                    
                    # Map model names to faster-whisper compatible names if needed
                    model_name_map = {
                        "tiny": "tiny",
                        "base": "base",
                        "small": "small",
                        "medium": "medium",
                        "large": "large",
                        "large-v2": "large-v2",
                        "large-v3": "large-v3"
                    }
                    # Use mapped name or original if not in map
                    model_name = model_name_map.get(self.model_name, self.model_name)
                    
                    # Load the model with faster-whisper
                    model = WhisperModel(model_name, device="cpu", compute_type="int8")
                    logging.info(f"[TranscriptionWorker] Model loaded, transcribing audio file: {audio_path}")
                    
                    # Transcribe the audio file
                    segments, info = model.transcribe(audio_path, beam_size=5)
                    
                    # Collect all segments into a single text
                    text = ""
                    for segment in segments:
                        text += segment.text + " "
                    text = text.strip()
                    
                    # Write result to JSON file for compatibility with existing code
                    result_json = {"text": text}
                    with open(result_path, 'w', encoding='utf-8') as f:
                        json.dump(result_json, f)
                        
                    logging.info(f"[TranscriptionWorker] Transcription completed: {text[:50]}...")
                    
                    if self._should_stop:
                        logging.info("[TranscriptionWorker] Stop requested after transcription, aborting.")
                        return
                    self.transcription_ready.emit(text)
                    self.finished.emit()
                except Exception as e:
                    logging.error(f"[TranscriptionWorker] Error during transcription: {e}")
                    self.error.emit(f"Error during transcription: {e}")
        except Exception as e:
            logging.error(f"[TranscriptionWorker] Unexpected error: {e}")
            self.error.emit(f"Unexpected error: {e}")
