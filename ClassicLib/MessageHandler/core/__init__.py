"""Core message handling types and routing logic.

This module provides the fundamental types for the message handling system:
- MessageType: Enumeration of message categories
- MessageTarget: Enumeration of message routing targets
- Message: Data structure for message content and metadata
- MessageRouter: Logic for determining message display based on mode and target
"""

from ClassicLib.MessageHandler.core.enums import MessageTarget, MessageType
from ClassicLib.MessageHandler.core.message import Message
from ClassicLib.MessageHandler.core.router import MessageRouter

__all__ = [
    "Message",
    "MessageRouter",
    "MessageTarget",
    "MessageType",
]
