"""Results viewer controller for CLASSIC interface.

This module provides the ResultsViewerController class that handles displaying
scan reports with markdown rendering and file watching for auto-refresh.

Example:
    >>> from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController
    >>> results_ctrl = ResultsViewerController(context)
    >>> results_ctrl.setup_results_tab()

"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QFileSystemWatcher, QPoint, Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ClassicLib.core.constants import YAML
from ClassicLib.core.logger import logger
from ClassicLib.core.registry import get_local_dir
from ClassicLib.integration.factory import is_component_available
from ClassicLib.Interface.widgets.ResultsViewerWidgets import (
    MarkdownViewer,
    ReportListWidget,
    ReportMetadataWidget,
)
from ClassicLib.core.async_bridge import AsyncBridge
from ClassicLib.integration.factory import get_file_io
from ClassicLib.io.yaml import classic_settings, yaml_settings
from ClassicLib.messaging import msg_error, msg_info, msg_warning

if TYPE_CHECKING:
    from ClassicLib.Interface.shared.context import FeatureContext


def _read_file(path: Path) -> str:
    """Read a file synchronously via AsyncBridge (GUI-only helper).

    Args:
        path: Path to the file to read.

    Returns:
        The file contents as a string.

    """
    io_core = get_file_io()
    return AsyncBridge.get_instance().run_async(io_core.read_file(path))


class ResultsViewerController:
    """Controller for the results viewer tab functionality.

    This controller manages the results viewer tab including:
    - Setting up the tab UI with report list and markdown viewer
    - Loading and displaying scan reports
    - File watching for auto-refresh on new reports
    - Context menu operations (view, copy, delete)

    Attributes:
        _ctx: The FeatureContext providing access to shared dependencies.
        _results_list: Widget displaying the list of reports.
        _markdown_viewer: Widget for rendering markdown content.
        _metadata_widget: Widget displaying report metadata.
        _file_watcher: File system watcher for directories.
        _refresh_timer: Timer for auto-refresh.
        _current_report_path: Path to currently loaded report.
        _file_watching_paused: Flag to pause file watching during scans.
        _refresh_pending: Flag for debounced refresh.

    Example:
        >>> controller = ResultsViewerController(context)
        >>> controller.setup_results_tab()
        >>> controller.refresh_reports_list()

    """

    def __init__(self, context: FeatureContext) -> None:
        """Initialize the ResultsViewerController.

        Args:
            context: FeatureContext providing access to main_window, signal_hub,
                and ui_widgets.

        """
        self._ctx = context

        # UI components (created during setup)
        self._results_list: ReportListWidget | None = None
        self._markdown_viewer: MarkdownViewer | None = None
        self._metadata_widget: ReportMetadataWidget | None = None
        self._file_watcher: QFileSystemWatcher | None = None
        self._refresh_timer: QTimer | None = None

        # State
        self._current_report_path: Path | None = None
        self._file_watching_paused = False
        self._refresh_pending = False

        # Connect to SignalHub signals
        self._ctx.signal_hub.pause_file_watching.connect(self._pause_file_watching)
        self._ctx.signal_hub.resume_file_watching.connect(self._resume_file_watching)
        self._ctx.signal_hub.refresh_reports_requested.connect(self.refresh_reports_list)

    def setup_results_tab(self) -> None:
        """Set up the results tab UI.

        Creates the main layout with a splitter containing the reports list
        panel and the viewer panel. Also initializes file watching and
        auto-refresh if enabled.
        """
        results_tab = self._ctx.ui_widgets.results_tab
        if results_tab is None:
            logger.warning("Results tab widget not found")
            return

        # Create main layout
        layout = QHBoxLayout(results_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left panel - reports list
        left_panel = self._create_reports_panel()

        # Right panel - viewer
        right_panel = self._create_viewer_panel()

        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)

        # Set initial sizes (30% for list, 70% for viewer)
        splitter.setSizes([300, 700])

        # Add splitter to main layout
        layout.addWidget(splitter)

        # Initialize file watcher for auto-refresh
        self._file_watcher = QFileSystemWatcher()
        self._file_watcher.directoryChanged.connect(self._on_directory_changed)

        # Setup refresh timer
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self.refresh_reports_list)

        # Initial scan for reports
        self.refresh_reports_list()

        # Setup auto-refresh if enabled
        self._setup_auto_refresh()

        # Log Rust acceleration status
        if is_component_available("classic_file_io"):
            logger.info("Results viewer using Rust-accelerated file I/O (10x faster)")
        else:
            logger.debug("Results viewer using Python file I/O implementation")

        logger.debug("Results viewer tab initialized")

    def _create_reports_panel(self) -> QWidget:
        """Create the reports list panel.

        Returns:
            QWidget containing the reports list and action buttons.

        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Create reports list widget
        try:
            self._results_list = ReportListWidget()
            self._results_list.itemSelectionChanged.connect(self._on_report_selected)
            logger.info("ReportListWidget created successfully")
        except Exception as e:
            logger.error(f"Failed to create ReportListWidget: {e}", exc_info=True)
            raise

        self._results_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._results_list.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self._results_list)

        # Create button bar
        button_bar = QWidget()
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(5)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_reports_list)
        refresh_btn.setToolTip("Refresh the reports list")
        button_layout.addWidget(refresh_btn)

        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._delete_selected_report)
        delete_btn.setToolTip("Delete the selected report")
        button_layout.addWidget(delete_btn)

        # Open folder button
        folder_btn = QPushButton("Open Folder")
        folder_btn.clicked.connect(self._open_reports_folder)
        folder_btn.setToolTip("Open the Crash Logs folder")
        button_layout.addWidget(folder_btn)

        button_layout.addStretch()

        layout.addWidget(button_bar)

        return panel

    def _create_viewer_panel(self) -> QWidget:
        """Create the viewer panel with markdown display and controls.

        Returns:
            QWidget containing the metadata, viewer, and toolbar.

        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Create metadata widget
        self._metadata_widget = ReportMetadataWidget()
        layout.addWidget(self._metadata_widget)

        # Create markdown viewer
        try:
            self._markdown_viewer = MarkdownViewer()
            layout.addWidget(self._markdown_viewer)
            logger.info("MarkdownViewer created successfully")
        except Exception as e:
            logger.error(f"Failed to create MarkdownViewer: {e}", exc_info=True)
            raise

        # Create viewer toolbar
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(5)

        # Copy button
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(self._copy_report)
        copy_btn.setToolTip("Copy report to clipboard")
        toolbar_layout.addWidget(copy_btn)

        toolbar_layout.addStretch()

        # Zoom controls
        zoom_out_btn = QPushButton("-")
        zoom_out_btn.clicked.connect(self._markdown_viewer.zoom_out)
        zoom_out_btn.setFixedWidth(30)
        zoom_out_btn.setToolTip("Zoom out")
        toolbar_layout.addWidget(zoom_out_btn)

        zoom_reset_btn = QPushButton("100%")
        zoom_reset_btn.clicked.connect(self._markdown_viewer.reset_zoom)
        zoom_reset_btn.setFixedWidth(50)
        zoom_reset_btn.setToolTip("Reset zoom")
        toolbar_layout.addWidget(zoom_reset_btn)

        zoom_in_btn = QPushButton("+")
        zoom_in_btn.clicked.connect(self._markdown_viewer.zoom_in)
        zoom_in_btn.setFixedWidth(30)
        zoom_in_btn.setToolTip("Zoom in")
        toolbar_layout.addWidget(zoom_in_btn)

        layout.addWidget(toolbar)

        return panel

    def scan_for_reports(self) -> list[Path]:
        """Scan directories for report files.

        Searches for *-AUTOSCAN.md files in:
        - Crash Logs folder in local directory
        - Custom scan folder from settings
        - Backup location for unsolved logs

        Returns:
            Sorted list of unique report paths (descending by name).

        """
        reports: list[Path] = []

        # Primary location - Crash Logs folder
        local_dir = self._ctx.local_dir
        if local_dir:
            crash_logs_dir = Path(local_dir) / "Crash Logs"
            if crash_logs_dir.exists():
                reports.extend(crash_logs_dir.glob("*-AUTOSCAN.md"))

                # Add directory to file watcher
                if self._file_watcher and crash_logs_dir.as_posix() not in self._file_watcher.directories():
                    self._file_watcher.addPath(str(crash_logs_dir))

        # Custom scan folder from settings
        custom_path_str = classic_settings(str, "SCAN Custom Path")
        if custom_path_str:
            custom_path = Path(custom_path_str)
            if custom_path.exists() and custom_path.is_dir():
                reports.extend(custom_path.glob("*-AUTOSCAN.md"))

                if self._file_watcher and custom_path.as_posix() not in self._file_watcher.directories():
                    self._file_watcher.addPath(str(custom_path))

        # Backup location for unsolved logs
        if local_dir:
            backup_path = Path(local_dir) / "CLASSIC Backup" / "Unsolved Logs"
            if backup_path.exists():
                reports.extend(backup_path.glob("*-AUTOSCAN.md"))

        # Remove duplicates and sort by name (descending)
        unique_reports = list(set(reports))
        unique_reports.sort(key=lambda p: p.name, reverse=True)

        logger.debug(f"Found {len(unique_reports)} scan reports")
        return unique_reports

    def refresh_reports_list(self) -> None:
        """Refresh the reports list from disk.

        Clears the current list, scans for reports, and repopulates.
        Auto-selects the first report if none is currently selected.
        """
        if self._results_list is None or self._markdown_viewer is None:
            return

        # Clear current list
        self._results_list.clear()

        # Scan for reports
        reports = self.scan_for_reports()

        # Populate list
        self._results_list.populate_reports(reports)

        # Emit signal for count change
        self._ctx.signal_hub.reports_count_changed.emit(len(reports))

        # Update status
        if not reports:
            if self._metadata_widget:
                self._metadata_widget.clear()
            self._markdown_viewer.clear()
            self._markdown_viewer.setMarkdown(
                "# No Reports Found\n\nNo scan reports are available. Run a crash log scan to generate reports."
            )
        else:
            # Check if current report is still available
            current_still_exists = self._current_report_path and self._current_report_path in reports

            if not current_still_exists:
                self._markdown_viewer.clear()
                self._markdown_viewer.setMarkdown("# Reports Available\n\nSelect a report from the list to view its contents.")
                self._current_report_path = None

                # Auto-select the first report
                if self._results_list.count() > 0:
                    self._results_list.setCurrentRow(0)

        logger.info(f"Refreshed reports list: {len(reports)} reports found")

    def load_report(self, report_path: Path) -> bool:
        """Load and display a report file.

        Args:
            report_path: Path to the report file.

        Returns:
            True if loaded successfully, False otherwise.

        """
        if self._markdown_viewer is None or self._metadata_widget is None:
            return False

        logger.info(f"Loading report: {report_path}")

        try:
            if not report_path.exists():
                QTimer.singleShot(0, lambda: msg_error(f"Report file not found: {report_path.name}"))
                logger.error(f"Report file not found: {report_path}")
                return False

            # Read report content with Rust-accelerated file I/O
            content = _read_file(report_path)

            # Display in viewer
            self._markdown_viewer.setMarkdown(content)

            # Update metadata
            self._metadata_widget.update_metadata(report_path, content)

            # Store current report path
            self._current_report_path = report_path

            # Emit signal
            self._ctx.signal_hub.report_loaded.emit(report_path)

            logger.debug(f"Loaded report: {report_path.name}")

        except OSError as e:
            error_message = f"Failed to load report: {e}"
            QTimer.singleShot(0, lambda: msg_error(error_message))
            logger.error(f"Error loading report {report_path}: {e}", exc_info=True)

            # Try displaying as plain text
            try:
                content = _read_file(report_path)
                self._markdown_viewer.setPlainText(content)
                QTimer.singleShot(0, lambda: msg_warning("Displayed report as plain text due to markdown error"))
            except OSError as fallback_e:
                logger.error(f"Fallback plain text also failed: {fallback_e}")
                return False
        else:
            return True

        return True

    def _on_report_selected(self) -> None:
        """Handle report selection from the list."""
        if self._results_list is None:
            return

        selected_items = self._results_list.selectedItems()
        if not selected_items:
            logger.debug("No items selected")
            return

        item = selected_items[0]
        report_path = self._results_list.get_report_path(item)

        if report_path:
            self.load_report(report_path)
        else:
            msg_error(f"No report path found for: {item.text()}")
            logger.error(f"No report path found for selected item: {item.text()}")

    def _delete_selected_report(self) -> None:
        """Delete the currently selected report with confirmation."""
        if self._results_list is None:
            return

        selected_items = self._results_list.selectedItems()
        if not selected_items:
            msg_warning("No report selected")
            return

        item = selected_items[0]
        report_path = self._results_list.get_report_path(item)

        if not report_path:
            return

        results_tab = self._ctx.ui_widgets.results_tab

        # Confirmation dialog
        reply = QMessageBox.question(
            results_tab,
            "Delete Report",
            f"Are you sure you want to delete:\n{report_path.name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Also delete the original crash log if it exists
                crash_log_path = report_path.with_suffix(".log")

                # Delete report
                report_path.unlink()
                logger.info(f"Deleted report: {report_path.name}")

                # Delete crash log if it exists
                if crash_log_path.exists():
                    crash_log_path.unlink()
                    logger.info(f"Deleted crash log: {crash_log_path.name}")

                # Clear viewer if this was the current report
                if self._current_report_path == report_path:
                    if self._markdown_viewer:
                        self._markdown_viewer.clear()
                    if self._metadata_widget:
                        self._metadata_widget.clear()
                    self._current_report_path = None

                # Refresh list
                self.refresh_reports_list()

                msg_info(f"Report deleted: {report_path.name}")

            except OSError as e:
                msg_error(f"Failed to delete report: {e}")
                logger.error(f"Error deleting report {report_path}: {e}")

    def _copy_report(self) -> None:
        """Copy the current report content to clipboard."""
        if not self._current_report_path:
            msg_warning("No report loaded")
            return

        try:
            from PySide6.QtWidgets import QApplication

            content = _read_file(self._current_report_path)
            QApplication.clipboard().setText(content)
            msg_info("Report copied to clipboard")

        except (OSError, RuntimeError) as e:
            msg_error(f"Failed to copy report: {e}")
            logger.error(f"Error copying report: {e}")

    @staticmethod
    def _open_reports_folder() -> None:
        """Open the Crash Logs folder in the file explorer."""
        local_dir = get_local_dir()
        if not local_dir:
            msg_warning("Local directory not configured")
            return

        crash_logs_dir = Path(local_dir) / "Crash Logs"

        if not crash_logs_dir.exists():
            msg_warning("Crash Logs folder does not exist")
            return

        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices

            QDesktopServices.openUrl(QUrl.fromLocalFile(str(crash_logs_dir)))

        except (ImportError, RuntimeError, OSError) as e:
            msg_error(f"Failed to open folder: {e}")
            logger.error(f"Error opening folder: {e}")

    def _show_context_menu(self, position: QPoint) -> None:
        """Show context menu for report list."""
        if self._results_list is None:
            return

        item = self._results_list.itemAt(position)
        if not item:
            return

        menu = QMenu(self._results_list)

        # View action
        view_action = QAction("View Report", menu)
        view_action.triggered.connect(self._on_report_selected)
        menu.addAction(view_action)

        menu.addSeparator()

        # Copy action
        copy_action = QAction("Copy to Clipboard", menu)
        copy_action.triggered.connect(self._copy_report)
        menu.addAction(copy_action)

        menu.addSeparator()

        # Delete action
        delete_action = QAction("Delete", menu)
        delete_action.triggered.connect(self._delete_selected_report)
        menu.addAction(delete_action)

        menu.exec(self._results_list.mapToGlobal(position))

    def _on_directory_changed(self, path: str) -> None:
        """Handle directory change notifications from file watcher."""
        logger.debug(f"Directory changed: {path}")

        # Skip if file watching is paused
        if self._file_watching_paused:
            logger.debug("File watching paused, ignoring directory change")
            return

        # Debounce rapid changes
        if self._refresh_pending:
            return

        self._refresh_pending = True
        QTimer.singleShot(500, self._debounced_refresh)

    def _debounced_refresh(self) -> None:
        """Debounced refresh to avoid rapid updates."""
        self._refresh_pending = False
        self.refresh_reports_list()

    def _pause_file_watching(self) -> None:
        """Pause file watching during scans.

        This prevents I/O bottlenecks where each new report triggers
        refresh_reports_list() which reads ALL existing reports.
        """
        self._file_watching_paused = True
        logger.debug("File watching paused")

    def _resume_file_watching(self) -> None:
        """Resume file watching after scan completion."""
        self._file_watching_paused = False
        logger.debug("File watching resumed")

    def _setup_auto_refresh(self) -> None:
        """Set up auto-refresh based on settings."""
        if self._refresh_timer is None:
            return

        auto_refresh = yaml_settings(bool, YAML.Settings, "ResultsViewer.AutoRefresh", False)

        if auto_refresh:
            interval = yaml_settings(int, YAML.Settings, "ResultsViewer.RefreshInterval", 5000)
            if interval is not None:
                self._refresh_timer.start(interval)
            logger.debug(f"Auto-refresh enabled with interval: {interval}ms")
