"""Reusable widget classes for the CLASSIC GUI.

This package provides reusable widgets:
- ResultsViewerWidgets: Report list widget
- UIHelpers: UI helper functions and style constants
- Papyrus: Papyrus stats and monitor worker
- markdown_viewer: Markdown viewer widget
- metadata_widget: Report metadata display widget
"""

from ClassicLib.Interface.widgets.markdown_viewer import MarkdownViewer
from ClassicLib.Interface.widgets.metadata_widget import ReportMetadataWidget
from ClassicLib.Interface.widgets.papyrus import PapyrusMonitorWorker, PapyrusStats
from ClassicLib.Interface.widgets.results_viewer_widgets import ReportListWidget
from ClassicLib.Interface.widgets.ui_helpers import (
    BOTTOM_BUTTON_STYLE,
    CHECKBOX_STYLE,
    ENABLED_BUTTON_STYLE,
    MAIN_BUTTON_STYLE,
    add_bottom_button,
    add_main_button,
    create_checkbox,
    create_separator,
    open_url,
    setup_folder_section,
)

__all__ = [
    "BOTTOM_BUTTON_STYLE",
    "CHECKBOX_STYLE",
    "ENABLED_BUTTON_STYLE",
    "MAIN_BUTTON_STYLE",
    "MarkdownViewer",
    "PapyrusMonitorWorker",
    "PapyrusStats",
    "ReportListWidget",
    "ReportMetadataWidget",
    "add_bottom_button",
    "add_main_button",
    "create_checkbox",
    "create_separator",
    "open_url",
    "setup_folder_section",
]
