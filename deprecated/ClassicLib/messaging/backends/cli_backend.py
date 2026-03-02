"""CLI output backend for command-line message display.

This module provides the CLIBackend class that handles message output
to the terminal with emoji prefixes. It does NOT import Qt, making it
safe for CLI-only usage.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, ClassVar, Final

from ClassicLib.messaging.core.enums import MessageType
from ClassicLib.messaging.formatting import strip_emoji

if TYPE_CHECKING:
    from ClassicLib.messaging.core.message import Message


class CLIBackend:
    """CLI output backend - prints to stdout/stderr with emoji prefixes.

    This backend handles command-line output with appropriate emoji prefixes
    for different message types. It strips emojis on Windows to avoid
    console encoding issues.

    Class Attributes:
        PREFIX_MAP: Mapping of message types to emoji prefixes.
    """

    PREFIX_MAP: ClassVar[dict[MessageType, str]] = {
        MessageType.INFO: "",
        MessageType.WARNING: "\u26a0\ufe0f ",  # Warning sign
        MessageType.ERROR: "\u274c ",  # Cross mark
        MessageType.SUCCESS: "\u2705 ",  # Check mark
        MessageType.CRITICAL: "\U0001f6a8 ",  # Rotating light
        MessageType.DEBUG: "\U0001f41b ",  # Bug
        MessageType.PROGRESS: "",
    }

    # Whether to strip emojis (for Windows console)
    _STRIP_EMOJI: Final[bool] = sys.platform == "win32"

    def show(self, message: Message) -> None:
        """Display a message to stdout/stderr.

        Args:
            message: The message to display.

        """
        prefix = self.PREFIX_MAP.get(message.msg_type, "")
        output = f"{prefix}{message.content}"

        if message.details:
            output += f"\n   Details: {message.details}"

        # Strip emojis for Windows console to avoid encoding issues
        if self._STRIP_EMOJI:
            output = strip_emoji(output)

        # Use stderr for errors and warnings
        if message.msg_type in {MessageType.ERROR, MessageType.WARNING, MessageType.CRITICAL}:
            try:
                print(output, file=sys.stderr, flush=True)
            except OSError:
                # Fallback to stdout if stderr is not available
                print(output, flush=True)
        else:
            print(output, flush=True)

    def is_available(self) -> bool:  # noqa: PLR6301
        """Check if CLI output is available.

        Returns:
            Always True - CLI is always available.

        """
        return True
