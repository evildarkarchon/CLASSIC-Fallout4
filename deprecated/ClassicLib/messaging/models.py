"""Backward compatibility re-exports for Message model.

This module re-exports Message from its new location in core/message.py
for backward compatibility with existing code.

Note: New code should import directly from ClassicLib.messaging.core.message
or from ClassicLib.MessageHandler (the main package).
"""

# Re-export from new location
from ClassicLib.messaging.core.message import Message

__all__ = ["Message"]
