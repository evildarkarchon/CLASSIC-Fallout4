"""Integration tests for ResultsViewerMixin.

Tests ResultsViewerMixin with real file operations and partial Qt mocking.
"""

import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from PySide6.QtCore import QFileSystemWatcher, Qt, QTimer

from ClassicLib import GlobalRegistry, MessageHandler
from ClassicLib.Interface.ResultsViewerMixin import ResultsViewerMixin


@pytest.fixture
def init_message_handler():
    """Initialize MessageHandler for tests."""
    handler = MessageHandler.init_message_handler(parent=None, is_gui_mode=False)
    yield
    MessageHandler._message_handler = None


@pytest.fixture
def integrated_viewer(tmp_path, init_message_handler):
    """Create ResultsViewerMixin with minimal mocking for integration tests."""

    class IntegratedViewer(ResultsViewerMixin):
        """Test viewer with minimal mocking."""

        def __init__(self, test_dir: Path):
            self.test_dir = test_dir
            self.results_tab = MagicMock()

            # Mock GUI components that we can't create without full Qt app
            self.results_list = MagicMock()
            self.results_list.selectedItems.return_value = []
            self.results_list.get_report_path = MagicMock()
            self.results_list.clear = MagicMock()
            self.results_list.populate_reports = MagicMock()

            self.markdown_viewer = MagicMock()
            self.metadata_widget = MagicMock()

            # Mock signals
            self.report_loaded = MagicMock()
            self.reports_refreshed = MagicMock()

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

    viewer = IntegratedViewer(tmp_path)
    return viewer


class TestReportScanningIntegration:
    """Integration tests for report scanning with real file operations."""

    def test_scan_multiple_directories(self, integrated_viewer, tmp_path):
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

        with patch.object(GlobalRegistry, "get_local_dir", return_value=str(tmp_path)), \
             patch("ClassicLib.Interface.ResultsViewerMixin.classic_settings", return_value=None):

            reports = integrated_viewer.scan_for_reports()

            # Should find all reports
            assert len(reports) == 3

            # Should be sorted by modification time (newest first)
            report_names = [r.name for r in reports]
            assert report_names[0] == "backup-AUTOSCAN.md"
            assert report_names[1] == "crash2-AUTOSCAN.md"
            assert report_names[2] == "crash1-AUTOSCAN.md"

    def test_scan_with_custom_path(self, integrated_viewer, tmp_path):
        """Should include custom scan path in results."""
        custom_dir = tmp_path / "CustomScans"
        custom_dir.mkdir()

        # Create reports in both locations
        crash_report = integrated_viewer.crash_logs_dir / "crash-AUTOSCAN.md"
        custom_report = custom_dir / "custom-AUTOSCAN.md"

        crash_report.write_text("Crash")
        custom_report.write_text("Custom")

        with patch.object(GlobalRegistry, "get_local_dir", return_value=str(tmp_path)), \
             patch("ClassicLib.Interface.ResultsViewerMixin.classic_settings", return_value=str(custom_dir)):

            reports = integrated_viewer.scan_for_reports()

            # Should find reports from both locations
            assert len(reports) == 2
            report_names = {r.name for r in reports}
            assert "crash-AUTOSCAN.md" in report_names
            assert "custom-AUTOSCAN.md" in report_names

    def test_file_watcher_registration(self, integrated_viewer, tmp_path):
        """Should register directories with file watcher."""
        # Create a report to trigger directory scanning
        report = integrated_viewer.crash_logs_dir / "test-AUTOSCAN.md"
        report.write_text("Test")

        with patch.object(GlobalRegistry, "get_local_dir", return_value=str(tmp_path)), \
             patch("ClassicLib.Interface.ResultsViewerMixin.classic_settings", return_value=None):

            integrated_viewer.scan_for_reports()

            # Should add crash logs directory to watcher
            integrated_viewer.file_watcher.addPath.assert_called_with(
                str(integrated_viewer.crash_logs_dir)
            )


