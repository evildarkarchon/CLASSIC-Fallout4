"""Background workers and thread management.

This package provides threading utilities:
- ThreadManager: Thread pool management
- Workers: Background worker classes
"""

from ClassicLib.Interface.workers.thread_manager import ThreadManager
from ClassicLib.Interface.workers.workers import (
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
