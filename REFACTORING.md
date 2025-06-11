# WhisperNotes Refactoring Plan

## Current Structure

```
whisper_notes.py    # Main application (2800+ lines, needs refactoring)
audio.py           # Audio recording thread
transcription.py   # Model loading and transcription
tray.py            # System tray UI
hotkeys.py         # Hotkey management
journaling.py      # Journal entry management
```

## Target Structure

```
app.py                    # Main application entry point
core/                    # Core application classes
  ├── __init__.py
  ├── application.py     # Main application class (moved from whisper_notes.py)
  └── constants.py      # Application-wide constants

services/                # Business logic services
  ├── __init__.py
  ├── audio_service.py   # Audio recording/playback
  ├── journal_service.py # Journal entry management
  ├── template_service.py # Template management
  └── transcription_service.py # Transcription orchestration

ui/                      # User interface components
  ├── __init__.py
  ├── dialogs/           # Dialog windows
  │   ├── __init__.py
  │   ├── config_dialog.py
  │   └── journal_preview_dialog.py
  ├── tray.py            # System tray (existing)
  └── widgets/          # Reusable UI components
      └── __init__.py

utils/                   # Utility functions
  ├── __init__.py
  ├── audio_utils.py     # Audio file handling
  ├── file_utils.py      # File system operations
  └── platform_utils.py  # Platform-specific code
```

## Refactoring Steps

### Phase 1: Setup and Core Structure
1. [ ] Create new directory structure
2. [ ] Set up `__init__.py` files
3. [ ] Move core application class to `core/application.py`
4. [ ] Create service interfaces

### Phase 2: Extract Services
1. [ ] Move audio-related code to `services/audio_service.py`
2. [ ] Move transcription logic to `services/transcription_service.py`
3. [ ] Move journaling logic to `services/journal_service.py`
4. [ ] Move template management to `services/template_service.py`

### Phase 3: UI Refactoring
1. [ ] Move dialog windows to `ui/dialogs/`
2. [ ] Update imports and references
3. [ ] Ensure all UI components are properly connected

### Phase 4: Cleanup and Testing
1. [ ] Remove old code from `whisper_notes.py`
2. [ ] Update imports throughout the codebase
3. [ ] Test all functionality
4. [ ] Update documentation

## Implementation Notes

- Each service should have a clear, single responsibility
- Use dependency injection for service dependencies
- Maintain backward compatibility during refactoring
- Add/update unit tests for new modules
- Update documentation as we go

## Current Progress

- [ ] Phase 1: Setup and Core Structure
  - [ ] Create directory structure
  - [ ] Set up core modules
  
- [ ] Phase 2: Extract Services
- [ ] Phase 3: UI Refactoring
- [ ] Phase 4: Cleanup and Testing
