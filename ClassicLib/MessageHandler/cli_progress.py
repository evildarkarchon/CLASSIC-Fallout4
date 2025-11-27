"""Backward compatibility re-exports for CLI progress bar.

This module re-exports CLIProgressBar from its new location in progress/cli_progress.py
for backward compatibility with existing code.

Note: New code should import directly from ClassicLib.MessageHandler.progress.cli_progress
or from ClassicLib.MessageHandler (the main package).
"""

# Re-export from new location
from ClassicLib.MessageHandler.progress.cli_progress import CLIProgressBar

__all__ = ["CLIProgressBar"]
