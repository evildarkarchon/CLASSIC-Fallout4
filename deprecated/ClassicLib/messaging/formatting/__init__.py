"""Formatting utilities for message handling.

This module provides Rust-accelerated text formatting functions including
emoji stripping and log message formatting.
"""

from ClassicLib.messaging.formatting.formatter import (
    format_log_message,
    strip_emoji,
)

__all__ = [
    "format_log_message",
    "strip_emoji",
]
