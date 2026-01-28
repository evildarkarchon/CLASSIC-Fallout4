"""Unit tests for ResultsViewerController.

This module tests the controller logic for the ResultsViewer system:
- Signal connections and initialization
- Report scanning and loading
- File watching pause/resume
- Error handling
- UI setup and panel creation
- Context menu operations
- Delete and copy operations
- Auto-refresh and debouncing

All tests in this module require Qt and cannot run in parallel workers.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Skip Qt-dependent tests in parallel workers
pytestmark = pytest.mark.skipif(
    os.environ.get("PYTEST_XDIST_WORKER") is not None,
    reason="Qt GUI tests cannot run in parallel workers",
)


# =============================================================================
# ResultsViewerController Tests
# =============================================================================


class TestResultsViewerController:
    """Tests for ResultsViewerController."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FeatureContext for testing."""
        context = MagicMock()
        context.signal_hub = MagicMock()
        context.signal_hub.pause_file_watching = MagicMock()
        context.signal_hub.pause_file_watching.connect = MagicMock()
        context.signal_hub.resume_file_watching = MagicMock()
        context.signal_hub.resume_file_watching.connect = MagicMock()
        context.signal_hub.refresh_reports_requested = MagicMock()
        context.signal_hub.refresh_reports_requested.connect = MagicMock()
        context.signal_hub.reports_count_changed = MagicMock()
        context.signal_hub.report_loaded = MagicMock()
        context.ui_widgets = MagicMock()
        context.ui_widgets.results_tab = None
        context.local_dir = None
        return context

    @pytest.fixture
    def mock_context_with_results_tab(self, mock_context, qt_application):
        """Create a mock context with a real Qt widget for results_tab."""
        from PySide6.QtWidgets import QWidget

        results_tab = QWidget()
        mock_context.ui_widgets.results_tab = results_tab
        yield mock_context
        results_tab.close()
        results_tab.deleteLater()

    @pytest.mark.unit
    def test_controller_creation(self, mock_context):
        """Test ResultsViewerController can be created."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        controller = ResultsViewerController(mock_context)

        assert controller is not None
        assert controller._ctx is mock_context
        assert controller._current_report_path is None
        assert controller._file_watching_paused is False

    @pytest.mark.unit
    def test_controller_signal_connections(self, mock_context):
        """Test that controller connects to SignalHub signals."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        ResultsViewerController(mock_context)

        # Verify signal connections were made
        mock_context.signal_hub.pause_file_watching.connect.assert_called_once()
        mock_context.signal_hub.resume_file_watching.connect.assert_called_once()
        mock_context.signal_hub.refresh_reports_requested.connect.assert_called_once()

    @pytest.mark.unit
    def test_scan_for_reports_empty(self, mock_context):
        """Test scan_for_reports returns empty list when no directories."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        mock_context.local_dir = None

        controller = ResultsViewerController(mock_context)
        controller._file_watcher = MagicMock()
        controller._file_watcher.directories.return_value = []

        with patch("ClassicLib.Interface.controllers.results_viewer.classic_settings", return_value=None):
            reports = controller.scan_for_reports()

        assert reports == []

    @pytest.mark.unit
    def test_scan_for_reports_with_directory(self, mock_context):
        """Test scan_for_reports finds reports in Crash Logs folder."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            crash_logs = tmppath / "Crash Logs"
            crash_logs.mkdir()

            # Create test reports
            report1 = crash_logs / "crash-2024-03-15-143022-AUTOSCAN.md"
            report2 = crash_logs / "crash-2024-03-14-120000-AUTOSCAN.md"
            report1.write_text("# Report 1")
            report2.write_text("# Report 2")

            mock_context.local_dir = tmppath

            controller = ResultsViewerController(mock_context)
            controller._file_watcher = MagicMock()
            controller._file_watcher.directories.return_value = []

            with patch("ClassicLib.Interface.controllers.results_viewer.classic_settings", return_value=None):
                reports = controller.scan_for_reports()

            assert len(reports) == 2
            assert report1 in reports
            assert report2 in reports

    @pytest.mark.unit
    def test_scan_for_reports_with_custom_path(self, mock_context):
        """Test scan_for_reports finds reports in custom path from settings."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create test reports in custom path
            report1 = tmppath / "crash-2024-03-15-143022-AUTOSCAN.md"
            report1.write_text("# Report 1")

            mock_context.local_dir = None

            controller = ResultsViewerController(mock_context)
            controller._file_watcher = MagicMock()
            controller._file_watcher.directories.return_value = []

            with patch(
                "ClassicLib.Interface.controllers.results_viewer.classic_settings",
                return_value=str(tmppath),
            ):
                reports = controller.scan_for_reports()

            assert len(reports) == 1
            assert report1 in reports

    @pytest.mark.unit
    def test_scan_for_reports_adds_backup_location(self, mock_context):
        """Test scan_for_reports includes backup location for unsolved logs."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create backup location
            backup_path = tmppath / "CLASSIC Backup" / "Unsolved Logs"
            backup_path.mkdir(parents=True)
            report1 = backup_path / "crash-2024-03-10-090000-AUTOSCAN.md"
            report1.write_text("# Backup Report")

            mock_context.local_dir = tmppath

            controller = ResultsViewerController(mock_context)
            controller._file_watcher = MagicMock()
            controller._file_watcher.directories.return_value = []

            with patch("ClassicLib.Interface.controllers.results_viewer.classic_settings", return_value=None):
                reports = controller.scan_for_reports()

            assert len(reports) == 1
            assert report1 in reports

    @pytest.mark.unit
    def test_scan_for_reports_removes_duplicates(self, mock_context):
        """Test scan_for_reports removes duplicate paths."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            crash_logs = tmppath / "Crash Logs"
            crash_logs.mkdir()

            # Create test report
            report1 = crash_logs / "crash-2024-03-15-143022-AUTOSCAN.md"
            report1.write_text("# Report 1")

            mock_context.local_dir = tmppath

            controller = ResultsViewerController(mock_context)
            controller._file_watcher = MagicMock()
            controller._file_watcher.directories.return_value = []

            # Mock custom path to point to same directory
            with patch(
                "ClassicLib.Interface.controllers.results_viewer.classic_settings",
                return_value=str(crash_logs),
            ):
                reports = controller.scan_for_reports()

            # Should only have one entry despite being in both locations
            assert len(reports) == 1
            assert report1 in reports

    @pytest.mark.unit
    def test_pause_resume_file_watching(self, mock_context):
        """Test pause and resume file watching."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        controller = ResultsViewerController(mock_context)

        assert controller._file_watching_paused is False

        controller._pause_file_watching()
        assert controller._file_watching_paused is True

        controller._resume_file_watching()
        assert controller._file_watching_paused is False

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.results_viewer.msg_error")
    def test_load_report_nonexistent(self, mock_msg, mock_context, qtbot):
        """Test load_report handles nonexistent file."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        controller = ResultsViewerController(mock_context)
        controller._markdown_viewer = MagicMock()
        controller._metadata_widget = MagicMock()

        fake_path = Path("/nonexistent/report.md")

        result = controller.load_report(fake_path)

        # Process any pending Qt events (like QTimer.singleShot)
        from PySide6.QtCore import QCoreApplication

        QCoreApplication.processEvents()

        assert result is False

    @pytest.mark.unit
    def test_load_report_success(self, mock_context):
        """Test successful report loading."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test Report\n\nSome content.")
            f.flush()
            temp_path = Path(f.name)

        try:
            controller = ResultsViewerController(mock_context)
            controller._markdown_viewer = MagicMock()
            controller._metadata_widget = MagicMock()

            result = controller.load_report(temp_path)

            assert result is True
            assert controller._current_report_path == temp_path
            controller._markdown_viewer.setMarkdown.assert_called_once()
            controller._metadata_widget.update_metadata.assert_called_once()
            mock_context.signal_hub.report_loaded.emit.assert_called_once_with(temp_path)
        finally:
            temp_path.unlink()

    @pytest.mark.unit
    def test_load_report_without_widgets(self, mock_context):
        """Test load_report returns False when widgets not initialized."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        controller = ResultsViewerController(mock_context)
        controller._markdown_viewer = None
        controller._metadata_widget = None

        result = controller.load_report(Path("/some/path.md"))

        assert result is False

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.results_viewer.read_file_sync")
    @patch("ClassicLib.Interface.controllers.results_viewer.msg_error")
    @patch("ClassicLib.Interface.controllers.results_viewer.msg_warning")
    def test_load_report_oserror_fallback_to_plain_text(self, mock_warning, mock_error, mock_read, mock_context, qt_application):
        """Test load_report falls back to plain text on OSError."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test Report")
            temp_path = Path(f.name)

        try:
            controller = ResultsViewerController(mock_context)
            controller._markdown_viewer = MagicMock()
            controller._metadata_widget = MagicMock()

            # First call raises OSError, second call (fallback) succeeds
            mock_read.side_effect = [OSError("Markdown error"), "Fallback content"]

            result = controller.load_report(temp_path)

            from PySide6.QtCore import QCoreApplication

            QCoreApplication.processEvents()

            # Result should be True because fallback succeeded
            assert result is True
            controller._markdown_viewer.setPlainText.assert_called_once_with("Fallback content")
        finally:
            temp_path.unlink()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.results_viewer.QTimer")
    @patch("ClassicLib.Interface.controllers.results_viewer.read_file_sync")
    @patch("ClassicLib.Interface.controllers.results_viewer.msg_error")
    def test_load_report_oserror_fallback_also_fails(self, mock_error, mock_read, mock_timer, mock_context):
        """Test load_report returns False when both markdown and plain text fail."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test Report")
            temp_path = Path(f.name)

        try:
            controller = ResultsViewerController(mock_context)
            controller._markdown_viewer = MagicMock()
            controller._metadata_widget = MagicMock()

            # Both calls raise OSError
            mock_read.side_effect = OSError("IO Error")

            result = controller.load_report(temp_path)

            # Result should be False as fallback also fails
            assert result is False
            # Verify that QTimer.singleShot was used for error handling
            assert mock_timer.singleShot.call_count >= 1
        finally:
            temp_path.unlink()


# =============================================================================
# Setup and Panel Creation Tests
# =============================================================================


class TestResultsViewerSetup:
    """Tests for ResultsViewerController setup and panel creation."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FeatureContext for testing."""
        context = MagicMock()
        context.signal_hub = MagicMock()
        context.signal_hub.pause_file_watching = MagicMock()
        context.signal_hub.pause_file_watching.connect = MagicMock()
        context.signal_hub.resume_file_watching = MagicMock()
        context.signal_hub.resume_file_watching.connect = MagicMock()
        context.signal_hub.refresh_reports_requested = MagicMock()
        context.signal_hub.refresh_reports_requested.connect = MagicMock()
        context.signal_hub.reports_count_changed = MagicMock()
        context.signal_hub.report_loaded = MagicMock()
        context.ui_widgets = MagicMock()
        context.ui_widgets.results_tab = None
        context.local_dir = None
        return context

    @pytest.mark.unit
    @pytest.mark.gui
    def test_setup_results_tab_no_widget(self, mock_context):
        """Test setup_results_tab handles missing results_tab widget."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        mock_context.ui_widgets.results_tab = None

        controller = ResultsViewerController(mock_context)
        controller.setup_results_tab()

        # Should return early without error
        assert controller._results_list is None
        assert controller._markdown_viewer is None

    @pytest.mark.unit
    @pytest.mark.gui
    def test_setup_results_tab_creates_widgets(self, mock_context, qt_application):
        """Test setup_results_tab creates all required widgets."""
        from PySide6.QtWidgets import QWidget

        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        results_tab = QWidget()
        mock_context.ui_widgets.results_tab = results_tab

        try:
            controller = ResultsViewerController(mock_context)

            with patch("ClassicLib.Interface.controllers.results_viewer.classic_settings", return_value=None):
                with patch("ClassicLib.Interface.controllers.results_viewer.yaml_settings", return_value=False):
                    controller.setup_results_tab()

            # Verify widgets were created
            assert controller._results_list is not None
            assert controller._markdown_viewer is not None
            assert controller._metadata_widget is not None
            assert controller._file_watcher is not None
            assert controller._refresh_timer is not None
        finally:
            results_tab.close()
            results_tab.deleteLater()

    @pytest.mark.unit
    @pytest.mark.gui
    def test_setup_results_tab_connects_file_watcher(self, mock_context, qt_application):
        """Test setup_results_tab connects file watcher to directory change handler."""
        from PySide6.QtWidgets import QWidget

        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        results_tab = QWidget()
        mock_context.ui_widgets.results_tab = results_tab

        try:
            controller = ResultsViewerController(mock_context)

            with patch("ClassicLib.Interface.controllers.results_viewer.classic_settings", return_value=None):
                with patch("ClassicLib.Interface.controllers.results_viewer.yaml_settings", return_value=False):
                    controller.setup_results_tab()

            # File watcher should be set up
            assert controller._file_watcher is not None
        finally:
            results_tab.close()
            results_tab.deleteLater()


# =============================================================================
# Refresh and Report List Tests
# =============================================================================


class TestResultsViewerRefresh:
    """Tests for ResultsViewerController refresh operations."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FeatureContext for testing."""
        context = MagicMock()
        context.signal_hub = MagicMock()
        context.signal_hub.pause_file_watching = MagicMock()
        context.signal_hub.pause_file_watching.connect = MagicMock()
        context.signal_hub.resume_file_watching = MagicMock()
        context.signal_hub.resume_file_watching.connect = MagicMock()
        context.signal_hub.refresh_reports_requested = MagicMock()
        context.signal_hub.refresh_reports_requested.connect = MagicMock()
        context.signal_hub.reports_count_changed = MagicMock()
        context.signal_hub.report_loaded = MagicMock()
        context.ui_widgets = MagicMock()
        context.ui_widgets.results_tab = None
        context.local_dir = None
        return context

    @pytest.mark.unit
    def test_refresh_reports_list_no_widgets(self, mock_context):
        """Test refresh_reports_list returns early when widgets not initialized."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        controller = ResultsViewerController(mock_context)
        controller._results_list = None
        controller._markdown_viewer = None

        # Should not raise
        controller.refresh_reports_list()

    @pytest.mark.unit
    def test_refresh_reports_list_clears_and_populates(self, mock_context):
        """Test refresh_reports_list clears and repopulates the list."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            crash_logs = tmppath / "Crash Logs"
            crash_logs.mkdir()

            report1 = crash_logs / "crash-2024-03-15-143022-AUTOSCAN.md"
            report1.write_text("# Report 1\n\nSOLVED")

            mock_context.local_dir = tmppath

            controller = ResultsViewerController(mock_context)
            controller._results_list = MagicMock()
            controller._results_list.count.return_value = 1
            controller._markdown_viewer = MagicMock()
            controller._metadata_widget = MagicMock()
            controller._file_watcher = MagicMock()
            controller._file_watcher.directories.return_value = []

            with patch("ClassicLib.Interface.controllers.results_viewer.classic_settings", return_value=None):
                controller.refresh_reports_list()

            controller._results_list.clear.assert_called_once()
            controller._results_list.populate_reports.assert_called_once()
            mock_context.signal_hub.reports_count_changed.emit.assert_called()

    @pytest.mark.unit
    def test_refresh_reports_list_no_reports_shows_message(self, mock_context):
        """Test refresh_reports_list shows message when no reports found."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        mock_context.local_dir = None

        controller = ResultsViewerController(mock_context)
        controller._results_list = MagicMock()
        controller._results_list.count.return_value = 0
        controller._markdown_viewer = MagicMock()
        controller._metadata_widget = MagicMock()
        controller._file_watcher = MagicMock()
        controller._file_watcher.directories.return_value = []

        with patch("ClassicLib.Interface.controllers.results_viewer.classic_settings", return_value=None):
            controller.refresh_reports_list()

        # Should show "No Reports Found" message
        controller._markdown_viewer.clear.assert_called_once()
        controller._markdown_viewer.setMarkdown.assert_called()
        call_args = controller._markdown_viewer.setMarkdown.call_args[0][0]
        assert "No Reports Found" in call_args

    @pytest.mark.unit
    def test_refresh_reports_list_preserves_current_report(self, mock_context):
        """Test refresh_reports_list preserves selection when current report still exists."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            crash_logs = tmppath / "Crash Logs"
            crash_logs.mkdir()

            report1 = crash_logs / "crash-2024-03-15-143022-AUTOSCAN.md"
            report1.write_text("# Report 1\n\nSOLVED")

            mock_context.local_dir = tmppath

            controller = ResultsViewerController(mock_context)
            controller._results_list = MagicMock()
            controller._results_list.count.return_value = 1
            controller._markdown_viewer = MagicMock()
            controller._metadata_widget = MagicMock()
            controller._file_watcher = MagicMock()
            controller._file_watcher.directories.return_value = []
            controller._current_report_path = report1  # Report exists

            with patch("ClassicLib.Interface.controllers.results_viewer.classic_settings", return_value=None):
                controller.refresh_reports_list()

            # Current report should be preserved
            assert controller._current_report_path == report1


