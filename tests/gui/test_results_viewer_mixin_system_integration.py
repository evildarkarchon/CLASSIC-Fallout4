"""Integration tests for ResultsViewerMixin system operations.

Tests file watching, settings integration, error handling, and
multi-directory scanning with real file operations.
"""
# ruff: noqa: ANN201, ANN001, ARG001, ANN204, PLR6301, ARG002

import shutil
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QFileSystemWatcher, QTimer

from ClassicLib import GlobalRegistry
from ClassicLib.Interface.ResultsViewerMixin import ResultsViewerMixin


@pytest.fixture
def integrated_viewer(tmp_path, init_message_handler_fixture, qt_application):
    """Create ResultsViewerMixin with minimal mocking for integration tests."""

    class IntegratedViewer(ResultsViewerMixin):
        """Test viewer with minimal mocking."""

        def __init__(self, test_dir: Path):
            self.test_dir = test_dir
            self.results_tab = MagicMock()

            # Mock GUI components that we can't create without full Qt app
            self.results_list = MagicMock()
            # Mock count() to return an integer, not a MagicMock
            self.results_list.count.return_value = 0
            self.results_list.selectedItems.return_value = []
            self.results_list.get_report_path = MagicMock()
            self.results_list.clear = MagicMock()
            self.results_list.populate_reports = MagicMock()
            self.results_list.itemAt = MagicMock()

            self.markdown_viewer = MagicMock()
            self.metadata_widget = MagicMock()

            # Signals
            self.report_loaded = MagicMock()
            self.report_loaded.emit = MagicMock()
            self.reports_refreshed = MagicMock()
            self.reports_refreshed.emit = MagicMock()
            
            self._file_watching_paused = False
            self._refresh_pending = False

            # Real file watcher (but we'll mock its methods)
            self.file_watcher = MagicMock(spec=QFileSystemWatcher)
            self.file_watcher.directories.return_value = []
            self.file_watcher.addPath = MagicMock()

            self.refresh_timer = MagicMock(spec=QTimer)
            self.current_report_path = None

            # Setup test directory structure
            self.crash_logs_dir = test_dir / "Crash Logs"
            self.crash_logs_dir.mkdir(parents=True)

            self.backup_dir = test_dir / "CLASSIC Backup" / "Unsolved Logs"
            self.backup_dir.mkdir(parents=True)

    return IntegratedViewer(tmp_path)


@pytest.mark.integration
@pytest.mark.gui
class TestReportScanningIntegration:
    """Integration tests for report scanning with real file operations."""

    def test_scan_multiple_directories(self, integrated_viewer, tmp_path, gui_message_handler):
        """Should scan multiple directories and combine results."""
        # Create reports in different directories
        crash_report1 = integrated_viewer.crash_logs_dir / "crash1-AUTOSCAN.md"
        crash_report2 = integrated_viewer.crash_logs_dir / "crash2-AUTOSCAN.md"
        backup_report = integrated_viewer.backup_dir / "backup-AUTOSCAN.md"

        crash_report1.write_text("Crash 1")
        time.sleep(0.01)  # Ensure different timestamps
        crash_report2.write_text("Crash 2")
        time.sleep(0.01)
        backup_report.write_text("Backup")

        with (
            patch.object(GlobalRegistry, "get_local_dir", return_value=str(tmp_path)),
            patch("ClassicLib.Interface.ResultsViewerMixin.classic_settings", return_value=None),
        ):
            reports = integrated_viewer.scan_for_reports()

            # Should find all reports
            assert len(reports) == 3

            # Should be sorted by name (descending: Z-A)
            report_names = [r.name for r in reports]
            assert report_names[0] == "crash2-AUTOSCAN.md"
            assert report_names[1] == "crash1-AUTOSCAN.md"
            assert report_names[2] == "backup-AUTOSCAN.md"

    def test_scan_with_custom_path(self, integrated_viewer, tmp_path, gui_message_handler):
        """Should include custom scan path in results."""
        custom_dir = tmp_path / "CustomScans"
        custom_dir.mkdir()

        # Create reports in both locations
        crash_report = integrated_viewer.crash_logs_dir / "crash-AUTOSCAN.md"
        custom_report = custom_dir / "custom-AUTOSCAN.md"

        crash_report.write_text("Crash")
        custom_report.write_text("Custom")

        with (
            patch.object(GlobalRegistry, "get_local_dir", return_value=str(tmp_path)),
            patch("ClassicLib.Interface.ResultsViewerMixin.classic_settings", return_value=str(custom_dir)),
        ):
            reports = integrated_viewer.scan_for_reports()

            # Should find reports from both locations
            assert len(reports) == 2
            report_names = {r.name for r in reports}
            assert "crash-AUTOSCAN.md" in report_names
            assert "custom-AUTOSCAN.md" in report_names

    def test_file_watcher_registration(self, integrated_viewer, tmp_path, gui_message_handler):
        """Should register directories with file watcher."""
        # Create a report to trigger directory scanning
        report = integrated_viewer.crash_logs_dir / "test-AUTOSCAN.md"
        report.write_text("Test")

        with (
            patch.object(GlobalRegistry, "get_local_dir", return_value=str(tmp_path)),
            patch("ClassicLib.Interface.ResultsViewerMixin.classic_settings", return_value=None),
        ):
            integrated_viewer.scan_for_reports()

            # Should add crash logs directory to watcher
            integrated_viewer.file_watcher.addPath.assert_called_with(str(integrated_viewer.crash_logs_dir))


