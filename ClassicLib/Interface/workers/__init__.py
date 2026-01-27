"""Background workers and thread management.

This package provides threading utilities:
- ThreadManager: Thread pool management
- Workers: Background worker classes
"""

from ClassicLib.Interface.workers.ThreadManager import ThreadManager
from ClassicLib.Interface.workers.Workers import (
    CrashLogsScanWorker,
    GameFilesScanWorker,
    UpdateCheckWorker,
)

__all__ = [
    "CrashLogsScanWorker",
    "GameFilesScanWorker",
    "ThreadManager",
    "UpdateCheckWorker",
]
