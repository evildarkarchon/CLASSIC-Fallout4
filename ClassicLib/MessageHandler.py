"""Message Handler for CLASSIC - Unified message handling for GUI and CLI modes.

This module provides a unified interface for displaying messages, warnings, errors,
and progress bars in both GUI (PySide6) and CLI modes. It replaces direct print
statements and QTextEdit output boxes with appropriate message boxes and progress bars.
"""

import logging
import sys
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

    # Forward references
    MessageHandler = "MessageHandler"
    ProgressContext = "ProgressContext"

# Try to import tqdm for enhanced CLI progress bars
try:
    # noinspection PyUnresolvedReferences
    from tqdm import tqdm  # noqa: TC002

    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# Try to import PySide6 for GUI mode
try:
    from PySide6.QtCore import QObject, Signal, QThread
    from PySide6.QtWidgets import QMessageBox, QProgressDialog, QWidget

    HAS_QT = True
except ImportError:
    HAS_QT = False
    # Define dummy classes for type checking when Qt is not available
    if TYPE_CHECKING:

        class QObject:
            pass

        class QWidget:
            pass

        class QThread:
            # noinspection PyPep8Naming
            @staticmethod
            def currentThread() -> "QThread":
                pass

        class QMessageBox:
            class Icon:
                Information: int = 0
                Warning: int = 1
                Critical: int = 2

        # noinspection PyPep8Naming
        class QProgressDialog:
            def hide(self) -> None:
                pass

            def setValue(self, value: int) -> None:
                pass

            def setLabelText(self, text: str) -> None:
                pass

        class Signal:
            def __init__(self, *args: Any) -> None:
                pass

            def emit(self, *args: Any) -> None:
                pass

            def connect(self, func: Any) -> None:
                pass


class MessageType(Enum):
    """Types of messages that can be displayed."""

    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    SUCCESS = auto()
    PROGRESS = auto()
    DEBUG = auto()
    CRITICAL = auto()


class MessageTarget(Enum):
    """Target destinations for messages."""

    ALL = auto()  # Show in both GUI and CLI
    GUI_ONLY = auto()  # Show only in GUI mode
    CLI_ONLY = auto()  # Show only in CLI mode
    LOG_ONLY = auto()  # Only write to log file, no display


@dataclass
class Message:
    """Container for a message with its metadata."""

    content: str
    msg_type: MessageType
    target: MessageTarget = MessageTarget.ALL
    title: str | None = None
    details: str | None = None
    parent: QWidget | None = None


class CLIProgressBar:
    """Simple progress bar for CLI when tqdm is not available."""

    def __init__(self, desc: str = "", total: int | None = None) -> None:
        """Initialize CLI progress bar.

        Args:
            desc: Description to show
            total: Total number of items
        """
        self.desc = desc
        self.total = total
        self.current = 0
        self._closed = False

    def update(self, n: int = 1) -> None:
        """Update progress by n steps."""
        if self._closed:
            return

        self.current += n
        if self.total:
            percent = int((self.current / self.total) * 100)
            bar_length = 40
            filled = int(bar_length * self.current / self.total)
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"\r{self.desc}: [{bar}] {percent}%", end="", flush=True)
        else:
            print(f"\r{self.desc}: {self.current} items processed", end="", flush=True)

    def set_description(self, desc: str) -> None:
        """Update the description."""
        self.desc = desc

    def close(self) -> None:
        """Close the progress bar."""
        if not self._closed:
            print()  # New line after progress
            self._closed = True


