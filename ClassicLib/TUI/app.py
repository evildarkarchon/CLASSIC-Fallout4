"""Main CLASSIC TUI Application.

This module contains the CLASSICApp class which is the main Textual application
for the CLASSIC TUI interface.
"""

from pathlib import Path
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import Footer, Header, TabbedContent, TabPane

from ClassicLib.TUI.tabs.articles_tab import ArticlesTab
from ClassicLib.TUI.tabs.backup_tab import BackupTab
from ClassicLib.TUI.tabs.main_tab import MainTab
from ClassicLib.TUI.tabs.results_tab import ResultsTab


class CLASSICApp(App[None]):
    """Main CLASSIC TUI application using Textual.

    This application provides a terminal-based interface for CLASSIC with
    feature parity to the PySide6 GUI.

    Attributes:
        TITLE: Application title shown in header.
        CSS_PATH: Path to the TCSS stylesheet.
        BINDINGS: Global keyboard shortcuts.

    """

    TITLE = "CLASSIC - Crash Log Auto Scanner & Setup Integrity Checker"
    CSS_PATH = Path(__file__).parent / "styles" / "classic.tcss"

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("f1", "show_help", "Help"),
        Binding("f5", "crash_scan", "Crash Scan"),
        Binding("f6", "game_scan", "Game Scan"),
        Binding("f7", "toggle_papyrus", "Papyrus"),
        Binding("ctrl+o", "show_settings", "Settings"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("q", "quit", "Quit", show=False),
        Binding("1", "switch_tab('main')", "Main", show=False),
        Binding("2", "switch_tab('backup')", "Backup", show=False),
        Binding("3", "switch_tab('articles')", "Articles", show=False),
        Binding("4", "switch_tab('results')", "Results", show=False),
    ]

    def compose(self) -> ComposeResult:  # noqa: PLR6301
        """Create the application layout with header, tabs, and footer.

        Yields:
            Header, TabbedContent with 4 tabs, and Footer widgets.

        """
        from ClassicLib.TUI.test_mode import is_test_mode

        # Disable clock in test mode for stable snapshots
        yield Header(show_clock=not is_test_mode())
        with TabbedContent(id="main-tabs"):
            with TabPane("MAIN OPTIONS", id="main"):
                yield MainTab()
            with TabPane("FILE BACKUP", id="backup"):
                yield BackupTab()
            with TabPane("ARTICLES", id="articles"):
                yield ArticlesTab()
            with TabPane("RESULTS", id="results"):
                yield ResultsTab()
        yield Footer()

    def action_switch_tab(self, tab_id: str) -> None:
        """Switch to a specific tab by ID.

        Args:
            tab_id: The ID of the tab to switch to (main, backup, articles, results).

        """
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = tab_id

    def action_show_help(self) -> None:
        """Show the help modal with keyboard shortcuts and usage guide."""
        from ClassicLib.TUI.screens.help_screen import HelpScreen

        self.push_screen(HelpScreen())

    def action_show_settings(self) -> None:
        """Show the settings modal for application configuration."""
        from ClassicLib.TUI.screens.settings_screen import SettingsScreen

        self.push_screen(SettingsScreen())

    def action_crash_scan(self) -> None:
        """Start a crash logs scan operation."""
        main_tab = self.query_one(MainTab)
        main_tab.start_crash_scan()

    def action_game_scan(self) -> None:
        """Start a game files scan operation."""
        main_tab = self.query_one(MainTab)
        main_tab.start_game_scan()

    def action_toggle_papyrus(self) -> None:
        """Toggle Papyrus monitoring on/off."""
        main_tab = self.query_one(MainTab)
        main_tab.toggle_papyrus()

    def switch_to_results_tab(self) -> None:
        """Switch to the Results tab (called after scan completion)."""
        self.action_switch_tab("results")
        results_tab = self.query_one(ResultsTab)
        results_tab.refresh_reports()
