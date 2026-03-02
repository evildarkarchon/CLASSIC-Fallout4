"""Dialog classes for the CLASSIC GUI.

This package provides dialog windows:
- Dialogs: Main dialogs module (CustomAboutDialog, CustomErrorDialog)
- PapyrusDialog: Papyrus monitor dialog
- PathDialog: Manual path selection dialog
- Pastebin: Pastebin fetch worker
"""

from ClassicLib.Interface.dialogs.dialogs import (
    CustomAboutDialog,
    CustomErrorDialog,
)
from ClassicLib.Interface.dialogs.papyrus_dialog import PapyrusMonitorDialog
from ClassicLib.Interface.dialogs.pastebin import PastebinFetchWorker
from ClassicLib.Interface.dialogs.path_dialog import ManualPathDialog

__all__ = [
    "CustomAboutDialog",
    "CustomErrorDialog",
    "ManualPathDialog",
    "PapyrusMonitorDialog",
    "PastebinFetchWorker",
]
