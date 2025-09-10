"""
Custom widgets for the results viewer interface.

This module provides backwards compatibility for the refactored widgets
that have been moved to ClassicLib.Interface.Widgets.
"""

from __future__ import annotations

import warnings

# Import from new locations
from ClassicLib.Interface.Widgets.markdown_viewer import MarkdownViewer
from ClassicLib.Interface.Widgets.report_list import ReportListWidget
from ClassicLib.Interface.Widgets.report_metadata import ReportMetadataWidget

# Show deprecation warning
warnings.warn(
    "Importing from ClassicLib.Interface.ResultsViewerWidgets is deprecated. "
    "Import from ClassicLib.Interface.Widgets instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ReportListWidget", "MarkdownViewer", "ReportMetadataWidget"]
