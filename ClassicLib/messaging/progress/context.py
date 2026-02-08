"""Progress context manager for unified progress tracking.

This module provides the ProgressContext class which adapts to either
GUI or CLI environments, displaying appropriate progress indicators.
The handler provides the appropriate progress implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ClassicLib.messaging.handler import MessageHandler
    from ClassicLib.messaging.progress.base import ProgressHandler


class ProgressContext:
    """Context manager for progress tracking in GUI or CLI environments.

    This class provides a unified interface for progress tracking that
    automatically adapts to the environment by delegating to the handler's
    progress handler implementation.

    Attributes:
        handler: The message handler managing the context.
        description: Description of the operation.
        total: Total items to process, or None for indeterminate.
        current: Current progress count.

    """

    def __init__(
        self,
        handler: MessageHandler,
        description: str,
        total: int | None = None,
    ) -> None:
        """Initialize the progress context.

        Args:
            handler: MessageHandler instance managing this context.
            description: Description of the operation.
            total: Total items, or None for indeterminate progress.

        """
        self.handler = handler
        self.description = description
        self.total = total
        self.current = 0

        self._progress_handler: ProgressHandler | None = None

    def __enter__(self) -> ProgressContext:
        """Enter the progress context.

        Returns:
            Self for use in with statement.

        """
        # Check if CLI progress is disabled
        if not self.handler.is_gui_mode and self._check_cli_progress_disabled():
            return self

        # Get the appropriate progress handler from the message handler
        self._progress_handler = self.handler.create_progress_handler()

        # Check if handler is available
        if self._progress_handler and self._progress_handler.is_available():
            self._progress_handler.start(self.description, self.total)
        else:
            self._progress_handler = None

        return self

    @staticmethod
    def _check_cli_progress_disabled() -> bool:
        """Check if CLI progress is disabled in settings.

        Returns:
            True if CLI progress should be disabled.

        """
        try:
            from ClassicLib.io.yaml import classic_settings

            return classic_settings(bool, "Disable CLI Progress") or False
        except (ImportError, FileNotFoundError, KeyError, TypeError, RuntimeError):
            return False

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: Any,
    ) -> None:
        """Exit the progress context.

        Args:
            exc_type: Exception type if raised.
            _exc_val: Exception value if raised.
            _exc_tb: Exception traceback if raised.

        """
        if self._progress_handler is not None:
            self._progress_handler.close()
            self._progress_handler = None

    def update(self, n: int = 1, description: str | None = None) -> None:
        """Update the progress.

        Args:
            n: Number of items completed since last update.
            description: Optional new description.

        """
        self.current += n

        if self._progress_handler is not None:
            self._progress_handler.update(n, description)

    def was_cancelled(self) -> bool:
        """Check if the operation was cancelled by the user.

        Returns:
            True if cancelled.

        """
        if self._progress_handler is not None:
            return self._progress_handler.was_cancelled()
        return False