# =============================================================================
# Delete and Copy Tests
# =============================================================================


class TestResultsViewerDeleteCopy:
    """Tests for ResultsViewerController delete and copy operations."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FeatureContext for testing."""
        context = MagicMock()
        context.signal_hub = MagicMock()
        context.signal_hub.pause_file_watching = MagicMock()
        context.signal_hub.pause_file_watching.connect = MagicMock()
        context.signal_hub.resume_file_watching = MagicMock()
        context.signal_hub.resume_file_watching.connect = MagicMock()
        context.signal_hub.refresh_reports_requested = MagicMock()
        context.signal_hub.refresh_reports_requested.connect = MagicMock()
        context.signal_hub.reports_count_changed = MagicMock()
        context.signal_hub.report_loaded = MagicMock()
        context.ui_widgets = MagicMock()
        context.ui_widgets.results_tab = MagicMock()
        context.local_dir = None
        return context

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.results_viewer.msg_warning")
    def test_delete_selected_report_no_selection(self, mock_warning, mock_context):
        """Test _delete_selected_report shows warning when nothing selected."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        controller = ResultsViewerController(mock_context)
        controller._results_list = MagicMock()
        controller._results_list.selectedItems.return_value = []

        controller._delete_selected_report()

        mock_warning.assert_called_once_with("No report selected")

    @pytest.mark.unit
    def test_delete_selected_report_no_list(self, mock_context):
        """Test _delete_selected_report returns early when list not initialized."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        controller = ResultsViewerController(mock_context)
        controller._results_list = None

        # Should not raise
        controller._delete_selected_report()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.results_viewer.QMessageBox")
    @patch("ClassicLib.Interface.controllers.results_viewer.msg_info")
    def test_delete_selected_report_confirmed(self, mock_info, mock_msgbox, mock_context):
        """Test _delete_selected_report deletes file when confirmed."""
        from PySide6.QtWidgets import QMessageBox as RealQMessageBox

        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            report_path = tmppath / "crash-2024-03-15-143022-AUTOSCAN.md"
            report_path.write_text("# Test Report")

            mock_item = MagicMock()
            controller = ResultsViewerController(mock_context)
            controller._results_list = MagicMock()
            controller._results_list.selectedItems.return_value = [mock_item]
            controller._results_list.get_report_path.return_value = report_path
            controller._markdown_viewer = MagicMock()
            controller._metadata_widget = MagicMock()
            controller._file_watcher = MagicMock()
            controller._file_watcher.directories.return_value = []
            controller._current_report_path = report_path

            # Mock confirmation dialog to return Yes
            mock_msgbox.question.return_value = RealQMessageBox.StandardButton.Yes
            mock_msgbox.StandardButton = RealQMessageBox.StandardButton

            with patch("ClassicLib.Interface.controllers.results_viewer.classic_settings", return_value=None):
                controller._delete_selected_report()

            # File should be deleted
            assert not report_path.exists()
            # Current report should be cleared
            assert controller._current_report_path is None

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.results_viewer.QMessageBox")
    def test_delete_selected_report_cancelled(self, mock_msgbox, mock_context):
        """Test _delete_selected_report does not delete when cancelled."""
        from PySide6.QtWidgets import QMessageBox as RealQMessageBox

        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            report_path = tmppath / "crash-2024-03-15-143022-AUTOSCAN.md"
            report_path.write_text("# Test Report")

            mock_item = MagicMock()
            controller = ResultsViewerController(mock_context)
            controller._results_list = MagicMock()
            controller._results_list.selectedItems.return_value = [mock_item]
            controller._results_list.get_report_path.return_value = report_path

            # Mock confirmation dialog to return No
            mock_msgbox.question.return_value = RealQMessageBox.StandardButton.No
            mock_msgbox.StandardButton = RealQMessageBox.StandardButton

            controller._delete_selected_report()

            # File should still exist
            assert report_path.exists()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.results_viewer.QMessageBox")
    @patch("ClassicLib.Interface.controllers.results_viewer.msg_info")
    def test_delete_selected_report_also_deletes_crash_log(self, mock_info, mock_msgbox, mock_context):
        """Test _delete_selected_report also deletes associated crash log."""
        from PySide6.QtWidgets import QMessageBox as RealQMessageBox

        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            report_path = tmppath / "crash-2024-03-15-143022-AUTOSCAN.md"
            crash_log_path = tmppath / "crash-2024-03-15-143022-AUTOSCAN.log"
            report_path.write_text("# Test Report")
            crash_log_path.write_text("Crash log content")

            mock_item = MagicMock()
            controller = ResultsViewerController(mock_context)
            controller._results_list = MagicMock()
            controller._results_list.selectedItems.return_value = [mock_item]
            controller._results_list.get_report_path.return_value = report_path
            controller._markdown_viewer = MagicMock()
            controller._metadata_widget = MagicMock()
            controller._file_watcher = MagicMock()
            controller._file_watcher.directories.return_value = []

            mock_msgbox.question.return_value = RealQMessageBox.StandardButton.Yes
            mock_msgbox.StandardButton = RealQMessageBox.StandardButton

            with patch("ClassicLib.Interface.controllers.results_viewer.classic_settings", return_value=None):
                controller._delete_selected_report()

            # Both files should be deleted
            assert not report_path.exists()
            assert not crash_log_path.exists()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.results_viewer.msg_warning")
    def test_copy_report_no_report_loaded(self, mock_warning, mock_context):
        """Test _copy_report shows warning when no report loaded."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        controller = ResultsViewerController(mock_context)
        controller._current_report_path = None

        controller._copy_report()

        mock_warning.assert_called_once_with("No report loaded")

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.results_viewer.read_file_sync")
    @patch("ClassicLib.Interface.controllers.results_viewer.msg_info")
    def test_copy_report_success(self, mock_info, mock_read, mock_context, qt_application):
        """Test _copy_report copies content to clipboard."""
        from PySide6.QtWidgets import QApplication

        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test Report Content")
            temp_path = Path(f.name)

        try:
            mock_read.return_value = "# Test Report Content"

            controller = ResultsViewerController(mock_context)
            controller._current_report_path = temp_path

            controller._copy_report()

            mock_info.assert_called_once_with("Report copied to clipboard")
            # Verify clipboard content
            assert QApplication.clipboard().text() == "# Test Report Content"
        finally:
            temp_path.unlink()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.results_viewer.read_file_sync")
    @patch("ClassicLib.Interface.controllers.results_viewer.msg_error")
    def test_copy_report_error(self, mock_error, mock_read, mock_context, qt_application):
        """Test _copy_report handles errors."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        mock_read.side_effect = OSError("Read failed")

        controller = ResultsViewerController(mock_context)
        controller._current_report_path = Path("/some/path.md")

        controller._copy_report()

        mock_error.assert_called_once()


