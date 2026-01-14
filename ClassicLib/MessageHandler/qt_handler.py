"""Qt-enabled message handler for GUI mode.

This module provides the QtMessageHandler class that extends the base
MessageHandler with Qt integration. It handles signal-based thread-safe
GUI updates and Qt progress dialogs.

Note: This module imports PySide6 and should only be imported when
Qt is available and GUI mode is needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Qt, QThread, Signal

from ClassicLib.MessageHandler.handler import MessageHandler
from ClassicLib.MessageHandler.output.gui_backend import GUIBackend
from ClassicLib.MessageHandler.progress.qt_progress import QtProgressHandler

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from ClassicLib.MessageHandler.core.message import Message
    from ClassicLib.MessageHandler.output.base import OutputBackend
    from ClassicLib.MessageHandler.progress.base import ProgressHandler


class QtMessageHandler(MessageHandler, QObject):
    """Qt-enabled message handler for GUI mode.

    This class extends MessageHandler with Qt integration:
    - Uses GUIBackend for QMessageBox display
    - Uses QtProgressHandler for QProgressDialog
    - Provides signals for thread-safe cross-thread communication

    Signals:
        message_signal: Emitted when a message needs display.
        progress_signal: Emitted to update progress (value, description).
        progress_create_signal: Emitted to create progress dialog (desc, total).
        progress_close_signal: Emitted to close progress dialog.
    """

    # Signals for thread-safe GUI updates
    message_signal = Signal(object)  # Message object
    progress_signal = Signal(int, str)  # value, description
    progress_create_signal = Signal(str, int)  # description, total
    progress_close_signal = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the Qt message handler.

        Args:
            parent: Parent widget for message boxes and dialogs.

        """
        # Initialize both parent classes
        MessageHandler.__init__(self, is_gui_mode=True)
        QObject.__init__(self, parent)

        self._parent_widget = parent
        self._gui_backend = GUIBackend(parent)
        self._qt_progress = QtProgressHandler(parent)

        # Override main thread reference with Qt thread
        self._main_thread = QThread.currentThread()  # type: ignore[assignment]

        # Connect progress signals to handler with QueuedConnection to ensure
        # slots always run on the main thread, even when emitted from workers
        self.progress_create_signal.connect(self._on_progress_create, Qt.ConnectionType.QueuedConnection)
        self.progress_signal.connect(self._on_progress_update, Qt.ConnectionType.QueuedConnection)
        self.progress_close_signal.connect(self._on_progress_close, Qt.ConnectionType.QueuedConnection)

    @property
    def parent_widget(self) -> QWidget | None:
        """Parent widget for dialogs.

        Returns:
            The parent QWidget, or None if not set.

        """
        return self._parent_widget

    @property
    def main_thread(self) -> QThread:
        """Reference to the main Qt thread.

        Returns:
            The main QThread instance.

        """
        return self._main_thread

    def _get_output_backend(self) -> OutputBackend:
        """Get the GUI output backend.

        Returns:
            GUIBackend for Qt message display.

        """
        return self._gui_backend

    def create_progress_handler(self) -> ProgressHandler:
        """Get the Qt progress handler.

        Returns the pre-created QtProgressHandler to ensure thread safety.
        Creating a new handler from a worker thread would cause the QObject
        to be associated with that thread, breaking cross-thread signal
        delivery and causing Qt widgets to be created on the wrong thread.

        Returns:
            QtProgressHandler for Qt progress dialogs.

        """
        return self._qt_progress

    def show(self, message: Message) -> None:
        """Display a message with GUI support.

        Always logs, then displays via GUI backend with signal-based
        thread safety.

        Args:
            message: The message to display.

        """
        # Always log
        self._log_backend.show(message)

        # Check if should display
        if not self._router.should_display(message.target):
            return

        # Use GUI backend (which uses signals internally)
        self._gui_backend.show(message)

    def _on_progress_create(self, description: str, total: int) -> None:
        """Handle progress creation signal.

        Args:
            description: Progress description.
            total: Total items (0 for indeterminate).

        """
        self._cancelled = False
        self._qt_progress.start(description, total if total > 0 else None)

    def _on_progress_update(self, value: int, description: str) -> None:
        """Handle progress update signal.

        Args:
            value: Current progress value.
            description: Optional new description.

        """
        self._qt_progress._current = value  # pyright: ignore[reportPrivateUsage]
        self._qt_progress._update_dialog(value, description)  # pyright: ignore[reportPrivateUsage]

        # Check for cancellation
        if self._qt_progress.was_cancelled():
            self._cancelled = True

    def _on_progress_close(self) -> None:
        """Handle progress close signal."""
        self._qt_progress.close()
        self._cancelled = False

    def is_cancelled(self) -> bool:
        """Check if operation was cancelled.

        Returns:
            True if user cancelled via progress dialog.

        """
        if self._qt_progress.was_cancelled():
            self._cancelled = True
        return self._cancelled

    def set_parent(self, parent: QWidget | None) -> None:
        """Update the parent widget.

        Args:
            parent: New parent widget.

        """
        self._parent_widget = parent
        self._gui_backend.set_parent(parent)
        self._qt_progress.set_parent(parent)
