"""Unit tests for ResultsViewerMixin core functionality.

Tests the core report scanning, loading, and management functionality
in isolation with mocked Qt components.
"""

# ruff: noqa: ANN001, ANN201, ANN204, ARG001, ARG002, F811, PLR6301

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QFileSystemWatcher, QTimer, Signal
from PySide6.QtWidgets import QWidget

from ClassicLib.Interface.ResultsViewerMixin import ResultsViewerMixin
from tests.fixtures.registry_fixtures import init_message_handler_fixture  # noqa: F401


@pytest.fixture
def mock_qt_components():
    """Mock Qt components for testing."""
    with (
        patch("ClassicLib.Interface.ResultsViewerMixin.QFileSystemWatcher") as mock_watcher,
        patch("ClassicLib.Interface.ResultsViewerMixin.QTimer") as mock_timer,
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
def viewer_mixin(mock_qt_components, init_message_handler_fixture):
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

            # Initialize signals with emit method
            self.report_loaded = MagicMock(spec=Signal)
            self.report_loaded.emit = MagicMock()
            self.reports_refreshed = MagicMock(spec=Signal)
            self.reports_refreshed.emit = MagicMock()

    viewer = TestViewer()
    viewer.file_watcher = mock_qt_components["watcher"]
    viewer.refresh_timer = mock_qt_components["timer"]
    viewer.current_report_path = None

    return viewer


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

    def test_scan_includes_backup_location(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should scan backup location for unsolved logs."""
        # Create backup location
        backup_dir = tmp_path / "CLASSIC Backup" / "Unsolved Logs"
        backup_dir.mkdir(parents=True)

        backup_report = backup_dir / "unsolved-AUTOSCAN.md"
        backup_report.write_text("Unsolved report")

        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.GlobalRegistry") as mock_registry,
            patch("ClassicLib.Interface.ResultsViewerMixin.classic_settings", return_value=None),
        ):
            mock_registry.get_local_dir.return_value = str(tmp_path)

            reports = viewer_mixin.scan_for_reports()

            # Should find report in backup location
            assert len(reports) == 1
            assert "unsolved-AUTOSCAN.md" in str(reports[0])


@pytest.mark.unit
@pytest.mark.gui
class TestReportLoading:
    """Tests for report loading functionality."""

    def test_load_report_success(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should successfully load and display a report."""
        report_path = tmp_path / "test-AUTOSCAN.md"
        report_content = "# Test Report\n\nContent here"
        report_path.write_text(report_content)

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
            patch("ClassicLib.Interface.ResultsViewerMixin.QTimer") as mock_timer_class
        ):
            result = viewer_mixin.load_report(missing_path)

            assert result is False
            assert viewer_mixin.current_report_path is None
            
            # msg_error is called inside QTimer.singleShot lambda, so verify singleShot called
            mock_timer_class.singleShot.assert_called_once()
            # Execute the lambda to verify it calls msg_error
            args = mock_timer_class.singleShot.call_args[0]
            # args[0] is delay (0), args[1] is callback
            callback = args[1]
            callback()
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

    def test_load_report_handles_exception(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should handle exceptions during report loading."""
        report_path = tmp_path / "error-report.md"
        report_path.write_text("Content")

        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.read_file_sync", side_effect=Exception("Unexpected error")),
            patch("ClassicLib.Interface.ResultsViewerMixin.msg_error") as mock_error,
            patch("ClassicLib.Interface.ResultsViewerMixin.QTimer") as mock_timer_class,
        ):
            result = viewer_mixin.load_report(report_path)

            assert result is False
            
            # Verify error reported
            mock_timer_class.singleShot.assert_called()
            # Execute the lambda to verify it calls msg_error
            args = mock_timer_class.singleShot.call_args[0]
            # args[0] is delay, args[1] is callback
            callback = args[1]
            callback()
            mock_error.assert_called_once()


@pytest.mark.unit
@pytest.mark.gui
class TestReportListRefresh:
    """Tests for report list refresh functionality."""

    def test_refresh_reports_list_with_reports(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should populate list when reports are found."""
        crash_logs_dir = tmp_path / "Crash Logs"
        crash_logs_dir.mkdir()

        report1 = crash_logs_dir / "report1-AUTOSCAN.md"
        report2 = crash_logs_dir / "report2-AUTOSCAN.md"
        report1.write_text("Report 1")
        report2.write_text("Report 2")

        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.GlobalRegistry") as mock_registry,
            patch("ClassicLib.Interface.ResultsViewerMixin.classic_settings", return_value=None),
        ):
            mock_registry.get_local_dir.return_value = str(tmp_path)

            viewer_mixin.refresh_reports_list()

            # List should be cleared and populated
            viewer_mixin.results_list.clear.assert_called_once()
            viewer_mixin.results_list.populate_reports.assert_called_once()

            # Should emit signal with count
            viewer_mixin.reports_refreshed.emit.assert_called_with(2)

    def test_refresh_reports_list_no_reports(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should show message when no reports found."""
        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.GlobalRegistry") as mock_registry,
            patch("ClassicLib.Interface.ResultsViewerMixin.classic_settings", return_value=None),
        ):
            mock_registry.get_local_dir.return_value = str(tmp_path)

            viewer_mixin.refresh_reports_list()

            # Should clear viewer and show message
            viewer_mixin.metadata_widget.clear.assert_called()
            viewer_mixin.markdown_viewer.clear.assert_called()

            # Should show "No Reports Found" message
            call_args = viewer_mixin.markdown_viewer.setMarkdown.call_args[0][0]
            assert "No Reports Found" in call_args

            # Should emit signal with 0 count
            viewer_mixin.reports_refreshed.emit.assert_called_with(0)


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

    def test_file_watcher_adds_multiple_paths(self, viewer_mixin, tmp_path, gui_message_handler):
        """Should add both crash logs and custom scan paths to watcher."""
        crash_logs_dir = tmp_path / "Crash Logs"
        crash_logs_dir.mkdir()
        custom_dir = tmp_path / "Custom"
        custom_dir.mkdir()

        crash_logs_dir.joinpath("report1-AUTOSCAN.md").write_text("Report 1")
        custom_dir.joinpath("report2-AUTOSCAN.md").write_text("Report 2")

        viewer_mixin.file_watcher.directories.return_value = []

        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.GlobalRegistry") as mock_registry,
            patch("ClassicLib.Interface.ResultsViewerMixin.classic_settings") as mock_settings,
        ):
            mock_registry.get_local_dir.return_value = str(tmp_path)
            mock_settings.return_value = str(custom_dir)

            viewer_mixin.scan_for_reports()

            # Both directories should be added
            assert viewer_mixin.file_watcher.addPath.call_count == 2
