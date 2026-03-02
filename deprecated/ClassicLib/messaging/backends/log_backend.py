"""Logging backend for message persistence.

This module provides the LogBackend class that handles message logging
via Python's logging module. It strips emojis to avoid encoding issues.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

from ClassicLib.messaging.core.enums import MessageType
from ClassicLib.messaging.formatting import format_log_message

if TYPE_CHECKING:
    from ClassicLib.messaging.core.message import Message


class LogBackend:
    """Logging-only backend - writes messages to Python logger.

    This backend always logs messages regardless of display target.
    It uses Rust-accelerated formatting when available.

    Class Attributes:
        LEVEL_MAP: Mapping of message types to logging levels.
    """

    LEVEL_MAP: ClassVar[dict[MessageType, int]] = {
        MessageType.INFO: logging.INFO,
        MessageType.WARNING: logging.WARNING,
        MessageType.ERROR: logging.ERROR,
        MessageType.SUCCESS: logging.INFO,
        MessageType.DEBUG: logging.DEBUG,
        MessageType.CRITICAL: logging.CRITICAL,
        MessageType.PROGRESS: logging.DEBUG,
    }

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """Initialize the log backend.

        Args:
            logger: Logger instance to use. Defaults to CLASSIC.MessageHandler.

        """
        self._logger = logger or logging.getLogger("CLASSIC.MessageHandler")

    def show(self, message: Message) -> None:
        """Log a message.

        Args:
            message: The message to log.

        """
        level = self.LEVEL_MAP.get(message.msg_type, logging.INFO)
        # Use Rust-accelerated formatting which strips emojis
        text = format_log_message(message.content, message.details)
        self._logger.log(level, text)

    def is_available(self) -> bool:  # noqa: PLR6301
        """Check if logging is available.

        Returns:
            Always True - logging is always available.

        """
        return True

    def set_logger(self, logger: logging.Logger) -> None:
        """Update the logger instance.

        Args:
            logger: New logger to use.

        """
        self._logger = logger
