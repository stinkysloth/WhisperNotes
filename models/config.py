"""Configuration models for WhisperNotes application."""
from pathlib import Path
from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field, validator
import uuid

class StorageConfig(BaseModel):
    """Configuration for storage locations."""
    audio_path: Optional[Path] = None
    markdown_path: Optional[Path] = None
    use_default: bool = True

    @validator('audio_path', 'markdown_path', pre=True)
    def convert_str_to_path(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return Path(v)
        return v
        
    class Config:
        json_encoders = {
            Path: str
        }

class NoteTypeConfig(BaseModel):
    """Configuration for a note type."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    hotkey: Optional[str] = None
    storage: StorageConfig = Field(default_factory=StorageConfig)
    summary_prompt: str = ""
    template: str = ""
    
    class Config:
        json_encoders = {
            Path: str
        }

class GeneralConfig(BaseModel):
    """General application configuration."""
    recording_device: Optional[str] = None
    default_storage: StorageConfig = Field(
        default_factory=lambda: StorageConfig(
            audio_path=Path.home() / "WhisperNotes" / "Recordings",
            markdown_path=Path.home() / "WhisperNotes" / "Notes"
        )
    )
    default_journal_dir: Path = Field(
        default_factory=lambda: Path.home() / "WhisperNotes" / "Journal"
    )
    default_summary_prompt: str = "Summarize the following transcription in a concise and informative way."
    ollama_model: str = "whisper"
    global_record_hotkey: str = "ctrl+shift+r"
    max_recording_duration: float = 900.0  # 15 minutes in seconds
    transcription_timeout: int = 120  # Timeout in seconds for transcription process

class AppConfig(BaseModel):
    """Root application configuration."""
    version: str = "1.0"
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    note_types: Dict[str, NoteTypeConfig] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            Path: str
        }
