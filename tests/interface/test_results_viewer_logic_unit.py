"""Unit tests for ResultsViewer pure logic components.

This module tests pure logic functions that don't require Qt:
- ReportListWidget timestamp extraction and status detection
- ReportMetadataWidget issue counting
- MarkdownViewer markdown preprocessing

All tests in this module can run in parallel without Qt initialization.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

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
