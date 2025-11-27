"""Qt progress handling for GUI progress dialogs.

This module provides Qt-based progress indicators using QProgressDialog.
It uses signals for thread-safe cross-thread communication.

Note: This module imports PySide6 and should only be imported when
Qt is available and needed.
"""

from __future__ import annotations

import time
from typing import Final

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QProgressDialog, QWidget


class QtProgressHandler(QObject):
    """Qt progress handler with signal-based thread safety.

    This handler manages QProgressDialog for GUI progress display.
    It uses signals to safely communicate between worker threads
    and the main GUI thread.

    Attributes:
        progress_create_signal: Signal to create progress dialog (desc, total).
        progress_update_signal: Signal to update progress (value, desc).
        progress_close_signal: Signal to close progress dialog.
    """

    # Signals for thread-safe progress dialog management
    progress_create_signal = Signal(str, int)  # description, total
    progress_update_signal = Signal(int, str)  # value, description
    progress_close_signal = Signal()

    # Throttle interval for updates (50ms = 20 updates/sec max)
    _THROTTLE_INTERVAL: Final[float] = 0.05

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the Qt progress handler.

        Args:
            parent: Parent widget for the progress dialog.
        """
        super().__init__(parent)
        self._parent = parent
        self._progress_dialog: QProgressDialog | None = None
        self._cancelled = False
        self._last_update_time = 0.0
        self._current = 0
        self._total: int | None = None

        # Connect signals to slots
        self.progress_create_signal.connect(self._create_dialog)
        self.progress_update_signal.connect(self._update_dialog)
        self.progress_close_signal.connect(self._close_dialog)

    def _is_main_thread(self) -> bool:  # noqa: PLR6301
        """Check if we're on the main thread."""
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is None:
                return False
            return QThread.currentThread() == app.thread()
        except (ImportError, RuntimeError):
            return False

    def start(self, description: str, total: int | None = None) -> None:
        """Start the progress indicator.

        Args:
            description: Description of the operation.
            total: Total items, or None for indeterminate.
        """
        self._cancelled = False
        self._current = 0
        self._total = total
        self._last_update_time = time.time()

        # Use signal for thread safety
        self.progress_create_signal.emit(description, total or 0)

    def _create_dialog(self, description: str, total: int) -> None:
        """Create the progress dialog on the main thread.

        Args:
            description: Description text.
            total: Total items (0 for indeterminate).
        """
        # Reset cancellation state
        self._cancelled = False

        self._progress_dialog = QProgressDialog(
            description,
            "Cancel",
            0,
            total,
            self._parent,
        )
        self._progress_dialog.setWindowTitle("Progress")
        self._progress_dialog.setAutoClose(True)
        self._progress_dialog.setAutoReset(True)

        if total == 0:
            self._progress_dialog.setRange(0, 0)  # Indeterminate

        self._progress_dialog.show()

    def update(self, n: int = 1, description: str | None = None) -> None:
        """Update progress.

        Args:
            n: Items completed since last update.
            description: Optional new description.
        """
        self._current += n

        # Throttle updates to reduce cross-thread overhead
        current_time = time.time()
        time_since_last = current_time - self._last_update_time

        # Always emit for last item or if enough time has passed
        is_last_item = self._total is not None and self._current >= self._total
        should_emit = is_last_item or time_since_last >= self._THROTTLE_INTERVAL

        if should_emit:
            self.progress_update_signal.emit(self._current, description or "")
            self._last_update_time = current_time

    def _update_dialog(self, value: int, description: str) -> None:
        """Update the progress dialog on the main thread.

        Args:
            value: Current progress value.
            description: Optional new description.
        """
        if self._progress_dialog is None:
            return

        self._progress_dialog.setValue(value)
        if description:
            self._progress_dialog.setLabelText(description)

        # Check for user cancellation
        if self._progress_dialog.wasCanceled():
            self._cancelled = True

    def close(self) -> None:
        """Close the progress indicator."""
        self.progress_close_signal.emit()

    def _close_dialog(self) -> None:
        """Close the progress dialog on the main thread."""
        if self._progress_dialog is not None:
            self._progress_dialog.hide()
            self._progress_dialog = None
        # Reset state
        self._cancelled = False
        self._current = 0

    def was_cancelled(self) -> bool:
        """Check if the user cancelled.

        Returns:
            True if cancelled.
        """
        # Also check dialog directly if on main thread
        if self._progress_dialog is not None and self._is_main_thread() and self._progress_dialog.wasCanceled():
            self._cancelled = True
        return self._cancelled

    def is_available(self) -> bool:  # noqa: PLR6301
        """Check if Qt progress is available.

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
            parent: New parent widget for progress dialogs.
        """
        self._parent = parent
