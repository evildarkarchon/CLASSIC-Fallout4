"""Main TUI application controller."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from .screens.main_screen import MainScreen


class CLASSICTuiApp(App):
    """CLASSIC Terminal User Interface Application."""

    CSS = """
    Screen {
        overflow: hidden;
    }
    
    #main-container {
        padding: 0 1;
        height: 100%;
    }
    
    .title {
        height: 1;
        margin: 0 0 1 0;
    }
    
    .folder-selector-container {
        height: 3;
    }
    
    .folder-input {
        width: 1fr;
        height: 3;
    }
    
    .folder-section {
        height: auto;
    }
    
    .folder-section Label {
        height: 1;
        margin: 0;
        padding: 0;
    }
    
    .folder-section FolderSelector {
        height: 3;
        margin-bottom: 1;
    }
    
    .error-label {
        display: none;
    }
    
    .settings-section {
        height: 2;
        margin: 0;
    }
    
    .scan-buttons {
        height: 3;
        margin: 0 0 1 0;
    }
    
    #output {
        border: solid darkgreen;
        height: 1fr;
        min-height: 5;
    }
    
    StatusBar {
        background: $panel;
        color: $text;
        height: 1;
        dock: bottom;
    }
    
    StatusBar .status-key {
        color: $primary;
        text-style: bold;
    }
    
    StatusBar .status-value {
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("ctrl+c", "quit", "Force Quit", priority=True),
        Binding("f1", "show_help", "Help"),
        Binding("f5", "run_crash_scan", "Crash Scan"),
        Binding("r", "run_crash_scan", "Crash Scan", show=False),
        Binding("f6", "run_game_scan", "Game Scan"),
        Binding("g", "run_game_scan", "Game Scan", show=False),
        Binding("f7", "toggle_papyrus", "Papyrus Monitor"),
        Binding("p", "toggle_papyrus", "Papyrus", show=False),
        Binding("ctrl+l", "clear_output", "Clear Output"),
        Binding("ctrl+o", "open_settings", "Settings"),
        Binding("/", "search_output", "Search"),
        Binding("tab", "focus_next", "Next", show=False),
        Binding("shift+tab", "focus_previous", "Previous", show=False),
        Binding("up", "focus_up", "Up", show=False),
        Binding("down", "focus_down", "Down", show=False),
        Binding("left", "focus_left", "Left", show=False),
        Binding("right", "focus_right", "Right", show=False),
        Binding("enter", "submit_focused", "Submit", show=False),
        Binding("space", "toggle_focused", "Toggle", show=False),
    ]

    TITLE = "CLASSIC - Crash Log Auto Scanner & Setup Integrity Checker"
    SUB_TITLE = "Terminal User Interface"

    def compose(self) -> ComposeResult:
        """Create initial application layout."""
        yield Header()
        from .widgets.status_bar import StatusBar

        yield StatusBar()
        yield Footer()

    def on_mount(self) -> None:
        """Set up the initial screen when app mounts."""
        self.push_screen(MainScreen())

    def action_show_help(self) -> None:
        """Display help information."""
        from .screens.help_screen import HelpScreen

        self.push_screen(HelpScreen())

    async def action_run_crash_scan(self) -> None:
        """Run crash logs scan (F5/R key)."""
        if isinstance(self.screen, MainScreen):
            await self.screen.perform_crash_scan()

    async def action_run_game_scan(self) -> None:
        """Run game files scan (F6/G key)."""
        if isinstance(self.screen, MainScreen):
            await self.screen.perform_game_scan()

    async def action_toggle_papyrus(self) -> None:
        """Toggle Papyrus monitor (F7/P key)."""
        if isinstance(self.screen, MainScreen):
            await self.screen.toggle_papyrus_monitor()

    def action_clear_output(self) -> None:
        """Clear output viewer (Ctrl+L)."""
        from .widgets.output_viewer import OutputViewer

        if isinstance(self.screen, MainScreen):
            try:
                output = self.screen.query_one(OutputViewer)
                output.clear()
            except Exception:
                pass

    def action_open_settings(self) -> None:
        """Open settings screen (Ctrl+O)."""
        from .screens.settings_screen import SettingsScreen

        self.push_screen(SettingsScreen())

    def action_search_output(self) -> None:
        """Search in output viewer (/)."""
        from .widgets.output_viewer import OutputViewer

        if isinstance(self.screen, MainScreen):
            try:
                output = self.screen.query_one(OutputViewer)
                output.start_search()
            except Exception:
                pass

    def action_focus_up(self) -> None:
        """Move focus up with arrow key."""
        if isinstance(self.screen, MainScreen):
            self.screen.focus_previous()

    def action_focus_down(self) -> None:
        """Move focus down with arrow key."""
        if isinstance(self.screen, MainScreen):
            self.screen.focus_next()

    def action_focus_left(self) -> None:
        """Move focus left with arrow key."""
        if isinstance(self.screen, MainScreen):
            # In horizontal layouts, move to previous sibling
            focused = self.focused
            if focused and focused.parent:
                siblings = list(focused.parent.children)
                if focused in siblings:
                    idx = siblings.index(focused)
                    if idx > 0:
                        siblings[idx - 1].focus()

    def action_focus_right(self) -> None:
        """Move focus right with arrow key."""
        if isinstance(self.screen, MainScreen):
            # In horizontal layouts, move to next sibling
            focused = self.focused
            if focused and focused.parent:
                siblings = list(focused.parent.children)
                if focused in siblings:
                    idx = siblings.index(focused)
                    if idx < len(siblings) - 1:
                        siblings[idx + 1].focus()

    def action_submit_focused(self) -> None:
        """Submit/activate the focused widget with Enter key."""
        from textual.widgets import Button, Checkbox

        focused = self.focused
        if isinstance(focused, Button):
            focused.press()
        elif isinstance(focused, Checkbox):
            focused.toggle()

    def action_toggle_focused(self) -> None:
        """Toggle the focused widget with Space key."""
        from textual.widgets import Button, Checkbox

        focused = self.focused
        if isinstance(focused, (Button, Checkbox)):
            if isinstance(focused, Button):
                focused.press()
            else:
                focused.toggle()
