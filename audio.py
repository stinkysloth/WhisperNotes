"""
audio.py
--------
Audio recording thread and sounddevice integration for WhisperNotes.

Responsibilities:
- RecordingThread class
- Audio data management and cleanup
- Memory management helpers
"""

# Audio recording and threading dependencies
import logging
import time
import numpy as np
import sounddevice as sd
from PySide6.QtCore import QThread, Signal, QCoreApplication

# Error handling dependencies (assume these are available in the main app)
try:
    from exceptions import AudioRecordingError, AudioSaveError, handle_error
except ImportError:
    class AudioRecordingError(Exception): pass
    class AudioSaveError(Exception): pass
    def handle_error(error: Exception, context: str = "") -> str:
        return str(error)


class RecordingThread(QThread):
    """
    A thread for recording audio.

    Handles audio recording in a background thread to avoid blocking the UI.
    Emits signals when recording is finished or if an error occurs.

    Args:
        max_duration (float): Maximum duration of recording in seconds (default: 900).
    """
    finished = Signal(object)  # Emits audio data when done
    error = Signal(str)

    def __init__(self, max_duration=900.0):
        """
        Initialize the recording thread.

        Args:
            max_duration (float): Maximum recording duration in seconds.
        """
        super().__init__()
        self.max_duration = max_duration
        self.stop_flag = False

    def run(self):
        """Record audio for up to max_duration seconds or until stopped."""
        try:
            logging.debug("Starting audio recording")
            self.audio_data = []

            def callback(indata, frames, time, status):
                if status:
                    logging.warning(f"Audio status: {status}")
                    if status.input_overflow:
                        logging.warning("Input overflow in audio stream")
                        raise AudioRecordingError("Audio input overflow - system can't keep up with recording")
                    elif status.input_error:
                        raise AudioRecordingError("Error in audio input device")

                if self.stop_flag:
                    raise sd.CallbackStop()

                if indata is not None and len(indata) > 0:
                    self.audio_data.append(indata.copy())

            # Check if input device is available
            devices = sd.query_devices()
            if not devices:
                raise AudioRecordingError("No audio input devices found")

            default_input = sd.default.device[0]
            if default_input >= len(devices):
                raise AudioRecordingError(f"Default input device {default_input} is out of range")

            device_info = devices[default_input]
            if device_info['max_input_channels'] == 0:
                raise AudioRecordingError("Default device has no input channels")

            logging.info(f"Using audio input device: {device_info['name']} (sample rate: {device_info['default_samplerate']} Hz)")

            # Start recording with a larger queue size
            with sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype='float32',
                callback=callback,
                blocksize=4096,
                device=None,  # Use default device
                latency='high'  # Better for stability
            ) as stream:
                logging.debug("Audio stream started")
                start_time = time.time()

                try:
                    while not self.stop_flag and (time.time() - start_time) < self.max_duration:
                        # Process events while waiting
                        QCoreApplication.processEvents()
                        time.sleep(0.1)  # Small sleep to prevent busy waiting

                    logging.debug("Stopping audio recording")
                    stream.stop()

                    if not self.audio_data:
                        raise AudioRecordingError("No audio data was recorded. Please check your microphone.")

                    audio_data = np.concatenate(self.audio_data, axis=0)

                    # Simple audio validation
                    if np.max(np.abs(audio_data)) < 0.001:  # Very quiet audio
                        logging.warning("Audio signal is very quiet - possible microphone issue")

                    self.finished.emit(audio_data)

                except sd.PortAudioError as e:
                    raise AudioRecordingError(f"Audio device error: {str(e)}")
                except Exception as e:
                    raise AudioRecordingError(f"Error during recording: {str(e)}")

        except Exception as e:
            # Use our custom error handling
            error_context = "audio recording"
            error_msg = handle_error(e, error_context)

            # Emit the error signal with the user-friendly message
            if not isinstance(e, (AudioRecordingError, AudioSaveError)):
                # If it's not one of our custom exceptions, wrap it in an AudioRecordingError
                e = AudioRecordingError(str(e))

            if hasattr(self, 'error'):
                self.error.emit(str(e))
            else:
                logging.error(f"Error signal not available: {error_msg}")

            # Re-raise the exception with the original traceback
            raise

    def stop(self):
        """Signal the thread to stop recording."""
        logging.info("Stopping recording thread...")
        self.stop_flag = True
