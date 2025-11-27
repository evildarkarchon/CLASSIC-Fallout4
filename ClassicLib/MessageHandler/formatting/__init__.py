"""Formatting utilities for message handling.

This module provides Rust-accelerated text formatting functions including
emoji stripping and log message formatting. Falls back to Python implementations
when Rust acceleration is unavailable.
"""

from ClassicLib.MessageHandler.formatting.formatter import (
    RUST_AVAILABLE,
    format_log_message,
    strip_emoji,
)

__all__ = [
    "RUST_AVAILABLE",
    "format_log_message",
    "strip_emoji",
]
