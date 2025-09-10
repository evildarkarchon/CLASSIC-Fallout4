"""Main MessageHandler class for unified message handling."""

from __future__ import annotations

import logging
import re
import sys
import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, LiteralString

from .enums import MessageTarget, MessageType
from .models import Message
from .progress_context import ProgressContext
from .qt_compat import HAS_QT, QMessageBox, QObject, QProgressDialog, QThread, QWidget, Signal

if TYPE_CHECKING:
    from collections.abc import Iterator


class MessageHandler(QObject):
    """Main message handler that routes messages to appropriate outputs."""

    # Qt signals for thread-safe GUI updates
    if HAS_QT:
        message_signal = Signal(Message)
        progress_signal = Signal(int, str)
        progress_create_signal = Signal(str, int)  # description, total
        progress_close_signal = Signal()

    def __init__(self, parent: QWidget | None = None, is_gui_mode: bool = False) -> None:
        """
        Initializes a message handler object with optional GUI mode.

        Used for handling messages and progress-related operations, with optional integration
        into a GUI framework if available.

        Parameters:
            parent (QWidget | None, optional): Parent widget for the GUI, if applicable. Defaults
                to None.
            is_gui_mode (bool, optional): Determines whether the handler operates in GUI mode if
                the GUI framework is available. Defaults to False.
        """
        if HAS_QT:
            super().__init__()

        self.parent_widget = parent
        self.is_gui_mode = is_gui_mode and HAS_QT
        self.logger = logging.getLogger("CLASSIC.MessageHandler")

        # Store reference to main thread for thread safety checks
        if HAS_QT:
            self.main_thread = QThread.currentThread()
        else:
            self.main_thread = threading.current_thread()  # type: ignore[assignment]

        # Connect signals if in GUI mode
        if self.is_gui_mode and HAS_QT:
            self.message_signal.connect(self._handle_gui_message)
            self.progress_create_signal.connect(self._create_progress_dialog)
            self.progress_close_signal.connect(self._close_progress_dialog)
            self.progress_signal.connect(self._update_progress_dialog)

        # Store progress dialog reference
        self._progress_dialog: QProgressDialog | None = None

    def _should_display(self, target: MessageTarget) -> bool:
        """Check if message should be displayed based on target and mode."""
        if target == MessageTarget.LOG_ONLY:
            return False
        if target == MessageTarget.GUI_ONLY:
            return self.is_gui_mode
        if target == MessageTarget.CLI_ONLY:
            return not self.is_gui_mode
        # MessageTarget.ALL
        return True

    @staticmethod
    def _strip_emoji(text: str) -> str:
        """Strip emoji characters from text to avoid encoding issues in logs."""
        # Unicode ranges for emojis and symbols
        emoji_pattern = re.compile(
            "["
            "\U0001f600-\U0001f64f"  # emoticons
            "\U0001f300-\U0001f5ff"  # symbols & pictographs
            "\U0001f680-\U0001f6ff"  # transport & map symbols
            "\U0001f1e0-\U0001f1ff"  # flags (iOS)
            "\U00002702-\U000027b0"  # dingbats
            "\U000024c2-\U0001f251"
            "\U0001f900-\U0001f9ff"  # supplemental symbols
            "\U00002600-\U000026ff"  # miscellaneous symbols
            "\U00002700-\U000027bf"  # dingbats
            "]+",
            flags=re.UNICODE,
        )
        return emoji_pattern.sub("", text).strip()

    def _log_message(self, message: Message) -> None:
        """Log message to file."""
        level_map = {
            MessageType.DEBUG: logging.DEBUG,
            MessageType.INFO: logging.INFO,
            MessageType.WARNING: logging.WARNING,
            MessageType.ERROR: logging.ERROR,
            MessageType.CRITICAL: logging.CRITICAL,
            MessageType.SUCCESS: logging.INFO,
            MessageType.PROGRESS: logging.DEBUG,
        }

        log_level = level_map.get(message.msg_type, logging.INFO)
        # Strip emoji characters for logging to avoid encoding issues on Windows console
        log_content = self._strip_emoji(message.content)
        if message.details:
            log_content += f"\nDetails: {self._strip_emoji(message.details)}"

        self.logger.log(log_level, log_content)

    def _handle_gui_message(self, message: Message) -> None:
        """Handle displaying message in GUI mode (runs in main thread)."""
        if not HAS_QT:
            return

        parent: QWidget | None = message.parent or self.parent_widget
        title: str | LiteralString = message.title or message.msg_type.name.title()
        icon_map = {
            MessageType.INFO: QMessageBox.Icon.Information,
            MessageType.WARNING: QMessageBox.Icon.Warning,
            MessageType.ERROR: QMessageBox.Icon.Critical,
            MessageType.SUCCESS: QMessageBox.Icon.Information,
            MessageType.CRITICAL: QMessageBox.Icon.Critical,
            MessageType.DEBUG: QMessageBox.Icon.Information,
        }

        icon = icon_map.get(message.msg_type, QMessageBox.Icon.Information)

        if message.details:
            msg_box = QMessageBox(parent=parent, text=message.content, icon=icon)
            msg_box.setWindowTitle(title)
            msg_box.setDetailedText(message.details)
            msg_box.exec()
        else:
            msg_box = QMessageBox(parent=parent, text=message.content, icon=icon)
            msg_box.setWindowTitle(title)
            msg_box.exec()

    def _create_progress_dialog(self, description: str, total: int) -> None:
        """Create progress dialog in main thread."""
        if not HAS_QT:
            return

        self._progress_dialog = QProgressDialog(description, "Cancel", 0, total, self.parent_widget)
        self._progress_dialog.setWindowTitle("Progress")
        self._progress_dialog.setAutoClose(True)
        self._progress_dialog.setAutoReset(True)
        if total == 0:
            self._progress_dialog.setRange(0, 0)  # Indeterminate
        self._progress_dialog.show()

    def _update_progress_dialog(self, value: int, description: str) -> None:
        """Update progress dialog in main thread."""
        if self._progress_dialog:
            self._progress_dialog.setValue(value)
            if description:
                self._progress_dialog.setLabelText(description)

    def _close_progress_dialog(self) -> None:
        """Close progress dialog in main thread."""
        if self._progress_dialog:
            self._progress_dialog.hide()
            self._progress_dialog = None

    @staticmethod
    def _handle_cli_message(message: Message) -> None:
        """Handle displaying message in CLI mode."""
        # Add emoji prefixes for different message types
        prefix_map: dict[MessageType, str] = {
            MessageType.INFO: "",
            MessageType.WARNING: "⚠️ ",
            MessageType.ERROR: "❌ ",
            MessageType.SUCCESS: "✅ ",
            MessageType.CRITICAL: "🚨 ",
            MessageType.DEBUG: "🐛 ",
        }

        prefix: str = prefix_map.get(message.msg_type, "")
        output: str = f"{prefix}{message.content}"

        if message.details:
            output += f"\n   Details: {message.details}"

        # Use stderr for errors and warnings
        # Use sys.stderr instead of sys.__stderr__ for better pytest compatibility
        if message.msg_type in (MessageType.ERROR, MessageType.WARNING, MessageType.CRITICAL):
            try:
                print(output, file=sys.stderr, flush=True)
            except OSError:
                # Fallback to stdout if stderr is not available
                print(output, flush=True)
        else:
            print(output, flush=True)

    def show(self, message: Message) -> None:
        """
        Displays a message either in a GUI or CLI interface, based on the mode and target. Ensures thread-safe
        operation for GUI and directly handles CLI output. The function always logs the provided message regardless
        of the display operation.

        Args:
            message (Message): The message object to be shown.

        Returns:
            None
        """
        # Always log the message
        self._log_message(message)

        # Check if should display
        if not self._should_display(message.target):
            return

        if self.is_gui_mode and HAS_QT:
            # Emit signal for thread-safe GUI update
            self.message_signal.emit(message)
        else:
            # Direct CLI output
            self._handle_cli_message(message)

    def info(self, content: str, **kwargs: Any) -> None:
        """
        Logs a message with an informational level.

        This method prepares a message with the specified content and an informational
        designation. It then displays the message using the `show` method.

        Arguments:
            content: The text content of the message.
            **kwargs: Additional arguments to customize the message if needed.

        Returns:
            None
        """
        message = Message(content, MessageType.INFO, **kwargs)
        self.show(message)

    def warning(self, content: str, **kwargs: Any) -> None:
        """
        Handle the creation and display of warning messages.

        This method creates a warning message using the provided content and additional
        keyword arguments, then displays the generated message.

        Parameters:
        content: str
            The main text content of the warning message.
        kwargs: Any
            Additional keyword arguments that can be passed while creating the message.

        Returns:
        None
        """
        message = Message(content, MessageType.WARNING, **kwargs)
        self.show(message)

    def error(self, content: str, **kwargs: Any) -> None:
        """
        Represents an action to log or display an error message with appropriate formatting
        and additional information.

        Args:
            content (str): The error message content to be displayed.
            **kwargs (Any): Additional keyword arguments to pass while creating the
                error message.

        Returns:
            None
        """
        message = Message(content, MessageType.ERROR, **kwargs)
        self.show(message)

    def success(self, content: str, **kwargs: Any) -> None:
        """
        Indicates a successful operation or result and displays the corresponding message.

        Parameters
        ----------
        content: str
            The textual content of the success message.
        **kwargs: Any
            Additional key-value arguments that may be used to construct or customize
            the message.

        Returns
        -------
        None
        """
        message = Message(content, MessageType.SUCCESS, **kwargs)
        self.show(message)

    def debug(self, content: str, **kwargs: Any) -> None:
        """
        Logs a debug message with provided content and additional parameters.

        The method creates a debug message object and sends it to be displayed.
        It allows for inclusion of additional contextual details using keyword arguments.

        Args:
            content (str): The main content/message to be logged with DEBUG level.
            **kwargs (Any): Additional keyword arguments containing contextual
                information to attach to the message.

        Returns:
            None
        """
        message = Message(content, MessageType.DEBUG, **kwargs)
        self.show(message)

    def critical(self, content: str, **kwargs: Any) -> None:
        """
        Logs a critical message by creating a Message object and utilizing the
        show method. This method is intended for handling messages of the
        critical severity level.

        Args:
            content (str): The main content of the critical message.
            **kwargs (Any): Additional keyword arguments for customizing
                the message attributes or behavior.

        Returns:
            None
        """
        message = Message(content, MessageType.CRITICAL, **kwargs)
        self.show(message)

    def progress_context(self, description: str, total: int | None = None) -> ProgressContext:
        """
        Provides a context manager for progress tracking with a given description and an optional
        total count. The progress context manager simplifies the tracking of progress over a set
        of actions or items, especially when definite progress information is available.

        Parameters:
        description: str
            The description of the progress to be tracked.
        total: int | None, optional
            The total count of items or actions for which progress will be tracked. If None, the
            total remains unspecified.

        Returns:
        ProgressContext
            A context manager object that represents and manages the progress tracking state.
        """
        return ProgressContext(self, description, total)


