"""MessageHandler module - Unified message handling for GUI and CLI modes.

This module provides the public API for message handling in CLASSIC.
It supports both GUI (Qt-based) and CLI modes with automatic adaptation.

Architecture:
    - Core types: MessageType, MessageTarget, Message
    - Output backends: CLIBackend, GUIBackend, LogBackend
    - Progress handlers: CLIProgressBar, QtProgressHandler
    - Main handlers: MessageHandler (CLI), QtMessageHandler (GUI)

Usage:
    # Initialize at startup
    from ClassicLib.MessageHandler import init_message_handler, msg_info
    init_message_handler(is_gui_mode=False)  # CLI mode

    # Use convenience functions
    msg_info("Operation completed")
    msg_error("An error occurred", details="Stack trace...")

    # Progress tracking
    from ClassicLib.MessageHandler import msg_progress_context
    with msg_progress_context("Processing", total=100) as progress:
        for i in range(100):
            do_work()
            progress.update(1)
"""

# ruff: noqa: TID252 - Relative imports intentional for __init__.py re-exports

# Core types from new module structure
from .core.enums import MessageTarget, MessageType
from .core.message import Message

# Formatting utilities (Rust-accelerated)
from .formatting import RUST_AVAILABLE, format_log_message, strip_emoji

# Main handler and convenience functions
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

# Progress components
from .progress.cli_progress import CLIProgressBar
from .progress.context import ProgressContext

__all__ = [
    # Core types
    "Message",
    "MessageTarget",
    "MessageType",
    # Progress components
    "CLIProgressBar",
    "ProgressContext",
    # Formatting utilities
    "RUST_AVAILABLE",
    "format_log_message",
    "strip_emoji",
    # Main handler
    "MessageHandler",
    # Functions
    "get_message_handler",
    "init_message_handler",
    "msg_critical",
    "msg_debug",
    "msg_error",
    "msg_info",
    "msg_progress_context",
    "msg_success",
    "msg_warning",
]
