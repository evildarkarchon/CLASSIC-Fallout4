# CLASSIC Terminal UI (TUI) Implementation Plan

## Overview
This document outlines the implementation plan for creating a Terminal User Interface (TUI) version of CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker). The TUI will provide a text-based interface that mirrors the functionality of the existing Qt GUI, with a focus on the main tab operations.

## Architecture Goals
- **Modular Design**: Clear separation of concerns with all TUI components in `ClassicLib/TUI/`
- **Maintainability**: Each component should be self-contained and easily testable
- **Consistency**: Mirror the Qt GUI's functionality and workflow
- **Performance**: Leverage existing async architecture from the core library
- **Accessibility**: Provide keyboard navigation and screen reader compatibility

## Technology Stack
- **Primary Framework**: `textual` - Modern Python TUI framework with async support
- **Alternative Option**: `rich` + `prompt_toolkit` for more control
- **Async Support**: Leverage existing asyncio patterns from ClassicLib
- **Configuration**: Use existing YAML settings infrastructure

## Directory Structure
```
ClassicLib/TUI/
├── __init__.py
├── app.py                 # Main TUI application class
├── screens/
│   ├── __init__.py
│   ├── main_screen.py     # Main tab equivalent
│   ├── scan_screen.py     # Scan operations screen
│   └── settings_screen.py # Settings management
├── widgets/
│   ├── __init__.py
│   ├── folder_selector.py # Folder path selection widget
│   ├── scan_buttons.py    # Scan operation buttons
│   ├── progress_bar.py    # Progress indicator
│   ├── output_viewer.py   # Log output display
│   └── checkbox_group.py  # Settings checkboxes
├── handlers/
│   ├── __init__.py
│   ├── scan_handler.py    # Handles scan operations
│   ├── folder_handler.py  # Folder management
│   └── message_handler.py # TUI message routing
└── themes/
    ├── __init__.py
    └── dark_theme.py      # Dark theme styling
```

## Core Components

### 1. Main Application (`app.py`)
```python
class CLASSICTuiApp:
    """Main TUI application controller"""
    - Initialize textual app
    - Setup screens and navigation
    - Handle global keybindings
    - Manage application lifecycle
```

### 2. Main Screen (`screens/main_screen.py`)
Implements the MAIN OPTIONS tab functionality:
- **Folder Selection Section**
  - Staging Mods Folder input
  - Custom Scan Folder input
  - Folder validation and browsing
  
- **Scan Operations Section**
  - Crash Logs Scan button
  - Game Files Scan button
  - Papyrus Monitor toggle
  - Progress indicators
  
- **Settings Section**
  - Update Check checkbox
  - TUI-specific settings
  - Quick access to settings file

### 3. Scan Handler (`handlers/scan_handler.py`)
Interfaces with existing scan infrastructure:
```python
class TuiScanHandler:
    """Bridges TUI events with core scan operations"""
    - Wraps ClassicScanLogs functionality
    - Manages async scan operations
    - Routes output to TUI widgets
    - Handles progress updates
```

### 4. Message Handler (`handlers/message_handler.py`)
TUI-specific message routing:
```python
class TuiMessageHandler:
    """Routes messages to appropriate TUI widgets"""
    - Implements MessageHandler interface
    - Routes to output viewer widget
    - Handles different message types (info, warning, error)
    - Manages modal dialogs
```

## Implementation Phases

### Phase 1: Foundation (Week 1) ✅ COMPLETED
1. **Setup Project Structure**
   - Create ClassicLib/TUI directory structure
   - Install textual dependency
   - Create CLASSIC_TUI.py entry point

2. **Basic Application Shell**
   - Implement CLASSICTuiApp class
   - Create main screen layout
   - Setup basic navigation

3. **Message Handler Integration**
   - Create TuiMessageHandler
   - Integrate with existing MessageHandler system
   - Test output routing

### Phase 2: Core Functionality (Week 2) ✅ COMPLETED
1. **Folder Management**
   - Implement folder selector widget
   - Add folder validation
   - Integrate with existing folder paths

2. **Scan Operations**
   - Create scan button widgets
   - Implement scan_handler.py
   - Connect to ClassicScanLogs
   - Add progress indicators

3. **Output Display**
   - Create scrollable output viewer
   - Implement log formatting
   - Clear button only (scan results already saved as markdown files)

### Phase 3: Polish and Testing (Week 3)
1. **User Experience**
   - Add keyboard shortcuts
   - Implement help system
   - Add status bar
   - Create confirmation dialogs

2. **Testing**
   - Unit tests for widgets
   - Integration tests for handlers
   - End-to-end workflow tests
   - Performance testing

3. **Documentation**
   - User guide for TUI
   - Developer documentation
   - Update README

## Key Design Decisions

### 1. Framework Choice: Textual
**Reasons:**
- Modern async-first design aligns with existing architecture
- Rich widget library reduces development time
- CSS-like styling for consistent theming
- Built-in testing support
- Active development and community

### 2. Async Pattern Consistency
- Use existing async orchestrator pattern
- Leverage FileIOCore for all file operations
- Maintain same error handling patterns

### 3. Settings Integration
- Use existing YamlSettingsCache
- Share settings with GUI version
- Add TUI-specific settings section

