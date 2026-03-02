"""Results Tab for CLASSIC TUI.

This tab provides a report browser with list selection and Markdown rendering.
"""

from datetime import UTC
from pathlib import Path
from typing import ClassVar, override

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, ListItem, ListView, Markdown, Static


class ResultsTab(Horizontal):
    """Results tab with split pane for report list and viewer.

    Provides:
        - Left panel: Selectable list of AUTOSCAN report files
        - Right panel: Markdown rendering of selected report
        - Action toolbar: Refresh, Delete, Copy, Open in Editor

    Keyboard shortcuts:
        - Ctrl+R: Refresh report list
        - Delete: Delete selected report
        - Ctrl+C: Copy report to clipboard
        - Ctrl+E: Open in external editor
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("ctrl+r", "refresh_reports", "Refresh"),
        Binding("delete", "delete_report", "Delete"),
        Binding("ctrl+c", "copy_report", "Copy"),
        Binding("ctrl+e", "open_external", "Open in Editor"),
    ]

    DEFAULT_CSS = """
    ResultsTab {
        padding: 1;
    }

    #report-list-panel {
        width: 30;
        border: solid #3c3c3c;
        margin-right: 1;
    }

    #report-list-header {
        text-style: bold;
        padding: 0 1;
        background: #3d3d3d;
    }

    #report-list {
        height: 1fr;
    }

    #report-list-actions {
        height: 3;
        dock: bottom;
        border-top: solid #3c3c3c;
    }

    #report-list-actions Button {
        margin: 0 1;
    }

    #report-viewer-panel {
        width: 1fr;
        border: solid #3c3c3c;
    }

    #report-filename {
        text-style: bold;
        padding: 0 1;
        background: #3d3d3d;
    }

    #report-metadata {
        padding: 0 1;
        color: #808080;
        border-bottom: solid #3c3c3c;
    }

    #report-content {
        height: 1fr;
        overflow-y: auto;
        padding: 1;
    }

    #viewer-actions {
        height: 3;
        dock: bottom;
        border-top: solid #3c3c3c;
    }
    """

    def __init__(self) -> None:
        """Initialize the ResultsTab."""
        super().__init__()
        self._reports: list[Path] = []
        self._current_report: Path | None = None

    @override
    def compose(self) -> ComposeResult:
        """Create the results tab layout.

        Yields:
            Left panel with report list, right panel with report viewer.

        """
        # Left Panel - Report List
        with Vertical(id="report-list-panel"):
            yield Label("AVAILABLE REPORTS", id="report-list-header")
            yield ListView(id="report-list")
            with Horizontal(id="report-list-actions"):
                yield Button("Refresh", id="btn-refresh")
                yield Button("Delete", id="btn-delete")

        # Right Panel - Report Viewer
        with Vertical(id="report-viewer-panel"):
            yield Label("Select a report to view", id="report-filename")
            yield Static("", id="report-metadata")
            yield Markdown("", id="report-content")
            with Horizontal(id="viewer-actions"):
                yield Button("Copy", id="btn-copy")
                yield Button("Open in Editor", id="btn-open-editor")

    def on_mount(self) -> None:
        """Load reports when tab is mounted."""
        self.refresh_reports()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle report selection from list.

        Args:
            event: The list view selection event.

        """
        if event.item.id and event.item.id.startswith("report-"):
            try:
                index = int(event.item.id.split("-")[1])
                if 0 <= index < len(self._reports):
                    self._load_report(self._reports[index])
            except (ValueError, IndexError):
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: The button pressed event.

        """
        button_id = event.button.id
        if button_id == "btn-refresh":
            self.action_refresh_reports()
        elif button_id == "btn-delete":
            self.action_delete_report()
        elif button_id == "btn-copy":
            self.action_copy_report()
        elif button_id == "btn-open-editor":
            self.action_open_external()

    def refresh_reports(self) -> None:
        """Scan for AUTOSCAN reports and populate the list."""
        self._reports = self._scan_for_reports()
        list_view = self.query_one("#report-list", ListView)
        list_view.clear()

        for i, report in enumerate(self._reports):
            # Truncate filename if too long
            name = report.stem
            if len(name) > 25:
                name = name[:22] + "..."
            list_view.append(ListItem(Label(name), id=f"report-{i}"))

    def action_refresh_reports(self) -> None:
        """Refresh the report list."""
        self.refresh_reports()
        self.notify("Report list refreshed")

    def action_delete_report(self) -> None:
        """Delete the currently selected report."""
        if self._current_report and self._current_report.exists():
            try:
                self._current_report.unlink()
                self.notify(f"Deleted: {self._current_report.name}")
                self._current_report = None
                self.refresh_reports()
                # Clear viewer
                self.query_one("#report-filename", Label).update("Select a report to view")
                self.query_one("#report-metadata", Static).update("")
                self.query_one("#report-content", Markdown).update("")
            except OSError as e:
                self.notify(f"Error deleting: {e}", severity="error")

    def action_copy_report(self) -> None:
        """Copy current report content to clipboard."""
        if self._current_report and self._current_report.exists():
            try:
                import pyclip

                content = self._current_report.read_text(encoding="utf-8", errors="ignore")
                pyclip.copy(content)
                self.notify("Report copied to clipboard")
            except ImportError:
                self.notify("Clipboard not available (pyclip not installed)", severity="warning")
            except (OSError, RuntimeError) as e:
                self.notify(f"Copy failed: {e}", severity="error")

    def action_open_external(self) -> None:
        """Open current report in external editor."""
        if self._current_report and self._current_report.exists():
            import subprocess
            import sys

            if sys.platform == "win32":
                subprocess.Popen(["notepad", str(self._current_report)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-e", str(self._current_report)])
            else:
                subprocess.Popen(["xdg-open", str(self._current_report)])

    @staticmethod
    def _scan_for_reports() -> list[Path]:
        """Scan standard locations for AUTOSCAN reports.

        Returns:
            List of report paths sorted by modification time (newest first).

        """
        from ClassicLib.TUI.test_mode import get_test_local_dir, is_test_mode

        if is_test_mode():
            local_dir = get_test_local_dir()
        else:
            from ClassicLib.core.registry import GlobalRegistry

            local_dir = GlobalRegistry.get_local_dir()

        from ClassicLib.io.yaml import classic_settings

        reports: list[Path] = []

        # Primary: Crash Logs folder
        crash_logs_dir = local_dir / "Crash Logs"
        if crash_logs_dir.exists():
            reports.extend(crash_logs_dir.glob("*-AUTOSCAN.md"))

        # Secondary: Custom scan folder (skip in test mode)
        if not is_test_mode():
            custom_path = classic_settings(str, "SCAN Custom Path")
            if custom_path:
                custom_dir = Path(custom_path)
                if custom_dir.exists():
                    reports.extend(custom_dir.glob("*-AUTOSCAN.md"))

        # Tertiary: Unsolved logs backup
        backup_path = local_dir / "CLASSIC Backup" / "Unsolved Logs"
        if backup_path.exists():
            reports.extend(backup_path.glob("*-AUTOSCAN.md"))

        # Deduplicate and sort by mtime descending
        unique_reports = list(set(reports))
        return sorted(unique_reports, key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)

    def _load_report(self, path: Path) -> None:
        """Load and display a report file.

        Args:
            path: Path to the report file to load.

        """
        from datetime import datetime

        self._current_report = path

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            stat = path.stat()

            # Update filename
            self.query_one("#report-filename", Label).update(path.name)

            # Update metadata
            modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC).strftime("%Y-%m-%d %H:%M")
            meta = f"Size: {stat.st_size:,} bytes  │  Modified: {modified}"
            self.query_one("#report-metadata", Static).update(meta)

            # Update content
            self.query_one("#report-content", Markdown).update(content)

        except (OSError, PermissionError, UnicodeDecodeError) as e:
            self.notify(f"Error loading report: {e}", severity="error")
