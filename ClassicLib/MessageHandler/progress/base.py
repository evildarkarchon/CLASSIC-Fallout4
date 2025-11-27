"""Base protocol for progress handlers.

This module defines the ProgressHandler protocol that all progress
implementations must follow, enabling the Strategy pattern for progress display.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProgressHandler(Protocol):
    """Protocol for progress indicator handlers.

    All progress handlers (CLI, Qt) must implement this protocol
    to be used by the MessageHandler and ProgressContext.
    """

    def start(self, description: str, total: int | None = None) -> None:
        """Start the progress indicator.

        Args:
            description: Description of the operation.
            total: Total items to process, or None for indeterminate.
        """
        ...

    def update(self, n: int = 1, description: str | None = None) -> None:
        """Update progress.

        Args:
            n: Number of items completed since last update.
            description: Optional updated description.
        """
        ...

    def close(self) -> None:
        """Close/hide the progress indicator."""
        ...

    def was_cancelled(self) -> bool:
        """Check if the user cancelled the operation.

        Returns:
            True if cancelled.
        """
        ...

    def is_available(self) -> bool:
        """Check if this handler is available.

        Returns:
            True if can be used.
        """
        ...
