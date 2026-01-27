"""Dialog classes for the CLASSIC GUI.

This package provides dialog windows:
- Dialogs: Main dialogs module (CustomAboutDialog, CustomErrorDialog)
- PapyrusDialog: Papyrus monitor dialog
- PathDialog: Manual path selection dialog
- Pastebin: Pastebin fetch worker
"""

from ClassicLib.Interface.dialogs.Dialogs import (
    CustomAboutDialog,
    CustomErrorDialog,
)
from ClassicLib.Interface.dialogs.PapyrusDialog import PapyrusMonitorDialog
from ClassicLib.Interface.dialogs.Pastebin import PastebinFetchWorker
from ClassicLib.Interface.dialogs.PathDialog import ManualPathDialog

__all__ = [
    "CustomAboutDialog",
    "CustomErrorDialog",
    "ManualPathDialog",
    "PapyrusMonitorDialog",
    "PastebinFetchWorker",
]