# Global instance management
_message_handler: MessageHandler | None = None
_message_handler_lock = threading.Lock()


def init_message_handler(parent: QWidget | None = None, is_gui_mode: bool = False) -> MessageHandler:
    """
    Initialize the global message handler for managing message interactions. This
    function creates a new instance of MessageHandler and assigns it to a global
    variable for universal access.

    Parameters:
        parent (QWidget | None): Parent widget for the MessageHandler instance. It
            can be None if no parent is required.
        is_gui_mode (bool): A flag indicating if the handler should operate in GUI
            mode. If True, the handler facilitates GUI-based operations.

    Returns:
        MessageHandler: The initialized MessageHandler instance prepared for use.
    """
    global _message_handler  # noqa: PLW0603
    with _message_handler_lock:
        _message_handler = MessageHandler(parent, is_gui_mode)
        return _message_handler


def get_message_handler() -> MessageHandler:
    """
    Fetches and returns the global message handler instance.

    The function retrieves the currently initialized global message handler. If
    the message handler has not been initialized by calling the
    `init_message_handler()` function prior to this call, it raises an exception
    to indicate that the handler is missing.

    Returns:
        MessageHandler: The initialized global message handler instance.

    Raises:
        RuntimeError: If the global message handler has not been initialized.
    """
    with _message_handler_lock:
        if _message_handler is None:
            raise RuntimeError("Message handler not initialized. Call init_message_handler() first.")
        return _message_handler


