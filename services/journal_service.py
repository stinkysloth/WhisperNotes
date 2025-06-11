"""
Journal service for managing journal entries and related functionality.

This module provides the JournalService class which handles the creation,
management, and persistence of journal entries.
"""

import os
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from PySide6.QtCore import QObject, Signal, QMutex

from core.constants import AppConstants
from utils.file_utils import ensure_directory_exists, sanitize_filename

logger = logging.getLogger(__name__)

class JournalService(QObject):
    """Service for managing journal entries and related functionality."""
    
    # Signals
    entry_created = Signal(dict)          # entry data
    entry_updated = Signal(dict)          # entry data
    entry_deleted = Signal(str)           # entry_id
    error_occurred = Signal(str)          # error_message
    journal_dir_changed = Signal(str)     # new_dir
    
    def __init__(self, journal_dir: Optional[str] = None):
        """Initialize the journal service.
        
        Args:
            journal_dir: Optional directory to store journal entries.
                       If not provided, a default will be used.
        """
        super().__init__()
        self.journal_dir = journal_dir or os.path.expanduser(AppConstants.DEFAULT_JOURNAL_DIR)
        self.entries = {}
        self.current_entry = None
        self.mutex = QMutex()
        self._ensure_journal_dir()
    
    def _ensure_journal_dir(self) -> None:
        """Ensure the journal directory exists."""
        try:
            ensure_directory_exists(self.journal_dir)
            logger.info(f"Using journal directory: {self.journal_dir}")
        except Exception as e:
            error_msg = f"Failed to create journal directory: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
    
    def set_journal_dir(self, directory: str) -> bool:
        """Set the journal directory.
        
        Args:
            directory: Path to the journal directory
            
        Returns:
            bool: True if directory was set successfully, False otherwise
        """
        try:
            ensure_directory_exists(directory)
            self.journal_dir = directory
            self.journal_dir_changed.emit(directory)
            logger.info(f"Journal directory set to: {directory}")
            return True
        except Exception as e:
            error_msg = f"Failed to set journal directory: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False
    
    def create_entry(
        self,
        content: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
        audio_data: Optional[bytes] = None,
        audio_format: str = "wav"
    ) -> Optional[Dict[str, Any]]:
        """Create a new journal entry.
        
        Args:
            content: The main content of the entry
            title: Optional title for the entry
            tags: Optional list of tags
            audio_data: Optional audio data to associate with the entry
            audio_format: Format of the audio data (e.g., 'wav', 'mp3')
            
        Returns:
            Dict containing the created entry data, or None on failure
        """
        try:
            # Create entry data
            entry_id = str(int(time.time()))
            timestamp = datetime.now().isoformat()
            
            entry = {
                'id': entry_id,
                'title': title or f"Entry {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                'content': content,
                'timestamp': timestamp,
                'tags': tags or [],
                'audio_path': None
            }
            
            # Save audio file if provided
            if audio_data is not None:
                audio_filename = f"{entry_id}.{audio_format}"
                audio_dir = os.path.join(self.journal_dir, "audio")
                ensure_directory_exists(audio_dir)
                
                audio_path = os.path.join(audio_dir, audio_filename)
                with open(audio_path, 'wb') as f:
                    f.write(audio_data)
                
                entry['audio_path'] = audio_path
            
            # Save entry to file
            entry_filename = f"{entry_id}.md"
            entry_path = os.path.join(self.journal_dir, entry_filename)
            
            with open(entry_path, 'w', encoding='utf-8') as f:
                f.write(self._format_entry_markdown(entry))
            
            # Update state
            self.entries[entry_id] = entry
            self.current_entry = entry
            
            logger.info(f"Created journal entry: {entry_id}")
            self.entry_created.emit(entry)
            return entry
            
        except Exception as e:
            error_msg = f"Failed to create journal entry: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return None
    
    def _format_entry_markdown(self, entry: Dict[str, Any]) -> str:
        """Format a journal entry as Markdown.
        
        Args:
            entry: The journal entry data
            
        Returns:
            str: Formatted Markdown
        """
        lines = [
            f"# {entry['title']}\n",
            f"*{datetime.fromisoformat(entry['timestamp']).strftime('%Y-%m-%d %H:%M')}*\n"
        ]
        
        # Add tags if present
        if entry.get('tags'):
            tags = " ".join(f"#{tag.replace(' ', '_')}" for tag in entry['tags'])
            lines.append(f"\n{tags}\n")
        
        # Add content
        lines.append(f"\n{entry['content']}")
        
        # Add audio link if present
        if entry.get('audio_path'):
            audio_filename = os.path.basename(entry['audio_path'])
            lines.append(f"\n\n[Audio](audio/{audio_filename})")
        
        return "\n".join(lines)
    
    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get a journal entry by ID.
        
        Args:
            entry_id: ID of the entry to retrieve
            
        Returns:
            Dict containing the entry data, or None if not found
        """
        return self.entries.get(entry_id)
    
    def get_all_entries(self) -> List[Dict[str, Any]]:
        """Get all journal entries.
        
        Returns:
            List of entry dictionaries, sorted by timestamp (newest first)
        """
        return sorted(
            list(self.entries.values()),
            key=lambda x: x['timestamp'],
            reverse=True
        )
    
    def update_entry(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing journal entry.
        
        Args:
            entry_id: ID of the entry to update
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        if entry_id not in self.entries:
            return False
            
        try:
            # Update entry data
            self.entries[entry_id].update(updates)
            entry = self.entries[entry_id]
            
            # Save to file
            entry_filename = f"{entry_id}.md"
            entry_path = os.path.join(self.journal_dir, entry_filename)
            
            with open(entry_path, 'w', encoding='utf-8') as f:
                f.write(self._format_entry_markdown(entry))
            
            self.entry_updated.emit(entry)
            return True
            
        except Exception as e:
            error_msg = f"Failed to update journal entry: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False
    
    def delete_entry(self, entry_id: str) -> bool:
        """Delete a journal entry.
        
        Args:
            entry_id: ID of the entry to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        if entry_id not in self.entries:
            return False
            
        try:
            # Delete entry file
            entry_filename = f"{entry_id}.md"
            entry_path = os.path.join(self.journal_dir, entry_filename)
            
            if os.path.exists(entry_path):
                os.remove(entry_path)
            
            # Delete associated audio file if it exists
            entry = self.entries[entry_id]
            if entry.get('audio_path') and os.path.exists(entry['audio_path']):
                os.remove(entry['audio_path'])
            
            # Update state
            del self.entries[entry_id]
            if self.current_entry and self.current_entry['id'] == entry_id:
                self.current_entry = None
            
            self.entry_deleted.emit(entry_id)
            return True
            
        except Exception as e:
            error_msg = f"Failed to delete journal entry: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False
    
    def load_entries(self) -> bool:
        """Load all journal entries from disk.
        
        Returns:
            bool: True if loading was successful, False otherwise
        """
        try:
            self.entries = {}
            
            if not os.path.exists(self.journal_dir):
                logger.warning(f"Journal directory does not exist: {self.journal_dir}")
                return False
            
            # Load entries from markdown files
            for filename in os.listdir(self.journal_dir):
                if not filename.endswith('.md'):
                    continue
                    
                try:
                    entry_id = filename[:-3]  # Remove .md extension
                    entry_path = os.path.join(self.journal_dir, filename)
                    
                    with open(entry_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Parse entry (simplified)
                    lines = content.split('\n')
                    title = lines[0].lstrip('#').strip()
                    
                    # Look for timestamp in the second line (if present)
                    timestamp = datetime.now().isoformat()
                    if len(lines) > 1 and lines[1].startswith('*'):
                        try:
                            timestamp_str = lines[1].strip('*')
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M').isoformat()
                        except (ValueError, IndexError):
                            pass
                    
                    # Look for tags (lines starting with #)
                    tags = []
                    content_lines = []
                    in_tags = False
                    
                    for line in lines[2:]:
                        if not in_tags and line.startswith('#'):
                            tags = [tag.lstrip('#').replace('_', ' ').strip() 
                                   for tag in line.split() if tag.startswith('#')]
                            in_tags = True
                        else:
                            content_lines.append(line)
                    
                    # Check for audio link
                    audio_path = None
                    audio_line = content_lines[-1] if content_lines else ""
                    if audio_line.startswith('[Audio](') and ')' in audio_line:
                        audio_rel_path = audio_line.split('(', 1)[1].split(')')[0]
                        audio_path = os.path.join(self.journal_dir, audio_rel_path)
                        if not os.path.exists(audio_path):
                            audio_path = None
                        else:
                            content_lines = content_lines[:-1]  # Remove audio line
                    
                    entry = {
                        'id': entry_id,
                        'title': title,
                        'content': '\n'.join(content_lines).strip(),
                        'timestamp': timestamp,
                        'tags': tags,
                        'audio_path': audio_path
                    }
                    
                    self.entries[entry_id] = entry
                    
                except Exception as e:
                    logger.error(f"Error loading journal entry {filename}: {str(e)}", exc_info=True)
            
            logger.info(f"Loaded {len(self.entries)} journal entries from {self.journal_dir}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to load journal entries: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            return False
