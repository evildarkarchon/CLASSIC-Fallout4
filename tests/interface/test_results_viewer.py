"""Unit tests for ResultsViewer components.

This module tests the ResultsViewer system including:
1. ReportListWidget - Report list management and display
2. ReportMetadataWidget - Metadata extraction and display
3. MarkdownViewer - Markdown rendering and preprocessing
4. ResultsViewerController - Controller logic

Tests are organized into:
- Pure logic tests (no Qt required)
- Widget tests (Qt required, skip in parallel)
- Integration tests (full component interaction)
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Skip Qt-dependent tests in parallel workers
pytestmark_qt = pytest.mark.skipif(
    os.environ.get("PYTEST_XDIST_WORKER") is not None,
    reason="Qt GUI tests cannot run in parallel workers",
)


# =============================================================================
# ReportListWidget Tests - Pure Logic (No Qt Required)
# =============================================================================


class TestExtractTimestamp:
    """Tests for ReportListWidget._extract_timestamp() static method."""

    @pytest.mark.unit
    def test_extract_timestamp_valid_format(self):
        """Test timestamp extraction from valid crash log filename."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        result = ReportListWidget._extract_timestamp("crash-2024-03-15-143022")
        assert result == "2024-03-15 14:30:22"

    @pytest.mark.unit
    def test_extract_timestamp_different_date(self):
        """Test timestamp extraction with different date."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        result = ReportListWidget._extract_timestamp("crash-2023-12-01-090000")
        assert result == "2023-12-01 09:00:00"

    @pytest.mark.unit
    def test_extract_timestamp_midnight(self):
        """Test timestamp extraction at midnight."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        result = ReportListWidget._extract_timestamp("crash-2024-01-01-000000")
        assert result == "2024-01-01 00:00:00"

    @pytest.mark.unit
    def test_extract_timestamp_end_of_day(self):
        """Test timestamp extraction at end of day."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        result = ReportListWidget._extract_timestamp("crash-2024-06-30-235959")
        assert result == "2024-06-30 23:59:59"

    @pytest.mark.unit
    def test_extract_timestamp_invalid_format(self):
        """Test timestamp extraction returns None for invalid format."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        result = ReportListWidget._extract_timestamp("some-random-filename")
        assert result is None

    @pytest.mark.unit
    def test_extract_timestamp_partial_match(self):
        """Test timestamp extraction returns None for partial match."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        result = ReportListWidget._extract_timestamp("crash-2024-03-15")
        assert result is None

    @pytest.mark.unit
    def test_extract_timestamp_with_suffix(self):
        """Test timestamp extraction works with -AUTOSCAN suffix."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        # The method receives the stem (without extension), but may have -AUTOSCAN
        result = ReportListWidget._extract_timestamp("crash-2024-03-15-143022-AUTOSCAN")
        # Pattern requires exact format at start, so this should match
        assert result == "2024-03-15 14:30:22"

    @pytest.mark.unit
    def test_extract_timestamp_invalid_date(self):
        """Test timestamp extraction with invalid date values."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        # Invalid month (13)
        result = ReportListWidget._extract_timestamp("crash-2024-13-15-143022")
        assert result is None

    @pytest.mark.unit
    def test_extract_timestamp_invalid_time(self):
        """Test timestamp extraction with invalid time values."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        # Invalid hour (25)
        result = ReportListWidget._extract_timestamp("crash-2024-03-15-253022")
        assert result is None