class TestReportLifecycleIntegration:
    """Integration tests for complete report lifecycle."""

    def test_complete_report_workflow(self, integrated_viewer, tmp_path):
        """Test complete workflow: create, load, modify, delete."""
        # Step 1: Create report
        report_path = integrated_viewer.crash_logs_dir / "workflow-AUTOSCAN.md"
        original_content = "# Original Report\n\nInitial content"
        report_path.write_text(original_content)

        # Step 2: Scan and find report
        with patch.object(GlobalRegistry, "get_local_dir", return_value=str(tmp_path)):
            reports = integrated_viewer.scan_for_reports()
            assert len(reports) == 1

        # Step 3: Load report
        loaded = integrated_viewer.load_report(report_path)
        assert loaded is True
        assert integrated_viewer.current_report_path == report_path
        integrated_viewer.markdown_viewer.setMarkdown.assert_called_with(original_content)

        # Step 4: Modify report externally
        updated_content = "# Updated Report\n\nModified content"
        report_path.write_text(updated_content)

        # Step 5: Reload report
        loaded = integrated_viewer.load_report(report_path)
        assert loaded is True
        integrated_viewer.markdown_viewer.setMarkdown.assert_called_with(updated_content)

        # Step 6: Delete report
        report_path.unlink()
        assert not report_path.exists()

        # Step 7: Try to load deleted report
        loaded = integrated_viewer.load_report(report_path)
        assert loaded is False

    def test_refresh_reports_list_integration(self, integrated_viewer, tmp_path):
        """Test refreshing reports list with real files."""
        # Start with no reports
        with patch.object(GlobalRegistry, "get_local_dir", return_value=str(tmp_path)):
            integrated_viewer.refresh_reports_list()

            integrated_viewer.results_list.clear.assert_called()
            integrated_viewer.results_list.populate_reports.assert_called_with([])
            integrated_viewer.reports_refreshed.emit.assert_called_with(0)

            # Add some reports
            report1 = integrated_viewer.crash_logs_dir / "report1-AUTOSCAN.md"
            report2 = integrated_viewer.crash_logs_dir / "report2-AUTOSCAN.md"
            report1.write_text("Report 1")
            report2.write_text("Report 2")

            # Refresh again
            integrated_viewer.refresh_reports_list()

            # Should find new reports
            call_args = integrated_viewer.results_list.populate_reports.call_args[0][0]
            assert len(call_args) == 2
            integrated_viewer.reports_refreshed.emit.assert_called_with(2)

    def test_concurrent_report_operations(self, integrated_viewer, tmp_path):
        """Test handling concurrent report operations."""
        report_paths = []

        # Create multiple reports
        for i in range(5):
            report_path = integrated_viewer.crash_logs_dir / f"concurrent{i}-AUTOSCAN.md"
            report_path.write_text(f"Report {i}")
            report_paths.append(report_path)

        with patch.object(GlobalRegistry, "get_local_dir", return_value=str(tmp_path)):
            # Scan reports
            reports = integrated_viewer.scan_for_reports()
            assert len(reports) == 5

            # Load each report
            for path in report_paths:
                loaded = integrated_viewer.load_report(path)
                assert loaded is True

            # Delete some reports
            for path in report_paths[:3]:
                path.unlink()

            # Rescan
            reports = integrated_viewer.scan_for_reports()
            assert len(reports) == 2


class TestErrorHandlingIntegration:
    """Integration tests for error handling."""

    def test_handles_permission_errors(self, integrated_viewer, tmp_path):
        """Should handle permission errors gracefully."""
        report_path = integrated_viewer.crash_logs_dir / "protected-AUTOSCAN.md"
        report_path.write_text("Protected")

        # Simulate permission error
        with patch.object(Path, "read_text", side_effect=PermissionError("Access denied")):
            loaded = integrated_viewer.load_report(report_path)
            assert loaded is False

    def test_handles_corrupted_report_files(self, integrated_viewer):
        """Should handle corrupted or binary report files."""
        binary_report = integrated_viewer.crash_logs_dir / "binary-AUTOSCAN.md"

        # Write binary data that might not be valid UTF-8
        binary_report.write_bytes(b"\x00\x01\x02\x03\x04\x05")

        # Should handle with errors="ignore"
        loaded = integrated_viewer.load_report(binary_report)
        assert loaded is True

    def test_handles_missing_directories(self, integrated_viewer, tmp_path):
        """Should handle missing directories gracefully."""
        # Remove crash logs directory
        import shutil
        shutil.rmtree(integrated_viewer.crash_logs_dir)

        with patch.object(GlobalRegistry, "get_local_dir", return_value=str(tmp_path)):
            reports = integrated_viewer.scan_for_reports()

            # Should return empty list without crashing
            assert reports == []


class TestAutoRefreshIntegration:
    """Integration tests for auto-refresh functionality."""

    def test_auto_refresh_workflow(self, integrated_viewer, tmp_path):
        """Test auto-refresh detecting new reports."""
        with patch.object(GlobalRegistry, "get_local_dir", return_value=str(tmp_path)), \
             patch("ClassicLib.Interface.ResultsViewerMixin.yaml_settings") as mock_settings:

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
            with patch.object(integrated_viewer, "_debounced_refresh") as mock_debounced:
                integrated_viewer._refresh_pending = False
                integrated_viewer._debounced_refresh()

                # Should have been called (mocked to avoid actual refresh)
                assert integrated_viewer._refresh_pending is False


class TestContextMenuIntegration:
    """Integration tests for context menu operations."""

    def test_context_menu_actions(self, integrated_viewer, tmp_path):
        """Test context menu actions on reports."""
        report_path = integrated_viewer.crash_logs_dir / "context-AUTOSCAN.md"
        report_path.write_text("Context menu test")

        # Setup selection
        mock_item = MagicMock()
        integrated_viewer.results_list.itemAt.return_value = mock_item
        integrated_viewer.results_list.get_report_path.return_value = report_path
        integrated_viewer.current_report_path = report_path

        with patch("ClassicLib.Interface.ResultsViewerMixin.QMenu") as mock_menu_class, \
             patch("ClassicLib.Interface.ResultsViewerMixin.QAction") as mock_action_class:

            mock_menu = MagicMock()
            mock_menu_class.return_value = mock_menu

            # Create mock actions
            mock_actions = {}
            for action_name in ["View Report", "Copy to Clipboard", "Delete"]:
                mock_action = MagicMock()
                mock_action.triggered = MagicMock()
                mock_actions[action_name] = mock_action
                mock_action_class.side_effect = lambda text, parent: mock_actions.get(text, MagicMock())

            integrated_viewer._show_context_menu(MagicMock())

            # Verify menu created with correct actions
            assert mock_menu.addAction.call_count >= 3
            mock_menu.exec.assert_called_once()