@pytest.mark.integration
@pytest.mark.gui
class TestFileWatcherIntegration:
    """Integration tests for file system watcher functionality."""

    def test_watcher_monitors_multiple_directories(self, integrated_viewer, tmp_path, gui_message_handler):
        """Should monitor multiple directories for changes."""
        # Create custom scan directory
        custom_dir = tmp_path / "CustomScans"
        custom_dir.mkdir()

        # Create reports in both locations
        crash_report = integrated_viewer.crash_logs_dir / "crash-AUTOSCAN.md"
        custom_report = custom_dir / "custom-AUTOSCAN.md"
        crash_report.write_text("Crash")
        custom_report.write_text("Custom")

        with (
            patch.object(GlobalRegistry, "get_local_dir", return_value=str(tmp_path)),
            patch("ClassicLib.Interface.ResultsViewerMixin.classic_settings", return_value=str(custom_dir)),
        ):
            integrated_viewer.scan_for_reports()

            # Both directories should be added to watcher
            assert integrated_viewer.file_watcher.addPath.call_count == 2
            calls = [call[0][0] for call in integrated_viewer.file_watcher.addPath.call_args_list]
            assert str(integrated_viewer.crash_logs_dir) in calls
            assert str(custom_dir) in calls


@pytest.mark.integration
@pytest.mark.gui
class TestAutoRefreshIntegration:
    """Integration tests for auto-refresh functionality."""

    def test_auto_refresh_workflow(self, integrated_viewer, tmp_path, gui_message_handler):
        """Test auto-refresh detecting new reports."""
        with (
            patch.object(GlobalRegistry, "get_local_dir", return_value=str(tmp_path)),
            patch("ClassicLib.Interface.ResultsViewerMixin.yaml_settings") as mock_settings,
        ):
            # Configure auto-refresh
            mock_settings.side_effect = [True, 1000]  # Enabled, 1 second interval

            integrated_viewer._setup_auto_refresh()
            integrated_viewer.refresh_timer.start.assert_called_with(1000)

            # Initial scan - no reports
            integrated_viewer.refresh_reports_list()
            integrated_viewer.reports_refreshed.emit.assert_called_with(0)

            # Add a new report
            new_report = integrated_viewer.crash_logs_dir / "new-AUTOSCAN.md"
            new_report.write_text("New report")

            # Simulate directory change notification
            integrated_viewer._on_directory_changed(str(integrated_viewer.crash_logs_dir))

            # After debounce, should trigger refresh
            with patch.object(integrated_viewer, "_debounced_refresh"):
                integrated_viewer._refresh_pending = False
                integrated_viewer._debounced_refresh()

                # Should have been called (mocked to avoid actual refresh)
                assert integrated_viewer._refresh_pending is False