# =============================================================================
# File Watcher and Auto-Refresh Tests
# =============================================================================


class TestResultsViewerFileWatcher:
    """Tests for ResultsViewerController file watcher and auto-refresh."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FeatureContext for testing."""
        context = MagicMock()
        context.signal_hub = MagicMock()
        context.signal_hub.pause_file_watching = MagicMock()
        context.signal_hub.pause_file_watching.connect = MagicMock()
        context.signal_hub.resume_file_watching = MagicMock()
        context.signal_hub.resume_file_watching.connect = MagicMock()
        context.signal_hub.refresh_reports_requested = MagicMock()
        context.signal_hub.refresh_reports_requested.connect = MagicMock()
        context.signal_hub.reports_count_changed = MagicMock()
        context.signal_hub.report_loaded = MagicMock()
        context.ui_widgets = MagicMock()
        context.ui_widgets.results_tab = None
        context.local_dir = None
        return context

    @pytest.mark.unit
    def test_on_directory_changed_paused(self, mock_context):
        """Test _on_directory_changed skips when file watching is paused."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        controller = ResultsViewerController(mock_context)
        controller._file_watching_paused = True
        controller._refresh_pending = False

        controller._on_directory_changed("/some/path")

        # Should not set refresh pending
        assert controller._refresh_pending is False

    @pytest.mark.unit
    def test_on_directory_changed_sets_refresh_pending(self, mock_context, qt_application):
        """Test _on_directory_changed sets refresh_pending and schedules debounce."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        controller = ResultsViewerController(mock_context)
        controller._file_watching_paused = False
        controller._refresh_pending = False

        controller._on_directory_changed("/some/path")

        assert controller._refresh_pending is True

    @pytest.mark.unit
    def test_on_directory_changed_debounce(self, mock_context, qt_application):
        """Test _on_directory_changed does not trigger multiple pending refreshes."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        controller = ResultsViewerController(mock_context)
        controller._file_watching_paused = False
        controller._refresh_pending = True  # Already pending

        # Second call should return early
        controller._on_directory_changed("/some/path")

        # Still just one pending
        assert controller._refresh_pending is True

    @pytest.mark.unit
    def test_debounced_refresh_clears_pending(self, mock_context):
        """Test _debounced_refresh clears pending flag and calls refresh."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        controller = ResultsViewerController(mock_context)
        controller._refresh_pending = True
        controller._results_list = MagicMock()
        controller._results_list.count.return_value = 0
        controller._markdown_viewer = MagicMock()
        controller._metadata_widget = MagicMock()
        controller._file_watcher = MagicMock()
        controller._file_watcher.directories.return_value = []

        with patch("ClassicLib.Interface.controllers.results_viewer.classic_settings", return_value=None):
            controller._debounced_refresh()

        assert controller._refresh_pending is False

    @pytest.mark.unit
    def test_setup_auto_refresh_disabled(self, mock_context, qt_application):
        """Test _setup_auto_refresh does nothing when auto-refresh disabled."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        controller = ResultsViewerController(mock_context)
        controller._refresh_timer = MagicMock()

        with patch("ClassicLib.Interface.controllers.results_viewer.yaml_settings", return_value=False):
            controller._setup_auto_refresh()

        controller._refresh_timer.start.assert_not_called()

    @pytest.mark.unit
    def test_setup_auto_refresh_enabled(self, mock_context, qt_application):
        """Test _setup_auto_refresh starts timer when enabled."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        controller = ResultsViewerController(mock_context)
        controller._refresh_timer = MagicMock()

        with patch("ClassicLib.Interface.controllers.results_viewer.yaml_settings") as mock_yaml:
            # First call for AutoRefresh, second for RefreshInterval
            mock_yaml.side_effect = [True, 3000]
            controller._setup_auto_refresh()

        controller._refresh_timer.start.assert_called_once_with(3000)

    @pytest.mark.unit
    def test_setup_auto_refresh_no_timer(self, mock_context):
        """Test _setup_auto_refresh handles missing timer gracefully."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        controller = ResultsViewerController(mock_context)
        controller._refresh_timer = None

        # Should not raise
        controller._setup_auto_refresh()


# =============================================================================
# Context Menu and Report Selection Tests
# =============================================================================


class TestResultsViewerContextMenu:
    """Tests for ResultsViewerController context menu and selection."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock FeatureContext for testing."""
        context = MagicMock()
        context.signal_hub = MagicMock()
        context.signal_hub.pause_file_watching = MagicMock()
        context.signal_hub.pause_file_watching.connect = MagicMock()
        context.signal_hub.resume_file_watching = MagicMock()
        context.signal_hub.resume_file_watching.connect = MagicMock()
        context.signal_hub.refresh_reports_requested = MagicMock()
        context.signal_hub.refresh_reports_requested.connect = MagicMock()
        context.signal_hub.reports_count_changed = MagicMock()
        context.signal_hub.report_loaded = MagicMock()
        context.ui_widgets = MagicMock()
        context.ui_widgets.results_tab = None
        context.local_dir = None
        return context

    @pytest.mark.unit
    def test_on_report_selected_no_list(self, mock_context):
        """Test _on_report_selected returns early when list not initialized."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        controller = ResultsViewerController(mock_context)
        controller._results_list = None

        # Should not raise
        controller._on_report_selected()

    @pytest.mark.unit
    def test_on_report_selected_no_selection(self, mock_context):
        """Test _on_report_selected handles empty selection."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        controller = ResultsViewerController(mock_context)
        controller._results_list = MagicMock()
        controller._results_list.selectedItems.return_value = []

        # Should return early without loading
        controller._on_report_selected()

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.results_viewer.msg_error")
    def test_on_report_selected_no_path(self, mock_error, mock_context):
        """Test _on_report_selected shows error when path not found."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        mock_item = MagicMock()
        mock_item.text.return_value = "Some Report"

        controller = ResultsViewerController(mock_context)
        controller._results_list = MagicMock()
        controller._results_list.selectedItems.return_value = [mock_item]
        controller._results_list.get_report_path.return_value = None

        controller._on_report_selected()

        mock_error.assert_called_once()

    @pytest.mark.unit
    def test_on_report_selected_loads_report(self, mock_context):
        """Test _on_report_selected loads the selected report."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test Report")
            temp_path = Path(f.name)

        try:
            mock_item = MagicMock()

            controller = ResultsViewerController(mock_context)
            controller._results_list = MagicMock()
            controller._results_list.selectedItems.return_value = [mock_item]
            controller._results_list.get_report_path.return_value = temp_path
            controller._markdown_viewer = MagicMock()
            controller._metadata_widget = MagicMock()

            controller._on_report_selected()

            controller._markdown_viewer.setMarkdown.assert_called_once()
        finally:
            temp_path.unlink()

    @pytest.mark.unit
    def test_show_context_menu_no_list(self, mock_context):
        """Test _show_context_menu returns early when list not initialized."""
        from PySide6.QtCore import QPoint

        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        controller = ResultsViewerController(mock_context)
        controller._results_list = None

        # Should not raise
        controller._show_context_menu(QPoint(0, 0))

    @pytest.mark.unit
    def test_show_context_menu_no_item(self, mock_context, qt_application):
        """Test _show_context_menu returns early when no item at position."""
        from PySide6.QtCore import QPoint

        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        controller = ResultsViewerController(mock_context)
        controller._results_list = MagicMock()
        controller._results_list.itemAt.return_value = None

        # Should not raise
        controller._show_context_menu(QPoint(0, 0))


