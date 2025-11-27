"""Backward compatibility re-exports for message enums.

This module re-exports MessageType and MessageTarget from their new location
in core/enums.py for backward compatibility with existing code.

Note: New code should import directly from ClassicLib.MessageHandler.core.enums
or from ClassicLib.MessageHandler (the main package).
"""

# Re-export from new location
from ClassicLib.MessageHandler.core.enums import MessageTarget, MessageType

__all__ = ["MessageTarget", "MessageType"]
