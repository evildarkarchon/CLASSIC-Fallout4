"""MessageHandler module - Unified message handling for GUI and CLI modes.

This module provides backwards compatibility for the refactored MessageHandler.
All classes and functions are re-exported from their new locations to maintain
API compatibility.
"""
# ruff: noqa: TID252 - Relative imports intentional for __init__.py re-exports

# Re-export all public components
from .cli_progress import CLIProgressBar
from .enums import MessageTarget, MessageType
from .handler import (
    MessageHandler,
    get_message_handler,
    init_message_handler,
    msg_critical,
    msg_debug,
    msg_error,
    msg_info,
    msg_progress_context,
    msg_success,
    msg_warning,
)
from .models import Message
from .progress_context import ProgressContext

__all__ = [
    # Enums
    "MessageType",
    "MessageTarget",
    # Models
    "Message",
    # Progress components
    "CLIProgressBar",
    "ProgressContext",
    # Main handler
    "MessageHandler",
    # Functions
    "init_message_handler",
    "get_message_handler",
    "msg_info",
    "msg_warning",
    "msg_error",
    "msg_success",
    "msg_debug",
    "msg_critical",
    "msg_progress_context",
]
