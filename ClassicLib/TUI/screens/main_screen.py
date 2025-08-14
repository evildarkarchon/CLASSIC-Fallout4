"""Main options screen for CLASSIC TUI."""

import os
import sys

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Input, Label

from ClassicLib.YamlSettingsCache import classic_settings

from ..widgets.folder_selector import FolderSelector
from ..widgets.output_viewer import OutputViewer
from ..widgets.scan_buttons import ScanButton


class MainScreen(Screen):
    """Main options screen with folder selection and scan operations."""

    BINDINGS = [
        Binding("ctrl+1", "focus_mods_folder", "Focus Mods Folder", show=False),
        Binding("ctrl+2", "focus_scan_folder", "Focus Scan Folder", show=False),
        Binding("ctrl+r", "focus_crash_scan", "Focus Crash Scan", show=False),
        Binding("ctrl+g", "focus_game_scan", "Focus Game Scan", show=False),
        Binding("ctrl+p", "focus_papyrus", "Focus Papyrus", show=False),
        Binding("ctrl+u", "focus_update_check", "Focus Update Check", show=False),
        Binding("alt+o", "focus_output", "Focus Output", show=False),
    ]

    staging_folder = reactive("")
    custom_folder = reactive("")

    def compose(self) -> ComposeResult:
        """Compose the main screen layout."""
        with Vertical(id="main-container"):
            yield Label("MAIN OPTIONS", classes="title")

            with Vertical(classes="folder-section"):
                yield Label("STAGING MODS FOLDER")
                yield FolderSelector(placeholder="Enter path to staging mods folder", id="mods-folder", classes="folder-input")

                yield Label("CUSTOM SCAN FOLDER")
                yield FolderSelector(placeholder="Enter path to custom scan folder", id="scan-folder", classes="folder-input")

            with Horizontal(classes="scan-buttons"):
                yield ScanButton("Crash Logs Scan", id="crash-scan", variant="primary")
                yield ScanButton("Game Files Scan", id="game-scan", variant="primary")
                yield Button("Papyrus Monitor", id="papyrus-monitor", variant="default")

            with Vertical(classes="settings-section"):
                yield Checkbox("Check for Updates", id="update-check", value=classic_settings(bool, "Update Check"))

            yield OutputViewer(id="output")

    def on_mount(self) -> None:
        """Initialize screen on mount."""
        # Cache frequently accessed widgets for performance
        self._widget_cache = {}
        self._cache_widgets()

        self._load_folder_paths()
        self._setup_event_handlers()
        self._setup_focus_order()

    def _cache_widgets(self) -> None:
        """Cache frequently accessed widgets to avoid repeated queries."""
        try:
            self._widget_cache = {
                "mods_folder": self.query_one("#mods-folder", FolderSelector),
                "scan_folder": self.query_one("#scan-folder", FolderSelector),
                "crash_scan": self.query_one("#crash-scan", ScanButton),
                "game_scan": self.query_one("#game-scan", ScanButton),
                "papyrus_monitor": self.query_one("#papyrus-monitor", Button),
                "update_check": self.query_one("#update-check", Checkbox),
                "output": self.query_one("#output", OutputViewer),
            }
        except Exception:
            # Widgets might not be ready yet
            self._widget_cache = {}

    def _setup_focus_order(self) -> None:
        """Set up the tab focus order for widgets."""
        # Use cached widget if available
        mods_folder = self._widget_cache.get("mods_folder") or self.query_one("#mods-folder", FolderSelector)
        mods_folder.focus()

    def _load_folder_paths(self) -> None:
        """Load saved folder paths from settings."""
        try:
            staging_path = classic_settings(str, "ModStagingFolder")
            if staging_path:
                mods_folder = self._widget_cache.get("mods_folder") or self.query_one("#mods-folder", FolderSelector)
                mods_folder.value = staging_path
                self.staging_folder = staging_path

            custom_path = classic_settings(str, "CustomScanFolder")
            if custom_path:
                scan_folder = self._widget_cache.get("scan_folder") or self.query_one("#scan-folder", FolderSelector)
                scan_folder.value = custom_path
                self.custom_folder = custom_path
        except Exception:
            pass

    def _setup_event_handlers(self) -> None:
        """Setup event handlers for widgets."""
        # Use cached widgets if available
        crash_scan = self._widget_cache.get("crash_scan") or self.query_one("#crash-scan", ScanButton)
        crash_scan.on_click = self.perform_crash_scan

        game_scan = self._widget_cache.get("game_scan") or self.query_one("#game-scan", ScanButton)
        game_scan.on_click = self.perform_game_scan

        papyrus_btn = self._widget_cache.get("papyrus_monitor") or self.query_one("#papyrus-monitor", Button)
        papyrus_btn.on_click = self.toggle_papyrus_monitor

    async def perform_crash_scan(self) -> None:
        """Perform crash logs scan."""
        # Use cached widget if available
        output = self._widget_cache.get("output") or self.query_one("#output", OutputViewer)
        output.clear()
        output.append_output("Starting crash logs scan...\n")

        from ..handlers.scan_handler import TuiScanHandler

        handler = TuiScanHandler(output_callback=output.append_output)
        await handler.perform_crash_scan()

    async def perform_game_scan(self) -> None:
        """Perform game files scan."""
        # Use cached widget if available
        output = self._widget_cache.get("output") or self.query_one("#output", OutputViewer)
        output.clear()
        output.append_output("Starting game files scan...\n")

        from ..handlers.scan_handler import TuiScanHandler

        handler = TuiScanHandler(output_callback=output.append_output)
        await handler.perform_game_scan()

    async def toggle_papyrus_monitor(self) -> None:
        """Toggle Papyrus monitoring."""
        # Import and push the Papyrus monitoring screen
        from .papyrus_screen import PapyrusScreen

        # Detect Unicode support for the screen
        use_unicode = self._detect_unicode_support()

        # Push the Papyrus screen
        self.app.push_screen(PapyrusScreen(use_unicode=use_unicode))

    def _detect_unicode_support(self) -> bool:
        """Detect if terminal supports Unicode.

        Returns:
            True if Unicode is likely supported, False for ASCII fallback
        """
        # Check environment variables for terminal type
        term = os.environ.get("TERM", "").lower()
        lang = os.environ.get("LANG", "").lower()

        # Windows Terminal and modern terminals support Unicode
        if os.environ.get("WT_SESSION"):  # Windows Terminal
            return True

        # Check for UTF-8 locale
        if "utf-8" in lang or "utf8" in lang:
            return True

        # Check if running in common modern terminals
        if any(t in term for t in ["xterm", "vt100", "linux", "screen", "tmux"]):
            return True

        # Windows Console Host
        if sys.platform == "win32":
            try:
                import ctypes

                kernel32 = ctypes.windll.kernel32
                cp = kernel32.GetConsoleOutputCP()
                return cp == 65001  # UTF-8 code page
            except:
                return False

        # Default to ASCII for safety
        return False

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox changes."""
        if event.checkbox.id == "update-check":
            classic_settings(bool, "Update Check", event.value)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        if event.input.id == "mods-folder":
            self.staging_folder = event.value
            classic_settings(str, "ModStagingFolder", event.value)
        elif event.input.id == "scan-folder":
            self.custom_folder = event.value
            classic_settings(str, "CustomScanFolder", event.value)

    def action_focus_mods_folder(self) -> None:
        """Focus the mods folder input."""
        widget = self._widget_cache.get("mods_folder") or self.query_one("#mods-folder", FolderSelector)
        widget.focus()

    def action_focus_scan_folder(self) -> None:
        """Focus the scan folder input."""
        widget = self._widget_cache.get("scan_folder") or self.query_one("#scan-folder", FolderSelector)
        widget.focus()

    def action_focus_crash_scan(self) -> None:
        """Focus the crash scan button."""
        widget = self._widget_cache.get("crash_scan") or self.query_one("#crash-scan", ScanButton)
        widget.focus()

    def action_focus_game_scan(self) -> None:
        """Focus the game scan button."""
        widget = self._widget_cache.get("game_scan") or self.query_one("#game-scan", ScanButton)
        widget.focus()

    def action_focus_papyrus(self) -> None:
        """Focus the papyrus monitor button."""
        widget = self._widget_cache.get("papyrus_monitor") or self.query_one("#papyrus-monitor", Button)
        widget.focus()

    def action_focus_update_check(self) -> None:
        """Focus the update check checkbox."""
        widget = self._widget_cache.get("update_check") or self.query_one("#update-check", Checkbox)
        widget.focus()

    def action_focus_output(self) -> None:
        """Focus the output viewer."""
        widget = self._widget_cache.get("output") or self.query_one("#output", OutputViewer)
        widget.focus()

    def on_key(self, event) -> None:
        """Handle keyboard events."""
        # Handle Escape key to unfocus current widget
        if event.key == "escape":
            if self.focused:
                self.focused.blur()
                event.stop()
