"""Status bar widget for displaying application state."""

from datetime import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label

from ClassicLib.YamlSettingsCache import classic_settings


class StatusBar(Widget):
    """Status bar showing current operation status and system state."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $panel;
        padding: 0 1;
    }
    
    StatusBar Horizontal {
        height: 1;
        width: 100%;
    }
    
    StatusBar .status-item {
        margin: 0 2;
    }
    
    StatusBar .status-label {
        color: $primary;
        text-style: bold;
    }
    
    StatusBar .status-value {
        color: $text;
    }
    
    StatusBar .status-active {
        color: $success;
    }
    
    StatusBar .status-error {
        color: $error;
    }
    
    StatusBar .status-warning {
        color: $warning;
    }
    """

    current_status = reactive("Ready")
    last_scan_time = reactive("")
    scan_folder = reactive("")
    is_scanning = reactive(False)
    papyrus_monitoring = reactive(False)
    papyrus_stats = reactive("")

    def compose(self) -> ComposeResult:
        """Compose the status bar layout."""
        with Horizontal():
            with Horizontal(classes="status-item"):
                yield Label("Status: ", classes="status-label")
                yield Label(self.current_status, id="status-text", classes="status-value")

            with Horizontal(classes="status-item"):
                yield Label("Last Scan: ", classes="status-label")
                yield Label(self.last_scan_time or "Never", id="last-scan", classes="status-value")

            with Horizontal(classes="status-item"):
                yield Label("Folder: ", classes="status-label")
                yield Label(self._get_display_folder(), id="scan-folder", classes="status-value")

            with Horizontal(classes="status-item"):
                yield Label("Papyrus: ", classes="status-label")
                yield Label(self._get_papyrus_status(), id="papyrus-status", classes="status-value")

    def _get_display_folder(self) -> str:
        """Get the display text for the current scan folder."""
        if not self.scan_folder:
            try:
                folder = classic_settings(str, "CustomScanFolder")
                if folder and Path(folder).exists():
                    return Path(folder).name
            except:
                pass
            return "Not Set"
        return Path(self.scan_folder).name if self.scan_folder else "Not Set"

    def _get_papyrus_status(self) -> str:
        """Get the Papyrus monitoring status text."""
        if self.papyrus_monitoring:
            if self.papyrus_stats:
                return f"Active {self.papyrus_stats}"
            return "Active"
        return "Inactive"

    def watch_current_status(self, old_status: str, new_status: str) -> None:
        """React to status changes."""
        try:
            status_label = self.query_one("#status-text", Label)
            status_label.update(new_status)

            # Update status color based on state
            if "Error" in new_status:
                status_label.add_class("status-error")
                status_label.remove_class("status-active", "status-warning")
            elif "Warning" in new_status:
                status_label.add_class("status-warning")
                status_label.remove_class("status-active", "status-error")
            elif new_status in ["Scanning...", "Processing..."]:
                status_label.add_class("status-active")
                status_label.remove_class("status-error", "status-warning")
            else:
                status_label.remove_class("status-active", "status-error", "status-warning")
        except:
            # Widget not yet composed, ignore
            pass

    def watch_last_scan_time(self, old_time: str, new_time: str) -> None:
        """React to last scan time changes."""
        try:
            scan_label = self.query_one("#last-scan", Label)
            scan_label.update(new_time or "Never")
        except:
            # Widget not yet composed, ignore
            pass

    def watch_scan_folder(self, old_folder: str, new_folder: str) -> None:
        """React to scan folder changes."""
        try:
            folder_label = self.query_one("#scan-folder", Label)
            folder_label.update(self._get_display_folder())
        except:
            # Widget not yet composed, ignore
            pass

    def update_status(self, status: str, is_error: bool = False) -> None:
        """Update the current status text."""
        self.current_status = status
        self.is_scanning = "Scanning" in status or "Processing" in status

    def mark_scan_complete(self, success: bool = True) -> None:
        """Mark a scan as complete and update the last scan time."""
        self.last_scan_time = datetime.now().strftime("%H:%M:%S")
        if success:
            self.current_status = "Ready"
        else:
            self.current_status = "Ready (Last scan had errors)"

    def set_scan_folder(self, folder: str) -> None:
        """Set the current scan folder."""
        self.scan_folder = folder

    def watch_papyrus_monitoring(self, old_state: bool, new_state: bool) -> None:
        """React to Papyrus monitoring state changes."""
        try:
            papyrus_label = self.query_one("#papyrus-status", Label)
            papyrus_label.update(self._get_papyrus_status())

            # Update color based on state
            if new_state:
                papyrus_label.add_class("status-active")
                papyrus_label.remove_class("status-error")
            else:
                papyrus_label.remove_class("status-active")
        except:
            # Widget not yet composed, ignore
            pass

    def watch_papyrus_stats(self, old_stats: str, new_stats: str) -> None:
        """React to Papyrus stats changes."""
        try:
            papyrus_label = self.query_one("#papyrus-status", Label)
            papyrus_label.update(self._get_papyrus_status())
        except:
            # Widget not yet composed, ignore
            pass

    def set_papyrus_monitoring(self, is_active: bool, stats: str = "") -> None:
        """Set the Papyrus monitoring state.

        Args:
            is_active: Whether monitoring is active
            stats: Optional stats summary string
        """
        self.papyrus_monitoring = is_active
        self.papyrus_stats = stats

    def update_papyrus_stats(self, dumps: int = 0, errors: int = 0, warnings: int = 0) -> None:
        """Update Papyrus stats display.

        Args:
            dumps: Number of dumps
            errors: Number of errors
            warnings: Number of warnings
        """
        if dumps > 0 or errors > 0 or warnings > 0:
            self.papyrus_stats = f"(D:{dumps} E:{errors} W:{warnings})"
        else:
            self.papyrus_stats = ""
