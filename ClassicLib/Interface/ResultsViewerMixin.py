"""
Results viewer functionality for displaying scan reports.

This module provides a mixin class for viewing and managing CLASSIC scan reports
in a dedicated tab with markdown rendering support.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QFileSystemWatcher, QPoint, Qt, QTimer, Signal
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

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML

# Import Rust-accelerated file I/O
from ClassicLib.FileIO import read_file_sync
from ClassicLib.integration.status import is_rust_accelerated

# Import the widget classes from ResultsViewerWidgets
from ClassicLib.Interface.ResultsViewerWidgets import (
    MarkdownViewer,  # noqa: TC001
    ReportListWidget,  # noqa: TC001
    ReportMetadataWidget,  # noqa: TC001
)
from ClassicLib.Logger import logger
from ClassicLib.MessageHandler import msg_error, msg_info, msg_warning
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


class ResultsViewerMixin:
    """
    Provides functionality for viewing and managing results or scan reports in a tab interface.

    ResultsViewerMixin contains utilities for displaying a list of reports, viewing report contents
    in markdown format, and managing report files. It handles initializing interface components,
    loading reports, refreshing the report list, and interacting with file system events via
    directory watching. This mixin is designed to be used within a graphical interface.

    Attributes:
        results_tab (QWidget): Widget serving as the main container for the results viewer tab.
        results_list (ReportListWidget): List widget displaying the available scan reports.
        markdown_viewer (MarkdownViewer): Viewer widget for rendering and displaying markdown content.
        metadata_widget (ReportMetadataWidget): Widget for displaying metadata of selected reports.
        file_watcher (QFileSystemWatcher): File watcher for monitoring directories for new or updated reports.
        refresh_timer (QTimer): Timer for periodically refreshing the reports list.
        current_report_path (Path | None): Path to the currently loaded report file, or None if no report is loaded.

    Signals:
        report_loaded (Path): Emitted when a report is successfully loaded, with the loaded report's path.
        reports_refreshed (int): Emitted when the reports list is refreshed, indicating the number of reports found.
    """

    # Type stubs for attributes that must be provided by the mixing class
    if TYPE_CHECKING:
        results_tab: QWidget
        results_list: ReportListWidget
        markdown_viewer: MarkdownViewer
        metadata_widget: ReportMetadataWidget
        file_watcher: QFileSystemWatcher
        refresh_timer: QTimer
        current_report_path: Path | None

    # Signals for inter-component communication
    report_loaded = Signal(Path)
    reports_refreshed = Signal(int)  # Number of reports found

    def setup_results_tab(self) -> None:
        """
        Sets up the results tab with a layout and functionality for displaying and managing
        reports.

        This method initializes the user interface elements, creates panels for report display
        and a viewer, and includes functionalities for refreshing the list of reports
        automatically when the associated directory changes. It also configures a timer
        to periodically refresh the reports list if auto-refresh is enabled.
        """

        # Create main layout
        layout = QHBoxLayout(self.results_tab)
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
        self.file_watcher = QFileSystemWatcher()
        self.file_watcher.directoryChanged.connect(self._on_directory_changed)

        # Setup refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_reports_list)

        # Initialize file watching state
        self._file_watching_paused = False
        self._refresh_pending = False

        # Initialize current report path
        self.current_report_path = None

        # Initial scan for reports
        self.refresh_reports_list()

        # Setup auto-refresh if enabled
        self._setup_auto_refresh()

        # Log Rust acceleration status for file I/O operations
        if is_rust_accelerated("file_io"):
            logger.info("Results viewer using Rust-accelerated file I/O (10x faster)")
        else:
            logger.debug("Results viewer using Python file I/O implementation")

        logger.debug("Results viewer tab initialized")

    def _create_reports_panel(self) -> QWidget:
        """
        Creates a reports panel containing a list widget to display reports and a button bar
        for additional actions like refreshing, deleting, and opening the reports folder.

        The panel includes:
        - A list widget (`ReportListWidget`) for displaying reports, allowing item selection
          and interaction via a context menu.
        - A button bar with buttons for refreshing the list, deleting a selected report,
          and opening the folder containing the crash logs.

        Returns:
            QWidget: The constructed reports panel containing the reports list and button bar.
        """
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Create reports list widget
        try:
            self.results_list = ReportListWidget()
            self.results_list.itemSelectionChanged.connect(self._on_report_selected)
            logger.info("ReportListWidget created successfully")
        except Exception as e:
            logger.error(f"Failed to create ReportListWidget: {e}", exc_info=True)
            raise
        self.results_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_list.customContextMenuRequested.connect(self._show_context_menu)

        # Add list to layout
        layout.addWidget(self.results_list)

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

    # noinspection PyUnresolvedReferences
    def _create_viewer_panel(self) -> QWidget:
        """
        Creates and returns a viewer panel containing a metadata widget, markdown
        viewer, and a toolbar with various controls.

        The panel includes:
        - A metadata widget for displaying report metadata.
        - A markdown viewer for rendering markdown content.
        - A toolbar for interactions such as copying the report to the clipboard
          and zoom controls for the markdown viewer.

        Returns:
            QWidget: A fully constructed viewer panel containing the components
            described above.
        """
        from ClassicLib.Interface.ResultsViewerWidgets import MarkdownViewer, ReportMetadataWidget

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Create metadata widget
        self.metadata_widget = ReportMetadataWidget()
        layout.addWidget(self.metadata_widget)

        # Create markdown viewer
        try:
            self.markdown_viewer = MarkdownViewer()
            # Don't set any initial content - let refresh_reports_list handle it
            layout.addWidget(self.markdown_viewer)
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
        zoom_out_btn = QPushButton("−")  # noqa: RUF001
        zoom_out_btn.clicked.connect(self.markdown_viewer.zoom_out)
        zoom_out_btn.setFixedWidth(30)
        zoom_out_btn.setToolTip("Zoom out")
        toolbar_layout.addWidget(zoom_out_btn)

        zoom_reset_btn = QPushButton("100%")
        zoom_reset_btn.clicked.connect(self.markdown_viewer.reset_zoom)
        zoom_reset_btn.setFixedWidth(50)
        zoom_reset_btn.setToolTip("Reset zoom")
        toolbar_layout.addWidget(zoom_reset_btn)

        zoom_in_btn = QPushButton("+")
        zoom_in_btn.clicked.connect(self.markdown_viewer.zoom_in)
        zoom_in_btn.setFixedWidth(30)
        zoom_in_btn.setToolTip("Zoom in")
        toolbar_layout.addWidget(zoom_in_btn)

        layout.addWidget(toolbar)

        return panel

    def scan_for_reports(self) -> list[Path]:
        """
        Scans multiple directories for specific report files and returns them in a sorted list.

        The method searches for report files with names matching the pattern "*-AUTOSCAN.md"
        in predefined directories. These include the "Crash Logs" folder in the local
        directory, a custom scan folder defined in the settings, and a backup folder for
        unsolved logs. The function also ensures that the directories are monitored by
        the file watcher for modifications. Duplicates in the list of found reports are removed,
        and the results are sorted by name in descending order.

        Returns:
            list[Path]: A sorted list of paths to all unique report files found, ordered
            by name in descending order (Z to A).
        """
        reports = []

        # Primary location - Crash Logs folder in local directory
        local_dir = GlobalRegistry.get_local_dir()
        if local_dir:
            crash_logs_dir = Path(local_dir) / "Crash Logs"
            if crash_logs_dir.exists():
                reports.extend(crash_logs_dir.glob("*-AUTOSCAN.md"))

                # Add directory to file watcher
                if crash_logs_dir.as_posix() not in self.file_watcher.directories():
                    self.file_watcher.addPath(str(crash_logs_dir))

        # Custom scan folder from settings
        custom_path_str = classic_settings(str, "SCAN Custom Path")
        if custom_path_str:
            custom_path = Path(custom_path_str)
            if custom_path.exists() and custom_path.is_dir():
                reports.extend(custom_path.glob("*-AUTOSCAN.md"))

                # Add to file watcher
                if custom_path.as_posix() not in self.file_watcher.directories():
                    self.file_watcher.addPath(str(custom_path))

        # Backup location for unsolved logs
        local_dir = GlobalRegistry.get_local_dir()
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
        """
        Clears the current list of reports, scans for updated reports, and populates
        the list with new data. Updates associated widgets and emits a signal to notify
        listeners of changes.
        """
        # Clear current list
        self.results_list.clear()

        # Scan for reports
        reports = self.scan_for_reports()

        # Populate list
        self.results_list.populate_reports(reports)

        # Emit signal
        self.reports_refreshed.emit(len(reports))

        # Update status
        if not reports:
            self.metadata_widget.clear()
            self.markdown_viewer.clear()
            self.markdown_viewer.setMarkdown(
                "# No Reports Found\n\nNo scan reports are available. Run a crash log scan to generate reports."
            )
        else:
            # Reports found - clear any error state and show instructions
            self.markdown_viewer.clear()
            self.markdown_viewer.setMarkdown("# Reports Available\n\nSelect a report from the list to view its contents.")
            # Auto-select the first report for better UX
            if self.results_list.count() > 0:
                self.results_list.setCurrentRow(0)

        logger.info(f"Refreshed reports list: {len(reports)} reports found")

    def load_report(self, report_path: Path) -> bool:
        """
        Loads a report file specified by the given path, displays its content in a markdown viewer,
        updates associated metadata, and signals the completion of the process. Verifies the
        existence of the file before attempting to load it, and handles errors gracefully.

        Args:
            report_path (Path): The path to the report file to be loaded.

        Returns:
            bool: True if the report is loaded successfully; False otherwise.
        """
        logger.info(f"Loading report: {report_path}")
        # msg_info removed - not needed for every report load

        try:
            if not report_path.exists():
                msg_error(f"Report file not found: {report_path.name}")
                logger.error(f"Report file not found: {report_path}")
                return False

            # Read report content with Rust-accelerated file I/O
            content = read_file_sync(report_path)

            # Display in viewer
            self.markdown_viewer.setMarkdown(content)

            # Update metadata
            self.metadata_widget.update_metadata(report_path, content)

            # Store current report path
            self.current_report_path = report_path

            # Emit signal
            self.report_loaded.emit(report_path)

            logger.debug(f"Loaded report: {report_path.name}")

        except Exception as e:  # noqa: BLE001
            msg_error(f"Failed to load report: {e}")
            logger.error(f"Error loading report {report_path}: {e}", exc_info=True)
            # If markdown fails, try displaying as plain text
            try:
                content = read_file_sync(report_path)
                self.markdown_viewer.setPlainText(content)
                msg_warning("Displayed report as plain text due to markdown error")
            except Exception as fallback_e:  # noqa: BLE001
                logger.error(f"Fallback plain text also failed: {fallback_e}")
                return False
        else:
            logger.debug(f"Successfully loaded report: {report_path.name}")
            return True

    def _on_report_selected(self) -> None:
        """Handle report selection from the list."""
        selected_items = self.results_list.selectedItems()
        if not selected_items:
            logger.debug("No items selected")
            return

        # Get the report path from the selected item
        item = selected_items[0]
        item_text = item.text()
        logger.debug(f"Selected item text: {item_text}")

        report_path = self.results_list.get_report_path(item)
        logger.debug(f"Report path from list: {report_path}")

        if report_path:
            self.load_report(report_path)
        else:
            msg_error(f"No report path found for: {item_text}")
            logger.error(f"No report path found for selected item: {item_text}")

    def _delete_selected_report(self) -> None:
        """Delete the currently selected report with confirmation."""
        selected_items = self.results_list.selectedItems()
        if not selected_items:
            msg_warning("No report selected")
            return

        item = selected_items[0]
        report_path = self.results_list.get_report_path(item)

        if not report_path:
            return

        # Confirmation dialog
        reply = QMessageBox.question(
            self.results_tab,
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
                if self.current_report_path == report_path:
                    self.markdown_viewer.clear()
                    self.metadata_widget.clear()
                    self.current_report_path = None

                # Refresh list
                self.refresh_reports_list()

                msg_info(f"Report deleted: {report_path.name}")

            except Exception as e:
                msg_error(f"Failed to delete report: {e}")
                logger.error(f"Error deleting report {report_path}: {e}")

    def _copy_report(self) -> None:
        """Copy the current report content to clipboard with Rust-accelerated file I/O."""
        if not self.current_report_path:
            msg_warning("No report loaded")
            return

        try:
            from PySide6.QtWidgets import QApplication

            content = read_file_sync(self.current_report_path)
            QApplication.clipboard().setText(content)
            msg_info("Report copied to clipboard")

        except Exception as e:
            msg_error(f"Failed to copy report: {e}")
            logger.error(f"Error copying report: {e}")

    @staticmethod
    def _open_reports_folder() -> None:
        """Open the Crash Logs folder in the file explorer."""
        local_dir = GlobalRegistry.get_local_dir()
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

        except Exception as e:
            msg_error(f"Failed to open folder: {e}")
            logger.error(f"Error opening folder: {e}")

    def _show_context_menu(self, position: QPoint) -> None:
        """Show context menu for report list."""
        item = self.results_list.itemAt(position)
        if not item:
            return

        menu = QMenu(self.results_list)

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

        # Show menu
        menu.exec(self.results_list.mapToGlobal(position))

    def _on_directory_changed(self, path: str) -> None:
        """Handle directory change notifications from file watcher."""
        logger.debug(f"Directory changed: {path}")

        # Skip if file watching is paused (e.g., during scan)
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
        """
        Pause file watching during scans to prevent I/O bottleneck.

        During a scan, each new report triggers a directory change event,
        which causes refresh_reports_list() to read ALL existing reports.
        With 754 reports, this causes 48,000+ file reads during a single scan!

        This method pauses the file watcher to eliminate this bottleneck.
        """
        self._file_watching_paused = True
        logger.debug("File watching paused")

    def _resume_file_watching(self) -> None:
        """
        Resume file watching after scan completion.

        The caller should trigger a single refresh after resuming to show
        all new reports created during the scan.
        """
        self._file_watching_paused = False
        logger.debug("File watching resumed")

    def _setup_auto_refresh(self) -> None:
        """Setup auto-refresh based on settings."""
        # Check if auto-refresh is enabled in settings
        auto_refresh = yaml_settings(bool, YAML.Settings, "ResultsViewer.AutoRefresh", False)

        if auto_refresh:
            # Get refresh interval (default 5 seconds)
            interval = yaml_settings(int, YAML.Settings, "ResultsViewer.RefreshInterval", 5000)
            if interval is not None:
                self.refresh_timer.start(interval)
            logger.debug(f"Auto-refresh enabled with interval: {interval}ms")
