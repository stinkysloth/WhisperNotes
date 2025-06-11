#!/usr/bin/env python3
"""
Hotkey Listener module for WhisperNotes.

This module provides a global hotkey listener that can register and handle
multiple hotkey combinations for different actions.
"""
import logging
import threading
import time
from typing import Dict, Callable, Optional
import keyboard

class HotkeyListener:
    """
    A class that listens for global hotkeys and triggers registered callbacks.
    
    This class uses the keyboard library to register global hotkeys and
    provides a clean interface for adding, removing, and managing hotkeys.
    """
    
    def __init__(self):
        """Initialize the hotkey listener."""
        self.running = False
        self.thread = None
        self.hotkeys: Dict[str, Callable] = {}
        self.lock = threading.Lock()
    
    def start(self):
        """Start the hotkey listener in a separate thread."""
        if self.running:
            logging.warning("Hotkey listener already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        logging.info("Hotkey listener started")
    
    def stop(self):
        """Stop the hotkey listener."""
        self.running = False
        logging.info("Hotkey listener stopping...")
    
    def join(self, timeout: Optional[float] = 1.0):
        """Join the listener thread to ensure it exits cleanly."""
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout)
            logging.info("Hotkey listener joined")
    
    def register_hotkey(self, hotkey: str, callback: Callable) -> bool:
        """
        Register a new hotkey with a callback function.
        
        Args:
            hotkey: The hotkey combination (e.g., 'cmd+shift+j')
            callback: The function to call when the hotkey is pressed
            
        Returns:
            bool: True if registration was successful, False otherwise
        """
        with self.lock:
            try:
                # Normalize hotkey format
                normalized_hotkey = self._normalize_hotkey(hotkey)
                
                # Check if hotkey is already registered
                if normalized_hotkey in self.hotkeys:
                    logging.warning(f"Hotkey {hotkey} already registered")
                    return False
                
                # Register the hotkey
                self.hotkeys[normalized_hotkey] = callback
                logging.info(f"Registered hotkey: {hotkey}")
                return True
            except Exception as e:
                logging.error(f"Error registering hotkey {hotkey}: {e}")
                return False
    
    def unregister_hotkey(self, hotkey: str) -> bool:
        """
        Unregister a previously registered hotkey.
        
        Args:
            hotkey: The hotkey combination to unregister
            
        Returns:
            bool: True if unregistration was successful, False otherwise
        """
        with self.lock:
            try:
                # Normalize hotkey format
                normalized_hotkey = self._normalize_hotkey(hotkey)
                
                # Check if hotkey is registered
                if normalized_hotkey not in self.hotkeys:
                    logging.warning(f"Hotkey {hotkey} not registered")
                    return False
                
                # Unregister the hotkey
                del self.hotkeys[normalized_hotkey]
                logging.info(f"Unregistered hotkey: {hotkey}")
                return True
            except Exception as e:
                logging.error(f"Error unregistering hotkey {hotkey}: {e}")
                return False
    
    def get_registered_hotkeys(self) -> Dict[str, Callable]:
        """Get a copy of the registered hotkeys dictionary."""
        with self.lock:
            return self.hotkeys.copy()
    
    def _normalize_hotkey(self, hotkey: str) -> str:
        """
        Normalize hotkey format for consistent handling.
        
        Args:
            hotkey: The hotkey combination to normalize
            
        Returns:
            str: The normalized hotkey string
        """
        # Split by + and sort the keys alphabetically
        parts = [part.strip().lower() for part in hotkey.split('+')]
        
        # Handle platform-specific modifiers
        modifier_map = {
            'command': 'cmd',
            'control': 'ctrl',
            'option': 'alt'
        }
        
        # Replace modifiers with their canonical forms
        normalized_parts = [modifier_map.get(part, part) for part in parts]
        
        # Sort modifiers first, then regular keys
        modifiers = [p for p in normalized_parts if p in ('cmd', 'ctrl', 'alt', 'shift')]
        other_keys = [p for p in normalized_parts if p not in ('cmd', 'ctrl', 'alt', 'shift')]
        
        # Combine and return
        return '+'.join(sorted(modifiers) + other_keys)
    
    def _listen(self):
        """
        Main listening loop that checks for registered hotkey combinations.
        
        This method runs in a separate thread and continuously checks if any
        registered hotkey combination is pressed.
        """
        try:
            while self.running:
                # Get a copy of the hotkeys to avoid issues with concurrent modification
                with self.lock:
                    hotkeys = self.hotkeys.copy()
                
                # Check each registered hotkey
                for hotkey, callback in hotkeys.items():
                    try:
                        # Check if the hotkey is pressed
                        if self._is_hotkey_pressed(hotkey):
                            # Call the callback function
                            callback()
                            
                            # Wait a bit to avoid multiple triggers
                            time.sleep(0.5)
                    except Exception as e:
                        logging.error(f"Error checking hotkey {hotkey}: {e}")
                
                # Sleep to reduce CPU usage
                time.sleep(0.1)
        except Exception as e:
            logging.error(f"Error in hotkey listener thread: {e}")
            self.running = False
    
    def _is_hotkey_pressed(self, hotkey: str) -> bool:
        """
        Check if a specific hotkey combination is currently pressed.
        
        Args:
            hotkey: The normalized hotkey combination to check
            
        Returns:
            bool: True if the hotkey is pressed, False otherwise
        """
        try:
            # Split the hotkey into individual keys
            keys = hotkey.split('+')
            
            # Check if all keys in the combination are pressed
            return all(keyboard.is_pressed(key) for key in keys)
        except Exception as e:
            logging.error(f"Error checking if hotkey {hotkey} is pressed: {e}")
            return False
