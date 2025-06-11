"""
Audio processing utilities for WhisperNotes.

This module provides utility functions for audio recording, playback, and processing.
"""

import logging
import os
import tempfile
import wave
import numpy as np
import sounddevice as sd
from typing import Optional, Tuple, Union, List
from pathlib import Path

logger = logging.getLogger(__name__)

def get_audio_devices() -> Tuple[List[dict], List[dict]]:
    """Get lists of available input and output audio devices.
    
    Returns:
        Tuple containing:
            - List of input devices (dictionaries)
            - List of output devices (dictionaries)
    """
    try:
        devices = sd.query_devices()
        host_apis = sd.query_hostapis()
        
        input_devices = []
        output_devices = []
        
        for i, device in enumerate(devices):
            device_info = {
                'id': i,
                'name': device['name'],
                'hostapi': host_apis[device['hostapi']]['name'],
                'max_input_channels': device['max_input_channels'],
                'max_output_channels': device['max_output_channels'],
                'default_samplerate': device['default_samplerate']
            }
            
            if device['max_input_channels'] > 0:
                input_devices.append(device_info)
                
            if device['max_output_channels'] > 0:
                output_devices.append(device_info)
        
        return input_devices, output_devices
        
    except Exception as e:
        logger.error(f"Failed to get audio devices: {str(e)}", exc_info=True)
        return [], []

def get_default_audio_device() -> Tuple[Optional[int], Optional[int]]:
    """Get the default input and output audio device IDs.
    
    Returns:
        Tuple containing:
            - Default input device ID (or None if not available)
            - Default output device ID (or None if not available)
    """
    try:
        input_devices, output_devices = get_audio_devices()
        
        default_input = sd.default.device[0] if isinstance(sd.default.device, tuple) else sd.default.device
        default_output = sd.default.device[1] if isinstance(sd.default.device, tuple) else sd.default.device
        
        # Verify the default devices are valid
        if input_devices and (default_input < 0 or default_input >= len(sd.query_devices())):
            default_input = sd.query_devices(kind='input')['index']
        if output_devices and (default_output < 0 or default_output >= len(sd.query_devices())):
            default_output = sd.query_devices(kind='output')['index']
            
        return default_input, default_output
        
    except Exception as e:
        logger.error(f"Failed to get default audio device: {str(e)}", exc_info=True)
        return None, None

def record_audio(
    duration: float = 10.0,
    sample_rate: int = 16000,
    channels: int = 1,
    device: Optional[int] = None,
    dtype: str = 'float32'
) -> Optional[Tuple[np.ndarray, int]]:
    """Record audio from the default microphone.
    
    Args:
        duration: Recording duration in seconds
        sample_rate: Sample rate in Hz
        channels: Number of audio channels
        device: Device ID to use (None for default)
        dtype: Data type for the recorded audio ('int16' or 'float32')
        
    Returns:
        Tuple containing:
            - NumPy array containing the audio data
            - Sample rate
        Or None if recording failed
    """
    try:
        logger.info(f"Starting audio recording for {duration} seconds...")
        
        # Validate dtype
        if dtype not in ('int16', 'float32'):
            logger.warning(f"Unsupported dtype '{dtype}', using 'float32'")
            dtype = 'float32'
        
        # Record audio
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=channels,
            device=device,
            dtype=dtype
        )
        
        # Wait for recording to complete
        sd.wait()
        
        logger.info("Audio recording completed")
        return recording, sample_rate
        
    except Exception as e:
        logger.error(f"Audio recording failed: {str(e)}", exc_info=True)
        return None

def play_audio(
    audio_data: np.ndarray,
    sample_rate: int = 16000,
    device: Optional[int] = None,
    blocking: bool = True
) -> bool:
    """Play audio data through the default speaker.
    
    Args:
        audio_data: NumPy array containing the audio data
        sample_rate: Sample rate in Hz
        device: Device ID to use (None for default)
        blocking: If True, block until playback is finished
        
    Returns:
        bool: True if playback started successfully, False otherwise
    """
    try:
        if audio_data is None or len(audio_data) == 0:
            logger.error("No audio data to play")
            return False
            
        logger.info("Starting audio playback...")
        
        # Ensure audio data is in the correct shape (samples, channels)
        if len(audio_data.shape) == 1:
            audio_data = audio_data.reshape(-1, 1)  # Mono
            
        # Play the audio
        sd.play(audio_data, samplerate=sample_rate, device=device)
        
        if blocking:
            sd.wait()
            logger.info("Audio playback completed")
        else:
            logger.info("Audio playback started (non-blocking)")
            
        return True
        
    except Exception as e:
        logger.error(f"Audio playback failed: {str(e)}", exc_info=True)
        return False

