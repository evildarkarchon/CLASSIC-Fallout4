"""Interface package - GUI components and utilities.

This package provides the GUI interface for CLASSIC, including:
- Composition-based controller architecture (SignalHub, FeatureContext)
- Papyrus monitoring components
- UI utilities and stylesheets

Subpackages:
- controllers: Controller classes for different UI features
- dialogs: Dialog windows
- widgets: Reusable widget components
- workers: Background worker classes
- shared: Shared components (context, signals, styles)
- Settings: Settings dialog and management
"""

from ClassicLib.Interface.dialogs.PapyrusDialog import PapyrusMonitorDialog
from ClassicLib.Interface.dialogs.Pastebin import PastebinFetchWorker
from ClassicLib.Interface.dialogs.PathDialog import ManualPathDialog
from ClassicLib.Interface.shared.context import FeatureContext, UIWidgets
from ClassicLib.Interface.shared.signal_hub import SignalHub
from ClassicLib.Interface.shared.StyleSheets import DARK_MODE
from ClassicLib.Interface.widgets.Papyrus import PapyrusMonitorWorker, PapyrusStats

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
