"""Main TUI application controller."""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.binding import Binding

from .screens.main_screen import MainScreen


class CLASSICTuiApp(App):
    """CLASSIC Terminal User Interface Application."""
    
    CSS = """
    #main-container {
        padding: 1;
    }
    
    .folder-input {
        margin: 1 0;
    }
    
    .scan-buttons {
        margin: 1 0;
        height: 3;
    }
    
    #output {
        border: solid darkgreen;
        margin: 1 0;
        padding: 1;
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