def save_audio(
    filepath: Union[str, Path],
    audio_data: np.ndarray,
    sample_rate: int = 16000,
    format: str = 'wav',
    subtype: Optional[str] = None
) -> bool:
    """Save audio data to a file.
    
    Args:
        filepath: Path to save the audio file
        audio_data: NumPy array containing the audio data
        sample_rate: Sample rate in Hz
        format: File format ('wav', 'flac', 'ogg', 'mp3')
        subtype: Subtype for the audio format (e.g., 'pcm_16' for WAV)
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        import soundfile as sf
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Set default subtype based on format if not specified
        if subtype is None:
            if format.lower() == 'wav':
                subtype = 'PCM_16'
            elif format.lower() == 'flac':
                subtype = 'PCM_16'
            elif format.lower() == 'ogg':
                subtype = 'VORBIS'
            elif format.lower() == 'mp3':
                subtype = 'MP3'
        
        sf.write(
            str(filepath),
            audio_data,
            sample_rate,
            format=format,
            subtype=subtype
        )
        
        logger.info(f"Audio saved to {filepath}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save audio to {filepath}: {str(e)}", exc_info=True)
        return False

def load_audio(
    filepath: Union[str, Path],
    start: Optional[float] = None,
    end: Optional[float] = None,
    sample_rate: Optional[int] = None,
    dtype: str = 'float32'
) -> Optional[Tuple[np.ndarray, int]]:
    """Load audio from a file.
    
    Args:
        filepath: Path to the audio file
        start: Start time in seconds (None for beginning)
        end: End time in seconds (None for end)
        sample_rate: Target sample rate (None to use file's sample rate)
        dtype: Data type for the loaded audio ('int16' or 'float32')
        
    Returns:
        Tuple containing:
            - NumPy array containing the audio data
            - Sample rate
        Or None if loading failed
    """
    try:
        import soundfile as sf
        
        filepath = Path(filepath)
        if not filepath.exists():
            logger.error(f"Audio file not found: {filepath}")
            return None
        
        # Load metadata first to get the sample rate
        info = sf.info(str(filepath))
        file_sample_rate = info.samplerate
        
        # Calculate frames to read
        frame_start = 0
        frame_end = info.frames
        
        if start is not None and start > 0:
            frame_start = int(start * file_sample_rate)
            
        if end is not None and end > start:
            frame_end = int(end * file_sample_rate)
        
        # Read the audio data
        audio_data, file_sample_rate = sf.read(
            str(filepath),
            start=frame_start,
            stop=min(frame_end, info.frames),
            dtype=dtype,
            always_2d=True  # Return (samples, channels)
        )
        
        # Convert to mono if needed
        if audio_data.ndim > 1 and audio_data.shape[1] > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # Resample if needed
        if sample_rate is not None and sample_rate != file_sample_rate:
            audio_data = resample_audio(audio_data, file_sample_rate, sample_rate)
            file_sample_rate = sample_rate
        
        return audio_data, file_sample_rate
        
    except Exception as e:
        logger.error(f"Failed to load audio from {filepath}: {str(e)}", exc_info=True)
        return None

def resample_audio(
    audio_data: np.ndarray,
    orig_sr: int,
    target_sr: int
) -> np.ndarray:
    """Resample audio data to a target sample rate.
    
    Args:
        audio_data: NumPy array containing the audio data
        orig_sr: Original sample rate
        target_sr: Target sample rate
        
    Returns:
        Resampled audio data
    """
    if orig_sr == target_sr:
        return audio_data
        
    try:
        # Simple linear resampling for small changes
        if abs(1 - (orig_sr / target_sr)) < 0.1:
            import scipy.signal
            ratio = target_sr / orig_sr
            n_samples = int(round(len(audio_data) * ratio))
            return scipy.signal.resample(audio_data, n_samples)
        else:
            # Use librosa for more sophisticated resampling
            import librosa
            return librosa.resample(
                audio_data,
                orig_sr=orig_sr,
                target_sr=target_sr
            )
    except ImportError:
        # Fallback to scipy if librosa is not available
        import scipy.signal
        ratio = target_sr / orig_sr
        n_samples = int(round(len(audio_data) * ratio))
        return scipy.signal.resample(audio_data, n_samples)

def normalize_audio(audio_data: np.ndarray, target_level: float = -20.0) -> np.ndarray:
    """Normalize audio to a target level in dBFS.
    
    Args:
        audio_data: NumPy array containing the audio data
        target_level: Target level in dBFS (negative number, e.g., -20.0)
        
    Returns:
        Normalized audio data
    """
    if audio_data.size == 0:
        return audio_data
        
    # Calculate current level (RMS in dBFS)
    rms = np.sqrt(np.mean(np.square(audio_data)))
    if rms < 1e-6:  # Avoid division by zero
        return audio_data
        
    current_level = 20 * np.log10(rms)
    gain = 10 ** ((target_level - current_level) / 20)
    
    # Apply gain with clipping protection
    normalized = audio_data * gain
    if np.issubdtype(audio_data.dtype, np.integer):
        max_val = np.iinfo(audio_data.dtype).max
        normalized = np.clip(normalized, -max_val, max_val).astype(audio_data.dtype)
    else:
        normalized = np.clip(normalized, -1.0, 1.0)
    
    return normalized

def trim_silence(
    audio_data: np.ndarray,
    sample_rate: int,
    top_db: float = 30.0,
    frame_length: int = 2048,
    hop_length: int = 512
) -> np.ndarray:
    """Trim leading and trailing silence from audio.
    
    Args:
        audio_data: NumPy array containing the audio data
        sample_rate: Sample rate in Hz
        top_db: The threshold (in decibels) below reference to consider as silence
        frame_length: Length of the frame for STFT
        hop_length: Number of samples between successive frames
        
    Returns:
        Trimmed audio data
    """
    try:
        import librosa
        
        # Convert to mono if needed
        if audio_data.ndim > 1 and audio_data.shape[1] > 1:
            y = np.mean(audio_data, axis=1)
        else:
            y = audio_data.flatten()
        
        # Trim silence
        trimmed, _ = librosa.effects.trim(
            y,
            top_db=top_db,
            frame_length=frame_length,
            hop_length=hop_length
        )
        
        return trimmed
        
    except ImportError:
        logger.warning("librosa not available, skipping silence trimming")
        return audio_data

def convert_audio_to_wav(
    input_file: Union[str, Path],
    output_file: Optional[Union[str, Path]] = None,
    sample_rate: int = 16000,
    channels: int = 1,
    format: str = 'wav'
) -> Optional[Path]:
    """Convert an audio file to WAV format using ffmpeg.
    
    Args:
        input_file: Path to the input audio file
        output_file: Path to save the output WAV file (None to auto-generate)
        sample_rate: Target sample rate in Hz
        channels: Number of audio channels (1 for mono, 2 for stereo)
        format: Output format ('wav', 'flac', 'mp3', etc.)
        
    Returns:
        Path to the converted file, or None if conversion failed
    """
    try:
        import subprocess
        import shutil
        
        input_file = Path(input_file)
        if not input_file.exists():
            logger.error(f"Input file not found: {input_file}")
            return None
        
        # Set output file path if not provided
        if output_file is None:
            output_file = input_file.with_suffix(f'.{format}')
        else:
            output_file = Path(output_file)
        
        # Create output directory if it doesn't exist
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if ffmpeg is available
        if not shutil.which('ffmpeg'):
            logger.error("ffmpeg is required for audio conversion but was not found")
            return None
        
        # Build ffmpeg command
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file if it exists
            '-i', str(input_file),  # Input file
            '-ac', str(channels),  # Audio channels
            '-ar', str(sample_rate),  # Sample rate
            '-acodec', 'pcm_s16le' if format == 'wav' else None,  # Codec
            '-f', format,  # Output format
            str(output_file)
        ]
        
        # Remove None values
        cmd = [c for c in cmd if c is not None]
        
        # Run ffmpeg
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        
        if output_file.exists() and output_file.stat().st_size > 0:
            logger.info(f"Successfully converted {input_file} to {output_file}")
            return output_file
        else:
            logger.error(f"Failed to convert {input_file}")
            return None
            
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg error: {e.stderr.decode('utf-8')}")
        return None
    except Exception as e:
        logger.error(f"Audio conversion failed: {str(e)}", exc_info=True)
        return None