class ProgressContext:
    """Context manager for progress tracking that works in both GUI and CLI modes."""

    def __init__(self, handler: "MessageHandler", description: str, total: int | None = None) -> None:
        """Initialize progress context.

        Args:
            handler: The message handler instance
            description: Description of the operation
            total: Total number of items to process
        """
        self.handler = handler
        self.description = description
        self.total = total
        self.current = 0
        self._progress_bar: tqdm | CLIProgressBar | QProgressDialog | None = None

    def __enter__(self) -> "ProgressContext":
        """Enter the context and create appropriate progress indicator."""
        if self.handler.is_gui_mode and HAS_QT:
            # Check if we're in the main thread and QApplication exists
            try:
                from PySide6.QtWidgets import QApplication

                app = QApplication.instance()
                is_main_thread = QThread.currentThread() == self.handler.main_thread

                if app is not None and is_main_thread:
                    # Create Qt progress dialog in main thread with QApplication available
                    self._progress_bar = QProgressDialog(self.description, "Cancel", 0, self.total or 0, self.handler.parent_widget)
                    self._progress_bar.setWindowTitle("Progress")
                    self._progress_bar.setAutoClose(True)
                    self._progress_bar.setAutoReset(True)
                    if self.total is None:
                        self._progress_bar.setRange(0, 0)  # Indeterminate
                    self._progress_bar.show()
                else:
                    # We're in a worker thread - use signals to create progress dialog in main thread
                    self.handler.progress_create_signal.emit(self.description, self.total or 0)
                    self._progress_bar = "qt_signal"  # Marker to indicate we're using Qt signals
            except (ImportError, RuntimeError):
                # Fallback to CLI progress if Qt is not available or has issues
                # Suppress progress in GUI mode even if Qt fails
                self._progress_bar = None
        # CLI mode
        elif HAS_TQDM:
            from tqdm import tqdm  # Import locally when we know it's available

            self._progress_bar = tqdm(total=self.total, desc=self.description, file=sys.stdout)
        else:
            self._progress_bar = CLIProgressBar(self.description, self.total)

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context and clean up progress indicator."""
        if self._progress_bar is not None:
            if isinstance(self._progress_bar, QProgressDialog):
                self._progress_bar.hide()
            elif self._progress_bar == "qt_signal":
                self.handler.progress_close_signal.emit()
            elif hasattr(self._progress_bar, "close"):
                self._progress_bar.close()

    def update(self, n: int = 1, description: str | None = None) -> None:
        """Update progress by n steps.

        Args:
            n: Number of steps to advance
            description: Optional new description
        """
        self.current += n

        if self._progress_bar is None:
            return

        if isinstance(self._progress_bar, QProgressDialog):
            self._progress_bar.setValue(self.current)
            if description:
                self._progress_bar.setLabelText(description)
        elif self._progress_bar == "qt_signal":
            self.handler.progress_signal.emit(self.current, description or "")
        elif hasattr(self._progress_bar, "update"):
            self._progress_bar.update(n)
            if description and hasattr(self._progress_bar, "set_description"):
                self._progress_bar.set_description(description)


class MessageHandler(QObject):
    """Main message handler that routes messages to appropriate outputs."""

    # Qt signals for thread-safe GUI updates
    if HAS_QT:
        message_signal = Signal(Message)
        progress_signal = Signal(int, str)
        progress_create_signal = Signal(str, int)  # description, total
        progress_close_signal = Signal()

    def __init__(self, parent: QWidget | None = None, is_gui_mode: bool = False) -> None:
        """Initialize the message handler.

        Args:
            parent: Parent widget for GUI message boxes
            is_gui_mode: Whether running in GUI mode
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
            self.main_thread = threading.current_thread()

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
        log_content = message.content
        if message.details:
            log_content += f"\nDetails: {message.details}"

        self.logger.log(log_level, log_content)

    def _handle_gui_message(self, message: Message) -> None:
        """Handle displaying message in GUI mode (runs in main thread)."""
        if not HAS_QT:
            return

        parent = message.parent or self.parent_widget
        title = message.title or message.msg_type.name.title()
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
            msg_box = QMessageBox(icon, title, message.content, parent=parent)
            msg_box.setDetailedText(message.details)
            msg_box.exec()
        else:
            QMessageBox(icon, title, message.content, parent=parent).exec()

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
        prefix_map = {
            MessageType.INFO: "",
            MessageType.WARNING: "⚠️ ",
            MessageType.ERROR: "❌ ",
            MessageType.SUCCESS: "✅ ",
            MessageType.CRITICAL: "🚨 ",
            MessageType.DEBUG: "🐛 ",
        }

        prefix = prefix_map.get(message.msg_type, "")
        output = f"{prefix}{message.content}"

        if message.details:
            output += f"\n   Details: {message.details}"

        # Use stderr for errors and warnings
        if message.msg_type in (MessageType.ERROR, MessageType.WARNING, MessageType.CRITICAL):
            print(output, file=sys.__stderr__, flush=True)
        else:
            print(output)

    def show(self, message: Message) -> None:
        """Show a message using the appropriate method."""
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
        """Show info message."""
        message = Message(content, MessageType.INFO, **kwargs)
        self.show(message)

    def warning(self, content: str, **kwargs: Any) -> None:
        """Show warning message."""
        message = Message(content, MessageType.WARNING, **kwargs)
        self.show(message)

    def error(self, content: str, **kwargs: Any) -> None:
        """Show error message."""
        message = Message(content, MessageType.ERROR, **kwargs)
        self.show(message)

    def success(self, content: str, **kwargs: Any) -> None:
        """Show success message."""
        message = Message(content, MessageType.SUCCESS, **kwargs)
        self.show(message)

    def debug(self, content: str, **kwargs: Any) -> None:
        """Show debug message."""
        message = Message(content, MessageType.DEBUG, **kwargs)
        self.show(message)

    def critical(self, content: str, **kwargs: Any) -> None:
        """Show critical message."""
        message = Message(content, MessageType.CRITICAL, **kwargs)
        self.show(message)

    def progress_context(self, description: str, total: int | None = None) -> ProgressContext:
        """Create a progress context manager.

        Args:
            description: Description of the operation
            total: Total number of items to process

        Returns:
            Progress context manager
        """
        return ProgressContext(self, description, total)


