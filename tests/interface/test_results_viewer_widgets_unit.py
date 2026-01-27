"""Unit tests for ResultsViewer Qt widget components.

This module tests Qt-dependent widgets:
- ReportListWidget - Report list management and display
- MarkdownViewer - Markdown rendering with zoom controls
- ReportMetadataWidget - Metadata extraction and display

All tests in this module require Qt and cannot run in parallel workers.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Skip Qt-dependent tests in parallel workers
pytestmark = pytest.mark.skipif(
    os.environ.get("PYTEST_XDIST_WORKER") is not None,
    reason="Qt GUI tests cannot run in parallel workers",
)


# =============================================================================
# ReportListWidget Tests (Qt Required)
# =============================================================================


class TestReportListWidgetQt:
    """Qt-dependent tests for ReportListWidget."""

    @pytest.mark.unit
    def test_report_list_widget_creation(self, qtbot):
        """Test ReportListWidget can be created."""
        from ClassicLib.Interface.widgets.ResultsViewerWidgets import ReportListWidget

        widget = ReportListWidget()
        qtbot.addWidget(widget)

        assert widget is not None
        assert hasattr(widget, "search_box")
        assert widget.alternatingRowColors() is True

    @pytest.mark.unit
    def test_report_list_widget_populate(self, qtbot):
        """Test populating the report list."""
        from ClassicLib.Interface.widgets.ResultsViewerWidgets import ReportListWidget

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
        from ClassicLib.Interface.widgets.ResultsViewerWidgets import ReportListWidget

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
        from ClassicLib.Interface.widgets.ResultsViewerWidgets import ReportListWidget

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


# =============================================================================
# MarkdownViewer Tests (Qt Required)
# =============================================================================


class TestMarkdownViewerQt:
    """Qt-dependent tests for MarkdownViewer."""

    @pytest.mark.unit
    def test_markdown_viewer_creation(self, qtbot):
        """Test MarkdownViewer can be created."""
        from ClassicLib.Interface.widgets.markdown_viewer import MarkdownViewer

        viewer = MarkdownViewer()
        qtbot.addWidget(viewer)

        assert viewer is not None
        assert viewer.isReadOnly() is True

    @pytest.mark.unit
    def test_markdown_viewer_set_markdown(self, qtbot):
        """Test setting markdown content."""
        from ClassicLib.Interface.widgets.markdown_viewer import MarkdownViewer

        viewer = MarkdownViewer()
        qtbot.addWidget(viewer)

        viewer.setMarkdown("# Test Header\n\nSome content.")

        html = viewer.toHtml()
        assert "Test Header" in html

    @pytest.mark.unit
    def test_markdown_viewer_zoom_in(self, qtbot):
        """Test zoom in functionality."""
        from ClassicLib.Interface.widgets.markdown_viewer import MarkdownViewer

        viewer = MarkdownViewer()
        qtbot.addWidget(viewer)

        initial_zoom = viewer.get_zoom_level()
        viewer.zoom_in()

        assert viewer.get_zoom_level() == initial_zoom + 10

    @pytest.mark.unit
    def test_markdown_viewer_zoom_out(self, qtbot):
        """Test zoom out functionality."""
        from ClassicLib.Interface.widgets.markdown_viewer import MarkdownViewer

        viewer = MarkdownViewer()
        qtbot.addWidget(viewer)

        initial_zoom = viewer.get_zoom_level()
        viewer.zoom_out()

        assert viewer.get_zoom_level() == initial_zoom - 10

    @pytest.mark.unit
    def test_markdown_viewer_zoom_reset(self, qtbot):
        """Test zoom reset functionality."""
        from ClassicLib.Interface.widgets.markdown_viewer import MarkdownViewer

        viewer = MarkdownViewer()
        qtbot.addWidget(viewer)

        viewer.zoom_in()
        viewer.zoom_in()
        viewer.reset_zoom()

        assert viewer.get_zoom_level() == 100

    @pytest.mark.unit
    def test_markdown_viewer_zoom_limits(self, qtbot):
        """Test zoom level limits."""
        from ClassicLib.Interface.widgets.markdown_viewer import MarkdownViewer

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


# =============================================================================
# ReportMetadataWidget Tests (Qt Required)
# =============================================================================


class TestReportMetadataWidgetQt:
    """Qt-dependent tests for ReportMetadataWidget."""

    @pytest.mark.unit
    def test_metadata_widget_creation(self, qtbot):
        """Test ReportMetadataWidget can be created."""
        from ClassicLib.Interface.widgets.metadata_widget import ReportMetadataWidget

        widget = ReportMetadataWidget()
        qtbot.addWidget(widget)

        assert widget is not None
        assert hasattr(widget, "date_label")
        assert hasattr(widget, "size_label")
        assert hasattr(widget, "issues_label")

    @pytest.mark.unit
    def test_metadata_widget_update(self, qtbot):
        """Test updating metadata display."""
        from ClassicLib.Interface.widgets.metadata_widget import ReportMetadataWidget

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
        from ClassicLib.Interface.widgets.metadata_widget import ReportMetadataWidget

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
