"""Shared interface components.

This package provides shared interface components:
- context: Feature context and UI widgets for dependency injection
- signal_hub: Signal hub for cross-component communication
- StyleSheets: Qt stylesheets
- FolderManagement: Folder management utilities
"""

from ClassicLib.Interface.shared.context import FeatureContext, UIWidgets
from ClassicLib.Interface.shared.folder_management import FolderManagementMixin
from ClassicLib.Interface.shared.signal_hub import SignalHub
from ClassicLib.Interface.shared.style_sheets import DARK_MODE

__all__ = [
    "DARK_MODE",
    "FeatureContext",
    "FolderManagementMixin",
    "SignalHub",
    "UIWidgets",
]
