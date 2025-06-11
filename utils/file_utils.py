"""
File system utilities for WhisperNotes.

This module provides utility functions for file system operations.
"""

import os
import logging
import shutil
from pathlib import Path
from typing import Optional, Union, List

logger = logging.getLogger(__name__)

def ensure_directory_exists(directory: Union[str, Path]) -> bool:
    """Ensure that a directory exists, creating it if necessary.
    
    Args:
        directory: Path to the directory
        
    Returns:
        bool: True if directory exists or was created, False otherwise
    """
    try:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {str(e)}", exc_info=True)
        return False

def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing or replacing invalid characters.
    
    Args:
        filename: The filename to sanitize
        
    Returns:
        str: Sanitized filename
    """
    # Replace invalid characters with underscore
    invalid_chars = '<>:"/\\|?*\0'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove control characters
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # Ensure the filename is not empty
    if not filename.strip():
        filename = 'unnamed_file'
    
    return filename

def get_unique_filename(directory: Union[str, Path], base_name: str, ext: str) -> Path:
    """Get a unique filename in the specified directory.
    
    If a file with the given name already exists, appends a number to make it unique.
    
    Args:
        directory: Directory where the file will be created
        base_name: Base name of the file (without extension)
        ext: File extension (without leading dot)
        
    Returns:
        Path: Path to a non-existent file
    """
    directory = Path(directory)
    base_name = sanitize_filename(base_name)
    ext = ext.lstrip('.')
    
    # Try the base name first
    counter = 1
    while True:
        if counter == 1:
            filename = f"{base_name}.{ext}"
        else:
            filename = f"{base_name}_{counter}.{ext}"
        
        filepath = directory / filename
        
        if not filepath.exists():
            return filepath
            
        counter += 1

def copy_file(src: Union[str, Path], dst: Union[str, Path], overwrite: bool = False) -> bool:
    """Copy a file from source to destination.
    
    Args:
        src: Source file path
        dst: Destination file path
        overwrite: If True, overwrite existing destination file
        
    Returns:
        bool: True if copy was successful, False otherwise
    """
    src = Path(src)
    dst = Path(dst)
    
    if not src.exists():
        logger.error(f"Source file does not exist: {src}")
        return False
    
    if dst.exists() and not overwrite:
        logger.error(f"Destination file already exists and overwrite=False: {dst}")
        return False
    
    try:
        ensure_directory_exists(dst.parent)
        shutil.copy2(src, dst)
        return True
    except Exception as e:
        logger.error(f"Failed to copy file from {src} to {dst}: {str(e)}", exc_info=True)
        return False

def delete_file(filepath: Union[str, Path]) -> bool:
    """Delete a file.
    
    Args:
        filepath: Path to the file to delete
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        filepath = Path(filepath)
        if filepath.exists():
            filepath.unlink()
        return True
    except Exception as e:
        logger.error(f"Failed to delete file {filepath}: {str(e)}", exc_info=True)
        return False

def list_files(directory: Union[str, Path], extensions: Optional[List[str]] = None) -> List[Path]:
    """List files in a directory with optional extension filtering.
    
    Args:
        directory: Directory to list files from
        extensions: List of file extensions to include (without leading dot).
                   If None, all files are included.
                   
    Returns:
        List of Path objects for matching files
    """
    directory = Path(directory)
    
    if not directory.is_dir():
        return []
    
    if extensions is not None:
        extensions = [ext.lower().lstrip('.') for ext in extensions]
        return [
            f for f in directory.iterdir() 
            if f.is_file() and f.suffix.lstrip('.').lower() in extensions
        ]
    else:
        return [f for f in directory.iterdir() if f.is_file()]

def read_text_file(filepath: Union[str, Path]) -> Optional[str]:
    """Read the contents of a text file.
    
    Args:
        filepath: Path to the file to read
        
    Returns:
        str: File contents, or None if reading failed
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read file {filepath}: {str(e)}", exc_info=True)
        return None

def write_text_file(filepath: Union[str, Path], content: str) -> bool:
    """Write content to a text file.
    
    Args:
        filepath: Path to the file to write
        content: Content to write to the file
        
    Returns:
        bool: True if write was successful, False otherwise
    """
    try:
        filepath = Path(filepath)
        ensure_directory_exists(filepath.parent)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"Failed to write to file {filepath}: {str(e)}", exc_info=True)
        return False
