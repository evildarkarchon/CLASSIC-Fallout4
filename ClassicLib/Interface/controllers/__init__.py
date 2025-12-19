"""Controller classes for CLASSIC interface composition architecture.

This package contains the controller classes that replace the previous mixin-based
architecture. Each controller handles a specific domain of functionality and
communicates with other controllers through the SignalHub.

Controllers:
    ScanController: Manages crash log and game file scanning operations.
    ResultsViewerController: Handles results tab UI and report display.
    UpdateManager: Manages application update checking.
    PapyrusManager: Controls Papyrus monitoring lifecycle.
    PastebinController: Handles Pastebin log fetching.
    BackupManager: Manages game file backup operations.
    FolderManager: Handles folder selection and validation.
    PathDialogController: Provides path selection dialogs.
    HelpAboutController: Shows help and about dialogs.
    WindowGeometryManager: Manages per-tab window sizing.
    UISetupController: Orchestrates tab UI setup.

Example:
    >>> from ClassicLib.Interface.controllers import ScanController, ResultsViewerController
    >>> scan = ScanController(context)
    >>> results = ResultsViewerController(context)

"""

from __future__ import annotations

# Infrastructure imports
from ClassicLib.Interface.context import FeatureContext, UIWidgets

# Controller imports
from ClassicLib.Interface.controllers.backup_manager import BackupManager
from ClassicLib.Interface.controllers.folder_manager import FolderManager
from ClassicLib.Interface.controllers.help_about import HelpAboutController
from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager
from ClassicLib.Interface.controllers.pastebin_controller import PastebinController
from ClassicLib.Interface.controllers.path_dialog import PathDialogController, show_game_path_dialog_static
from ClassicLib.Interface.controllers.results_viewer import ResultsViewerController
from ClassicLib.Interface.controllers.scan_controller import ScanController
from ClassicLib.Interface.controllers.update_manager import UpdateManager
from ClassicLib.Interface.controllers.window_geometry import WindowGeometryManager
from ClassicLib.Interface.signal_hub import SignalHub

# UISetupController is imported separately to avoid circular imports
# from ClassicLib.Interface.controllers.ui_setup import UISetupController

__all__ = [
    # Infrastructure
    "FeatureContext",
    "SignalHub",
    "UIWidgets",
    # Controllers
    "ScanController",
    "ResultsViewerController",
    "UpdateManager",
    "PapyrusManager",
    "PastebinController",
    "BackupManager",
    "FolderManager",
    "PathDialogController",
    "show_game_path_dialog_static",
    "HelpAboutController",
    "WindowGeometryManager",
    # "UISetupController",  # Import directly from ui_setup module
]
