"""Progress tracking handlers for GUI and CLI modes.

This module provides the ProgressHandler protocol and concrete implementations:
- CLIProgressHandler: Text-based progress bar for CLI
- QtProgressHandler: Qt QProgressDialog for GUI (separate module)
- ProgressContext: Context manager for progress tracking
"""

from ClassicLib.MessageHandler.progress.base import ProgressHandler
from ClassicLib.MessageHandler.progress.cli_progress import CLIProgressBar, CLIProgressHandler
from ClassicLib.MessageHandler.progress.context import ProgressContext

# QtProgressHandler is imported conditionally to avoid Qt dependency

__all__ = [
    "CLIProgressBar",
    "CLIProgressHandler",
    "ProgressContext",
    "ProgressHandler",
]
