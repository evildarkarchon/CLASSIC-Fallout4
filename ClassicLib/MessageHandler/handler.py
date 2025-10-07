"""
Module for handling message display and logging in both GUI and CLI environments.

This module defines the MessageHandler class, which facilitates routing messages to appropriate
outputs (e.g., GUI for graphical applications or CLI for command-line tools). It also supports
logging and managing progress dialogs where a GUI framework like Qt is available.
"""

from __future__ import annotations

import logging
import re
import sys
import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, LiteralString

from ClassicLib.MessageHandler.enums import MessageTarget, MessageType
from ClassicLib.MessageHandler.models import Message
from ClassicLib.MessageHandler.progress_context import ProgressContext
from ClassicLib.MessageHandler.qt_compat import HAS_QT, QMessageBox, QObject, QProgressDialog, QThread, QWidget, Signal

if TYPE_CHECKING:
    from collections.abc import Iterator


class MessageHandler(QObject):
    """
    Handles message and progress operations for both GUI and command-line interfaces (CLI).

    This class is responsible for managing messages including their logging, displaying, and formatting.
    It supports integration with GUI environments through signals, allowing for thread-safe updates.
    Progress dialogs and related GUI components are also managed, alongside CLI output where applicable.

    Attributes:
        parent_widget (QWidget | None): Reference to the parent widget, if operating in GUI mode.
        is_gui_mode (bool): Specifies whether the handler operates in GUI mode. Set to True if the GUI
            framework is available and enabled.
        logger (logging.Logger): Logger instance for managing logs related to messaging operations.
        main_thread (QThread | threading.Thread): Reference to the main thread for thread-safety
            validation. Depending on the present framework, this is a QThread or threading.Thread
            instance.
    """

    # Qt signals for thread-safe GUI updates
    if HAS_QT:
        message_signal = Signal(Message)
        progress_signal = Signal(int, str)
        progress_create_signal = Signal(str, int)  # description, total
        progress_close_signal = Signal()

    def __init__(self, parent: QWidget | None = None, is_gui_mode: bool = False) -> None:
        """
        Initializes an instance of the class with parent widget, GUI mode flag, and sets up appropriate
        logging, thread safety references, and signal connections if in GUI mode.

        Args:
            parent: The parent widget for this instance, expected to be of type QWidget or None.
            is_gui_mode: A boolean flag indicating whether the GUI mode is enabled or not.

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
        """
        Determines whether a message should be displayed based on the provided message target.

        Args:
            target (MessageTarget): The target medium for the message (e.g., LOG_ONLY, GUI_ONLY,
                CLI_ONLY, or ALL).

        Returns:
            bool: True if the message should be displayed for the specified target;
                False otherwise.
        """
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
        """
        Strips emojis from the given text.

        This method removes all emojis and symbols within specified Unicode ranges from
        the input text. Emojis and symbols are identified through a compiled regex pattern.

        Args:
            text (str): The input text string possibly containing emojis.

        Returns:
            str: A text string with all emojis removed.
        """
        # Unicode ranges for emojis and symbols
        emoji_pattern = re.compile(
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
        return emoji_pattern.sub("", text).strip()

    def _log_message(self, message: Message) -> None:
        """
        Logs messages based on the provided message attributes. The function maps
        specific message types to corresponding logging levels and ensures that log
        content is stripped of emoji characters to avoid encoding issues, especially
        on Windows consoles.

        Args:
            message (Message): The message object containing the content, type,
                and additional details to be logged.
        """
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
        """
        Handles GUI messages using QMessageBox to display content and associated details
        to the user. The function ensures proper message categorization based on
        the type of message provided and only operates if the `HAS_QT` condition is met.

        Args:
            message (Message): The message object containing information such as content,
                title, type, parent reference, and optional detailed text for display.

        """
        if not HAS_QT:
            return

        parent: QWidget | None = message.parent or self.parent_widget  # type: ignore[assignment]
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
        """
        Creates and displays a progress dialog with a cancel button.

        This method initializes and shows a progress dialog, typically used to
        indicate progress for a lengthy operation. If the operation's total
        progress is set to zero, the dialog will be displayed in an indeterminate
        state. The dialog can be cancelled by the user.

        Args:
            description (str): The description or label displayed in the progress
                dialog to inform the user about the ongoing operation.
            total (int): The total value representing the completion of the
                operation. If set to 0, the dialog acts as an indeterminate
                progress indicator.

        """
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
        """
        Updates the progress dialog with the given value and description.

        This method updates the progress dialog's current progress and label text if
        the progress dialog is available.

        Args:
            value (int): The current progress value to be set in the progress dialog.
            description (str): The label text describing the current progress.
        """
        if self._progress_dialog:
            self._progress_dialog.setValue(value)
            if description:
                self._progress_dialog.setLabelText(description)

    def _close_progress_dialog(self) -> None:
        """
        Closes the progress dialog if it is currently open.

        This method checks whether a progress dialog is active. If it is, the method
        hides it and sets the internal reference to None, ensuring proper cleanup.

        """
        if self._progress_dialog:
            self._progress_dialog.hide()
            self._progress_dialog = None

    @staticmethod
    def _handle_cli_message(message: Message) -> None:
        """
        Handles command-line interface (CLI) messages by adding emoji prefixes based on message type
        and formatting accordingly. Outputs the formatted message to either standard output (stdout)
        or standard error (stderr) depending on the message type.

        This method ensures that critical, warning, and error messages are directed to stderr for better
        error handling, while informational and other types of messages are directed to stdout.

        Args:
            message (Message): The message object containing type, content, and optional details.
        """
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
        if message.msg_type in {MessageType.ERROR, MessageType.WARNING, MessageType.CRITICAL}:
            try:
                print(output, file=sys.stderr, flush=True)
            except OSError:
                # Fallback to stdout if stderr is not available
                print(output, flush=True)
        else:
            print(output, flush=True)

    def show(self, message: Message) -> None:
        """
        Logs and displays a message based on the current mode (GUI or CLI).

        This method ensures the message is always logged and subsequently
        evaluates whether it should be displayed. Depending on the mode
        (GUI or CLI), it either emits a signal for a GUI update or handles
        the message directly for CLI output.

        Args:
            message: The message to be logged and potentially displayed.
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
        Displays an informational message using the Message class.

        This method creates an informational message with the given content
        and additional keyword arguments and then displays it using the
        `show` method.

        Args:
            content (str): The content of the informational message.
            **kwargs (Any): Additional optional arguments for the `Message`
                class.
        """
        message = Message(content, MessageType.INFO, **kwargs)
        self.show(message)

    def warning(self, content: str, **kwargs: Any) -> None:
        """
        Logs a warning message with the specified content and additional keyword
        arguments. The warning will be formatted into a Message object with warning
        message type and displayed using the `show` method.

        Args:
            content (str): The warning message content to be logged.
            **kwargs (Any): Additional keyword arguments for the message.
        """
        message = Message(content, MessageType.WARNING, **kwargs)
        self.show(message)

    def error(self, content: str, **kwargs: Any) -> None:
        """
        Logs an error message and displays it using the corresponding message type.

        Args:
            content (str): The text content of the error message to be logged.
            **kwargs (Any): Additional keyword arguments to customize the message
                creation or display.

        """
        message = Message(content, MessageType.ERROR, **kwargs)
        self.show(message)

    def success(self, content: str, **kwargs: Any) -> None:
        """
        Displays a successful status message.

        Args:
            content (str): The content of the success message.
            **kwargs (Any): Additional optional parameters for message customization.
        """
        message = Message(content, MessageType.SUCCESS, **kwargs)
        self.show(message)

    def debug(self, content: str, **kwargs: Any) -> None:
        """
        Logs a debug level message. The function creates a `Message` instance
        with the provided content and message type, then displays it.

        Args:
            content (str): Content of the debug message.
            **kwargs (Any): Additional arguments passed to the `Message` instance.

        """
        message = Message(content, MessageType.DEBUG, **kwargs)
        self.show(message)

    def critical(self, content: str, **kwargs: Any) -> None:
        """
        Logs a critical message.

        This method creates a message object with the specified critical content
        and passes it to the `show` method for display or further processing.

        Args:
            content: The message content to log as critical.
            **kwargs: Additional keyword arguments to pass when creating the message.
        """
        message = Message(content, MessageType.CRITICAL, **kwargs)
        self.show(message)

    def progress_context(self, description: str, total: int | None = None) -> ProgressContext:
        """
        Creates a ProgressContext for tracking progress.

        This method initializes and returns a ProgressContext object, allowing
        for tracking and displaying the progress of an operation. The progress
        can be customized with a description and a specified total count.

        Args:
            description: A brief description of the progress being tracked.
            total: An optional total value for the operation. If None, the
                progress context will not enforce a maximum value.

        Returns:
            ProgressContext: An instance of the ProgressContext class to manage
                progress tracking.
        """
        return ProgressContext(self, description, total)


# Global instance management
_message_handler: MessageHandler | None = None
_message_handler_lock = threading.Lock()


def init_message_handler(parent: QWidget | None = None, is_gui_mode: bool = False) -> MessageHandler:
    """
    Initializes and returns a global MessageHandler instance.

    This function creates and sets a global MessageHandler instance. The instance
    is initialized with the given parent widget and the GUI mode. Thread safety
    is ensured via a lock mechanism.

    Args:
        parent (QWidget | None): The parent widget for the MessageHandler instance.
            Use None if no parent widget is required.
        is_gui_mode (bool): Flag to indicate if the MessageHandler should operate
            in GUI mode or not.

    Returns:
        MessageHandler: The initialized global MessageHandler instance.
    """
    global _message_handler  # noqa: PLW0603
    with _message_handler_lock:
        _message_handler = MessageHandler(parent, is_gui_mode)
        return _message_handler


def get_message_handler() -> MessageHandler:
    """
    Retrieves the global message handler instance.

    The function ensures thread-safe access to the global message handler.
    If the message handler is not initialized, it raises a `RuntimeError`
    to indicate that initialization must occur prior to usage.

    Returns:
        MessageHandler: The global message handler instance.

    Raises:
        RuntimeError: If the message handler has not been initialized.
    """
    with _message_handler_lock:
        if _message_handler is None:
            raise RuntimeError("Message handler not initialized. Call init_message_handler() first.")
        return _message_handler


# Convenience functions for direct access
def msg_info(content: str, **kwargs: Any) -> None:
    """
    Logs an informational message using the message handler.

    This function sends an informational message to a message handler for logging or
    displaying. Additional keyword arguments can be passed to modify or enhance the
    message behavior as required by the handler.

    Args:
        content: The message content to be logged as an informational message.
        **kwargs: Additional keyword arguments to customize the message behavior.
    """
    get_message_handler().info(content, **kwargs)


def msg_warning(content: str, **kwargs: Any) -> None:
    """
    Logs a warning message through the active message handler.

    This function utilizes the currently active message handler to log a
    warning message specified by the `content` parameter. Additional
    optional keyword arguments can be passed to the handler for custom
    behavior or extensions.

    Args:
        content (str): The message to log as a warning.
        **kwargs (Any): Optional keyword arguments to customize the warning
            message handling.

    """
    get_message_handler().warning(content, **kwargs)


def msg_error(content: str, **kwargs: Any) -> None:
    """
    Logs an error message using the message handler.

    This function retrieves the current message handler and calls its
    `error` method with the provided message content and additional
    keyword arguments.

    Args:
        content (str): The error message to be logged.
        **kwargs: Additional keyword arguments to pass to the message handler's
            `error` method.
    """
    get_message_handler().error(content, **kwargs)


def msg_success(content: str, **kwargs: Any) -> None:
    """
    Logs a success message by utilizing the message handler.

    This function delegates the responsibility of logging a success message
    to the appropriate message handler configured in the application.

    Args:
        content: The message content to be logged as a success.
        **kwargs: Additional keyword arguments to customize the behavior
            of the message handler.

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
    Logs a critical message using the designated message handler.

    Args:
        content (str): The critical message to log.
        **kwargs (Any): Additional parameters to pass to the message handler.
    """
    get_message_handler().critical(content, **kwargs)


@contextmanager
def msg_progress_context(description: str, total: int | None = None) -> Iterator[ProgressContext]:
    """
    Provides a context manager for handling message progress updates.

    This function integrates with a messaging handler to allow progress updates
    to be displayed while performing operations that need to signal their
    progress to the user.

    Args:
        description (str): A description of the progress activity. This is typically displayed
            to give context about the ongoing operation.
        total (int | None, optional): The total number of steps in the progress activity.
            If set to None, the total is treated as indefinite or unknown. Defaults to None.

    Yields:
        ProgressContext: The context object for updating progress during the operation.
    """
    handler = get_message_handler()
    with handler.progress_context(description, total) as progress:
        yield progress
