"""Rust-accelerated text formatting utilities.

This module provides emoji stripping and log message formatting functions
with Rust acceleration when available. The Rust implementation provides
15-50x faster emoji stripping compared to Python regex.

Functions:
    strip_emoji: Remove emojis from text for log safety.
    format_log_message: Format message content with optional details for logging.
"""

from __future__ import annotations

import re
from typing import Any

RUST_AVAILABLE: bool = False
# Try to import Rust acceleration
try:
    import classic_message

    RUST_AVAILABLE = True
except ImportError:
    classic_message: Any = None  # type: ignore[no-redef]

# Module-level compiled regex pattern for Python fallback
# Only compiled once, reused for all calls (unlike the old implementation)
_EMOJI_PATTERN: re.Pattern[str] | None = None


def _get_emoji_pattern() -> re.Pattern[str]:
    """Get or create the compiled emoji pattern.

    Returns:
        Compiled regex pattern for emoji matching.
    """
    global _EMOJI_PATTERN  # noqa: PLW0603
    if _EMOJI_PATTERN is None:
        # Unicode ranges for emojis and symbols
        _EMOJI_PATTERN = re.compile(
            r"["
            r"\U0001f600-\U0001f64f"  # emoticons
            r"\U0001f300-\U0001f5ff"  # symbols & pictographs
            r"\U0001f680-\U0001f6ff"  # transport & map symbols
            r"\U0001f1e0-\U0001f1ff"  # flags (iOS)
            r"\U00002702-\U000027b0"  # dingbats
            r"\U000024c2-\U0001f251"
            r"\U0001f900-\U0001f9ff"  # supplemental symbols
            r"\U00002600-\U000026ff"  # miscellaneous symbols
            r"\U00002700-\U000027bf"  # dingbats
            r"]+",
            flags=re.UNICODE,
        )
    return _EMOJI_PATTERN


def _python_strip_emoji(text: str) -> str:
    """Python fallback for emoji stripping.

    Args:
        text: Input text possibly containing emojis.

    Returns:
        Text with emojis removed and whitespace trimmed.
    """
    pattern = _get_emoji_pattern()
    return pattern.sub("", text).strip()


def strip_emoji(text: str) -> str:
    """Strip emojis from text for log safety.

    Uses Rust acceleration when available (15-50x faster), falling back
    to Python regex implementation otherwise.

    Args:
        text: Input text possibly containing emojis.

    Returns:
        Text with emojis removed and whitespace trimmed.

    Example:
        >>> strip_emoji("Hello World!")
        'Hello  World !'
    """
    if RUST_AVAILABLE and classic_message is not None:
        return classic_message.strip_emoji(text)
    return _python_strip_emoji(text)


def _python_format_log_message(content: str, details: str | None = None) -> str:
    """Python fallback for log message formatting.

    Args:
        content: Main message content.
        details: Optional additional details.

    Returns:
        Formatted log message with emojis stripped.
    """
    log_content = _python_strip_emoji(content)
    if details:
        log_content += f"\nDetails: {_python_strip_emoji(details)}"
    return log_content


def format_log_message(content: str, details: str | None = None) -> str:
    """Format message content with optional details for logging.

    Strips emojis from both content and details to avoid encoding issues
    on Windows console. Uses Rust acceleration when available.

    Args:
        content: Main message content.
        details: Optional additional details.

    Returns:
        Formatted log message suitable for logging.

    Example:
        >>> format_log_message("Success!", "All tests passed")
        'Success!\nDetails: All tests passed'
    """
    if RUST_AVAILABLE and classic_message is not None:
        return classic_message.format_log_message(content, details)
    return _python_format_log_message(content, details)
