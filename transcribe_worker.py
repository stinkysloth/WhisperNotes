#!/usr/bin/env python3
import sys
import os
import json
import logging
import traceback
import time
from faster_whisper import WhisperModel

# Configure logging to stdout for the subprocess
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def validate_audio_file(audio_path):
    """Validate that the audio file exists and is readable."""
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    if not os.access(audio_path, os.R_OK):
        raise PermissionError(f"Cannot read audio file (permission denied): {audio_path}")
    if os.path.getsize(audio_path) == 0:
        raise ValueError(f"Audio file is empty: {audio_path}")

def main():
    try:
        start_time = time.time()
        logger.info("Starting transcription worker...")
        
        if len(sys.argv) != 4:
            error_msg = f"Usage: {sys.argv[0]} <model_name> <audio_wav_path> <result_path>"
            logger.error(error_msg)
            print(json.dumps({"error": error_msg}), file=sys.stderr)
            sys.exit(1)
            
        model_name = sys.argv[1]
        audio_path = sys.argv[2]
        result_path = sys.argv[3]
        
        logger.info(f"Python executable: {sys.executable}")
        logger.info(f"Working directory: {os.getcwd()}")
        logger.info(f"Input audio: {audio_path}")
        logger.info(f"Output result: {result_path}")
        
        # Validate input file
        try:
            validate_audio_file(audio_path)
            logger.info(f"Audio file validation passed: {os.path.getsize(audio_path)} bytes")
        except Exception as e:
            error_msg = f"Audio file validation failed: {str(e)}"
            logger.error(error_msg)
            with open(result_path, 'w') as f:
                json.dump({"error": error_msg}, f)
            sys.exit(2)
        
        # Map model names if needed (e.g., 'base' -> 'base.en')
        model_map = {
            'base': 'base.en',
            'small': 'small.en',
            'medium': 'medium.en',
            'large': 'large-v3'
        }
        model_name = model_map.get(model_name, model_name)
        
        # Load model
        logger.info(f"Loading model: {model_name}")
        try:
            model = WhisperModel(model_name, device="cpu", compute_type="int8")
            logger.info("Model loaded successfully")
            
            # Transcribe
            logger.info("Starting transcription...")
            segments, info = model.transcribe(
                audio_path,
                language="en",  # Force English for better accuracy
                beam_size=5
            )
            
            # Combine segments into single text
            transcription = " ".join([segment.text for segment in segments])
            
            # Save result
            result_data = {
                "text": transcription.strip(),
                "language": info.language,
                "duration": info.duration
            }
            
            # Write result
            with open(result_path, 'w') as f:
                output_json = {
                    "status": "success",
                    "text": result_data["text"],
                    "data": result_data
                }
                json.dump(output_json, f, indent=2)
            
            elapsed = time.time() - start_time
            logger.info(f"Transcription completed in {elapsed:.2f} seconds")
            
        except Exception as e:
            error_msg = f"Transcription failed: {str(e)}"
            logger.error(error_msg)
            with open(result_path, 'w') as f:
                json.dump({
                    "status": "error",
                    "error": error_msg,
                    "traceback": traceback.format_exc()
                }, f, indent=2)
            sys.exit(5)
            
    except Exception as e:
        error_msg = f"Unexpected error in transcription worker: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        try:
            with open(result_path, 'w') as f:
                json.dump({
                    "status": "error",
                    "error": error_msg,
                    "traceback": traceback.format_exc()
                }, f, indent=2)
        except Exception as write_err:
            # If we can't write to the result file, at least print the error
            print(json.dumps({
                "status": "error",
                "error": f"{error_msg}. Also failed to write error file: {str(write_err)}",
                "original_traceback": traceback.format_exc()
            }), file=sys.stderr)
        sys.exit(99)
    
    logger.info("Worker process completed successfully")
    sys.exit(0)

if __name__ == "__main__":
    main()