# =============================================================================
# Open Folder Tests
# =============================================================================


class TestResultsViewerOpenFolder:
    """Tests for ResultsViewerController open folder functionality."""

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.results_viewer.get_local_dir", return_value=None)
    @patch("ClassicLib.Interface.controllers.results_viewer.msg_warning")
    def test_open_reports_folder_no_local_dir(self, mock_warning, mock_get_local_dir):
        """Test _open_reports_folder warns when local dir not configured."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        ResultsViewerController._open_reports_folder()

        mock_warning.assert_called_once_with("Local directory not configured")

    @pytest.mark.unit
    @patch("ClassicLib.Interface.controllers.results_viewer.msg_warning")
    def test_open_reports_folder_no_crash_logs_dir(self, mock_warning):
        """Test _open_reports_folder warns when Crash Logs folder doesn't exist."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("ClassicLib.Interface.controllers.results_viewer.get_local_dir", return_value=tmpdir):
                # Note: Crash Logs folder is not created

                ResultsViewerController._open_reports_folder()

                mock_warning.assert_called_once_with("Crash Logs folder does not exist")

    @pytest.mark.unit
    @patch("PySide6.QtGui.QDesktopServices")
    def test_open_reports_folder_success(self, mock_desktop, qt_application):
        """Test _open_reports_folder opens folder in file explorer."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        with tempfile.TemporaryDirectory() as tmpdir:
            crash_logs = Path(tmpdir) / "Crash Logs"
            crash_logs.mkdir()

            with patch("ClassicLib.Interface.controllers.results_viewer.get_local_dir", return_value=tmpdir):
                ResultsViewerController._open_reports_folder()

                mock_desktop.openUrl.assert_called_once()

    @pytest.mark.unit
    @patch("PySide6.QtGui.QDesktopServices")
    @patch("ClassicLib.Interface.controllers.results_viewer.msg_error")
    def test_open_reports_folder_error(self, mock_error, mock_desktop, qt_application):
        """Test _open_reports_folder handles errors."""
        from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController

        with tempfile.TemporaryDirectory() as tmpdir:
            crash_logs = Path(tmpdir) / "Crash Logs"
            crash_logs.mkdir()

            mock_desktop.openUrl.side_effect = RuntimeError("Desktop error")

            with patch("ClassicLib.Interface.controllers.results_viewer.get_local_dir", return_value=tmpdir):
                ResultsViewerController._open_reports_folder()

                mock_error.assert_called_once()