class TestDetermineReportStatus:
    """Tests for ReportListWidget._determine_report_status() static method."""

    @pytest.mark.unit
    def test_determine_status_solved(self):
        """Test status detection for solved reports."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Crash Report\n\nStatus: SOLVED\n\nRecommendations applied.")
            f.flush()
            temp_path = Path(f.name)

        try:
            result = ReportListWidget._determine_report_status(temp_path)
            assert result == "solved"
        finally:
            temp_path.unlink()

    @pytest.mark.unit
    def test_determine_status_solved_recommendations(self):
        """Test status detection when RECOMMENDATIONS keyword present."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Crash Report\n\n## RECOMMENDATIONS\n\n- Fix mod A")
            f.flush()
            temp_path = Path(f.name)

        try:
            result = ReportListWidget._determine_report_status(temp_path)
            assert result == "solved"
        finally:
            temp_path.unlink()

    @pytest.mark.unit
    def test_determine_status_unsolved(self):
        """Test status detection for unsolved reports."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Crash Report\n\nStatus: UNSOLVED\n\nNo known cause.")
            f.flush()
            temp_path = Path(f.name)

        try:
            result = ReportListWidget._determine_report_status(temp_path)
            assert result == "unsolved"
        finally:
            temp_path.unlink()

    @pytest.mark.unit
    def test_determine_status_unsolved_alternative(self):
        """Test status detection with alternative unsolved phrase."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Crash Report\n\nThe cause could not be determined.")
            f.flush()
            temp_path = Path(f.name)

        try:
            result = ReportListWidget._determine_report_status(temp_path)
            assert result == "unsolved"
        finally:
            temp_path.unlink()

    @pytest.mark.unit
    def test_determine_status_incomplete(self):
        """Test status detection for incomplete reports."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Crash Report\n\nStatus: INCOMPLETE\n\nMissing data.")
            f.flush()
            temp_path = Path(f.name)

        try:
            result = ReportListWidget._determine_report_status(temp_path)
            assert result == "incomplete"
        finally:
            temp_path.unlink()

    @pytest.mark.unit
    def test_determine_status_unknown(self):
        """Test status detection returns unknown for no indicators."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Crash Report\n\nSome generic content without status.")
            f.flush()
            temp_path = Path(f.name)

        try:
            result = ReportListWidget._determine_report_status(temp_path)
            assert result == "unknown"
        finally:
            temp_path.unlink()

    @pytest.mark.unit
    def test_determine_status_nonexistent_file(self):
        """Test status detection for nonexistent file."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        fake_path = Path("/nonexistent/path/to/report.md")
        result = ReportListWidget._determine_report_status(fake_path)
        assert result == "unknown"

    @pytest.mark.unit
    def test_determine_status_case_insensitive(self):
        """Test status detection is case insensitive."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Crash Report\n\nstatus: solved\n\nAll fixed.")
            f.flush()
            temp_path = Path(f.name)

        try:
            result = ReportListWidget._determine_report_status(temp_path)
            assert result == "solved"
        finally:
            temp_path.unlink()


# =============================================================================
# ReportMetadataWidget Tests - Pure Logic (No Qt Required)
# =============================================================================


class TestCountIssues:
    """Tests for ReportMetadataWidget._count_issues() static method."""

    @pytest.mark.unit
    def test_count_issues_with_errors(self):
        """Test counting errors in content."""
        from ClassicLib.Interface.ResultsViewer import ReportMetadataWidget

        content = "[ERROR] Something failed\n[ERROR] Another error\n[WARNING] A warning"
        result = ReportMetadataWidget._count_issues(content)
        assert result == "2 errors, 1 warnings"

    @pytest.mark.unit
    def test_count_issues_with_warnings_only(self):
        """Test counting warnings only."""
        from ClassicLib.Interface.ResultsViewer import ReportMetadataWidget

        content = "[WARNING] First warning\n[WARNING] Second warning"
        result = ReportMetadataWidget._count_issues(content)
        assert result == "2 warnings"

    @pytest.mark.unit
    def test_count_issues_with_list_items(self):
        """Test counting list items when no errors/warnings."""
        from ClassicLib.Interface.ResultsViewer import ReportMetadataWidget

        content = "- Item one\n- Item two\n- Item three\n* Item four"
        result = ReportMetadataWidget._count_issues(content)
        assert result == "4 items"

    @pytest.mark.unit
    def test_count_issues_none_found(self):
        """Test when no issues found."""
        from ClassicLib.Interface.ResultsViewer import ReportMetadataWidget

        content = "This is just plain text without any issues."
        result = ReportMetadataWidget._count_issues(content)
        assert result == "None found"

    @pytest.mark.unit
    def test_count_issues_empty_content(self):
        """Test with empty content."""
        from ClassicLib.Interface.ResultsViewer import ReportMetadataWidget

        result = ReportMetadataWidget._count_issues("")
        assert result == "None found"

    @pytest.mark.unit
    def test_count_issues_error_variations(self):
        """Test various ERROR format variations."""
        from ClassicLib.Interface.ResultsViewer import ReportMetadataWidget

        content = "[ERROR] Standard\n[! ERROR] With exclamation\n[error] Lowercase"
        result = ReportMetadataWidget._count_issues(content)
        # Should match all three variations
        assert "3 errors" in result

    @pytest.mark.unit
    def test_count_issues_warning_variations(self):
        """Test various WARNING format variations."""
        from ClassicLib.Interface.ResultsViewer import ReportMetadataWidget

        content = "[WARNING] Standard\n[! WARNING] With exclamation\n[warning] Lowercase"
        result = ReportMetadataWidget._count_issues(content)
        assert result == "3 warnings"

    @pytest.mark.unit
    def test_count_issues_mixed_content(self):
        """Test with mixed error, warning, and list content."""
        from ClassicLib.Interface.ResultsViewer import ReportMetadataWidget

        content = """[ERROR] Critical error
[WARNING] Minor warning
- List item 1
- List item 2
Some other text"""
        result = ReportMetadataWidget._count_issues(content)
        # Errors take precedence in display
        assert result == "1 errors, 1 warnings"


