# WhisperNotes Tasks

## Feature Enhancements (2025-06-09) ✅ 2025-03-25

-   [x] **Batch Audio Import:**
    - [x] Add "Import Audio Files..." option to tray menu
    - [x] Support importing multiple audio files (.wav, .mp3, .m4a, .amr)
    - [ ] Convert unsupported formats to WAV using pydub (TODO: Requires pydub and ffmpeg)
    - [x] Process files sequentially with progress feedback
    - [x] Save transcriptions as individual journal entries

## Feature Enhancements (2025-05-26)

-   [x] **Add 'Quit' option to tray menu:**
    -   Implement a "Quit" action in the system tray icon's context menu that cleanly exits the application.
-   [x] **Configurable Markdown Output File:**
    -   Add a menu option ("Set Output File...") to allow the user to select a Markdown file for saving transcriptions.
    -   Store the selected file path persistently (e.g., using `QSettings`).
    -   If no file is set, or on first run, prompt the user or use a default.
-   [x] **Persistent Timestamped Transcriptions:**
    -   When a transcription is successful, append it to the configured Markdown file.
    -   Each entry should include a timestamp (e.g., "YYYY-MM-DD HH:MM:SS - Transcription text").
    -   Ensure file operations are robust (e.g., handle cases where the file might be temporarily unavailable).
-   [x] **Journaling System:**
    -   Implement journal entry creation with timestamps
    -   Add support for audio recording storage
    -   Create summary generation using Ollama
    -   Add configuration for journal directory

## Code Improvements (2025-06-02)

-   [x] **Fix QSystemTrayIcon MessageIcon in error handling:**
    -   Update `QSystemTrayIcon.Critical` to `QSystemTrayIcon.MessageIcon.Critical` for consistency with PyQt6 API.
-   [x] **Create a unified UI update method:**
    -   Implement a `update_ui_state` method to centralize UI updates across the application.
    -   Refactor existing code to use this method to reduce duplication.
-   [x] **Improve memory management:**
    -   Add a `_clear_audio_data` method to explicitly free memory from audio processing.
    -   Call this method at appropriate points to prevent memory leaks.
-   [x] **Enhance thread safety:**
    -   Use mutex locks consistently when accessing shared resources.
    -   Particularly in the `handle_recording_finished` method.
-   [x] **Simplify cleanup logic:**
    -   Refactor the complex `quit` method into smaller, focused methods for better maintainability.
    -   Create separate cleanup methods for each thread type.
-   [ ] **Improve exception handling:**
    -   Add more targeted exception handling for specific operations.
    -   Add appropriate error recovery mechanisms.

## Discovered Issues

-   [ ] PyQt6 enum access causing AttributeError in system tray notifications
-   [ ] Missing `_clear_transcription_thread_references` method causing application crashes
-   [ ] Inconsistent error handling across different recording scenarios
-   [ ] Potential memory leaks during long recording sessions

## Future Enhancements

### Core Functionality
- [ ] Add support for custom hotkey configuration
- [ ] Implement a proper settings dialog
- [ ] Add keyboard shortcut indicators in the UI
- [ ] Support for multiple output formats (TXT, DOCX, etc.)

### Journaling Features
- [ ] Add tagging system for journal entries
- [ ] Implement search functionality for past entries
- [ ] Add export/import for journal data
- [ ] Support for rich text formatting in journal entries

### Performance & Stability
- [ ] Optimize memory usage during long recording sessions
- [ ] Add progress indicators for long-running operations
- [ ] Implement proper cancellation for in-progress transcriptions
- [ ] Add automated tests for critical functionality

### User Experience
- [ ] Add visual feedback during recording and transcription
- [ ] Implement a proper onboarding experience
- [ ] Add tooltips and help text throughout the UI
- [ ] Create a system for user preferences and settings

## Documentation

- [ ] Update README with comprehensive setup instructions
- [ ] Add developer documentation for extending the application
- [ ] Create user guide for all features
- [ ] Document the journal file format and structure
