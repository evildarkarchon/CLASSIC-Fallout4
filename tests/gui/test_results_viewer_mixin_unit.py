"""Unit tests for ResultsViewerMixin.

Tests the results viewer functionality in isolation with mocked Qt components.
"""
# ruff: noqa: ANN201, ANN001, ARG001, ANN204, PLR6301, ARG002, ANN202, ANN002, ANN003, RUF001

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Skip all tests in this module when running in xdist worker (parallel execution)
pytestmark = pytest.mark.skipif(os.environ.get("PYTEST_XDIST_WORKER") is not None, reason="Qt GUI tests cannot run in parallel workers")

from PySide6.QtCore import QFileSystemWatcher, QTimer, Signal
from PySide6.QtWidgets import QMessageBox, QWidget

from ClassicLib.Interface.ResultsViewerMixin import ResultsViewerMixin
from tests.fixtures.registry_fixtures import init_message_handler_fixture  # noqa: F401

# Note: MessageHandler initialization is now handled by standardized
# fixtures in tests/fixtures/registry_fixtures.py which provide:
# - message_handler: For non-GUI tests
# - gui_message_handler: For GUI tests (from qt_fixtures.py)
# - Automatic cleanup via ensure_message_handler_cleanup


@pytest.fixture
def mock_qt_components():
    """Mock Qt components for testing."""
    with (
        patch("ClassicLib.Interface.ResultsViewerMixin.QFileSystemWatcher") as mock_watcher,
        patch("ClassicLib.Interface.ResultsViewerMixin.QTimer") as mock_timer,
        patch("ClassicLib.Interface.ResultsViewerMixin.QHBoxLayout"),
        patch("ClassicLib.Interface.ResultsViewerMixin.QVBoxLayout"),
        patch("ClassicLib.Interface.ResultsViewerMixin.QSplitter"),
        patch("ClassicLib.Interface.ResultsViewerMixin.QPushButton"),
        patch("ClassicLib.Interface.ResultsViewerMixin.QWidget"),
    ):
        # Setup watcher mock
        watcher_instance = MagicMock(spec=QFileSystemWatcher)
        watcher_instance.directories.return_value = []
        mock_watcher.return_value = watcher_instance

        # Setup timer mock
        timer_instance = MagicMock(spec=QTimer)
        mock_timer.return_value = timer_instance

        yield {"watcher": watcher_instance, "timer": timer_instance, "watcher_class": mock_watcher, "timer_class": mock_timer}


@pytest.fixture
def viewer_mixin(mock_qt_components, init_message_handler_fixture):  # noqa: F811
    """Create a ResultsViewerMixin instance with mocked dependencies."""

    class TestViewer(ResultsViewerMixin):
        """Test class that includes the mixin."""

        def __init__(self):
            # Mock required attributes
            self.results_tab = MagicMock(spec=QWidget)
            self.results_list = MagicMock()
            # Mock count() to return an integer, not a MagicMock
            self.results_list.count.return_value = 0
            self.markdown_viewer = MagicMock()
            self.metadata_widget = MagicMock()

            # Mock required methods
            self.select_folder_mods = MagicMock()
            self.select_folder_scan = MagicMock()
            self.validate_scan_folder_text = MagicMock()
            self.open_url = MagicMock()
            self.show_about = MagicMock()
            self.help_popup_main = MagicMock()
            self.open_settings = MagicMock()
            self.open_crash_logs_folder = MagicMock()
            self.update_popup_explicit = MagicMock()
            self.toggle_papyrus_worker = MagicMock()
            self.update_papyrus_button_style = MagicMock()
            self.crash_logs_scan = MagicMock()
            self.game_files_scan = MagicMock()
            self.open_backup_folder = MagicMock()
            self.check_existing_backups = MagicMock()

            # Initialize signals with emit method
            self.report_loaded = MagicMock(spec=Signal)
            self.report_loaded.emit = MagicMock()
            self.reports_refreshed = MagicMock(spec=Signal)
            self.reports_refreshed.emit = MagicMock()

            self._file_watching_paused = False
            self._refresh_pending = False

    viewer = TestViewer()
    viewer.file_watcher = mock_qt_components["watcher"]
    viewer.refresh_timer = mock_qt_components["timer"]
    viewer.current_report_path = None

    return viewer


