"""Base message handler for CLI mode.

This module provides the base MessageHandler class that works without Qt
dependencies. It handles message routing, logging, and CLI output.
For GUI mode with Qt, use QtMessageHandler from qt_handler.py.
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from ClassicLib.MessageHandler.core.enums import MessageTarget, MessageType  # noqa: F401
from ClassicLib.MessageHandler.core.message import Message
from ClassicLib.MessageHandler.core.router import MessageRouter
from ClassicLib.MessageHandler.output.cli_backend import CLIBackend
from ClassicLib.MessageHandler.output.log_backend import LogBackend
from ClassicLib.MessageHandler.progress.cli_progress import CLIProgressHandler
from ClassicLib.MessageHandler.progress.context import ProgressContext

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ClassicLib.MessageHandler.output.base import OutputBackend
    from ClassicLib.MessageHandler.progress.base import ProgressHandler


class MessageHandler:
    """Base message handler for CLI mode (no Qt dependency).

    This class handles message routing between different output backends.
    It always logs messages and routes display to CLI. For GUI support,
    use QtMessageHandler instead.

    Attributes:
        is_gui_mode: Whether operating in GUI mode.
        parent_widget: Parent widget reference (always None for base class).

    """

    def __init__(self, is_gui_mode: bool = False) -> None:
        """Initialize the message handler.

        Args:
            is_gui_mode: Whether operating in GUI mode.

        """
        self._is_gui_mode = is_gui_mode
        self._router = MessageRouter(is_gui_mode)
        self._log_backend = LogBackend()
        self._cli_backend = CLIBackend()
        self._cancelled = False

        # Store reference to main thread
        self._main_thread = threading.current_thread()

        # Logger for internal operations
        self._logger = logging.getLogger("CLASSIC.MessageHandler")

    @property
    def is_gui_mode(self) -> bool:
        """Whether operating in GUI mode."""
        return self._is_gui_mode

    @property
    def parent_widget(self) -> Any:
        """Parent widget (None for base class)."""
        return None

    @property
    def main_thread(self) -> threading.Thread | Any:
        """Reference to the main thread.

        Returns:
            threading.Thread for CLI mode, QThread for Qt mode.

        """
        return self._main_thread

    def _get_output_backend(self) -> OutputBackend:
        """Get the output backend for display.

        Override in subclass for different output (e.g., GUI).

        Returns:
            The output backend to use.

        """
        return self._cli_backend

    def create_progress_handler(self) -> ProgressHandler:  # noqa: PLR6301
        """Create a progress handler for this environment.

        Override in subclass for different progress display (e.g., Qt).

        Returns:
            A progress handler implementing the ProgressHandler protocol.

        """
        return CLIProgressHandler()

    def show(self, message: Message) -> None:
        """Display a message.

        Always logs the message, then displays if appropriate for target.

        Args:
            message: The message to display.

        """
        # Always log the message
        self._log_backend.show(message)

        # Check if should display
        if not self._router.should_display(message.target):
            return

        # Route to appropriate backend
        self._get_output_backend().show(message)

    def info(self, content: str, **kwargs: Any) -> None:
        """Display an informational message.

        Args:
            content: Message content.
            **kwargs: Additional message attributes (target, title, details, parent).

        """
        message = Message(content, MessageType.INFO, **kwargs)
        self.show(message)

    def warning(self, content: str, **kwargs: Any) -> None:
        """Display a warning message.

        Args:
            content: Message content.
            **kwargs: Additional message attributes.

        """
        message = Message(content, MessageType.WARNING, **kwargs)
        self.show(message)

    def error(self, content: str, **kwargs: Any) -> None:
        """Display an error message.

        Args:
            content: Message content.
            **kwargs: Additional message attributes.

        """
        message = Message(content, MessageType.ERROR, **kwargs)
        self.show(message)

    def success(self, content: str, **kwargs: Any) -> None:
        """Display a success message.

        Args:
            content: Message content.
            **kwargs: Additional message attributes.

        """
        message = Message(content, MessageType.SUCCESS, **kwargs)
        self.show(message)

    def debug(self, content: str, **kwargs: Any) -> None:
        """Display a debug message.

        Args:
            content: Message content.
            **kwargs: Additional message attributes.

        """
        message = Message(content, MessageType.DEBUG, **kwargs)
        self.show(message)

    def critical(self, content: str, **kwargs: Any) -> None:
        """Display a critical message.

        Args:
            content: Message content.
            **kwargs: Additional message attributes.

        """
        message = Message(content, MessageType.CRITICAL, **kwargs)
        self.show(message)

    def progress_context(
        self,
        description: str,
        total: int | None = None,
    ) -> ProgressContext:
        """Create a progress context for tracking operations.

        Args:
            description: Description of the operation.
            total: Total items, or None for indeterminate.

        Returns:
            ProgressContext for use in with statement.

        """
        return ProgressContext(self, description, total)

    def is_cancelled(self) -> bool:
        """Check if the current operation was cancelled.

        Returns:
            True if cancelled.

        """
        return self._cancelled

    def _set_cancelled(self, cancelled: bool) -> None:
        """Set the cancellation state.

        Args:
            cancelled: Whether cancelled.

        """
        self._cancelled = cancelled


# Global instance management
_message_handler: MessageHandler | None = None
_message_handler_lock = threading.Lock()


def init_message_handler(
    parent: Any = None,
    is_gui_mode: bool = False,
) -> MessageHandler:
    """Initialize the global message handler.

    This function creates the appropriate handler based on mode:
    - CLI mode: Creates base MessageHandler (no Qt dependency)
    - GUI mode: Creates QtMessageHandler (requires Qt)

    Args:
        parent: Parent widget for GUI mode (ignored in CLI mode).
        is_gui_mode: Whether to enable GUI mode.

    Returns:
        The initialized message handler.

    """
    global _message_handler  # noqa: PLW0603

    with _message_handler_lock:
        if is_gui_mode:
            # Import Qt handler only when needed
            from ClassicLib.MessageHandler.qt_handler import QtMessageHandler

            _message_handler = QtMessageHandler(parent)
        else:
            _message_handler = MessageHandler(is_gui_mode=False)

        return _message_handler


def get_message_handler() -> MessageHandler:
    """Get the global message handler.

    Returns:
        The initialized message handler.

    Raises:
        RuntimeError: If handler not initialized.

    """
    with _message_handler_lock:
        if _message_handler is None:
            msg = "Message handler not initialized. Call init_message_handler() first."
            raise RuntimeError(msg)
        return _message_handler


# Convenience functions for direct access
def msg_info(content: str, **kwargs: Any) -> None:
    """Log an informational message.

    Args:
        content: Message content.
        **kwargs: Additional message attributes.

    """
    get_message_handler().info(content, **kwargs)


def msg_warning(content: str, **kwargs: Any) -> None:
    """Log a warning message.

    Args:
        content: Message content.
        **kwargs: Additional message attributes.

    """
    get_message_handler().warning(content, **kwargs)


def msg_error(content: str, **kwargs: Any) -> None:
    """Log an error message.

    Args:
        content: Message content.
        **kwargs: Additional message attributes.

    """
    get_message_handler().error(content, **kwargs)


def msg_success(content: str, **kwargs: Any) -> None:
    """Log a success message.

    Args:
        content: Message content.
        **kwargs: Additional message attributes.

    """
    get_message_handler().success(content, **kwargs)


def msg_debug(content: str, **kwargs: Any) -> None:
    """Log a debug message.

    Args:
        content: Message content.
        **kwargs: Additional message attributes.

    """
    get_message_handler().debug(content, **kwargs)


def msg_critical(content: str, **kwargs: Any) -> None:
    """Log a critical message.

    Args:
        content: Message content.
        **kwargs: Additional message attributes.

    """
    get_message_handler().critical(content, **kwargs)


@contextmanager
def msg_progress_context(
    description: str,
    total: int | None = None,
) -> Iterator[ProgressContext]:
    """Context manager for progress tracking.

    Args:
        description: Description of the operation.
        total: Total items, or None for indeterminate.

    Yields:
        ProgressContext for tracking progress.

    """
    handler = get_message_handler()
    with handler.progress_context(description, total) as progress:
        yield progress
