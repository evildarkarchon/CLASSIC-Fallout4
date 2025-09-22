"""Integration tests for ResultsViewerMixin report lifecycle.

Tests complete report workflows including creation, loading, modification,
and deletion with real file operations.
"""

import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from PySide6.QtCore import QFileSystemWatcher, Qt, QTimer
from PySide6.QtWidgets import QMessageBox

from ClassicLib import GlobalRegistry, MessageHandler
from ClassicLib.Interface.ResultsViewerMixin import ResultsViewerMixin
from ClassicLib.MessageHandler import init_message_handler
from tests.fixtures.qt_fixtures import qt_application


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


@pytest.mark.integration
@pytest.mark.gui
class TestReportLifecycleIntegration:
    """Integration tests for complete report lifecycle."""

    def test_complete_report_workflow(self, integrated_viewer, tmp_path, gui_message_handler):
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

    def test_concurrent_report_operations(self, integrated_viewer, tmp_path, gui_message_handler):
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


@pytest.mark.integration
@pytest.mark.gui
class TestReportDeletionIntegration:
    """Integration tests for report deletion with file system operations."""

    def test_delete_report_and_associated_crash_log(self, integrated_viewer, tmp_path, gui_message_handler):
        """Should delete both report and associated crash log file."""
        # Create report and associated crash log
        report_path = integrated_viewer.crash_logs_dir / "crash-AUTOSCAN.md"
        crash_log_path = integrated_viewer.crash_logs_dir / "crash-AUTOSCAN.log"

        report_path.write_text("Report content")
        crash_log_path.write_text("Crash log content")

        # Setup selection
        mock_item = MagicMock()
        integrated_viewer.results_list.selectedItems.return_value = [mock_item]
        integrated_viewer.results_list.get_report_path.return_value = report_path
        integrated_viewer.current_report_path = report_path

        with patch("ClassicLib.Interface.ResultsViewerMixin.QMessageBox") as mock_msgbox, \
             patch.object(integrated_viewer, "refresh_reports_list"):

            # Mock user confirmation
            mock_msgbox.StandardButton = QMessageBox.StandardButton
            mock_msgbox.question.return_value = QMessageBox.StandardButton.Yes

            integrated_viewer._delete_selected_report()

            # Both files should be deleted
            assert not report_path.exists()
            assert not crash_log_path.exists()

    def test_delete_report_only_when_no_crash_log(self, integrated_viewer, tmp_path, gui_message_handler):
        """Should handle deletion when only report exists without crash log."""
        report_path = integrated_viewer.crash_logs_dir / "report-only-AUTOSCAN.md"
        report_path.write_text("Report without crash log")

        # Setup selection
        mock_item = MagicMock()
        integrated_viewer.results_list.selectedItems.return_value = [mock_item]
        integrated_viewer.results_list.get_report_path.return_value = report_path

        with patch("ClassicLib.Interface.ResultsViewerMixin.QMessageBox") as mock_msgbox:
            mock_msgbox.StandardButton = QMessageBox.StandardButton
            mock_msgbox.question.return_value = QMessageBox.StandardButton.Yes

            integrated_viewer._delete_selected_report()

            # Only report should be deleted (no crash log to delete)
            assert not report_path.exists()


@pytest.mark.integration
@pytest.mark.gui
class TestReportListRefreshIntegration:
    """Integration tests for report list refresh operations."""

    def test_refresh_clears_viewer_when_no_reports(self, integrated_viewer, gui_message_handler):
        """Should clear viewer and show message when no reports found."""
        with patch.object(GlobalRegistry, "get_local_dir", return_value=str(integrated_viewer.test_dir)):
            integrated_viewer.refresh_reports_list()

            # Viewer should be cleared
            integrated_viewer.markdown_viewer.clear.assert_called()
            integrated_viewer.metadata_widget.clear.assert_called()

            # Should show "No Reports Found" message
            integrated_viewer.markdown_viewer.setMarkdown.assert_called()
            call_args = integrated_viewer.markdown_viewer.setMarkdown.call_args[0][0]
            assert "No Reports Found" in call_args

    def test_refresh_maintains_viewer_content_after_refresh(self, integrated_viewer, tmp_path, gui_message_handler):
        """Should maintain viewer content when refreshing with existing report loaded."""
        # Create and load a report
        report_path = integrated_viewer.crash_logs_dir / "loaded-AUTOSCAN.md"
        report_content = "Loaded report content"
        report_path.write_text(report_content)

        # Load the report
        integrated_viewer.load_report(report_path)
        assert integrated_viewer.current_report_path == report_path

        # Add a new report
        new_report = integrated_viewer.crash_logs_dir / "new-AUTOSCAN.md"
        new_report.write_text("New report")

        with patch.object(GlobalRegistry, "get_local_dir", return_value=str(tmp_path)):
            # Clear call counts
            integrated_viewer.markdown_viewer.clear.reset_mock()
            integrated_viewer.metadata_widget.clear.reset_mock()

            integrated_viewer.refresh_reports_list()

            # Viewer should NOT be cleared (report still loaded)
            integrated_viewer.markdown_viewer.clear.assert_not_called()
            integrated_viewer.metadata_widget.clear.assert_not_called()

            # Current report should remain loaded
            assert integrated_viewer.current_report_path == report_path

    def test_refresh_reports_list_integration(self, integrated_viewer, tmp_path, gui_message_handler):
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


@pytest.mark.integration
@pytest.mark.gui
class TestBackupLocationIntegration:
    """Integration tests for backup location scanning."""

    def test_scan_includes_backup_location(self, integrated_viewer, tmp_path, gui_message_handler):
        """Should scan backup location for unsolved logs."""
        # Create report in backup location
        backup_report = integrated_viewer.backup_dir / "unsolved-AUTOSCAN.md"
        backup_report.write_text("Unsolved report")

        with patch.object(GlobalRegistry, "get_local_dir", return_value=str(tmp_path)):
            reports = integrated_viewer.scan_for_reports()

            # Should find report in backup location
            assert len(reports) == 1
            assert reports[0].name == "unsolved-AUTOSCAN.md"
            assert "Unsolved Logs" in str(reports[0].parent)
