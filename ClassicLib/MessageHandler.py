import sys
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Literal

from PySide6.QtCore import QCoreApplication, QObject, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
    QProgressDialog,
    QWidget,
)

from ClassicLib.Logger import logger

# Try to import tqdm for nice progress bars, fall back to custom implementation
#
try:
    # noinspection PyUnresolvedReferences
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


class CLIProgressBar:
    """Simple progress bar for CLI when tqdm is not available."""

    def __init__(
        self,
        total: int,
        desc: str = "",
        bar_length: int = 40,
        fill_char: str = "█",
        empty_char: str = "░",
    ) -> None:
        self.total = total
        self.desc = desc
        self.bar_length = bar_length
        self.fill_char = fill_char
        self.empty_char = empty_char
        self.current = 0
        self.start_time = time.time()
        self._last_line_length = 0

    def update(self, n: int = 1) -> None:
        """Update progress by n steps."""
        self.current = min(self.current + n, self.total)
        self._render()

    def set_description(self, desc: str) -> None:
        """Update the description."""
        self.desc = desc
        self._render()

    def _render(self) -> None:
        """Render the progress bar."""
        percent: float | Literal[100] = 100 if self.total == 0 else self.current / self.total * 100

        filled_length = int(self.bar_length * self.current // self.total)
        bar = self.fill_char * filled_length + self.empty_char * (self.bar_length - filled_length)

        # Calculate elapsed time and speed
        elapsed = time.time() - self.start_time
        if self.current > 0:
            speed = self.current / elapsed
            if self.current < self.total:
                eta = (self.total - self.current) / speed
                time_info = f" [{self._format_time(elapsed)}<{self._format_time(eta)}, {speed:.1f}it/s]"
            else:
                time_info = f" [{self._format_time(elapsed)}, {speed:.1f}it/s]"
        else:
            time_info = ""

        # Build the complete line
        line = f"\r{self.desc}: {percent:3.0f}%|{bar}| {self.current}/{self.total}{time_info}"

        # Clear previous line if it was longer
        if len(line) < self._last_line_length:
            line += " " * (self._last_line_length - len(line))
        self._last_line_length = len(line)

        # Write the line
        sys.stdout.write(line)
        sys.stdout.flush()

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format time in a human-readable way."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        if seconds < 3600:
            return f"{seconds / 60:.0f}m{seconds % 60:02.0f}s"
        hours: float = seconds // 3600
        minutes: float = (seconds % 3600) // 60
        return f"{hours:.0f}h{minutes:02.0f}m"

    def close(self) -> None:
        """Close the progress bar and move to new line."""
        if self.current < self.total:
            self.current = self.total
            self._render()
        sys.stdout.write("\n")
        sys.stdout.flush()


class ProgressContext:
    """Context manager for progress tracking."""

    def __init__(
        self,
        handler: "MessageHandler",
        title: str,
        total: int,
        desc: str = "",
        parent: QWidget | None = None,
    ) -> None:
        self.handler: MessageHandler = handler
        self.title: str = title
        self.total: int = total
        self.desc: str = desc or title
        self.parent: QWidget | None = parent
        self.current = 0
        self.cli_progress: Any | None = None

    def __enter__(self) -> "ProgressContext":
        """Enter the progress context."""
        if self.handler.is_gui_mode:
            # noinspection PyProtectedMember
            self.handler._create_progress_dialog_direct(self.title, self.desc, 0, self.total, self.parent)
        # Create CLI progress bar
        elif HAS_TQDM:
            self.cli_progress = tqdm( # type: ignore
                total=self.total,
                desc=self.desc,
                ncols=80,
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
            )
        else:
            self.cli_progress = CLIProgressBar(self.total, self.desc)
        return self

    def update(self, n: int = 1, desc: str | None = None) -> None:
        """Update progress by n steps."""
        self.current = min(self.current + n, self.total)

        if self.handler.is_gui_mode:
            if desc is not None:
                self.handler.update_progress.emit(self.current, desc)
            else:
                self.handler.update_progress.emit(self.current, self.desc)
        elif self.cli_progress:
            if desc is not None:
                if HAS_TQDM:
                    self.cli_progress.set_description(desc)
                else:
                    self.cli_progress.set_description(desc)
            self.cli_progress.update(n)

    def set_progress(self, value: int, desc: str | None = None) -> None:
        """Set absolute progress value."""
        diff = value - self.current
        if diff > 0:
            self.update(diff, desc)

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the progress context."""
        if self.handler.is_gui_mode:
            self.handler.close_progress.emit()
        elif self.cli_progress:
            self.cli_progress.close()


class MessageType(Enum):
    """Enumeration of message types for the application."""

    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    SUCCESS = auto()
    PROGRESS = auto()
    DEBUG = auto()
    CRITICAL = auto()


class MessageTarget(Enum):
    """Where messages should be displayed."""

    ALL = auto()  # Both GUI and CLI
    GUI_ONLY = auto()  # Only in GUI
    CLI_ONLY = auto()  # Only in CLI/console
    LOG_ONLY = auto()  # Only in log file


@dataclass
class Message:
    """Represents a message to be displayed."""

    content: str
    msg_type: MessageType = MessageType.INFO
    title: str | None = None
    target: MessageTarget = MessageTarget.ALL
    details: str | None = None
    parent: QWidget | None = None


class MessageHandler(QObject):
    """
    Centralized message handling system for both GUI and CLI interfaces.

    This class provides a unified API for displaying messages across different
    interfaces while respecting the target constraints.
    """

    # Signals for GUI updates (must happen on main thread)
    show_message_box = Signal(Message)
    update_progress = Signal(int, str)
    close_progress = Signal()

    def __init__(self, parent: QWidget | None = None, is_gui_mode: bool = True) -> None:
        """
        Initialize the message handler.

        Args:
            parent: Parent widget for GUI dialogs
            is_gui_mode: Whether the application is running in GUI mode
        """
        super().__init__()
        self.parent = parent # type: ignore
        self.is_gui_mode = is_gui_mode
        self.progress_dialog: QProgressDialog | None = None
        self.cli_progress: Any | None = None  # tqdm or CLIProgressBar instance

        # Connect signals to slots for thread-safe GUI updates
        if self.is_gui_mode:
            self.show_message_box.connect(self._show_message_box_slot)
            self.update_progress.connect(self._update_progress_slot)
            self.close_progress.connect(self._close_progress_slot)

        # Message type to icon mapping
        self.icon_map = {
            MessageType.INFO: QMessageBox.Icon.Information,
            MessageType.WARNING: QMessageBox.Icon.Warning,
            MessageType.ERROR: QMessageBox.Icon.Critical,
            MessageType.CRITICAL: QMessageBox.Icon.Critical,
            MessageType.SUCCESS: QMessageBox.Icon.Information,
        }

        # Message type to console prefix mapping
        self.prefix_map: dict[MessageType, str] = {
            MessageType.INFO: "ℹ️",  # noqa: RUF001
            MessageType.WARNING: "⚠️",
            MessageType.ERROR: "❌",
            MessageType.CRITICAL: "🔴",
            MessageType.SUCCESS: "✅",
            MessageType.DEBUG: "🔍",
            MessageType.PROGRESS: "⏳",
        }

    def print(  # noqa: PLR0913
        self,
        content: str,
        msg_type: MessageType = MessageType.INFO,
        title: str | None = None,
        target: MessageTarget = MessageTarget.ALL,
        details: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """
        Display a message using the appropriate method based on the target and mode.

        Args:
            content: The main message content
            msg_type: Type of message (info, warning, error, etc.)
            title: Optional title for GUI message boxes
            target: Where the message should be displayed
            details: Optional detailed information (for GUI)
            parent: Optional parent widget for GUI dialogs
        """
        message = Message(
            content=content,
            msg_type=msg_type,
            title=title or self._get_default_title(msg_type),
            target=target,
            details=details,
            parent=parent or self.parent,
        )

        # Log the message
        self._log_message(message)

        # Display in CLI if appropriate
        if self._should_show_cli(message):
            self._print_cli(message)

        # Display in GUI if appropriate
        if self._should_show_gui(message):
            # Use signal to ensure GUI updates happen on main thread
            self.show_message_box.emit(message)

    def progress(  # noqa: PLR0913
        self,
        title: str,
        message: str,
        minimum: int = 0,
        maximum: int = 100,
        value: int = 0,
        parent: QWidget | None = None,
    ) -> None:
        """
        Show or update a progress dialog/bar.

        Args:
            title: Progress dialog title
            message: Progress message
            minimum: Minimum progress value
            maximum: Maximum progress value
            value: Current progress value
            parent: Parent widget for the dialog
        """
        if not self.is_gui_mode:
            # For CLI, create or update progress bar
            if self.cli_progress is None:
                # Create new progress bar
                total = maximum - minimum
                if HAS_TQDM:
                    self.cli_progress = tqdm( # type: ignore
                        total=total,
                        desc=message,
                        initial=value - minimum,
                        ncols=80,
                        bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
                    )
                else:
                    self.cli_progress = CLIProgressBar(total, message)
                    self.cli_progress.current = value - minimum
                    # noinspection PyProtectedMember
                    self.cli_progress._render()
            # Update existing progress bar
            elif HAS_TQDM:
                self.cli_progress.n = value - minimum
                self.cli_progress.set_description(message)
                self.cli_progress.refresh()
            else:
                self.cli_progress.current = value - minimum
                self.cli_progress.set_description(message)
            return

        if self.progress_dialog is None:
            # Create new progress dialog on main thread
            app_instance: QCoreApplication | None = QApplication.instance()
            if app_instance and app_instance.thread() == self.thread():
                self._create_progress_dialog(title, message, minimum, maximum, parent)
            else:
                # If called from worker thread, we need to use signals
                # For now, just print to console
                self._print_cli_progress(message, value)
                return

        # Update existing progress dialog
        self.update_progress.emit(value, message)

    def close_progress_dialog(self) -> None:
        """Close the current progress dialog/bar if one exists."""
        if self.is_gui_mode and self.progress_dialog:
            self.close_progress.emit()
        elif not self.is_gui_mode and self.cli_progress:
            self.cli_progress.close()
            self.cli_progress = None

    def progress_context(
        self,
        title: str,
        total: int,
        desc: str = "",
        parent: QWidget | None = None,
    ) -> ProgressContext:
        """
        Create a progress context manager for cleaner progress tracking.

        Args:
            title: Progress title (used for GUI window title)
            total: Total number of items to process
            desc: Description (used as progress text)
            parent: Parent widget for GUI dialog

        Returns:
            ProgressContext that can be used with 'with' statement

        Example:
            with msg_handler.progress_context("Processing Files", 100) as progress:
                for i in range(100):
                    progress.update(1, f"Processing file {i+1}")
        """
        return ProgressContext(self, title, total, desc or title, parent or self.parent)

    def info(self, content: str, **kwargs: Any) -> None:
        """Convenience method for info messages."""
        self.print(content, MessageType.INFO, **kwargs)

    def warning(self, content: str, **kwargs: Any) -> None:
        """Convenience method for warning messages."""
        self.print(content, MessageType.WARNING, **kwargs)

    def error(self, content: str, **kwargs: Any) -> None:
        """Convenience method for error messages."""
        self.print(content, MessageType.ERROR, **kwargs)

    def success(self, content: str, **kwargs: Any) -> None:
        """Convenience method for success messages."""
        self.print(content, MessageType.SUCCESS, **kwargs)

    def debug(self, content: str, **kwargs: Any) -> None:
        """Convenience method for debug messages."""
        self.print(content, MessageType.DEBUG, **kwargs)

    def critical(self, content: str, **kwargs: Any) -> None:
        """Convenience method for critical messages."""
        self.print(content, MessageType.CRITICAL, **kwargs)

    # Private methods

    @staticmethod
    def _should_show_cli(message: Message) -> bool:
        """Determine if message should be shown in CLI."""
        if message.target == MessageTarget.GUI_ONLY:
            return False
        return message.target != MessageTarget.LOG_ONLY

    def _should_show_gui(self, message: Message) -> bool:
        """Determine if message should be shown in GUI."""
        if not self.is_gui_mode:
            return False
        if message.target == MessageTarget.CLI_ONLY:
            return False
        if message.target == MessageTarget.LOG_ONLY:
            return False
        if message.msg_type == MessageType.DEBUG:
            return False  # Don't show debug messages in GUI
        return message.msg_type != MessageType.PROGRESS  # Progress uses different mechanism

    @staticmethod
    def _get_default_title(msg_type: MessageType) -> str:
        """Get default title based on message type."""
        return {
            MessageType.INFO: "Information",
            MessageType.WARNING: "Warning",
            MessageType.ERROR: "Error",
            MessageType.CRITICAL: "Critical Error",
            MessageType.SUCCESS: "Success",
            MessageType.DEBUG: "Debug",
            MessageType.PROGRESS: "Progress",
        }.get(msg_type, "Message")

    @staticmethod
    def _log_message(message: Message) -> None:
        """Log message to file using the logger."""
        log_methods = {
            MessageType.INFO: logger.info,
            MessageType.WARNING: logger.warning,
            MessageType.ERROR: logger.error,
            MessageType.CRITICAL: logger.critical,
            MessageType.DEBUG: logger.debug,
            MessageType.SUCCESS: logger.info,
            MessageType.PROGRESS: logger.info,
        }

        log_method = log_methods.get(message.msg_type, logger.info)
        log_content = f"{message.title}: {message.content}"
        if message.details:
            log_content += f"\nDetails: {message.details}"
        log_method(log_content)

    def _print_cli(self, message: Message) -> None:
        """Print message to CLI/console."""
        prefix = self.prefix_map.get(message.msg_type, "")
        output = f"{prefix} {message.content}"

        # Use stderr for errors and warnings
        if message.msg_type in (MessageType.ERROR, MessageType.WARNING, MessageType.CRITICAL):
            print(output, file=sys.stderr, flush=True)
        else:
            print(output, flush=True)

    @staticmethod
    def _print_cli_progress(message: str, percentage: int) -> None:
        """Print progress update to CLI (fallback when no progress bar)."""
        # Use \r to overwrite the same line for progress updates
        output = f"\r⏳ {message} [{percentage}%]"
        print(output, end="", flush=True)
        if percentage >= 100:
            print()  # New line when complete

    def _create_progress_dialog_direct(
        self,
        title: str,
        message: str,
        minimum: int,
        maximum: int,
        parent: QWidget | None,
    ) -> None:
        """Create progress dialog directly (for context manager)."""
        if self.is_gui_mode:
            self._create_progress_dialog(title, message, minimum, maximum, parent)

    # Qt Slots (must run on main thread)

    def _show_message_box_slot(self, message: Message) -> None:
        """Show message box on main thread."""
        msg_box = QMessageBox(message.parent)
        msg_box.setWindowTitle(message.title)
        msg_box.setText(message.content)

        if message.details:
            msg_box.setDetailedText(message.details)

        icon = self.icon_map.get(message.msg_type, QMessageBox.Icon.Information)
        msg_box.setIcon(icon)

        msg_box.exec()

    def _create_progress_dialog(
        self,
        title: str,
        message: str,
        minimum: int,
        maximum: int,
        parent: QWidget | None,
    ) -> None:
        """Create progress dialog on main thread."""
        self.progress_dialog = QProgressDialog(message, "Cancel", minimum, maximum, parent or self.parent)
        self.progress_dialog.setWindowTitle(title)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.show()

    def _update_progress_slot(self, value: int, message: str) -> None:
        """Update progress dialog on main thread."""
        if self.progress_dialog:
            self.progress_dialog.setValue(value)
            self.progress_dialog.setLabelText(message)

    def _close_progress_slot(self) -> None:
        """Close progress dialog on main thread."""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        if self.cli_progress:
            self.cli_progress.close()
            self.cli_progress = None


# Store handler in a container to avoid global statement
_handler_container: list[MessageHandler | None] = [None]


def init_message_handler(parent: QWidget | None = None, is_gui_mode: bool = True) -> MessageHandler:
    """
    Initialize the global message handler.

    Args:
        parent: Parent widget for GUI dialogs
        is_gui_mode: Whether the application is running in GUI mode

    Returns:
        The initialized MessageHandler instance
    """
    handler = MessageHandler(parent, is_gui_mode)
    _handler_container[0] = handler
    return handler


def get_message_handler() -> MessageHandler:
    """
    Get the global message handler instance.

    Returns:
        The global MessageHandler instance

    Raises:
        RuntimeError: If message handler hasn't been initialized
    """
    if _handler_container[0] is None:
        raise RuntimeError("Message handler not initialized. Call init_message_handler() first.")
    return _handler_container[0]


# Convenience functions for direct access
def msg_print(  # noqa: PLR0913
    content: str,
    msg_type: MessageType = MessageType.INFO,
    title: str | None = None,
    target: MessageTarget = MessageTarget.ALL,
    details: str | None = None,
    parent: QWidget | None = None,
) -> None:
    """Print a message using the global message handler."""
    get_message_handler().print(content, msg_type, title, target, details, parent)


def msg_info(content: str, **kwargs: Any) -> None:
    """Print an info message."""
    get_message_handler().info(content, **kwargs)


def msg_warning(content: str, **kwargs: Any) -> None:
    """Print a warning message."""
    get_message_handler().warning(content, **kwargs)


def msg_error(content: str, **kwargs: Any) -> None:
    """Print an error message."""
    get_message_handler().error(content, **kwargs)


def msg_success(content: str, **kwargs: Any) -> None:
    """Print a success message."""
    get_message_handler().success(content, **kwargs)


def msg_progress(  # noqa: PLR0913
    title: str,
    message: str,
    minimum: int = 0,
    maximum: int = 100,
    value: int = 0,
    parent: QWidget | None = None,
) -> None:
    """Show or update a progress dialog."""
    get_message_handler().progress(title, message, minimum, maximum, value, parent)


def msg_close_progress() -> None:
    """Close the current progress dialog."""
    get_message_handler().close_progress_dialog()


def msg_progress_context(
    title: str,
    total: int,
    desc: str = "",
    parent: QWidget | None = None,
) -> ProgressContext:
    """
    Create a progress context manager for cleaner progress tracking.

    Args:
        title: Progress title (used for GUI window title)
        total: Total number of items to process
        desc: Description (used as progress text)
        parent: Parent widget for GUI dialog

    Returns:
        ProgressContext that can be used with 'with' statement

    Example:
        with msg_progress_context("Processing Files", 100) as progress:
            for i in range(100):
                progress.update(1, f"Processing file {i+1}")
    """
    return get_message_handler().progress_context(title, total, desc, parent)