# =============================================================================
# MarkdownViewer Tests - Pure Logic (No Qt Required for preprocessing)
# =============================================================================


class TestPreprocessMarkdown:
    """Tests for MarkdownViewer._preprocess_markdown() method.

    Note: This tests the preprocessing logic without requiring Qt.
    We create a minimal mock to test the pure logic.
    """

    @pytest.fixture
    def preprocessor(self):
        """Create a preprocessor function without full Qt initialization."""
        # Import the class but don't instantiate it (requires Qt)
        from ClassicLib.Interface.ResultsViewer.markdown_viewer import MarkdownViewer

        # Return the unbound method - it's essentially a static function
        return MarkdownViewer._preprocess_markdown

    @pytest.mark.unit
    def test_preprocess_suspect_found(self, preprocessor):
        """Test preprocessing of SUSPECT FOUND blocks."""
        # Create a minimal self object (method doesn't use self)
        mock_self = MagicMock()

        text = "- **Checking for bad mod. SUSPECT FOUND! Remove this mod.**"
        result = preprocessor(mock_self, text)

        assert 'class="suspect-box"' in result
        assert 'class="suspect-title"' in result
        assert 'class="suspect-info"' in result
        assert "SUSPECT FOUND!" in result

    @pytest.mark.unit
    def test_preprocess_found_mod(self, preprocessor):
        """Test preprocessing of FOUND mod blocks."""
        mock_self = MagicMock()

        text = """**[!] FOUND : [Mod Category] Bad Mod Name**
    - Description of the issue
    - How to fix it
-----"""
        result = preprocessor(mock_self, text)

        assert 'class="found-box"' in result
        assert 'class="found-header"' in result

    @pytest.mark.unit
    def test_preprocess_main_error(self, preprocessor):
        """Test preprocessing of Main Error lines."""
        mock_self = MagicMock()

        text = "**Main Error: Access violation at 0x12345678**"
        result = preprocessor(mock_self, text)

        assert 'class="error-box"' in result

    @pytest.mark.unit
    def test_preprocess_buffout_version(self, preprocessor):
        """Test preprocessing of Buffout version info."""
        mock_self = MagicMock()

        text = "**Detected Buffout 4 Version: 1.26.2**"
        result = preprocessor(mock_self, text)

        assert 'class="info-box"' in result

    @pytest.mark.unit
    def test_preprocess_success_text(self, preprocessor):
        """Test preprocessing of success checkmark lines."""
        mock_self = MagicMock()

        # The pattern requires the checkmark emoji at the start
        text = "✅ All checks passed successfully"
        result = preprocessor(mock_self, text)

        assert 'class="success-text"' in result

    @pytest.mark.unit
    def test_preprocess_bold_conversion(self, preprocessor):
        """Test bold text conversion."""
        mock_self = MagicMock()

        text = "This is **bold text** in the report."
        result = preprocessor(mock_self, text)

        assert "<b>bold text</b>" in result
        assert "**" not in result

    @pytest.mark.unit
    def test_preprocess_plain_text(self, preprocessor):
        """Test that plain text passes through unchanged."""
        mock_self = MagicMock()

        text = "This is just plain text without any special markers."
        result = preprocessor(mock_self, text)

        assert result == text

    @pytest.mark.unit
    def test_preprocess_html_escaping(self, preprocessor):
        """Test that HTML special characters are escaped in special blocks."""
        mock_self = MagicMock()

        text = "**Main Error: Test <script>alert('xss')</script> error**"
        result = preprocessor(mock_self, text)

        # Should escape HTML in error box
        assert "<script>" not in result or "&lt;script&gt;" in result


