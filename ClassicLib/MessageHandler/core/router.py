"""Message routing logic for determining display behavior.

This module provides the MessageRouter class which encapsulates the logic
for determining whether and where messages should be displayed based on
the current mode (GUI/CLI) and message target.
"""

from __future__ import annotations

from ClassicLib.MessageHandler.core.enums import MessageTarget


class MessageRouter:
    """Determines whether messages should be displayed based on mode and target.

    This class encapsulates the routing logic that was previously scattered
    throughout the MessageHandler. It provides a clean interface for checking
    if a message should be displayed given the current operating mode.

    Attributes:
        is_gui_mode: Whether the handler is operating in GUI mode.
    """

    def __init__(self, is_gui_mode: bool = False) -> None:
        """Initialize the router.

        Args:
            is_gui_mode: Whether operating in GUI mode.
        """
        self._is_gui_mode = is_gui_mode

    @property
    def is_gui_mode(self) -> bool:
        """Whether operating in GUI mode."""
        return self._is_gui_mode

    def should_display(self, target: MessageTarget) -> bool:
        """Determine if a message should be displayed.

        Args:
            target: The message target specifying where to display.

        Returns:
            True if the message should be displayed in the current mode.
        """
        # Normalize legacy enum values
        normalized = target.normalize()

        # LOG_ONLY never displays
        if normalized == MessageTarget.LOG_ONLY:
            return False

        # Check mode-specific targets
        if normalized == MessageTarget.GUI:
            return self._is_gui_mode

        if normalized == MessageTarget.CONSOLE:
            return not self._is_gui_mode

        # ALL displays in both modes
        return True

    def get_display_mode(self, target: MessageTarget) -> str | None:  # noqa: PLR6301
        """Get the display mode for a message target.

        Args:
            target: The message target.

        Returns:
            'gui', 'cli', 'both', or None (for log-only).
        """
        normalized = target.normalize()

        if normalized == MessageTarget.LOG_ONLY:
            return None
        if normalized == MessageTarget.GUI:
            return "gui"
        if normalized == MessageTarget.CONSOLE:
            return "cli"
        return "both"
