"""ResultsViewer widgets for displaying scan reports.

This package provides widgets for the Results Viewer interface,
including markdown rendering and metadata display.
"""

from ClassicLib.Interface.ResultsViewer.markdown_viewer import MarkdownViewer
from ClassicLib.Interface.ResultsViewer.metadata_widget import ReportMetadataWidget

__all__ = ["MarkdownViewer", "ReportMetadataWidget"]
