"""Main options screen for CLASSIC TUI."""

import os
import sys
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Label

from ClassicLib.Constants import YAML
from ClassicLib.TUI.input_validator import InputValidator
from ClassicLib.TUI.widgets.folder_selector import FolderSelector
from ClassicLib.TUI.widgets.output_viewer import OutputViewer
from ClassicLib.TUI.widgets.scan_buttons import ScanButton
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


class MainScreen(Screen):
    """Main options screen with folder selection and scan operations."""

    BINDINGS: ClassVar[list[Binding]] = [
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
                yield ScanButton("Crash Logs Scan", scan_type="crash", id="crash-scan", variant="primary")
                yield ScanButton("Game Files Scan", scan_type="game", id="game-scan", variant="primary")
                yield Button("Papyrus Monitor", id="papyrus-monitor", variant="default")

            with Vertical(classes="settings-section"):
                # Safe settings retrieval with default value
                try:
                    update_check_value = classic_settings(bool, "Update Check") or False
                except (RuntimeError, KeyError, ValueError):
                    update_check_value = False
                yield Checkbox("Check for Updates", id="update-check", value=update_check_value)

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
        except (LookupError, ValueError, AttributeError):
            # Widgets might not be ready yet or query failed
            self._widget_cache = {}

    def _setup_focus_order(self) -> None:
        """Set up the tab focus order for widgets."""
        # Use cached widget if available
        mods_folder = self._widget_cache.get("mods_folder") or self.query_one("#mods-folder", FolderSelector)
        mods_folder.focus()

    def _load_folder_paths(self) -> None:
        """Load saved folder paths from settings."""
        try:
            # Initialize message handler if not already done (for tests)
            from ClassicLib.MessageHandler import init_message_handler

            init_message_handler(parent=None, is_gui_mode=False)

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
        except (LookupError, ValueError, AttributeError, KeyError, FileNotFoundError):
            # Handle missing widgets, invalid settings, or file access issues
            pass

    def _setup_event_handlers(self) -> None:
        """Setup event handlers for widgets."""
        # ScanButton widgets use message-based event handling
        # They automatically handle button presses and send ScanStarted/ScanCompleted messages
        # The actual scan logic is handled in the message handlers below

    async def perform_crash_scan(self) -> None:
        """Perform crash logs scan."""
        # Use cached widget if available
        output = self._widget_cache.get("output") or self.query_one("#output", OutputViewer)
        output.clear()
        output.append_output("Starting crash logs scan...\n")

        from ClassicLib.TUI.handlers.scan_handler import TuiScanHandler

        handler = TuiScanHandler(output_callback=output.append_output)
        await handler.perform_crash_scan()

    async def perform_game_scan(self) -> None:
        """Perform game files scan."""
        # Use cached widget if available
        output = self._widget_cache.get("output") or self.query_one("#output", OutputViewer)
        output.clear()
        output.append_output("Starting game files scan...\n")

        from ClassicLib.TUI.handlers.scan_handler import TuiScanHandler

        handler = TuiScanHandler(output_callback=output.append_output)
        await handler.perform_game_scan()

    async def toggle_papyrus_monitor(self) -> None:
        """Toggle Papyrus monitoring."""
        # Import and push the Papyrus monitoring screen
        from .papyrus_screen import PapyrusScreen

        # Detect Unicode support for the screen
        use_unicode = self._detect_unicode_support()

        # Push the Papyrus screen
        await self.app.push_screen(PapyrusScreen(use_unicode=use_unicode))

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
        from ClassicLib.TUI.constants import UNICODE_TERMINAL_TYPES
        if any(t in term for t in UNICODE_TERMINAL_TYPES):
            return True

        # Windows Console Host
        if sys.platform == "win32":
            try:
                import ctypes

                kernel32 = ctypes.windll.kernel32
                # noinspection PyUnresolvedReferences
                cp = kernel32.GetConsoleOutputCP()
                return cp == 65001  # UTF-8 code page  # noqa: TRY300
            except (ImportError, AttributeError, OSError):
                # ctypes not available, attribute error, or OS error
                return False

        # Default to ASCII for safety
        return False

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox changes."""
        if event.checkbox.id == "update-check":
            yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Update Check", event.value)

    def on_scan_button_scan_started(self, event: ScanButton.ScanStarted) -> None:
        """Handle scan started events from ScanButton."""
        if event.scan_type == "crash":
            self.app.call_later(self.perform_crash_scan)
        elif event.scan_type == "game":
            self.app.call_later(self.perform_game_scan)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "papyrus-monitor":
            self.app.call_later(self.toggle_papyrus_monitor)

    def on_folder_selector_path_changed(self, event: FolderSelector.PathChanged) -> None:
        """Handle secure path changes from FolderSelector widgets."""
        # Only save valid paths
        if not event.valid:
            return

        # Get the sender to identify which folder selector
        sender_id = event.sender.id if hasattr(event, "sender") and event.sender else None

        if sender_id == "mods-folder":
            # Validate and sanitize before saving
            is_valid, sanitized = InputValidator.validate_settings_value("CLASSIC_Settings.MODS Folder Path", event.path)
            if is_valid and sanitized:
                self.staging_folder = sanitized
                yaml_settings(str, YAML.Settings, "CLASSIC_Settings.MODS Folder Path", sanitized)
        elif sender_id == "scan-folder":
            # Validate and sanitize before saving
            is_valid, sanitized = InputValidator.validate_settings_value("CLASSIC_Settings.SCAN Custom Path", event.path)
            if is_valid and sanitized:
                self.custom_folder = sanitized
                yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", sanitized)

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

    def on_key(self, event: Key) -> None:
        """Handle keyboard events."""
        # Handle Escape key to unfocus current widget
        if event.key == "escape" and self.focused:
            self.focused.blur()
            event.stop()