# Global instance management
_message_handler: MessageHandler | None = None


def init_message_handler(parent: QWidget | None = None, is_gui_mode: bool = False) -> MessageHandler:
    """Initialize the global message handler.

    Args:
        parent: Parent widget for GUI message boxes
        is_gui_mode: Whether running in GUI mode

    Returns:
        The initialized message handler
    """
    global _message_handler  # noqa: PLW0603
    _message_handler = MessageHandler(parent, is_gui_mode)
    return _message_handler


def get_message_handler() -> MessageHandler:
    """Get the global message handler instance.

    Returns:
        The message handler instance

    Raises:
        RuntimeError: If handler not initialized
    """
    if _message_handler is None:
        raise RuntimeError("Message handler not initialized. Call init_message_handler() first.")
    return _message_handler


# Convenience functions for direct access
def msg_info(content: str, **kwargs: Any) -> None:
    """Show info message."""
    get_message_handler().info(content, **kwargs)


def msg_warning(content: str, **kwargs: Any) -> None:
    """Show warning message."""
    get_message_handler().warning(content, **kwargs)


def msg_error(content: str, **kwargs: Any) -> None:
    """Show error message."""
    get_message_handler().error(content, **kwargs)


def msg_success(content: str, **kwargs: Any) -> None:
    """Show success message."""
    get_message_handler().success(content, **kwargs)


def msg_debug(content: str, **kwargs: Any) -> None:
    """Show debug message."""
    get_message_handler().debug(content, **kwargs)


def msg_critical(content: str, **kwargs: Any) -> None:
    """Show critical message."""
    get_message_handler().critical(content, **kwargs)


@contextmanager
def msg_progress_context(description: str, total: int | None = None) -> 'Iterator[ProgressContext]':
    """Create a progress context manager using the global handler.
    
    Args:
        description: Description of the operation
        total: Total number of items to process
        
    Yields:
        Progress context manager
    """
    handler = get_message_handler()
    with handler.progress_context(description, total) as progress:
        yield progress