@pytest.mark.unit
@pytest.mark.gui
class TestResultsViewerMixinInit:
    """Tests for ResultsViewerMixin initialization."""

    def test_setup_results_tab_initializes_components(self, viewer_mixin, gui_message_handler):
        """Should initialize all required components."""
        with (
            patch.object(viewer_mixin, "_create_reports_panel") as mock_reports_panel,
            patch.object(viewer_mixin, "_create_viewer_panel") as mock_viewer_panel,
            patch.object(viewer_mixin, "refresh_reports_list") as mock_refresh,
            patch.object(viewer_mixin, "_setup_auto_refresh") as mock_auto_refresh,
        ):
            mock_reports_panel.return_value = MagicMock()
            mock_viewer_panel.return_value = MagicMock()

            viewer_mixin.setup_results_tab()

            # Verify initialization
            assert viewer_mixin.file_watcher is not None
            assert viewer_mixin.refresh_timer is not None
            assert viewer_mixin.current_report_path is None

            # Verify methods called
            mock_reports_panel.assert_called_once()
            mock_viewer_panel.assert_called_once()
            mock_refresh.assert_called_once()
            mock_auto_refresh.assert_called_once()

    def test_create_reports_panel_sets_up_list_and_buttons(self, viewer_mixin, gui_message_handler):
        """Should create reports panel with list and buttons."""
        with patch("ClassicLib.Interface.ResultsViewerWidgets.ReportListWidget") as mock_list_widget:
            mock_list_instance = MagicMock()
            mock_list_widget.return_value = mock_list_instance

            viewer_mixin._create_reports_panel()

            # Verify list widget created
            mock_list_widget.assert_called_once()
            assert viewer_mixin.results_list == mock_list_instance

            # Verify signals connected
            mock_list_instance.itemSelectionChanged.connect.assert_called()
            mock_list_instance.customContextMenuRequested.connect.assert_called()

    def test_create_viewer_panel_sets_up_viewer_components(self, viewer_mixin, gui_message_handler):
        """Should create viewer panel with markdown viewer and metadata."""
        with (
            patch("ClassicLib.Interface.ResultsViewerWidgets.MarkdownViewer") as mock_markdown,
            patch("ClassicLib.Interface.ResultsViewerWidgets.ReportMetadataWidget") as mock_metadata,
        ):
            mock_markdown_instance = MagicMock()
            mock_metadata_instance = MagicMock()
            mock_markdown.return_value = mock_markdown_instance
            mock_metadata.return_value = mock_metadata_instance

            viewer_mixin._create_viewer_panel()

            # Verify components created
            assert viewer_mixin.markdown_viewer == mock_markdown_instance
            assert viewer_mixin.metadata_widget == mock_metadata_instance


