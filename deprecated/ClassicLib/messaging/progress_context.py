"""Backward compatibility re-exports for ProgressContext.

This module re-exports ProgressContext from its new location in progress/context.py
for backward compatibility with existing code.

Note: New code should import directly from ClassicLib.messaging.progress.context
or from ClassicLib.MessageHandler (the main package).
"""

# Re-export from new location
from ClassicLib.messaging.progress.context import ProgressContext

__all__ = ["ProgressContext"]
