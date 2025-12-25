"""Unit tests for ResultsViewerController.

This module tests the controller logic for the ResultsViewer system:
- Signal connections and initialization
- Report scanning and loading
- File watching pause/resume
- Error handling

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
