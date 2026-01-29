"""Scan Progress Modal for CLASSIC TUI.

Modal overlay shown during scan operations with progress bar and cancel button.
"""

from typing import ClassVar, Literal

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ProgressBar, Static
from textual.worker import Worker, get_current_worker


class ScanProgressModal(ModalScreen[bool]):
    """Modal progress indicator for scan operations.

    Shows a progress bar with percentage, status text, and cancel button.
    Returns True if scan completed successfully, False if cancelled.

    Attributes:
        scan_type: Type of scan ("crash_logs" or "game_files").

    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    ScanProgressModal {
        align: center middle;
    }

    #progress-container {
        width: 60;
        height: auto;
        background: #2d2d2d;
        border: solid #3c3c3c;
        padding: 2;
    }

    #scan-title {
        text-style: bold;
        color: #4a9eff;
        text-align: center;
        margin-bottom: 1;
    }

    #progress-bar {
        margin: 1 0;
    }

    #status-text {
        text-align: center;
        margin-bottom: 1;
    }

    #file-counter {
        text-align: center;
        color: #808080;
        margin-bottom: 1;
    }

    #cancel-btn {
        margin-top: 1;
        width: 100%;
    }
    """

    def __init__(self, scan_type: Literal["crash_logs", "game_files"] = "crash_logs") -> None:
        """Initialize the scan progress modal.

        Args:
            scan_type: Type of scan to perform.

        """
        super().__init__()
        self.scan_type = scan_type
        self._worker: Worker[bool] | None = None
        self._cancel_requested = False

    def compose(self) -> ComposeResult:
        """Create the progress modal layout.

        Yields:
            Container with title, progress bar, status text, and cancel button.

        """
        title = "CRASH LOGS SCAN" if self.scan_type == "crash_logs" else "GAME FILES SCAN"

        with Vertical(id="progress-container"):
            yield Label(title, id="scan-title")
            yield ProgressBar(total=100, id="progress-bar")
            yield Static("Initializing scan...", id="status-text")
            yield Static("Files processed: 0 / 0", id="file-counter")
            yield Button("Cancel Scan", id="cancel-btn", variant="error")

    def on_mount(self) -> None:
        """Start the scan worker when modal is mounted."""
        self._start_scan()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle cancel button press.

        Args:
            event: The button pressed event.

        """
        if event.button.id == "cancel-btn":
            self.action_cancel()

    def action_cancel(self) -> None:
        """Request cancellation of the current scan."""
        self._cancel_requested = True
        self.query_one("#status-text", Static).update("Cancelling...")
        if self._worker:
            self._worker.cancel()
        self.dismiss(False)

    def _start_scan(self) -> None:
        """Start the appropriate scan worker."""
        if self.scan_type == "crash_logs":
            self._worker = self.run_worker(self._run_crash_scan, exclusive=True)
        else:
            self._worker = self.run_worker(self._run_game_scan, exclusive=True)

    async def _run_crash_scan(self) -> bool:
        """Run crash logs scan with progress updates.

        Returns:
            True if completed successfully, False if cancelled or error.

        """
        from ClassicLib.scanning.log import crash_logs_scan

        try:
            # Update UI to show scan is starting
            self.call_from_thread(self._update_status, "Scanning crash logs...", 0, 0)

            # Run the scan
            crash_logs_scan()

            # Check for cancellation
            worker = get_current_worker()
            if worker.is_cancelled:
                return False
        except (OSError, PermissionError, RuntimeError) as e:
            self.call_from_thread(self._update_status, f"Error: {e}", 0, 0)
            self.call_from_thread(self.dismiss, False)
            return False
        else:
            # Update to complete
            self.call_from_thread(self._update_status, "Scan complete!", 100, 0)
            self.call_from_thread(self.dismiss, True)
            return True

    async def _run_game_scan(self) -> bool:
        """Run game files scan with progress updates.

        Returns:
            True if completed successfully, False if cancelled or error.

        """
        from ClassicLib.scanning.game import game_files_scan

        try:
            # Update UI to show scan is starting
            self.call_from_thread(self._update_status, "Scanning game files...", 0, 0)

            # Run the scan
            game_files_scan()

            # Check for cancellation
            worker = get_current_worker()
            if worker.is_cancelled:
                return False
        except (OSError, PermissionError, RuntimeError) as e:
            self.call_from_thread(self._update_status, f"Error: {e}", 0, 0)
            self.call_from_thread(self.dismiss, False)
            return False
        else:
            # Update to complete
            self.call_from_thread(self._update_status, "Scan complete!", 100, 0)
            self.call_from_thread(self.dismiss, True)
            return True

    def _update_status(self, status: str, progress: float, total: int) -> None:
        """Update the progress display.

        Args:
            status: Current status message.
            progress: Progress percentage (0-100).
            total: Total files count.

        """
        self.query_one("#status-text", Static).update(status)
        self.query_one("#progress-bar", ProgressBar).progress = progress
        if total > 0:
            processed = int((progress / 100) * total)
            self.query_one("#file-counter", Static).update(f"Files processed: {processed} / {total}")