### 4. Message Routing Strategy
- Create TUI-specific MessageHandler implementation
- Route to appropriate widgets based on message type
- Maintain compatibility with existing message formats

## Widget Specifications

### Folder Selector Widget
```python
class FolderSelector(TextInput):
    """Custom folder path input with validation"""
    Features:
    - Path validation on change
    - Browse button integration
    - Placeholder text support
    - Error state display
```

### Scan Button Widget
```python
class ScanButton(Button):
    """Scan operation trigger button"""
    Features:
    - Disabled state during scan
    - Progress indicator overlay
    - Success/failure state
    - Tooltip support
```

### Output Viewer Widget
```python
class OutputViewer(ScrollView):
    """Scrollable log output display"""
    Features:
    - Auto-scroll to bottom
    - Text selection and copy
    - Search functionality
    - Export to file
```

## Integration Points

### 1. ClassicScanLogs Integration
```python
# In scan_handler.py
async def perform_crash_scan(self):
    scanner = ClassicScanLogs()
    # Route output through TUI message handler
    init_message_handler(parent=self.app, is_gui_mode=False)
    await scanner.orchestrator.async_scan_logs()
```

### 2. Settings Management
```python
# Leverage existing settings
from ClassicLib.YamlSettingsCache import classic_settings
update_check = classic_settings(bool, "Update Check")
```

### 3. File Operations
```python
# Use existing FileIOCore
from ClassicLib.FileIOCore import FileIOCore
io_core = FileIOCore()
content = await io_core.read_file(path)
```

## Error Handling

### 1. User Input Validation
- Validate folder paths before operations
- Show clear error messages in status bar
- Prevent invalid operations

### 2. Operation Failures
- Graceful degradation for scan failures
- Clear error reporting to output viewer
- Recovery options for common issues

### 3. System Compatibility
- Handle terminal capability differences
- Fallback for unsupported features
- Windows terminal specific handling

## Testing Strategy

### 1. Unit Tests
- Test each widget in isolation
- Mock external dependencies
- Verify event handling

### 2. Integration Tests
- Test handler-widget interactions
- Verify message routing
- Test async operation handling

### 3. End-to-End Tests
- Complete scan workflow
- Settings persistence
- Error recovery scenarios

## Performance Considerations

### 1. Async Operations
- All I/O operations must be async
- Use existing async patterns from core
- Prevent UI blocking during scans

### 2. Memory Management
- Stream large log files
- Limit output viewer buffer
- Clean up completed operations

### 3. Rendering Optimization
- Update only changed widgets
- Batch UI updates
- Use virtual scrolling for large outputs

## Accessibility Features

### 1. Keyboard Navigation
- Full keyboard support
- Consistent shortcut scheme
- Vi-style navigation option

### 2. Screen Reader Support
- Semantic widget roles
- Clear label associations
- Status announcements

### 3. High Contrast Mode
- Support system theme
- Adjustable color schemes
- Clear visual indicators

## Future Enhancements

### Phase 4: Additional Tabs
- Implement FILE BACKUP tab
- Add ARTICLES tab with links
- Settings management screen

### Phase 5: Advanced Features
- Papyrus monitoring integration
- Real-time log watching
- Batch operations support

### Phase 6: Platform Features
- SSH/remote operation support
- Configuration profiles
- Automation scripting

## Dependencies

### Required Packages
```toml
[tool.poetry.dependencies]
textual = "^5.3.0"  # Main TUI framework
```

### Optional Packages
```toml
[tool.poetry.dev-dependencies]
textual-dev = "^1.7.0"  # Development tools
pytest-textual-snapshot = "^1.1.0"  # Testing support
```

## Code Examples

### Entry Point (`CLASSIC_TUI.py`)
```python
#!/usr/bin/env python
"""CLASSIC Terminal User Interface"""

import sys
from ClassicLib.TUI.app import CLASSICTuiApp
from ClassicLib.SetupCoordinator import SetupCoordinator

def main():
    # Initialize application
    coordinator = SetupCoordinator()
    coordinator.initialize_application(is_gui=False)
    
    # Run TUI
    app = CLASSICTuiApp()
    app.run()

if __name__ == "__main__":
    main()
```

### Main Screen Layout Example
```python
class MainScreen(Screen):
    """Main options screen"""
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            yield Label("STAGING MODS FOLDER")
            yield FolderSelector(id="mods-folder")
            yield Label("CUSTOM SCAN FOLDER")
            yield FolderSelector(id="scan-folder")
            with Horizontal():
                yield ScanButton("Crash Logs Scan", id="crash-scan")
                yield ScanButton("Game Files Scan", id="game-scan")
            yield OutputViewer(id="output")
        yield Footer()
```

## Conclusion

This implementation plan provides a structured approach to creating a Terminal UI for CLASSIC that maintains consistency with the existing Qt GUI while leveraging the modular architecture of the core library. The phased approach allows for incremental development and testing, ensuring a stable and maintainable TUI implementation.

The focus on modularity, clear separation of concerns, and reuse of existing components will result in a TUI that is both powerful and maintainable, providing users with a lightweight alternative to the GUI while maintaining full functionality.