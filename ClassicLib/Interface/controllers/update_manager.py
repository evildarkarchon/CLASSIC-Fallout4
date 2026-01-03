"""Update manager controller for CLASSIC interface.

This module provides the UpdateManager class that handles checking for
application updates and notifying users of available updates.

Example:
    >>> from ClassicLib.Interface.controllers.update_manager import UpdateManager
    >>> update_mgr = UpdateManager(context)
    >>> update_mgr.update_popup()

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QThread, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox

from ClassicLib.Constants import YAML
from ClassicLib.Interface.ThreadManager import ThreadType
from ClassicLib.Interface.Workers import UpdateCheckWorker
from ClassicLib.Logger import logger
from ClassicLib.YamlSettings import yaml_settings

if TYPE_CHECKING:
    from ClassicLib.Interface.context import FeatureContext


class UpdateManager:
    """Controller for application update checking functionality.

    This controller manages update-related operations including:
    - Checking for updates on startup (if enabled)
    - Explicit update checks triggered by user
    - Displaying update availability notifications
    - Opening release download page

    All update checks run in a separate thread to avoid blocking the UI.

    Attributes:
        _ctx: The FeatureContext providing access to shared dependencies.
        _is_update_check_running: Flag indicating if update check is in progress.
        _update_check_timer: Timer for scheduling update checks.
        _update_check_thread: Current update check thread (or None).
        _update_check_worker: Current update check worker (or None).

    Example:
        >>> manager = UpdateManager(context)
        >>> manager.update_popup()  # Check with timer delay
        >>> manager.update_popup_explicit()  # Check immediately

    """

    def __init__(self, context: FeatureContext) -> None:
        """Initialize the UpdateManager.

        Args:
            context: FeatureContext providing access to main_window, thread_manager,
                and signal_hub.

        """
        self._ctx = context
        self._is_update_check_running = False
        self._update_check_timer = QTimer()
        self._update_check_thread: QThread | None = None
        self._update_check_worker: UpdateCheckWorker | None = None

        # Store pending result to show dialog after thread cleanup
        self._pending_update_result: bool | None = None
        self._pending_error_message: str | None = None

        # Connect timer to perform_update_check by default
        self._update_check_timer.timeout.connect(self.perform_update_check)

    def update_popup(self) -> None:
        """Initiate an update check with timer delay.

        Starts the update timer immediately, which triggers perform_update_check.
        Prevents duplicate checks if one is already running.
        """
        if not self._is_update_check_running:
            self._is_update_check_running = True
            self._update_check_timer.start(0)  # Start immediately

    def update_popup_explicit(self) -> None:
        """Initiate an explicit (user-triggered) update check.

        Switches the timer to use force_update_check and starts immediately.
        The explicit check always shows results, even if up-to-date.
        """
        import contextlib

        # Switch timer to force check
        with contextlib.suppress(RuntimeError):
            self._update_check_timer.timeout.disconnect(self.perform_update_check)
        self._update_check_timer.timeout.connect(self.force_update_check)

        if not self._is_update_check_running:
            self._is_update_check_running = True
            self._update_check_timer.start(0)

    def perform_update_check(self) -> None:
        """Perform a background update check.

        Creates a worker thread to check for updates without blocking.
        Results are shown only if an update is available.
        """
        self._update_check_timer.stop()

        # Check if update check is already running
        if self._ctx.thread_manager.is_thread_running(ThreadType.UPDATE_CHECK):
            return

        # Create new thread and worker
        self._update_check_thread = QThread()
        self._update_check_worker = UpdateCheckWorker(explicit=False)
        self._update_check_worker.moveToThread(self._update_check_thread)

        # Register with thread manager
        if not self._ctx.thread_manager.register_thread(
            ThreadType.UPDATE_CHECK,
            self._update_check_thread,
            self._update_check_worker,
        ):
            logger.error("Failed to register update check thread")
            return

        # Connect signals with proper connection types for cross-thread safety
        # Use QueuedConnection for signals that trigger UI operations to prevent
        # threading issues when the modal QMessageBox runs a nested event loop
        self._update_check_thread.started.connect(self._update_check_worker.run)
        self._update_check_worker.updateAvailable.connect(self._on_update_result, Qt.ConnectionType.QueuedConnection)
        self._update_check_worker.error.connect(self._on_update_error, Qt.ConnectionType.QueuedConnection)

        # Worker signals thread to quit
        self._update_check_worker.finished.connect(self._update_check_thread.quit, Qt.ConnectionType.QueuedConnection)

        # Only delete the thread after it finishes - don't call deleteLater() on worker
        # The worker will be garbage collected when Python refs are cleared
        # This avoids cross-thread deletion issues with QBasicTimer
        # Use QueuedConnection to ensure these run on the main thread, not the worker thread
        self._update_check_thread.finished.connect(self._update_check_thread.deleteLater, Qt.ConnectionType.QueuedConnection)
        self._update_check_thread.finished.connect(self._update_check_finished, Qt.ConnectionType.QueuedConnection)

        # Start through thread manager
        self._ctx.thread_manager.start_thread(ThreadType.UPDATE_CHECK)

    def force_update_check(self) -> None:
        """Perform an explicit update check that always shows results.

        Similar to perform_update_check but uses explicit=True, which
        shows a message even if the application is up-to-date.
        """
        self._is_update_check_running = True
        self._update_check_timer.stop()

        # Check if update check is already running
        if self._ctx.thread_manager.is_thread_running(ThreadType.UPDATE_CHECK):
            QMessageBox.information(
                self._ctx.main_window,
                "Update Check",
                "An update check is already in progress.",
            )
            return

        # Create new thread and worker for explicit check
        self._update_check_thread = QThread()
        self._update_check_worker = UpdateCheckWorker(explicit=True)
        self._update_check_worker.moveToThread(self._update_check_thread)

        # Register with thread manager
        if not self._ctx.thread_manager.register_thread(
            ThreadType.UPDATE_CHECK,
            self._update_check_thread,
            self._update_check_worker,
        ):
            logger.error("Failed to register update check thread")
            self._is_update_check_running = False
            return

        # Connect signals with proper connection types for cross-thread safety
        # Use QueuedConnection for signals that trigger UI operations to prevent
        # threading issues when the modal QMessageBox runs a nested event loop
        self._update_check_thread.started.connect(self._update_check_worker.run)
        self._update_check_worker.updateAvailable.connect(self._on_update_result, Qt.ConnectionType.QueuedConnection)
        self._update_check_worker.error.connect(self._on_update_error, Qt.ConnectionType.QueuedConnection)

        # Worker signals thread to quit
        self._update_check_worker.finished.connect(self._update_check_thread.quit, Qt.ConnectionType.QueuedConnection)

        # Only delete the thread after it finishes - don't call deleteLater() on worker
        # The worker will be garbage collected when Python refs are cleared
        # This avoids cross-thread deletion issues with QBasicTimer
        # Use QueuedConnection to ensure these run on the main thread, not the worker thread
        self._update_check_thread.finished.connect(self._update_check_thread.deleteLater, Qt.ConnectionType.QueuedConnection)
        self._update_check_thread.finished.connect(self._update_check_finished, Qt.ConnectionType.QueuedConnection)

        # Start through thread manager
        self._ctx.thread_manager.start_thread(ThreadType.UPDATE_CHECK)

    def _update_check_finished(self) -> None:
        """Handle update check completion.

        Resets the running flag, clears thread/worker references, and shows
        any pending dialog. The dialog is shown AFTER thread cleanup to avoid
        cross-thread QObject parenting issues.
        """
        self._is_update_check_running = False
        self._update_check_thread = None
        self._update_check_worker = None

        # Show pending dialog AFTER thread cleanup is complete
        # Use singleShot to ensure we're fully out of the signal handler
        if self._pending_error_message is not None:
            error_msg = self._pending_error_message
            self._pending_error_message = None
            QTimer.singleShot(0, lambda: self.show_update_error(error_msg))
        elif self._pending_update_result is not None:
            result = self._pending_update_result
            self._pending_update_result = None
            QTimer.singleShot(0, lambda: self.show_update_result(result))

    def _on_update_result(self, update_available: bool) -> None:
        """Handle update result signal by storing result for later display.

        The dialog is NOT shown here - it's shown from _update_check_finished
        after the thread has fully cleaned up to prevent cross-thread issues.

        Args:
            update_available: True if an update IS available (not up-to-date),
                False if no update available (is up-to-date).

        """
        # Signal sends True if update IS available (not up-to-date).
        # show_update_result expects True if IS up-to-date.
        # Invert the value to match expected semantics.
        self._pending_update_result = not update_available

    def _on_update_error(self, error_message: str) -> None:
        """Handle update error signal by storing error for later display.

        The dialog is NOT shown here - it's shown from _update_check_finished
        after the thread has fully cleaned up to prevent cross-thread issues.

        Args:
            error_message: Description of the error that occurred.

        """
        # Store error - dialog will be shown from _update_check_finished
        self._pending_error_message = error_message

    def show_update_result(self, is_up_to_date: bool) -> None:
        """Display the update check result to the user.

        Args:
            is_up_to_date: True if current version is the latest.

        """
        if is_up_to_date:
            QMessageBox.information(
                self._ctx.main_window,
                "CLASSIC UPDATE",
                "You have the latest version of CLASSIC!",
                QMessageBox.StandardButton.Ok,
            )
        else:
            update_popup_text: str = yaml_settings(str, YAML.Main, "CLASSIC_Interface.update_popup_text") or ""
            result = QMessageBox.question(
                self._ctx.main_window,
                "CLASSIC UPDATE",
                update_popup_text,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.NoButton,
            )
            if result == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl("https://github.com/evildarkarchon/CLASSIC-Fallout4/releases/latest"))

    def show_update_error(self, error_message: str) -> None:
        """Display an update check error to the user.

        Args:
            error_message: Description of the error that occurred.

        """
        QMessageBox.warning(
            self._ctx.main_window,
            "Update Check Failed",
            f"Failed to check for updates: {error_message}",
            QMessageBox.StandardButton.NoButton,
            QMessageBox.StandardButton.NoButton,
        )

    def stop_timer(self) -> None:
        """Stop the update check timer.

        Should be called during application shutdown.
        """
        if self._update_check_timer:
            self._update_check_timer.stop()
