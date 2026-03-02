"""Base protocol for output backends.

This module defines the OutputBackend protocol that all output implementations
must follow, enabling the Strategy pattern for message output.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ClassicLib.messaging.core.message import Message


@runtime_checkable
class OutputBackend(Protocol):
    """Protocol for message output backends.

    All output backends (CLI, GUI, Log) must implement this protocol
    to be used by the MessageHandler.
    """

    def show(self, message: Message) -> None:
        """Display a message.

        Args:
            message: The message to display.

        """
        ...

    def is_available(self) -> bool:
        """Check if this backend is available for use.

        Returns:
            True if the backend can be used.

        """
        ...
