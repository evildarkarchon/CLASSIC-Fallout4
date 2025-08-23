"""
Results viewer functionality for displaying scan reports.

This module provides a mixin class for viewing and managing CLASSIC scan reports
in a dedicated tab with markdown rendering support.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QFileSystemWatcher, Qt, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QFileDialog,
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
from ClassicLib.Logger import logger
from ClassicLib.MessageHandler import msg_error, msg_info, msg_warning
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings

if TYPE_CHECKING:

    from ClassicLib.Interface.ResultsViewerWidgets import (
        MarkdownViewer,
        ReportListWidget,
        ReportMetadataWidget,
    )


class ResultsViewerMixin:
    """
    Mixin class providing results viewer functionality for the MainWindow.

    This class manages the display and interaction with CLASSIC scan reports,
    including report discovery, loading, rendering, and management operations.
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
        """Initialize the results viewer tab with all components."""

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

        # Initialize current report path
        self.current_report_path = None

        # Initial scan for reports
        self.refresh_reports_list()

        # Setup auto-refresh if enabled
        self._setup_auto_refresh()

        logger.debug("Results viewer tab initialized")

    def _create_reports_panel(self) -> QWidget:
        """Create the left panel containing the reports list."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Create reports list widget
        self.results_list = ReportListWidget()
        self.results_list.itemSelectionChanged.connect(self._on_report_selected)
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

    def _create_viewer_panel(self) -> QWidget:
        """Create the right panel containing the report viewer."""
        from ClassicLib.Interface.ResultsViewerWidgets import (
            MarkdownViewer,
            ReportMetadataWidget,
        )

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Create metadata widget
        self.metadata_widget = ReportMetadataWidget()
        layout.addWidget(self.metadata_widget)

        # Create markdown viewer
        self.markdown_viewer = MarkdownViewer()
        layout.addWidget(self.markdown_viewer)

        # Create viewer toolbar
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(5)

        # Export button
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._export_report)
        export_btn.setToolTip("Export the current report")
        toolbar_layout.addWidget(export_btn)

        # Print button
        print_btn = QPushButton("Print")
        print_btn.clicked.connect(self._print_report)
        print_btn.setToolTip("Print the current report")
        toolbar_layout.addWidget(print_btn)

        # Copy button
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(self._copy_report)
        copy_btn.setToolTip("Copy report to clipboard")
        toolbar_layout.addWidget(copy_btn)

        toolbar_layout.addStretch()

        # Zoom controls
        zoom_out_btn = QPushButton("−")
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
        Scan for available report files in configured directories.

        Returns:
            List of Path objects for found report files.
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

        # Remove duplicates and sort by modification time (newest first)
        unique_reports = list(set(reports))
        unique_reports.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        logger.debug(f"Found {len(unique_reports)} scan reports")
        return unique_reports

    def refresh_reports_list(self) -> None:
        """Refresh the list of available reports."""
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
            self.markdown_viewer.setMarkdown("# No Reports Found\n\nNo scan reports are available. Run a crash log scan to generate reports.")

        logger.info(f"Refreshed reports list: {len(reports)} reports found")

    def load_report(self, report_path: Path) -> bool:
        """
        Load and display a report file.

        Args:
            report_path: Path to the report file to load.

        Returns:
            True if report was loaded successfully, False otherwise.
        """
        try:
            if not report_path.exists():
                msg_error(f"Report file not found: {report_path.name}")
                return False

            # Read report content
            content = report_path.read_text(encoding="utf-8", errors="ignore")

            # Display in viewer
            self.markdown_viewer.setMarkdown(content)

            # Update metadata
            self.metadata_widget.update_metadata(report_path, content)

            # Store current report path
            self.current_report_path = report_path

            # Emit signal
            self.report_loaded.emit(report_path)

            logger.debug(f"Loaded report: {report_path.name}")
            return True

        except Exception as e:
            msg_error(f"Failed to load report: {e}")
            logger.error(f"Error loading report {report_path}: {e}")
            return False

    def _on_report_selected(self) -> None:
        """Handle report selection from the list."""
        selected_items = self.results_list.selectedItems()
        if not selected_items:
            return

        # Get the report path from the selected item
        item = selected_items[0]
        report_path = self.results_list.get_report_path(item)

        if report_path:
            self.load_report(report_path)

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
            QMessageBox.StandardButton.No
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

    def _export_report(self) -> None:
        """Export the current report to various formats."""
        if not self.current_report_path:
            msg_warning("No report loaded")
            return

        # File dialog for export location
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self.results_tab,
            "Export Report",
            str(self.current_report_path.with_suffix("")),
            "Markdown Files (*.md);;HTML Files (*.html);;Text Files (*.txt);;All Files (*.*)"
        )

        if not file_path:
            return

        try:
            export_path = Path(file_path)

            if "html" in selected_filter.lower():
                # Export as HTML
                html_content = self.markdown_viewer.toHtml()
                export_path.write_text(html_content, encoding="utf-8")
            else:
                # Export as markdown or text
                content = self.current_report_path.read_text(encoding="utf-8", errors="ignore")
                export_path.write_text(content, encoding="utf-8")

            msg_info(f"Report exported to: {export_path.name}")
            logger.info(f"Exported report to: {export_path}")

        except Exception as e:
            msg_error(f"Failed to export report: {e}")
            logger.error(f"Error exporting report: {e}")

    def _print_report(self) -> None:
        """Print the current report."""
        if not self.current_report_path:
            msg_warning("No report loaded")
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self.results_tab)

        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            # noinspection PyUnresolvedReferences
            self.markdown_viewer.print(printer)
            msg_info("Report sent to printer")

    def _copy_report(self) -> None:
        """Copy the current report content to clipboard."""
        if not self.current_report_path:
            msg_warning("No report loaded")
            return

        try:
            from PySide6.QtWidgets import QApplication

            content = self.current_report_path.read_text(encoding="utf-8", errors="ignore")
            QApplication.clipboard().setText(content)
            msg_info("Report copied to clipboard")

        except Exception as e:
            msg_error(f"Failed to copy report: {e}")
            logger.error(f"Error copying report: {e}")

    def _open_reports_folder(self) -> None:
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

    def _show_context_menu(self, position) -> None:
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

        # Export action
        export_action = QAction("Export...", menu)
        export_action.triggered.connect(self._export_report)
        menu.addAction(export_action)

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

        # Debounce rapid changes
        if hasattr(self, "_refresh_pending") and self._refresh_pending:
            return

        self._refresh_pending = True
        QTimer.singleShot(500, self._debounced_refresh)

    def _debounced_refresh(self) -> None:
        """Debounced refresh to avoid rapid updates."""
        self._refresh_pending = False
        self.refresh_reports_list()

    def _setup_auto_refresh(self) -> None:
        """Setup auto-refresh based on settings."""
        # Check if auto-refresh is enabled in settings
        auto_refresh = yaml_settings(bool, YAML.Settings, "ResultsViewer.AutoRefresh", False)

        if auto_refresh:
            # Get refresh interval (default 5 seconds)
            interval = yaml_settings(int, YAML.Settings, "ResultsViewer.RefreshInterval", 5000)
            self.refresh_timer.start(interval)
            logger.debug(f"Auto-refresh enabled with interval: {interval}ms")
