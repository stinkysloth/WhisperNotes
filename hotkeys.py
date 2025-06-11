"""
hotkeys.py
---------
Global hotkey registration, handling, and signal emission for WhisperNotes.

Responsibilities:
- Register/unregister global hotkeys
- Handle hotkey events and emit signals
- Support for dynamic template hotkeys
- Platform-specific hotkey logic and permission checks
"""

import logging
from typing import Dict, Callable, Set, Optional
from pynput import keyboard

class HotkeyManager:
    """
    Manages global hotkey registration and handling for WhisperNotes.

    Responsibilities:
    - Register and listen for global hotkeys
    - Emit callbacks or signals for actions (record, journal, quit)
    - Support dynamic registration of template hotkeys
    - Maintain hotkey state and pressed keys
    """
    def __init__(self, on_toggle_recording, on_toggle_journal, on_quit):
        """
        Initialize the hotkey manager.
        Args:
            on_toggle_recording: Callback for recording hotkey
            on_toggle_journal: Callback for journal hotkey
            on_quit: Callback for quit hotkey
        """
        self.on_toggle_recording = on_toggle_recording
        self.on_toggle_journal = on_toggle_journal
        self.on_quit = on_quit
        self.pressed_keys = set()
        self.hotkey_active = True
        
        # Define built-in hotkey combinations
        self.TOGGLE_HOTKEY = {keyboard.Key.cmd, keyboard.Key.shift, keyboard.KeyCode(char='r')}
        self.JOURNAL_HOTKEY = {keyboard.Key.cmd, keyboard.Key.shift, keyboard.KeyCode(char='j')}
        self.QUIT_HOTKEY = {keyboard.Key.cmd, keyboard.KeyCode(char='q')}
        
        # Dictionary to store template hotkeys and their callbacks
        # Format: {hotkey_set: (template_name, callback_function)}
        self.template_hotkeys: Dict[frozenset, tuple] = {}
        
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()
        logging.info("Hotkey listener started.")

    def register_template_hotkey(self, hotkey_str: str, template_name: str, callback: Callable) -> bool:
        """
        Register a new template hotkey.
        
        Args:
            hotkey_str: String representation of the hotkey (e.g., 'cmd+shift+t')
            template_name: Name of the template associated with this hotkey
            callback: Function to call when the hotkey is pressed
            
        Returns:
            bool: True if registration was successful, False otherwise
        """
        try:
            # Convert hotkey string to set of keys
            hotkey_set = self._parse_hotkey_string(hotkey_str)
            if not hotkey_set:
                logging.error(f"Invalid hotkey format: {hotkey_str}")
                return False
                
            # Check for conflicts with built-in hotkeys
            if hotkey_set == self.TOGGLE_HOTKEY or hotkey_set == self.JOURNAL_HOTKEY or hotkey_set == self.QUIT_HOTKEY:
                logging.warning(f"Hotkey {hotkey_str} conflicts with a built-in hotkey")
                return False
                
            # Store as frozenset to use as dictionary key
            frozen_set = frozenset(hotkey_set)
            self.template_hotkeys[frozen_set] = (template_name, callback)
            logging.info(f"Registered template hotkey {hotkey_str} for template '{template_name}'.")
            return True
        except Exception as e:
            logging.error(f"Error registering template hotkey {hotkey_str}: {e}")
            return False
            
    def unregister_template_hotkey(self, hotkey_str: str) -> bool:
        """
        Unregister a template hotkey.
        
        Args:
            hotkey_str: String representation of the hotkey to unregister
            
        Returns:
            bool: True if unregistration was successful, False otherwise
        """
        try:
            hotkey_set = self._parse_hotkey_string(hotkey_str)
            if not hotkey_set:
                return False
                
            frozen_set = frozenset(hotkey_set)
            if frozen_set in self.template_hotkeys:
                template_name = self.template_hotkeys[frozen_set][0]
                del self.template_hotkeys[frozen_set]
                logging.info(f"Unregistered template hotkey {hotkey_str} for template '{template_name}'.")
                return True
            else:
                logging.warning(f"Hotkey {hotkey_str} not found in registered template hotkeys")
                return False
        except Exception as e:
            logging.error(f"Error unregistering template hotkey {hotkey_str}: {e}")
            return False
            
    def _parse_hotkey_string(self, hotkey_str: str) -> Optional[Set]:
        """
        Parse a hotkey string into a set of keyboard keys.
        
        Args:
            hotkey_str: String representation of the hotkey (e.g., 'cmd+shift+t')
            
        Returns:
            Set of keyboard keys or None if parsing failed
        """
        try:
            parts = [part.strip().lower() for part in hotkey_str.split('+')]
            key_set = set()
            
            for part in parts:
                if part in ('cmd', 'command'):
                    key_set.add(keyboard.Key.cmd)
                elif part == 'ctrl':
                    key_set.add(keyboard.Key.ctrl)
                elif part == 'alt':
                    key_set.add(keyboard.Key.alt)
                elif part == 'shift':
                    key_set.add(keyboard.Key.shift)
                elif len(part) == 1:  # Single character
                    key_set.add(keyboard.KeyCode(char=part))
                else:
                    # Try to parse as a special key
                    try:
                        key_set.add(getattr(keyboard.Key, part))
                    except AttributeError:
                        logging.error(f"Unknown key: {part}")
                        return None
                        
            return key_set
        except Exception as e:
            logging.error(f"Error parsing hotkey string {hotkey_str}: {e}")
            return None
    
    def on_press(self, key):
        """
        Handle key press events for hotkeys.
        """
        if not self.hotkey_active:
            return
            
        self.pressed_keys.add(key)
        pressed_set = frozenset(self.pressed_keys)
        
        # Check for Cmd+Shift+R to toggle recording
        if self.TOGGLE_HOTKEY.issubset(self.pressed_keys):
            logging.info("Toggle recording hotkey detected (Cmd+Shift+R). Calling callback.")
            try:
                self.on_toggle_recording()
                logging.info("on_toggle_recording callback called successfully.")
            except Exception as e:
                logging.error(f"Exception during on_toggle_recording callback: {e}", exc_info=True)
            return
            
        # Check for Cmd+Shift+J to toggle journaling
        if self.JOURNAL_HOTKEY.issubset(self.pressed_keys):
            logging.info("Toggle journaling hotkey detected (Cmd+Shift+J). Calling callback.")
            try:
                self.on_toggle_journal()
                logging.info("on_toggle_journal callback called successfully.")
            except Exception as e:
                logging.error(f"Exception during on_toggle_journal callback: {e}", exc_info=True)
            return
            
        # Check for Cmd+Q to quit
        if self.QUIT_HOTKEY.issubset(self.pressed_keys):
            logging.info("Quit hotkey detected (Cmd+Q). Calling callback.")
            try:
                self.on_quit()
                logging.info("on_quit callback called successfully.")
            except Exception as e:
                logging.error(f"Exception during on_quit callback: {e}", exc_info=True)
            return
                
        # Check for template hotkeys
        for hotkey_set, (template_name, callback) in self.template_hotkeys.items():
            if hotkey_set.issubset(self.pressed_keys):
                logging.info(f"Template hotkey detected for '{template_name}'. Calling callback.")
                try:
                    callback(template_name)
                    logging.info(f"Template hotkey callback for '{template_name}' called successfully.")
                except Exception as e:
                    logging.error(f"Exception during template hotkey callback for '{template_name}': {e}", exc_info=True)
                return

    def on_release(self, key):
        """
        Handle key release events for hotkeys.
        """
        if key in self.pressed_keys:
            self.pressed_keys.remove(key)

    def stop(self):
        """
        Stop the hotkey listener.
        """
        if self.listener:
            self.listener.stop()
            logging.info("Hotkey listener stopped.")
