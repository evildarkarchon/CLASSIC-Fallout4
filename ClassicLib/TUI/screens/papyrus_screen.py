"""Papyrus monitoring screen for TUI."""

import asyncio
import contextlib
from typing import Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Static

from ClassicLib.TUI.handlers.papyrus_handler import PapyrusStats, TuiPapyrusHandler
from ClassicLib.TUI.widgets.output_viewer import OutputViewer
from ClassicLib.TUI.widgets.papyrus_monitor import PapyrusMonitorWidget


class PapyrusScreen(Screen):
    """Full-screen Papyrus monitoring display."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "close_screen", "Close", priority=True),
        Binding("q", "close_screen", "Close", show=False),
        Binding("s", "toggle_monitoring", "Start/Stop", priority=True),
        Binding("r", "refresh_stats", "Refresh", priority=True),
        Binding("c", "clear_output", "Clear Output"),
        Binding("u", "toggle_unicode", "Toggle Unicode"),
        Binding("ctrl+c", "stop_and_close", "Stop & Exit"),
    ]

    CSS = """
    PapyrusScreen {
        background: $surface;
    }

    #papyrus-container {
        layout: vertical;
        height: 100%;
        padding: 1;
    }

    .screen-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        padding: 1;
        border: double $primary;
        margin-bottom: 1;
    }

    #monitor-widget {
        height: auto;
        margin-bottom: 1;
    }

    #log-output {
        height: 1fr;
        border: solid $primary;
        min-height: 10;
    }

    .control-bar {
        height: 3;
        dock: bottom;
        background: $panel;
        align: center middle;
        padding: 0 2;
    }

    .control-button {
        margin: 0 1;
    }

    .status-indicator {
        dock: right;
        width: auto;
        padding: 0 2;
    }

    .status-indicator.active {
        color: $success;
    }

    .status-indicator.stopped {
        color: $error;
    }
    """

    # Reactive properties
    is_monitoring = reactive(False)
    use_unicode = reactive(True)

    def __init__(self, use_unicode: bool = True, **kwargs: Any) -> None:
        """
        Initializes the instance of the class with specified parameters. Sets up default
        values for attributes and prepares the class for use.

        Args:
            use_unicode (bool): Determines whether Unicode encoding should be used. Defaults to True.
            **kwargs (Any): Additional keyword arguments to be passed to the superclass initializer.

        Attributes:
            use_unicode (bool): Determines whether Unicode encoding is used.
            handler (TuiPapyrusHandler | None): Handler for TUI operations, initialized as None.
            monitor_widget (PapyrusMonitorWidget | None): Widget for monitoring, initialized as None.
            output_viewer (OutputViewer | None): Viewer for output display, initialized as None.
            monitor_task (asyncio.Task | None): Async task for monitoring, initialized as None.
        """
        super().__init__(**kwargs)
        self.use_unicode = use_unicode
        self.handler: TuiPapyrusHandler | None = None
        self.monitor_widget: PapyrusMonitorWidget | None = None
        self.output_viewer: OutputViewer | None = None
        self.monitor_task: asyncio.Task | None = None
        self._background_tasks: set[asyncio.Task] = set()

    def compose(self) -> ComposeResult:
        """
        Generates and arranges UI components for a monitoring screen within an application.

        This method defines the UI layout and components needed for a monitoring interface. It includes
        a header, a vertical container for a title, a monitor widget, and an output viewer for raw log
        data. Additionally, a horizontal control bar is defined with buttons for managing monitoring
        operations such as start, refresh, clear, and close. A footer is included to complete the
        interface. Components use defined classes and IDs for identification and styling.

        Yields:
            ComposeResult: A generator yielding UI components arranged in the required hierarchy.
        """
        yield Header()

        with Vertical(id="papyrus-container"):
            # Title
            title_text = self._get_title_text()
            yield Static(title_text, classes="screen-title")

            # Monitor widget
            self.monitor_widget = PapyrusMonitorWidget(use_unicode=self.use_unicode, show_controls=False, id="monitor-widget")
            yield self.monitor_widget

            # Output viewer for raw log data
            yield Label("Raw Log Output:", classes="section-label")
            self.output_viewer = OutputViewer(id="log-output")
            yield self.output_viewer

        # Control bar
        with Horizontal(classes="control-bar"):
            yield Button("Start Monitoring", id="start-stop-btn", variant="success", classes="control-button")
            yield Button("Refresh", id="refresh-btn", variant="primary", classes="control-button")
            yield Button("Clear", id="clear-btn", variant="default", classes="control-button")
            yield Button("Close", id="close-btn", variant="warning", classes="control-button")
            yield Static(self._get_status_text(), id="status-indicator", classes="status-indicator stopped")

        yield Footer()

    def _get_title_text(self) -> str:
        """
        Generates the title text for the log monitoring system.

        This method determines the appropriate title format based on the `use_unicode`
        flag. If the `use_unicode` attribute is set to True, the title includes emoji
        characters for visually enhanced display. Otherwise, it defaults to a plain
        text format for compatibility.

        Returns:
            str: The formatted title text.

        """
        if self.use_unicode:
            return "📊 PAPYRUS LOG MONITORING 📊"
        return "=== PAPYRUS LOG MONITORING ==="

    def _get_status_text(self) -> str:
        """
        Generates the status text based on the monitoring state and Unicode usage.

        Determines the appropriate status text to display depending on whether
        the monitoring is active and if Unicode symbols are enabled.

        Returns:
            str: The textual representation of the current monitoring status.
        """
        if self.is_monitoring:
            if self.use_unicode:
                return "● MONITORING"
            return "[*] MONITORING"
        if self.use_unicode:
            return "○ STOPPED"
        return "[ ] STOPPED"

    async def on_mount(self) -> None:
        """Initialize the screen when mounted."""
        # Create the handler
        self.handler = TuiPapyrusHandler(stats_callback=self._on_stats_update, error_callback=self._on_error, use_unicode=self.use_unicode)

        # Auto-start monitoring
        await self.start_monitoring()

    def _on_stats_update(self, stats: PapyrusStats) -> None:
        """Handle stats updates from the handler.

        Args:
            stats: Updated statistics
        """
        if self.monitor_widget:
            self.monitor_widget.update_stats(stats)

        # Also show raw output in the viewer
        if self.output_viewer and stats.raw_output:
            # Clear and show latest output
            self.output_viewer.clear()
            self.output_viewer.append_output(stats.raw_output)

    def _on_error(self, error_msg: str) -> None:
        """Handle error messages from the handler.

        Args:
            error_msg: Error message to display
        """
        if self.output_viewer:
            error_prefix = "❌" if self.use_unicode else "[ERROR]"
            self.output_viewer.append_output(f"\n{error_prefix} {error_msg}\n")

    async def start_monitoring(self) -> None:
        """Start Papyrus monitoring."""
        if self.handler and not self.handler.is_monitoring_active():
            success = await self.handler.start_monitoring()
            if success:
                self.is_monitoring = True
                self._update_ui_state()
                if self.monitor_widget:
                    self.monitor_widget.set_monitoring_state(True)

    async def stop_monitoring(self) -> None:
        """Stop Papyrus monitoring."""
        if self.handler:
            await self.handler.stop_monitoring()
            self.is_monitoring = False
            self._update_ui_state()
            if self.monitor_widget:
                self.monitor_widget.set_monitoring_state(False)

    def _update_ui_state(self) -> None:
        """Update UI elements based on monitoring state."""
        try:
            # Update start/stop button
            btn = self.query_one("#start-stop-btn", Button)
            if self.is_monitoring:
                btn.label = "Stop Monitoring"
                btn.variant = "error"
            else:
                btn.label = "Start Monitoring"
                btn.variant = "success"

            # Update status indicator
            indicator = self.query_one("#status-indicator", Static)
            indicator.update(self._get_status_text())
            if self.is_monitoring:
                indicator.add_class("active")
                indicator.remove_class("stopped")
            else:
                indicator.add_class("stopped")
                indicator.remove_class("active")

        except (LookupError, AttributeError):
            # UI might not be fully composed yet or widgets not found
            pass

    async def action_toggle_monitoring(self) -> None:
        """Toggle monitoring on/off."""
        if self.is_monitoring:
            await self.stop_monitoring()
        else:
            await self.start_monitoring()

    async def action_refresh_stats(self) -> None:
        """Manually refresh statistics."""
        if self.handler and self.handler.is_monitoring_active():
            # Force a refresh by restarting monitoring
            await self.stop_monitoring()
            await self.start_monitoring()

    def action_clear_output(self) -> None:
        """Clear the output viewer."""
        if self.output_viewer:
            self.output_viewer.clear()
        if self.monitor_widget:
            self.monitor_widget.clear_stats()

    # noinspection PyProtectedMember
    def action_toggle_unicode(self) -> None:
        """Toggle between Unicode and ASCII display."""
        self.use_unicode = not self.use_unicode

        # Update handler
        if self.handler:
            self.handler.set_unicode_mode(self.use_unicode)

        # Update monitor widget
        if self.monitor_widget:
            self.monitor_widget.use_unicode = self.use_unicode
            self.monitor_widget._update_display()

        # Update title
        try:
            title = self.query_one(".screen-title", Static)
            title.update(self._get_title_text())
        except (LookupError, AttributeError):
            # Widget might not be ready or query failed
            pass

        # Update status indicator
        self._update_ui_state()

    async def action_close_screen(self) -> None:
        """Close the screen and return to main."""
        await self.stop_monitoring()
        await self.app.pop_screen()

    async def action_stop_and_close(self) -> None:
        """Stop monitoring and close screen."""
        await self.stop_monitoring()
        await self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "start-stop-btn":
            self.app.call_later(self.action_toggle_monitoring)
        elif button_id == "refresh-btn":
            self.app.call_later(self.action_refresh_stats)
        elif button_id == "clear-btn":
            self.action_clear_output()
        elif button_id == "close-btn":
            self.app.call_later(self.action_close_screen)

    def on_papyrus_monitor_widget_monitoring_toggled(self) -> None:
        """Handle monitoring toggle from widget."""
        self.app.call_later(self.action_toggle_monitoring)

    def on_papyrus_monitor_widget_refresh_requested(self) -> None:
        """Handle refresh request from widget."""
        self.app.call_later(self.action_refresh_stats)

    def on_unmount(self) -> None:
        """Clean up when screen is unmounted."""
        # Schedule async cleanup
        if self.handler and self.handler.is_monitoring_active():
            # Create a task to stop monitoring properly and store reference
            task = asyncio.create_task(self._async_cleanup())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    async def _async_cleanup(self) -> None:
        """Async cleanup helper."""
        with contextlib.suppress(OSError, RuntimeError, asyncio.CancelledError):
            # Ignore specific errors during cleanup:
            # OSError: File/resource access issues
            # RuntimeError: Event loop or async operation issues
            # CancelledError: Task cancellation during shutdown
            await self.stop_monitoring()
