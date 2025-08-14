"""Help screen for CLASSIC TUI."""

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Markdown, Static, TabbedContent, TabPane


class HelpScreen(ModalScreen):
    """Modal help screen with keyboard shortcuts and usage information."""

    CSS = """
    HelpScreen {
        align: center middle;
    }
    
    #help-container {
        width: 80;
        height: 40;
        border: thick $primary;
        padding: 1;
        background: $surface;
    }
    
    .help-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: $primary;
        text-style: bold underline;
    }
    
    .help-content {
        margin: 1 0;
        height: 100%;
    }
    
    TabbedContent {
        height: 100%;
    }
    
    TabPane {
        padding: 1;
    }
    
    .shortcut-key {
        color: $primary;
        text-style: bold;
    }
    
    .shortcut-desc {
        color: $text;
    }
    
    #close-help {
        dock: bottom;
        width: 100%;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose help screen layout."""
        with Container(id="help-container"):
            yield Static("📚 CLASSIC TUI - Help & Documentation", classes="help-title")

            with TabbedContent(classes="help-content"):
                with TabPane("Keyboard Shortcuts", id="shortcuts-tab"):
                    yield VerticalScroll(Markdown(self._get_shortcuts_text()))

                with TabPane("Usage Guide", id="usage-tab"):
                    yield VerticalScroll(Markdown(self._get_usage_text()))

                with TabPane("Features", id="features-tab"):
                    yield VerticalScroll(Markdown(self._get_features_text()))

                with TabPane("Troubleshooting", id="troubleshooting-tab"):
                    yield VerticalScroll(Markdown(self._get_troubleshooting_text()))

            yield Button("Close (ESC)", id="close-help", variant="primary")

    def _get_shortcuts_text(self) -> str:
        """Generate keyboard shortcuts documentation."""
        return """
# Keyboard Shortcuts

## Navigation
- **Tab** / **Shift+Tab** - Navigate between elements
- **Arrow Keys** - Navigate within lists and text
- **Enter** - Activate button/submit input
- **ESC** - Close dialogs/cancel operations

## Application Control
- **F1** - Show this help screen
- **Q** - Quit application
- **Ctrl+C** - Force quit

## Scan Operations
- **F5** / **R** - Run crash logs scan
- **F6** / **G** - Run game files scan  
- **F7** / **P** - Toggle Papyrus monitor

## Output Management
- **Ctrl+L** - Clear output viewer
- **/** - Search in output
- **ESC** - Exit search mode (when searching)

## Settings
- **Ctrl+O** - Open settings screen

## During Scans
- **Space** - Pause/Resume scan
- **ESC** - Cancel current scan
"""

    def _get_usage_text(self) -> str:
        """Generate usage guide."""
        return """
# Usage Guide

## Getting Started

### 1. Configure Folder Paths
Set up your folder paths in the main screen:
- **Staging Mods Folder**: Directory containing your mod files
- **Custom Scan Folder**: Alternative location for scanning logs

### 2. Running Scans

#### Crash Logs Scan
1. Press **F5** or click "Crash Logs Scan"
2. The scanner will analyze all crash logs in the configured folders
3. Results appear in the output viewer with color coding:
   - 🔴 Red: Errors and critical issues
   - 🟡 Yellow: Warnings
   - 🟢 Green: Success messages
   - 🔵 Blue: Information

#### Game Files Scan
1. Press **F6** or click "Game Files Scan"
2. Checks game installation integrity
3. Validates mod files and dependencies
4. Reports any missing or corrupted files

### 3. Papyrus Monitor
- Press **F7** to toggle real-time Papyrus log monitoring
- Watches for script errors and performance issues
- Highlights problematic patterns automatically

### 4. Managing Output
- **Auto-scroll**: Automatically follows new output
- **Search**: Press **/** to search within output
- **Clear**: Press **Ctrl+L** to clear the display
- **Note**: Scan results are automatically saved during the scanning process

### 5. Settings
Access settings with **Ctrl+O** to configure:
- Update checking preferences
- Default folder paths
- Display options
- Performance settings
"""

    def _get_features_text(self) -> str:
        """Generate features documentation."""
        return """
# Features

## Core Functionality

### Advanced Log Analysis
- Pattern recognition for common crash causes
- FormID resolution to identify problematic mods
- Stack trace analysis with mod identification
- Memory allocation tracking

### Real-time Monitoring
- Live Papyrus log monitoring
- Performance metrics tracking
- Error rate analysis
- Alert thresholds

### Comprehensive Reporting
- Detailed crash analysis reports
- Mod conflict detection
- Load order recommendations
- Performance optimization suggestions

## User Interface

### Smart Output Viewer
- Syntax highlighting for better readability
- Search functionality with highlighting
- Export capabilities for sharing
- Automatic timestamp addition

### Status Bar
- Current operation status
- Last scan timestamp
- Active folder indicator
- Progress tracking

### Confirmation Dialogs
- Prevents accidental operations
- Clear action descriptions
- Keyboard navigation support

## Data Management

### Settings Persistence
- Automatic configuration saving
- Session state restoration
- Folder path memory
- Preference storage

### Output Management
- Timestamped log files
- Structured export format
- Filtering capabilities
- History tracking
"""

    def _get_troubleshooting_text(self) -> str:
        """Generate troubleshooting guide."""
        return """
# Troubleshooting

## Common Issues

### Scanner Not Finding Logs
**Problem**: No crash logs detected during scan
**Solutions**:
1. Verify folder paths are correct
2. Check folder permissions
3. Ensure logs exist in the specified location
4. Try using absolute paths instead of relative

### Slow Performance
**Problem**: Scans taking too long
**Solutions**:
1. Reduce max lines in output viewer
2. Clear output before starting new scan
3. Close other applications
4. Check disk I/O performance

### Output Not Updating
**Problem**: Results not appearing in viewer
**Solutions**:
1. Check auto-scroll is enabled
2. Clear output and retry
3. Verify scan is actually running (check status bar)
4. Look for error messages in red

### Keyboard Shortcuts Not Working
**Problem**: Hotkeys unresponsive
**Solutions**:
1. Ensure correct window has focus
2. Check no modal dialogs are open
3. Try using alternative shortcuts
4. Restart the application

## Error Messages

### "Permission Denied"
- Run application with appropriate permissions
- Check folder access rights
- Verify antivirus isn't blocking

### "Path Not Found"
- Verify folder exists
- Check for typos in path
- Use browse button to select folder

### "Memory Error"
- Clear output viewer
- Reduce max lines setting
- Process smaller batches of logs

## Getting Help

If issues persist:
1. Check the full documentation
2. Review the error messages carefully
3. Export the output log for analysis
4. Contact support with detailed information
"""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "close-help":
            self.dismiss()

    def on_key(self, event) -> None:
        """Handle key press."""
        if event.key == "escape":
            self.dismiss()
