"""Interface package - GUI components and utilities."""

from ClassicLib.Interface.Papyrus import PapyrusMonitorWorker, PapyrusStats
from ClassicLib.Interface.PapyrusDialog import PapyrusMonitorDialog
from ClassicLib.Interface.Pastebin import PastebinFetchWorker
from ClassicLib.Interface.PathDialog import ManualPathDialog
from ClassicLib.Interface.StyleSheets import DARK_MODE

try:
    from ClassicLib.Interface.Audio import AudioPlayer

    _has_audio = True
except ImportError:
    _has_audio = False

if _has_audio:
    from ClassicLib.Interface.Audio import AudioPlayer  # noqa: F401

__all__ = [
    "DARK_MODE",
    "ManualPathDialog",
    "PapyrusMonitorDialog",
    "PapyrusMonitorWorker",
    "PapyrusStats",
    "PastebinFetchWorker",
]

if _has_audio:
    __all__.append("AudioPlayer")