# Convenience functions for direct access
def msg_info(content: str, **kwargs: Any) -> None:
    """
    Logs an informational message using the message handler.

    This function utilizes the message handler to log an informational
    message. The primary message content is specified through the `content`
    parameter, and additional keyword arguments may be passed to provide
    context or formatting for the message.

    Parameters:
    content: str
        The main content of the informational message to log.
    kwargs: Any
        Optional keyword arguments to provide additional details or
        formatting for the message.

    Returns:
    None
    """
    get_message_handler().info(content, **kwargs)


def msg_warning(content: str, **kwargs: Any) -> None:
    """
    Log a warning message through the configured message handler.

    This function triggers the warning level logging behavior of the current
    message handler, passing the provided content and optional keyword arguments.

    Parameters:
    content: str
        The warning message to log.
    **kwargs: Any
        Additional keyword arguments passed to the message handler.
    """
    get_message_handler().warning(content, **kwargs)


def msg_error(content: str, **kwargs: Any) -> None:
    """
    Logs an error message through the message handler.

    This function allows the user to log an error message with optional
    keyword arguments. The actual error handling mechanism is delegated to
    the `get_message_handler` function's `error` method.

    Parameters:
        content: str
            The content of the error message to be logged.
        **kwargs: Any
            Additional context or metadata to be passed to the message handler's
            `error` method.

    Returns:
        None
    """
    get_message_handler().error(content, **kwargs)