# =============================================================================
# Widget Tests (Qt Required)
# =============================================================================


@pytest.mark.skipif(
    os.environ.get("PYTEST_XDIST_WORKER") is not None,
    reason="Qt GUI tests cannot run in parallel workers",
)
class TestReportListWidgetQt:
    """Qt-dependent tests for ReportListWidget."""

    @pytest.mark.unit
    def test_report_list_widget_creation(self, qtbot):
        """Test ReportListWidget can be created."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        widget = ReportListWidget()
        qtbot.addWidget(widget)

        assert widget is not None
        assert hasattr(widget, "search_box")
        assert widget.alternatingRowColors() is True

    @pytest.mark.unit
    def test_report_list_widget_populate(self, qtbot):
        """Test populating the report list."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        widget = ReportListWidget()
        qtbot.addWidget(widget)

        # Create temp report files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create test reports
            report1 = tmppath / "crash-2024-03-15-143022-AUTOSCAN.md"
            report2 = tmppath / "crash-2024-03-14-120000-AUTOSCAN.md"

            report1.write_text("# Report 1\nStatus: SOLVED")
            report2.write_text("# Report 2\nStatus: UNSOLVED")

            reports = [report1, report2]
            widget.populate_reports(reports)

            assert widget.count() == 2

    @pytest.mark.unit
    def test_report_list_widget_filter(self, qtbot):
        """Test filtering reports by search text."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        widget = ReportListWidget()
        qtbot.addWidget(widget)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            report1 = tmppath / "crash-2024-03-15-143022-AUTOSCAN.md"
            report2 = tmppath / "crash-2024-03-14-120000-AUTOSCAN.md"

            report1.write_text("# Report 1\nSOLVED")
            report2.write_text("# Report 2\nUNSOLVED")

            widget.populate_reports([report1, report2])

            # Filter by date
            widget._filter_reports("2024-03-15")

            # Check visibility
            visible_count = sum(1 for i in range(widget.count()) if not widget.item(i).isHidden())
            assert visible_count == 1

    @pytest.mark.unit
    def test_report_list_widget_get_report_path(self, qtbot):
        """Test getting report path from list item."""
        from ClassicLib.Interface.ResultsViewerWidgets import ReportListWidget

        widget = ReportListWidget()
        qtbot.addWidget(widget)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            report = tmppath / "crash-2024-03-15-143022-AUTOSCAN.md"
            report.write_text("# Test Report\nSOLVED")

            widget.populate_reports([report])

            item = widget.item(0)
            path = widget.get_report_path(item)

            assert path == report


@pytest.mark.skipif(
    os.environ.get("PYTEST_XDIST_WORKER") is not None,
    reason="Qt GUI tests cannot run in parallel workers",
)
class TestMarkdownViewerQt:
    """Qt-dependent tests for MarkdownViewer."""

    @pytest.mark.unit
    def test_markdown_viewer_creation(self, qtbot):
        """Test MarkdownViewer can be created."""
        from ClassicLib.Interface.ResultsViewer import MarkdownViewer

        viewer = MarkdownViewer()
        qtbot.addWidget(viewer)

        assert viewer is not None
        assert viewer.isReadOnly() is True

    @pytest.mark.unit
    def test_markdown_viewer_set_markdown(self, qtbot):
        """Test setting markdown content."""
        from ClassicLib.Interface.ResultsViewer import MarkdownViewer

        viewer = MarkdownViewer()
        qtbot.addWidget(viewer)

        viewer.setMarkdown("# Test Header\n\nSome content.")

        html = viewer.toHtml()
        assert "Test Header" in html

    @pytest.mark.unit
    def test_markdown_viewer_zoom_in(self, qtbot):
        """Test zoom in functionality."""
        from ClassicLib.Interface.ResultsViewer import MarkdownViewer

        viewer = MarkdownViewer()
        qtbot.addWidget(viewer)

        initial_zoom = viewer.get_zoom_level()
        viewer.zoom_in()

        assert viewer.get_zoom_level() == initial_zoom + 10

    @pytest.mark.unit
    def test_markdown_viewer_zoom_out(self, qtbot):
        """Test zoom out functionality."""
        from ClassicLib.Interface.ResultsViewer import MarkdownViewer

        viewer = MarkdownViewer()
        qtbot.addWidget(viewer)

        initial_zoom = viewer.get_zoom_level()
        viewer.zoom_out()

        assert viewer.get_zoom_level() == initial_zoom - 10

    @pytest.mark.unit
    def test_markdown_viewer_zoom_reset(self, qtbot):
        """Test zoom reset functionality."""
        from ClassicLib.Interface.ResultsViewer import MarkdownViewer

        viewer = MarkdownViewer()
        qtbot.addWidget(viewer)

        viewer.zoom_in()
        viewer.zoom_in()
        viewer.reset_zoom()

        assert viewer.get_zoom_level() == 100

    @pytest.mark.unit
    def test_markdown_viewer_zoom_limits(self, qtbot):
        """Test zoom level limits."""
        from ClassicLib.Interface.ResultsViewer import MarkdownViewer

        viewer = MarkdownViewer()
        qtbot.addWidget(viewer)

        # Test max zoom
        for _ in range(20):
            viewer.zoom_in()
        assert viewer.get_zoom_level() <= 200

        # Test min zoom
        viewer.reset_zoom()
        for _ in range(20):
            viewer.zoom_out()
        assert viewer.get_zoom_level() >= 50


@pytest.mark.skipif(
    os.environ.get("PYTEST_XDIST_WORKER") is not None,
    reason="Qt GUI tests cannot run in parallel workers",
)
class TestReportMetadataWidgetQt:
    """Qt-dependent tests for ReportMetadataWidget."""

    @pytest.mark.unit
    def test_metadata_widget_creation(self, qtbot):
        """Test ReportMetadataWidget can be created."""
        from ClassicLib.Interface.ResultsViewer import ReportMetadataWidget

        widget = ReportMetadataWidget()
        qtbot.addWidget(widget)

        assert widget is not None
        assert hasattr(widget, "date_label")
        assert hasattr(widget, "size_label")
        assert hasattr(widget, "issues_label")

    @pytest.mark.unit
    def test_metadata_widget_update(self, qtbot):
        """Test updating metadata display."""
        from ClassicLib.Interface.ResultsViewer import ReportMetadataWidget

        widget = ReportMetadataWidget()
        qtbot.addWidget(widget)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("[ERROR] Test error\n[WARNING] Test warning")
            f.flush()
            temp_path = Path(f.name)

        try:
            content = temp_path.read_text()
            widget.update_metadata(temp_path, content)

            assert "Date:" in widget.date_label.text()
            assert "N/A" not in widget.date_label.text()
            assert "Size:" in widget.size_label.text()
            assert "KB" in widget.size_label.text()
            assert "Issues:" in widget.issues_label.text()
        finally:
            temp_path.unlink()

    @pytest.mark.unit
    def test_metadata_widget_clear(self, qtbot):
        """Test clearing metadata display."""
        from ClassicLib.Interface.ResultsViewer import ReportMetadataWidget

        widget = ReportMetadataWidget()
        qtbot.addWidget(widget)

        # First set some values
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Test content")
            f.flush()
            temp_path = Path(f.name)

        try:
            widget.update_metadata(temp_path, "Test content")
            widget.clear()

            assert widget.date_label.text() == "Date: N/A"
            assert widget.size_label.text() == "Size: N/A"
            assert widget.issues_label.text() == "Issues: N/A"
        finally:
            temp_path.unlink()


# =============================================================================
# ResultsViewerController Tests
# =============================================================================


@pytest.mark.skipif(
    os.environ.get("PYTEST_XDIST_WORKER") is not None,
    reason="Qt GUI tests cannot run in parallel workers",
)
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