@pytest.mark.unit
@pytest.mark.gui
class TestReportScanning:
    """Tests for report scanning functionality."""

    def test_scan_for_reports_finds_autoscan_files(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should find AUTOSCAN.md files in configured directories."""
        # Setup test directories
        crash_logs_dir = tmp_path / "Crash Logs"
        crash_logs_dir.mkdir()

        # Create test report files
        report1 = crash_logs_dir / "test1-AUTOSCAN.md"
        report2 = crash_logs_dir / "test2-AUTOSCAN.md"
        other_file = crash_logs_dir / "other.txt"

        report1.write_text("Report 1")
        report2.write_text("Report 2")
        other_file.write_text("Not a report")

        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.GlobalRegistry") as mock_registry,
            patch("ClassicLib.Interface.ResultsViewerMixin.classic_settings") as mock_settings,
        ):
            mock_registry.get_local_dir.return_value = str(tmp_path)
            mock_settings.return_value = None  # No custom path

            reports = viewer_mixin.scan_for_reports()

            # Should find only AUTOSCAN files
            assert len(reports) == 2
            assert all("-AUTOSCAN.md" in str(r) for r in reports)

            # Should add directory to file watcher
            viewer_mixin.file_watcher.addPath.assert_called()

    def test_scan_for_reports_handles_custom_path(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should scan custom path if configured."""
        custom_dir = tmp_path / "Custom"
        custom_dir.mkdir()

        custom_report = custom_dir / "custom-AUTOSCAN.md"
        custom_report.write_text("Custom report")

        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.GlobalRegistry") as mock_registry,
            patch("ClassicLib.Interface.ResultsViewerMixin.classic_settings") as mock_settings,
        ):
            mock_registry.get_local_dir.return_value = None
            mock_settings.return_value = str(custom_dir)

            reports = viewer_mixin.scan_for_reports()

            assert len(reports) == 1
            assert "custom-AUTOSCAN.md" in str(reports[0])

    def test_scan_for_reports_sorts_by_name(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should sort reports by name, descending (Z-A)."""
        crash_logs_dir = tmp_path / "Crash Logs"
        crash_logs_dir.mkdir()

        # Create reports
        a_report = crash_logs_dir / "a-AUTOSCAN.md"
        a_report.write_text("A")

        z_report = crash_logs_dir / "z-AUTOSCAN.md"
        z_report.write_text("Z")

        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.GlobalRegistry") as mock_registry,
            patch("ClassicLib.Interface.ResultsViewerMixin.classic_settings") as mock_settings,
        ):
            mock_registry.get_local_dir.return_value = str(tmp_path)
            mock_settings.return_value = None

            reports = viewer_mixin.scan_for_reports()

            # Z should be first (descending)
            assert "z-AUTOSCAN.md" in str(reports[0])
            assert "a-AUTOSCAN.md" in str(reports[1])


@pytest.mark.unit
@pytest.mark.gui
class TestReportLoading:
    """Tests for report loading functionality."""

    def test_load_report_success(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should successfully load and display a report."""
        report_path = tmp_path / "test-AUTOSCAN.md"
        report_content = "# Test Report\n\nContent here"

        # Mock read_file_sync to return consistent content regardless of OS
        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.read_file_sync", return_value=report_content),
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
        ):
            mock_stat.return_value.st_mtime = 1234567890
            mock_stat.return_value.st_size = 1024

            result = viewer_mixin.load_report(report_path)

            assert result is True
            assert viewer_mixin.current_report_path == report_path

            # Verify display methods called
            viewer_mixin.markdown_viewer.setMarkdown.assert_called_with(report_content)
            viewer_mixin.metadata_widget.update_metadata.assert_called_with(report_path, report_content)
            viewer_mixin.report_loaded.emit.assert_called_with(report_path)

    def test_load_report_file_not_found(self, viewer_mixin, gui_message_handler):
        """Should handle missing report file gracefully."""
        missing_path = Path("/nonexistent/report.md")

        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.msg_error") as mock_error,
            patch("ClassicLib.Interface.ResultsViewerMixin.QTimer") as mock_timer_class,
        ):
            result = viewer_mixin.load_report(missing_path)

            assert result is False
            assert viewer_mixin.current_report_path is None

            # Execute callback
            args = mock_timer_class.singleShot.call_args[0]
            args[1]()
            mock_error.assert_called_once()

    def test_load_report_handles_encoding_errors(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should handle encoding errors when reading report."""
        report_path = tmp_path / "bad-encoding.md"
        # Write binary data that might cause encoding issues
        report_path.write_bytes(b"\x80\x81\x82 Test")

        result = viewer_mixin.load_report(report_path)

        # Should still succeed with errors="ignore"
        assert result is True
        viewer_mixin.markdown_viewer.setMarkdown.assert_called()


@pytest.mark.unit
@pytest.mark.gui
class TestReportManagement:
    """Tests for report management operations."""

    def test_delete_selected_report_with_confirmation(self, viewer_mixin, gui_message_handler):
        """Should delete report after user confirmation."""
        # Create mock path objects
        mock_report_path = MagicMock(spec=Path)
        mock_report_path.name = "test-AUTOSCAN.md"
        mock_report_path.exists.return_value = True

        # Create mock crash log path that doesn't exist
        mock_crash_log_path = MagicMock(spec=Path)
        mock_crash_log_path.exists.return_value = False
        mock_report_path.with_suffix.return_value = mock_crash_log_path

        # Setup mocks
        viewer_mixin.results_list.selectedItems.return_value = [MagicMock()]
        viewer_mixin.results_list.get_report_path.return_value = mock_report_path
        viewer_mixin.current_report_path = mock_report_path

        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.QMessageBox") as mock_msgbox,
            patch("ClassicLib.Interface.ResultsViewerMixin.msg_info") as mock_info,
            patch("ClassicLib.Interface.ResultsViewerMixin.msg_warning"),
            patch("ClassicLib.Interface.ResultsViewerMixin.msg_error"),
            patch("ClassicLib.Interface.ResultsViewerMixin.logger"),
            patch.object(viewer_mixin, "refresh_reports_list") as mock_refresh,
        ):
            # Set up StandardButton enum on the mock
            mock_msgbox.StandardButton = QMessageBox.StandardButton
            mock_msgbox.question.return_value = QMessageBox.StandardButton.Yes

            viewer_mixin._delete_selected_report()

            # Verify unlink called on path
            mock_report_path.unlink.assert_called_once()

            # Verify UI updated
            viewer_mixin.markdown_viewer.clear.assert_called()
            viewer_mixin.metadata_widget.clear.assert_called()
            assert viewer_mixin.current_report_path is None
            mock_refresh.assert_called_once()
            mock_info.assert_called_once()

    def test_delete_selected_report_cancelled(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should not delete if user cancels."""
        report_path = tmp_path / "test-AUTOSCAN.md"
        report_path.write_text("Report")

        viewer_mixin.results_list.selectedItems.return_value = [MagicMock()]
        viewer_mixin.results_list.get_report_path.return_value = report_path

        with patch("ClassicLib.Interface.ResultsViewerMixin.QMessageBox") as mock_msgbox:
            mock_msgbox.question.return_value = QMessageBox.StandardButton.No

            viewer_mixin._delete_selected_report()

            # File should still exist
            assert report_path.exists()

    def test_copy_report_to_clipboard(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should copy report content to clipboard."""
        report_path = tmp_path / "test-AUTOSCAN.md"
        report_content = "Report content"
        report_path.write_text(report_content)

        viewer_mixin.current_report_path = report_path

        with patch("PySide6.QtWidgets.QApplication") as mock_app, patch("ClassicLib.Interface.ResultsViewerMixin.msg_info") as mock_info:
            mock_clipboard = MagicMock()
            mock_app.clipboard.return_value = mock_clipboard

            viewer_mixin._copy_report()

            mock_clipboard.setText.assert_called_with(report_content)
            mock_info.assert_called_once()

    def test_copy_report_no_report_loaded(self, viewer_mixin, gui_message_handler):
        """Should show warning when no report is loaded."""
        viewer_mixin.current_report_path = None

        with patch("ClassicLib.Interface.ResultsViewerMixin.msg_warning") as mock_warning:
            viewer_mixin._copy_report()

            mock_warning.assert_called_once_with("No report loaded")

    def test_copy_report_handles_read_error(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should handle errors when reading report for clipboard."""
        report_path = tmp_path / "test-AUTOSCAN.md"
        viewer_mixin.current_report_path = report_path

        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.read_file_sync", side_effect=OSError("Read error")),
            patch("ClassicLib.Interface.ResultsViewerMixin.msg_error") as mock_error,
        ):
            viewer_mixin._copy_report()

            mock_error.assert_called_once()

    def test_open_reports_folder(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should open reports folder in file explorer."""
        crash_logs_dir = tmp_path / "Crash Logs"
        crash_logs_dir.mkdir()

        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.GlobalRegistry") as mock_registry,
            patch("PySide6.QtGui.QDesktopServices") as mock_desktop,
        ):
            mock_registry.get_local_dir.return_value = str(tmp_path)

            viewer_mixin._open_reports_folder()

            mock_desktop.openUrl.assert_called_once()

    def test_open_reports_folder_no_local_dir(self, viewer_mixin, gui_message_handler):
        """Should show warning when local directory not configured."""
        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.GlobalRegistry") as mock_registry,
            patch("ClassicLib.Interface.ResultsViewerMixin.msg_warning") as mock_warning,
        ):
            mock_registry.get_local_dir.return_value = None

            viewer_mixin._open_reports_folder()

            mock_warning.assert_called_once_with("Local directory not configured")

    def test_open_reports_folder_not_exists(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should show warning when Crash Logs folder doesn't exist."""
        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.GlobalRegistry") as mock_registry,
            patch("ClassicLib.Interface.ResultsViewerMixin.msg_warning") as mock_warning,
        ):
            mock_registry.get_local_dir.return_value = str(tmp_path)
            # Crash Logs directory not created

            viewer_mixin._open_reports_folder()

            mock_warning.assert_called_once_with("Crash Logs folder does not exist")

    def test_open_reports_folder_handles_error(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should handle errors when opening folder."""
        crash_logs_dir = tmp_path / "Crash Logs"
        crash_logs_dir.mkdir()

        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.GlobalRegistry") as mock_registry,
            patch("PySide6.QtGui.QDesktopServices") as mock_desktop,
            patch("ClassicLib.Interface.ResultsViewerMixin.msg_error") as mock_error,
        ):
            mock_registry.get_local_dir.return_value = str(tmp_path)
            mock_desktop.openUrl.side_effect = RuntimeError("Failed to open")

            viewer_mixin._open_reports_folder()

            mock_error.assert_called_once()


@pytest.mark.unit
@pytest.mark.gui
class TestAutoRefresh:
    """Tests for auto-refresh functionality."""

    def test_setup_auto_refresh_enabled(self, viewer_mixin, gui_message_handler):
        """Should enable auto-refresh when configured."""
        with patch("ClassicLib.Interface.ResultsViewerMixin.yaml_settings") as mock_settings:
            mock_settings.side_effect = [True, 5000]  # Enabled, 5 second interval

            viewer_mixin._setup_auto_refresh()

            viewer_mixin.refresh_timer.start.assert_called_with(5000)

    def test_setup_auto_refresh_disabled(self, viewer_mixin, gui_message_handler):
        """Should not start timer when auto-refresh is disabled."""
        with patch("ClassicLib.Interface.ResultsViewerMixin.yaml_settings") as mock_settings:
            mock_settings.return_value = False

            viewer_mixin._setup_auto_refresh()

            viewer_mixin.refresh_timer.start.assert_not_called()

    def test_setup_auto_refresh_with_default_interval(self, viewer_mixin, gui_message_handler):
        """Should use default interval when not configured."""
        with patch("ClassicLib.Interface.ResultsViewerMixin.yaml_settings") as mock_settings:
            # First call returns True (enabled), second call raises to trigger default
            def side_effect(*args, **kwargs):
                if mock_settings.call_count == 1:
                    return True
                return 5000  # Default value from the function call

            mock_settings.side_effect = side_effect

            viewer_mixin._setup_auto_refresh()

            viewer_mixin.refresh_timer.start.assert_called_with(5000)

    def test_directory_changed_triggers_debounced_refresh(self, viewer_mixin, gui_message_handler):
        """Should debounce rapid directory changes."""
        with patch("ClassicLib.Interface.ResultsViewerMixin.QTimer") as mock_timer:
            viewer_mixin._on_directory_changed("/some/path")

            # Should schedule debounced refresh
            mock_timer.singleShot.assert_called_with(500, viewer_mixin._debounced_refresh)

            # Second call should not schedule another
            viewer_mixin._on_directory_changed("/some/path")
            assert mock_timer.singleShot.call_count == 1

    def test_debounced_refresh_clears_pending_flag(self, viewer_mixin, gui_message_handler):
        """Should clear pending flag after refresh."""
        viewer_mixin._refresh_pending = True

        with patch.object(viewer_mixin, "refresh_reports_list") as mock_refresh:
            viewer_mixin._debounced_refresh()

            assert viewer_mixin._refresh_pending is False
            mock_refresh.assert_called_once()


@pytest.mark.unit
@pytest.mark.gui
class TestContextMenu:
    """Tests for context menu functionality."""

    def test_show_context_menu_with_item(self, viewer_mixin, gui_message_handler):
        """Should show context menu with all actions when item selected."""
        mock_item = MagicMock()
        mock_position = MagicMock()

        viewer_mixin.results_list.itemAt.return_value = mock_item

        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.QMenu") as mock_menu_class,
            patch("ClassicLib.Interface.ResultsViewerMixin.QAction"),
        ):
            mock_menu = MagicMock()
            mock_menu_class.return_value = mock_menu

            viewer_mixin._show_context_menu(mock_position)

            # Verify menu created
            mock_menu_class.assert_called_once_with(viewer_mixin.results_list)

            # Verify actions added (3 actions + 2 separators)
            assert mock_menu.addAction.call_count == 3
            assert mock_menu.addSeparator.call_count == 2

            # Verify menu shown
            mock_menu.exec.assert_called_once()

    def test_show_context_menu_no_item(self, viewer_mixin, gui_message_handler):
        """Should not show menu when no item at position."""
        viewer_mixin.results_list.itemAt.return_value = None

        with patch("ClassicLib.Interface.ResultsViewerMixin.QMenu") as mock_menu_class:
            viewer_mixin._show_context_menu(MagicMock())

            # Menu should not be created
            mock_menu_class.assert_not_called()


@pytest.mark.unit
@pytest.mark.gui
class TestReportSelection:
    """Tests for report selection handling."""

    def test_on_report_selected_with_valid_item(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should load report when valid item selected."""
        report_path = tmp_path / "test-AUTOSCAN.md"
        report_path.write_text("Test content")

        mock_item = MagicMock()
        viewer_mixin.results_list.selectedItems.return_value = [mock_item]
        viewer_mixin.results_list.get_report_path.return_value = report_path

        with patch.object(viewer_mixin, "load_report") as mock_load:
            viewer_mixin._on_report_selected()

            mock_load.assert_called_once_with(report_path)

    def test_on_report_selected_no_items(self, viewer_mixin, gui_message_handler):
        """Should do nothing when no items selected."""
        viewer_mixin.results_list.selectedItems.return_value = []

        with patch.object(viewer_mixin, "load_report") as mock_load:
            viewer_mixin._on_report_selected()

            mock_load.assert_not_called()

    def test_on_report_selected_null_path(self, viewer_mixin, gui_message_handler):
        """Should not load when get_report_path returns None."""
        mock_item = MagicMock()
        viewer_mixin.results_list.selectedItems.return_value = [mock_item]
        viewer_mixin.results_list.get_report_path.return_value = None

        with patch.object(viewer_mixin, "load_report") as mock_load:
            viewer_mixin._on_report_selected()

            mock_load.assert_not_called()


@pytest.mark.unit
@pytest.mark.gui
class TestFileWatcher:
    """Tests for file watcher functionality."""

    def test_file_watcher_adds_new_directories(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should add new directories to file watcher."""
        crash_logs_dir = tmp_path / "Crash Logs"
        crash_logs_dir.mkdir()

        report = crash_logs_dir / "test-AUTOSCAN.md"
        report.write_text("Test")

        viewer_mixin.file_watcher.directories.return_value = []

        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.GlobalRegistry") as mock_registry,
            patch("ClassicLib.Interface.ResultsViewerMixin.classic_settings") as mock_settings,
        ):
            mock_registry.get_local_dir.return_value = str(tmp_path)
            mock_settings.return_value = None

            viewer_mixin.scan_for_reports()

            viewer_mixin.file_watcher.addPath.assert_called_with(str(crash_logs_dir))

    def test_file_watcher_skips_existing_directories(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should not add directories already in file watcher."""
        crash_logs_dir = tmp_path / "Crash Logs"
        crash_logs_dir.mkdir()

        report = crash_logs_dir / "test-AUTOSCAN.md"
        report.write_text("Test")

        # Directory already in watcher
        viewer_mixin.file_watcher.directories.return_value = [crash_logs_dir.as_posix()]

        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.GlobalRegistry") as mock_registry,
            patch("ClassicLib.Interface.ResultsViewerMixin.classic_settings", return_value=None),
        ):
            mock_registry.get_local_dir.return_value = str(tmp_path)

            viewer_mixin.scan_for_reports()

            viewer_mixin.file_watcher.addPath.assert_not_called()


@pytest.mark.unit
@pytest.mark.gui
class TestZoomControls:
    """Tests for zoom control functionality in viewer panel."""

    def test_zoom_buttons_connected_to_viewer_methods(self, viewer_mixin, gui_message_handler):
        """Should connect zoom buttons to markdown viewer methods."""
        with patch("ClassicLib.Interface.ResultsViewerMixin.QPushButton") as mock_button_class:
            buttons = []

            def create_button(text):
                btn = MagicMock()
                btn.clicked = MagicMock()
                buttons.append((text, btn))
                return btn

            mock_button_class.side_effect = create_button

            viewer_mixin._create_viewer_panel()

            # Find zoom buttons
            zoom_buttons = [b for t, b in buttons if t in {"−", "100%", "+"}]
            assert len(zoom_buttons) == 3

            # Verify connections (these are set in _create_viewer_panel)
            for text, btn in buttons:
                if text == "−":
                    btn.clicked.connect.assert_called_with(viewer_mixin.markdown_viewer.zoom_out)
                elif text == "100%":
                    btn.clicked.connect.assert_called_with(viewer_mixin.markdown_viewer.reset_zoom)
                elif text == "+":
                    btn.clicked.connect.assert_called_with(viewer_mixin.markdown_viewer.zoom_in)
