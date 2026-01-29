"""Help Screen for CLASSIC TUI.

Modal help overlay with keyboard shortcuts and usage guide.
"""

from typing import ClassVar, override

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Markdown, TabbedContent, TabPane

SHORTCUTS_CONTENT = """
## Global Shortcuts

| Key           | Action                    |
|---------------|---------------------------|
| F1            | Show this help            |
| F5            | Run crash logs scan       |
| F6            | Run game files scan       |
| F7            | Toggle Papyrus monitor    |
| Ctrl+O        | Open settings             |
| Ctrl+Q / Q    | Quit application          |
| 1-4           | Switch to tab by number   |
| Tab           | Next element              |
| Shift+Tab     | Previous element          |

## Results Tab

| Key           | Action                    |
|---------------|---------------------------|
| ↑/↓           | Select report             |
| Enter         | Load selected report      |
| Delete        | Delete selected report    |
| Ctrl+C        | Copy report to clipboard  |
| Ctrl+R        | Refresh report list       |

## Backup Tab

| Key           | Action                    |
|---------------|---------------------------|
| ↑/↓           | Select backup type        |
| B             | Backup selected           |
| R             | Restore selected          |
| D             | Delete selected backup    |
| O             | Open backup folder        |
"""

USAGE_CONTENT = """
## Getting Started

1. **Configure Folders**: Set your staging mods folder and optional custom scan path on the Main tab.

2. **Run Scans**: Press F5 to scan crash logs or F6 to scan game files. Results will appear in the Results tab.

3. **View Reports**: Switch to the Results tab to view and manage scan reports.

4. **Papyrus Monitoring**: Toggle Papyrus log monitoring with F7 to track script issues in real-time.

## Tips

- Use keyboard shortcuts for faster navigation
- Reports are automatically saved to the Crash Logs folder
- Backups are stored in CLASSIC Backup/Game Files/
"""

FEATURES_CONTENT = """
## Features

### Crash Log Scanning
Analyzes Buffout 4 crash logs to identify:
- Missing or outdated mods
- Plugin conflicts
- Script errors
- Common crash causes

### Game Files Scanning
Validates game installation:
- F4SE/SKSE installation
- Required dependencies
- File integrity

### Papyrus Monitoring
Real-time monitoring of Papyrus script logs:
- Stack dumps
- Script errors and warnings
- Performance issues

### File Backups
Backup and restore game files:
- Script extender (F4SE/SKSE)
- ReShade configurations
- Vulkan layers
- ENB presets
"""


class HelpScreen(ModalScreen[None]):
    """Modal help overlay with tabbed content.

    Displays keyboard shortcuts, usage guide, and feature descriptions.
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "close", "Close"),
    ]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-container {
        width: 80%;
        height: 80%;
        background: #2d2d2d;
        border: solid #3c3c3c;
        padding: 1;
    }

    #help-title {
        text-style: bold;
        color: #4a9eff;
        text-align: center;
        margin-bottom: 1;
    }

    #help-tabs {
        height: 1fr;
    }

    #close-btn {
        dock: bottom;
        margin-top: 1;
    }
    """

    @override
    def compose(self) -> ComposeResult:
        """Create the help modal layout.

        Yields:
            Container with title, tabbed help content, and close button.

        """
        with Vertical(id="help-container"):
            yield Label("📚 Help & Shortcuts", id="help-title")
            with TabbedContent(id="help-tabs"):
                with TabPane("Shortcuts", id="shortcuts-tab"), VerticalScroll():
                    yield Markdown(SHORTCUTS_CONTENT)
                with TabPane("Usage", id="usage-tab"), VerticalScroll():
                    yield Markdown(USAGE_CONTENT)
                with TabPane("Features", id="features-tab"), VerticalScroll():
                    yield Markdown(FEATURES_CONTENT)
            yield Button("Close (ESC)", id="close-btn", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle close button press.

        Args:
            event: The button pressed event.

        """
        if event.button.id == "close-btn":
            self.action_close()

    def action_close(self) -> None:
        """Close the help modal."""
        self.dismiss(None)
