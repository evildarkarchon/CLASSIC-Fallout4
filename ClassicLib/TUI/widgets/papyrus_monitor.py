"""Papyrus monitoring widget for TUI."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Label, Static

from ..handlers.papyrus_handler import PapyrusStats


class PapyrusMonitorWidget(Widget):
    """Widget for displaying Papyrus log monitoring statistics."""

    DEFAULT_CSS = """
    PapyrusMonitorWidget {
        layout: vertical;
        height: auto;
        min-height: 15;
        padding: 1;
        border: solid $primary;
    }
    
    PapyrusMonitorWidget:focus {
        border: solid $accent;
    }
    
    .papyrus-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    .papyrus-stats {
        layout: grid;
        grid-size: 2 5;
        grid-gutter: 1 2;
        margin: 0 1;
    }
    
    .stat-label {
        text-align: right;
        color: $text-muted;
    }
    
    .stat-value {
        text-align: left;
        text-style: bold;
    }
    
    .stat-value.normal {
        color: $success;
    }
    
    .stat-value.warning {
        color: $warning;
    }
    
    .stat-value.error {
        color: $error;
    }
    
    .papyrus-status {
        margin-top: 1;
        padding: 1;
        text-align: center;
        border: solid $primary;
    }
    
    .papyrus-status.monitoring {
        background: $panel;
        border: solid $success;
        color: $success;
    }
    
    .papyrus-status.error {
        background: $panel;
        border: solid $error;
        color: $error;
    }
    
    .papyrus-status.warning {
        background: $panel;
        border: solid $warning;
        color: $warning;
    }
    
    .papyrus-timestamp {
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }
    
    .papyrus-controls {
        layout: horizontal;
        align: center middle;
        margin-top: 1;
        height: 3;
    }
    """

    BINDINGS = [
        Binding("r", "refresh", "Refresh Stats", show=False),
        Binding("s", "toggle_monitoring", "Start/Stop", show=False),
        Binding("c", "clear_stats", "Clear", show=False),
    ]

    # Reactive attributes
    dumps = reactive(0)
    stacks = reactive(0)
    warnings = reactive(0)
    errors = reactive(0)
    ratio = reactive(0.0)
    is_monitoring = reactive(False)
    last_update = reactive("")
    use_unicode = reactive(True)

    def __init__(self, use_unicode: bool = True, show_controls: bool = True, **kwargs):
        """Initialize the Papyrus monitor widget.

        Args:
            use_unicode: Whether to use Unicode symbols
            show_controls: Whether to show control buttons
        """
        super().__init__(**kwargs)
        self.use_unicode = use_unicode
        self.show_controls = show_controls
        self.last_stats: PapyrusStats | None = None

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        yield Label(self._get_title(), classes="papyrus-title")

        with Container(classes="papyrus-stats"):
            # Row 1: Dumps
            yield Label("Dumps:", classes="stat-label")
            yield Label(str(self.dumps), id="dumps-value", classes="stat-value normal")

            # Row 2: Stacks
            yield Label("Stacks:", classes="stat-label")
            yield Label(str(self.stacks), id="stacks-value", classes="stat-value normal")

            # Row 3: Ratio
            yield Label("Ratio:", classes="stat-label")
            yield Label(f"{self.ratio:.3f}", id="ratio-value", classes="stat-value normal")

            # Row 4: Warnings
            yield Label("Warnings:", classes="stat-label")
            yield Label(str(self.warnings), id="warnings-value", classes="stat-value normal")

            # Row 5: Errors
            yield Label("Errors:", classes="stat-label")
            yield Label(str(self.errors), id="errors-value", classes="stat-value normal")

        yield Static(self._get_status_text(), id="status-box", classes="papyrus-status monitoring")
        yield Label(self.last_update, id="timestamp", classes="papyrus-timestamp")

        if self.show_controls:
            with Horizontal(classes="papyrus-controls"):
                yield Button("Start", id="toggle-btn", variant="success")
                yield Button("Refresh", id="refresh-btn", variant="primary")
                yield Button("Clear", id="clear-btn", variant="default")

    def _get_title(self) -> str:
        """Get the title with appropriate symbol."""
        if self.use_unicode:
            return "📊 Papyrus Log Monitor"
        return "[=] Papyrus Log Monitor"

    def _get_status_text(self) -> str:
        """Get status text based on current state."""
        if not self.is_monitoring:
            return "Monitoring Stopped"

        if self.last_stats:
            symbol = self.last_stats.get_status_symbol(self.use_unicode)
            return f"{symbol} Monitoring Active"
        return "Waiting for data..."

    def _get_status_class(self) -> str:
        """Get CSS class for status box based on stats."""
        if not self.is_monitoring:
            return "papyrus-status"

        if self.last_stats:
            color = self.last_stats.get_status_color()
            if color == "red":
                return "papyrus-status error"
            if color == "yellow":
                return "papyrus-status warning"

        return "papyrus-status monitoring"

    def update_stats(self, stats: PapyrusStats) -> None:
        """Update displayed statistics.

        Args:
            stats: The new statistics to display
        """
        self.last_stats = stats
        self.dumps = stats.dumps
        self.stacks = stats.stacks
        self.warnings = stats.warnings
        self.errors = stats.errors
        self.ratio = stats.ratio
        self.last_update = stats.timestamp.strftime("%H:%M:%S")

        # Update display elements
        self._update_display()

    def _update_display(self) -> None:
        """Update the display elements with current values."""
        try:
            # Update values
            self.query_one("#dumps-value", Label).update(str(self.dumps))
            self.query_one("#stacks-value", Label).update(str(self.stacks))
            self.query_one("#ratio-value", Label).update(f"{self.ratio:.3f}")
            self.query_one("#warnings-value", Label).update(str(self.warnings))
            self.query_one("#errors-value", Label).update(str(self.errors))
            self.query_one("#timestamp", Label).update(f"Last Update: {self.last_update}")

            # Update status box
            status_box = self.query_one("#status-box", Static)
            status_box.update(self._get_status_text())

            # Update CSS classes based on values
            self._update_value_styles()

            # Update status box class
            status_box.set_class(self._get_status_class())

        except Exception:
            # Widget might not be fully composed yet
            pass

    def _get_severity_class(self, value: float, warning_threshold: float, error_threshold: float) -> str:
        """Get severity class based on value and thresholds.

        Args:
            value: The value to check
            warning_threshold: Threshold for warning level
            error_threshold: Threshold for error level

        Returns:
            CSS class name: "normal", "warning", or "error"
        """
        if value > error_threshold:
            return "error"
        if value > warning_threshold:
            return "warning"
        return "normal"

    def _update_value_styles(self) -> None:
        """Update value label styles based on thresholds."""
        try:
            # Define thresholds for each metric
            thresholds = {
                "#dumps-value": (self.dumps, 5, 10),
                "#warnings-value": (self.warnings, 20, 50),
                "#errors-value": (self.errors, 5, 10),
                "#ratio-value": (self.ratio, 0.2, 0.5),
            }

            # Batch update all labels efficiently
            for selector, (value, warn_threshold, error_threshold) in thresholds.items():
                label = self.query_one(selector, Label)
                severity_class = self._get_severity_class(value, warn_threshold, error_threshold)

                # Set classes in one operation instead of multiple add/remove calls
                label.set_classes(f"stat-value {severity_class}")

        except Exception:
            # Widget might not be fully composed yet
            pass

    def set_monitoring_state(self, is_monitoring: bool) -> None:
        """Set the monitoring state.

        Args:
            is_monitoring: Whether monitoring is active
        """
        self.is_monitoring = is_monitoring
        self._update_display()

        # Update toggle button if present
        if self.show_controls:
            try:
                toggle_btn = self.query_one("#toggle-btn", Button)
                if is_monitoring:
                    toggle_btn.label = "Stop"
                    toggle_btn.variant = "error"
                else:
                    toggle_btn.label = "Start"
                    toggle_btn.variant = "success"
            except Exception:
                pass

    def clear_stats(self) -> None:
        """Clear all statistics."""
        self.dumps = 0
        self.stacks = 0
        self.warnings = 0
        self.errors = 0
        self.ratio = 0.0
        self.last_update = ""
        self.last_stats = None
        self._update_display()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "toggle-btn":
            self.post_message(self.MonitoringToggled(self))
        elif event.button.id == "refresh-btn":
            self.post_message(self.RefreshRequested(self))
        elif event.button.id == "clear-btn":
            self.clear_stats()

    class MonitoringToggled(Message):
        """Message sent when monitoring is toggled."""

    class RefreshRequested(Message):
        """Message sent when refresh is requested."""

    def action_toggle_monitoring(self) -> None:
        """Toggle monitoring action."""
        self.post_message(self.MonitoringToggled(self))

    def action_refresh(self) -> None:
        """Refresh stats action."""
        self.post_message(self.RefreshRequested(self))

    def action_clear_stats(self) -> None:
        """Clear stats action."""
        self.clear_stats()
