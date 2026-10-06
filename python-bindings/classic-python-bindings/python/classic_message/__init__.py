"""Python module for CLASSIC message routing and formatting.

This module provides Rust-accelerated message handling with type-safe
message types, targets, and formatting utilities.

Core Classes:
    MessageType: Enum for message categories (INFO, WARNING, ERROR, etc.)
    MessageTarget: Enum for message routing (ALL, GUI, CONSOLE, LOG_ONLY)
    Message: Data structure for messages with content, type, target, and metadata
    Logger: Centralized logging facility for the CLASSIC application

Core Functions:
    format_log_message(content, details): Format message for logging while preserving UTF-8

Example:
    >>> import classic_message
    >>> # Create a message
    >>> msg = classic_message.Message("Operation started", classic_message.MessageType.INFO)
    >>> msg = msg.with_title("Process").with_details("Processing 100 items")
    >>>
    >>> # Check routing
    >>> if msg.target().should_display():
    ...     print(msg.content())
    >>>
    >>> # Format for logging
    >>> log_text = classic_message.format_log_message(msg.content(), msg.details())
    >>>
    >>> # Use the logger
    >>> logger = classic_message.Logger()
    >>> logger.info("Application started")
    >>> logger.log_message(msg)
"""

# Direct-import facade over the one CLASSIC native extension. Every name is
# the canonical native object, so values and exceptions created through any
# facade are the same Python types everywhere. Keep the import list and the
# literal ``__all__`` in step with ``__init__.pyi``: validate_stubs.py and the
# Python parity resolver read both.

from _classic_native._native.classic_message import (
    Logger,
    Message,
    MessageTarget,
    MessageType,
    __version__,
    format_contract_event,
    format_log_message,
    init_logging,
)

__all__ = [
    "Logger",
    "Message",
    "MessageTarget",
    "MessageType",
    "__version__",
    "format_contract_event",
    "format_log_message",
    "init_logging",
]
