"""Interface package - GUI components and utilities.

This package provides the GUI interface for CLASSIC, including:
- Composition-based controller architecture (SignalHub, FeatureContext)
- Papyrus monitoring components
- UI utilities and stylesheets
"""

from ClassicLib.Interface.context import FeatureContext, UIWidgets
from ClassicLib.Interface.Papyrus import PapyrusMonitorWorker, PapyrusStats
from ClassicLib.Interface.PapyrusDialog import PapyrusMonitorDialog
from ClassicLib.Interface.Pastebin import PastebinFetchWorker
from ClassicLib.Interface.PathDialog import ManualPathDialog
from ClassicLib.Interface.signal_hub import SignalHub
from ClassicLib.Interface.StyleSheets import DARK_MODE

__all__ = [
    # Infrastructure
    "FeatureContext",
    "SignalHub",
    "UIWidgets",
    # Papyrus components
    "PapyrusMonitorDialog",
    "PapyrusMonitorWorker",
    "PapyrusStats",
    # Other components
    "DARK_MODE",
    "ManualPathDialog",
    "PastebinFetchWorker",
]
