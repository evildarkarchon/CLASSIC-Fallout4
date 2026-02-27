"""Rust-accelerated text formatting utilities (required)."""

from __future__ import annotations

import classic_message


def strip_emoji(text: str) -> str:
    """Strip emojis from text for log safety.

    Uses required Rust implementation.

    Args:
        text: Input text possibly containing emojis.

    Returns:
        Text with emojis removed and whitespace trimmed.

    Example:
        >>> strip_emoji("Hello World!")
        'Hello  World !'

    """
    return classic_message.strip_emoji(text)


def format_log_message(content: str, details: str | None = None) -> str:
    r"""Format message content with optional details for logging.

    Strips emojis from both content and details to avoid encoding issues
    on Windows console. Uses required Rust implementation.

    Args:
        content: Main message content.
        details: Optional additional details.

    Returns:
        Formatted log message suitable for logging.

    Example:
        >>> format_log_message("Success!", "All tests passed")
        'Success!\nDetails: All tests passed'

    """
    return classic_message.format_log_message(content, details)
