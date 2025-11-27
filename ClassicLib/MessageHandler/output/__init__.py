"""Output backends for message display.

This module provides the OutputBackend protocol and concrete implementations
for different output targets:
- CLIBackend: Command-line output with emoji prefixes
- GUIBackend: Qt-based GUI output with QMessageBox dialogs
- LogBackend: Python logging integration
"""

from ClassicLib.MessageHandler.output.base import OutputBackend
from ClassicLib.MessageHandler.output.cli_backend import CLIBackend
from ClassicLib.MessageHandler.output.log_backend import LogBackend

# GUIBackend is imported conditionally to avoid Qt dependency

__all__ = [
    "CLIBackend",
    "LogBackend",
    "OutputBackend",
]
