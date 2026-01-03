"""Qt GUI output backend for graphical message display.

This module provides the GUIBackend class that handles message output
via Qt's QMessageBox dialogs. It uses Qt signals for thread-safe
cross-thread communication.

Note: This module imports PySide6 and should only be imported when
Qt is available and needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QMessageBox, QWidget

from ClassicLib.MessageHandler.core.enums import MessageType

if TYPE_CHECKING:
    from ClassicLib.MessageHandler.core.message import Message


class GUIBackend(QObject):
    """Qt GUI output backend - displays QMessageBox dialogs.

    This backend handles GUI message display using Qt's QMessageBox.
    It uses signals for thread-safe updates from worker threads.

    Attributes:
        message_signal: Signal emitted when a message needs display.

    Class Attributes:
        ICON_MAP: Mapping of message types to QMessageBox icons.

    """

    # Signal for thread-safe message display
    message_signal = Signal(object)

    ICON_MAP: ClassVar[dict[MessageType, QMessageBox.Icon]] = {
        MessageType.INFO: QMessageBox.Icon.Information,
        MessageType.WARNING: QMessageBox.Icon.Warning,
        MessageType.ERROR: QMessageBox.Icon.Critical,
        MessageType.SUCCESS: QMessageBox.Icon.Information,
        MessageType.CRITICAL: QMessageBox.Icon.Critical,
        MessageType.DEBUG: QMessageBox.Icon.Information,
        MessageType.PROGRESS: QMessageBox.Icon.Information,
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the GUI backend.

        Args:
            parent: Parent widget for message boxes.

        """
        super().__init__(parent)
        self._parent = parent
        # Use QueuedConnection explicitly to ensure _handle_message always runs
        # on the main thread, even when show() is called from a worker thread
        self.message_signal.connect(self._handle_message, Qt.ConnectionType.QueuedConnection)

    def show(self, message: Message) -> None:
        """Display a message via signal emission.

        This method emits a signal to ensure thread-safe GUI updates.
        The actual display happens in _handle_message on the main thread.

        Args:
            message: The message to display.

        """
        self.message_signal.emit(message)

    def _handle_message(self, message: Message) -> None:
        """Handle message display on the main thread.

        Args:
            message: The message to display.

        """
        parent: QWidget | None = message.parent or self._parent  # type: ignore[assignment]
        title = message.get_display_title()
        icon = self.ICON_MAP.get(message.msg_type, QMessageBox.Icon.Information)

        msg_box = QMessageBox(parent=parent, text=message.content, icon=icon)
        msg_box.setWindowTitle(title)

        if message.details:
            msg_box.setDetailedText(message.details)

        msg_box.exec()

    def is_available(self) -> bool:  # noqa: PLR6301
        """Check if GUI output is available.

        Returns:
            True if Qt is properly initialized.

        """
        try:
            from PySide6.QtWidgets import QApplication

            return QApplication.instance() is not None
        except ImportError:
            return False

    def set_parent(self, parent: QWidget | None) -> None:
        """Update the parent widget.

        Args:
            parent: New parent widget for message boxes.

        """
        self._parent = parent