def msg_success(content: str, **kwargs: Any) -> None:
    """
    Provides a utility function to generate a success message. This function relies
    on the message handler obtained from the `get_message_handler` method to
    construct and process a success message with the specified content and any
    additional optional keyword arguments.

    Args:
        content: The content of the success message.
        **kwargs: Additional key-value arguments to be forwarded to the success
        handler. The exact usage of these arguments depends on the implementation
        of the message handler.

    Returns:
        None
    """
    get_message_handler().success(content, **kwargs)


def msg_debug(content: str, **kwargs: Any) -> None:
    """
    Provides a utility function to generate a debug message. This function relies
    on the message handler obtained from the `get_message_handler` method to
    construct and process a success message with the specified content and any
    additional optional keyword arguments.

    Args:
        content: The debug message content to be logged.
        kwargs: Additional parameters to be passed to the message handler.
    """
    get_message_handler().debug(content, **kwargs)


def msg_critical(content: str, **kwargs: Any) -> None:
    """
    Logs a critical level message using the message handler.

    A critical message denotes a serious issue that requires immediate attention.
    The function uses the existing message handler to log the specified content
    and any additional supported key-value data.

    Parameters:
        content: str
            The critical message content to be logged.
        **kwargs: Any
            Additional parameters to be passed to the message handler.

    Returns:
        None
    """
    get_message_handler().critical(content, **kwargs)


@contextmanager
def msg_progress_context(description: str, total: int | None = None) -> Iterator[ProgressContext]:
    """
    Helper function to manage a progress context for message handlers. This function acts as a
    context manager to track progress during a task.

    Parameters:
        description (str): A short description of the task being tracked.
        total (int | None): The total amount of work to be completed. If None, the progress is
            treated as indeterminate.

    Yields:
        Iterator[ProgressContext]: An iterator that provides the progress context object
            encapsulating current state and methods for updating progress.
    """
    handler = get_message_handler()
    with handler.progress_context(description, total) as progress:
        yield progress