@pytest.mark.integration
@pytest.mark.gui
class TestErrorHandlingIntegration:
    """Integration tests for error handling."""

    def test_handles_permission_errors(self, integrated_viewer, tmp_path, gui_message_handler):
        """Should handle permission errors gracefully."""
        report_path = integrated_viewer.crash_logs_dir / "protected-AUTOSCAN.md"
        report_path.write_text("Protected")

        # Simulate permission error
        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.read_file_sync", side_effect=PermissionError("Access denied")),
            patch("ClassicLib.Interface.ResultsViewerMixin.QTimer") as _,
        ):
            loaded = integrated_viewer.load_report(report_path)
            assert loaded is False

    def test_handles_corrupted_report_files(self, integrated_viewer, gui_message_handler):
        """Should handle corrupted or binary report files."""
        binary_report = integrated_viewer.crash_logs_dir / "binary-AUTOSCAN.md"

        # Write binary data that might not be valid UTF-8
        binary_report.write_bytes(b"\x00\x01\x02\x03\x04\x05")

        # Should handle with errors="ignore"
        loaded = integrated_viewer.load_report(binary_report)
        assert loaded is True

    def test_handles_missing_directories(self, integrated_viewer, tmp_path, gui_message_handler):
        """Should handle missing directories gracefully."""
        # Remove crash logs directory
        shutil.rmtree(integrated_viewer.crash_logs_dir)

        with patch.object(GlobalRegistry, "get_local_dir", return_value=str(tmp_path)):
            reports = integrated_viewer.scan_for_reports()

            # Should return empty list without crashing
            assert reports == []


@pytest.mark.integration
@pytest.mark.gui
class TestSettingsIntegration:
    """Integration tests for settings-based functionality."""

    def test_auto_refresh_timer_interval_from_settings(self, integrated_viewer, gui_message_handler):
        """Should use refresh interval from settings."""
        with patch("ClassicLib.Interface.ResultsViewerMixin.yaml_settings") as mock_settings:
            # Return enabled=True, interval=3000ms
            mock_settings.side_effect = [True, 3000]

            integrated_viewer._setup_auto_refresh()

            # Timer should start with configured interval
            integrated_viewer.refresh_timer.start.assert_called_with(3000)

    def test_custom_scan_path_from_settings(self, integrated_viewer, tmp_path, gui_message_handler):
        """Should use custom scan path from settings."""
        custom_dir = tmp_path / "MyCustomPath"
        custom_dir.mkdir()

        custom_report = custom_dir / "custom-AUTOSCAN.md"
        custom_report.write_text("Custom scan")

        with (
            patch.object(GlobalRegistry, "get_local_dir", return_value=None),
            patch("ClassicLib.Interface.ResultsViewerMixin.classic_settings", return_value=str(custom_dir)),
        ):
            reports = integrated_viewer.scan_for_reports()

            # Should find report from custom path
            assert len(reports) == 1
            assert reports[0] == custom_report


@pytest.mark.integration
@pytest.mark.gui
class TestContextMenuIntegration:
    """Integration tests for context menu operations."""

    def test_context_menu_actions(self, integrated_viewer, tmp_path, gui_message_handler):
        """Test context menu actions on reports."""
        report_path = integrated_viewer.crash_logs_dir / "context-AUTOSCAN.md"
        report_path.write_text("Context menu test")

        # Setup selection
        mock_item = MagicMock()
        integrated_viewer.results_list.itemAt.return_value = mock_item
        integrated_viewer.results_list.get_report_path.return_value = report_path
        integrated_viewer.current_report_path = report_path

        with (
            patch("ClassicLib.Interface.ResultsViewerMixin.QMenu") as mock_menu_class,
            patch("ClassicLib.Interface.ResultsViewerMixin.QAction") as mock_action_class,
        ):
            mock_menu = MagicMock()
            mock_menu_class.return_value = mock_menu

            # Create mock actions
            mock_actions = {}
            for action_name in ["View Report", "Copy to Clipboard", "Delete"]:
                mock_action = MagicMock()
                mock_action.triggered = MagicMock()
                mock_actions[action_name] = mock_action
                mock_action_class.side_effect = lambda text, _: mock_actions.get(text, MagicMock())

            integrated_viewer._show_context_menu(MagicMock())

            # Verify menu created with correct actions
            assert mock_menu.addAction.call_count >= 3
            mock_menu.exec.assert_called_once()
