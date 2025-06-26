"""ClassicLib GUI components - Available only when PySide6 is installed.

This module contains all GUI-specific components that require PySide6.
Import from this module only when running in GUI mode with PySide6 available.
"""

try:
    from PySide6.QtCore import QObject, Signal
    from PySide6.QtWidgets import QWidget

    HAS_PYSIDE6 = True
except ImportError:
    HAS_PYSIDE6 = False

    # Define dummy types for static type checking
    class QObject:
        pass

    class QWidget:
        pass

    class Signal:
        def __init__(self, *args) -> None:  # noqa: ANN002
            pass


# Only import GUI components if PySide6 is available
if HAS_PYSIDE6:
    from ClassicLib.GuiComponents import ManualDocsPath
    from ClassicLib.Interface.Audio import AudioPlayer
    from ClassicLib.Interface.Papyrus import PapyrusMonitorWorker, PapyrusStats
    from ClassicLib.Interface.PapyrusDialog import PapyrusMonitorDialog
    from ClassicLib.Interface.Pastebin import PastebinFetchWorker
    from ClassicLib.Interface.PathDialog import ManualPathDialog

    __all__ = [
        "HAS_PYSIDE6",
        "AudioPlayer",
        "ManualDocsPath",
        "ManualPathDialog",
        "PapyrusMonitorDialog",
        "PapyrusMonitorWorker",
        "PapyrusStats",
        "PastebinFetchWorker",
    ]
else:
    __all__ = ["HAS_PYSIDE6"]
