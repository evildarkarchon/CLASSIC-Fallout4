"""Scan button widgets for TUI."""

import asyncio

from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button


class ScanButton(Button):
    """Scan operation trigger button with progress support."""

    BINDINGS = [
        Binding("enter", "activate", "Activate", show=False),
        Binding("space", "activate", "Activate", show=False),
    ]

    scanning = reactive(False)
    progress = reactive(0.0)

    class ScanStarted(Message):
        """Message sent when scan starts."""

        def __init__(self, scan_type: str) -> None:
            super().__init__()
            self.scan_type = scan_type

    class ScanCompleted(Message):
        """Message sent when scan completes."""

        def __init__(self, scan_type: str, success: bool) -> None:
            super().__init__()
            self.scan_type = scan_type
            self.success = success

    def __init__(self, label: str, scan_type: str = "generic", *args, **kwargs) -> None:
        super().__init__(label, *args, **kwargs)
        self.scan_type = scan_type
        self.original_label = label
        self._scan_task: asyncio.Task | None = None

    def on_button_pressed(self) -> None:
        """Handle button press."""
        if not self.scanning:
            self.start_scan()

    def start_scan(self) -> None:
        """Start the scan operation."""
        if self.scanning:
            return

        self.scanning = True
        self.progress = 0.0
        self.disabled = True
        self.label = f"{self.original_label} (0%)"
        self.add_class("scanning")

        # Post scan started message
        self.post_message(self.ScanStarted(self.scan_type))

    def update_progress(self, progress: float) -> None:
        """Update scan progress."""
        self.progress = min(max(progress, 0.0), 1.0)
        percentage = int(self.progress * 100)
        self.label = f"{self.original_label} ({percentage}%)"

    def complete_scan(self, success: bool = True) -> None:
        """Complete the scan operation."""
        self.scanning = False
        self.progress = 0.0
        self.disabled = False

        if success:
            self.label = f"✓ {self.original_label}"
            self.add_class("success")
        else:
            self.label = f"✗ {self.original_label}"
            self.add_class("error")

        self.remove_class("scanning")

        # Post scan completed message
        self.post_message(self.ScanCompleted(self.scan_type, success))

        # Reset label after 2 seconds
        self.set_timer(2.0, self._reset_label)

    def _reset_label(self) -> None:
        """Reset button label to original."""
        self.label = self.original_label
        self.remove_class("success", "error")

    def cancel_scan(self) -> None:
        """Cancel the current scan."""
        if self._scan_task and not self._scan_task.done():
            self._scan_task.cancel()

        self.scanning = False
        self.progress = 0.0
        self.disabled = False
        self.label = self.original_label
        self.remove_class("scanning", "success", "error")

    def action_activate(self) -> None:
        """Activate button with keyboard (Enter/Space)."""
        if not self.disabled and not self.scanning:
            self.start_scan()

    def on_key(self, event) -> None:
        """Handle keyboard events."""
        # Allow cancellation with Escape during scan
        if event.key == "escape" and self.scanning:
            self.cancel_scan()
            event.stop()
