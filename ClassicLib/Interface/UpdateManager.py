"""
Update management functionality for the CLASSIC interface.

This module contains a mixin class that handles update checking and notification functionality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QThread, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox

from ClassicLib.Constants import YAML
from ClassicLib.Interface.ThreadManager import ThreadType
from ClassicLib.Interface.Workers import UpdateCheckWorker
from ClassicLib.Logger import logger
from ClassicLib.YamlSettingsCache import yaml_settings

if TYPE_CHECKING:
    from PySide6.QtCore import QTimer

    from ClassicLib.Interface.ThreadManager import ThreadManager


class UpdateManagerMixin:
    """
    Mixin class providing update management functionality for the MainWindow.

    This class requires the following attributes to be present in the class it's mixed into:
    - is_update_check_running: bool tracking if update check is in progress
    - update_check_timer: QTimer for scheduling update checks
    - thread_manager: ThreadManager instance
    - update_check_thread: QThread for update checking
    - update_check_worker: UpdateCheckWorker instance
    """

    # Type stubs for attributes that must be provided by the mixing class
    if TYPE_CHECKING:
        is_update_check_running: bool
        update_check_timer: QTimer
        thread_manager: ThreadManager
        update_check_thread: QThread | None
        update_check_worker: UpdateCheckWorker | None

        # Required methods that must be implemented by the mixing class
        def perform_update_check(self) -> None: ...
        def force_update_check(self) -> None: ...

    def update_popup(self) -> None:
        """
        Starts the update check process when the update popup is invoked.

        This method initiates the update checking process by setting the
        `is_update_check_running` flag to True and starting the
        `update_check_timer` with immediate execution.

        Attributes:
            is_update_check_running (bool): Tracks if the update check process is currently running.
            update_check_timer (QTimer): Timer object used to schedule and manage the update checks.

        """
        if not self.is_update_check_running:
            self.is_update_check_running = True
            self.update_check_timer.start(0)  # Start immediately

    # noinspection PyUnresolvedReferences
    def update_popup_explicit(self) -> None:
        """
        Executes an explicit popup update by modifying the update timer's behavior and
        initiating the update process, ensuring the check occurs immediately.

        This function disconnects the timer's default slot for performing an update
        check and reconnects it to a more immediate update check method. If no update
        is currently in progress, it sets the appropriate flag and starts the timer
        with no delay, triggering the explicit check process.

        Attributes:
            update_check_timer (QTimer): Timer used for managing periodic update
                checks in the application.
            is_update_check_running (bool): Flag indicating whether an update check
                is currently in progress.
        """
        self.update_check_timer.timeout.disconnect(self.perform_update_check)
        self.update_check_timer.timeout.connect(self.force_update_check)
        if not self.is_update_check_running:
            self.is_update_check_running = True
            self.update_check_timer.start(0)

    def perform_update_check(self) -> None:
        """
        Stops the update check timer and performs an asynchronous update check.

        This method is responsible for stopping the ongoing update check timer and
        invokes the asynchronous update check function to ensure that updates are
        checked in an orderly and non-blocking manner. Uses a QThread worker
        managed by ThreadManager.

        """
        self.update_check_timer.stop()

        # Check if update check is already running
        if self.thread_manager.is_thread_running(ThreadType.UPDATE_CHECK):
            return  # Update check already in progress

        # Create new thread and worker
        self.update_check_thread = QThread()
        self.update_check_worker = UpdateCheckWorker(explicit=False)
        self.update_check_worker.moveToThread(self.update_check_thread)

        # Register with thread manager
        if not self.thread_manager.register_thread(ThreadType.UPDATE_CHECK, self.update_check_thread, self.update_check_worker):
            logger.error("Failed to register update check thread")
            return

        # Connect signals
        self.update_check_thread.started.connect(self.update_check_worker.run)
        self.update_check_worker.updateAvailable.connect(self.show_update_result)
        self.update_check_worker.error.connect(self.show_update_error)
        self.update_check_worker.finished.connect(self.update_check_thread.quit)
        self.update_check_worker.finished.connect(self.update_check_worker.deleteLater)
        self.update_check_thread.finished.connect(self.update_check_thread.deleteLater)
        self.update_check_thread.finished.connect(self._update_check_finished)

        # Start through thread manager
        self.thread_manager.start_thread(ThreadType.UPDATE_CHECK)

    def force_update_check(self) -> None:
        """
        Directly initiates an update check process, bypassing any saved settings or
        scheduled events to trigger the process immediately. This function ensures that
        any update checking mechanism will execute explicitly without user configuration
        intervention.

        """
        # Directly perform the update check without reading from settings
        self.is_update_check_running = True
        self.update_check_timer.stop()

        # Check if update check is already running
        if self.thread_manager.is_thread_running(ThreadType.UPDATE_CHECK):
            QMessageBox.information(self, "Update Check", "An update check is already in progress.")
            return

        # Create new thread and worker for explicit check
        self.update_check_thread = QThread()
        self.update_check_worker = UpdateCheckWorker(explicit=True)
        self.update_check_worker.moveToThread(self.update_check_thread)

        # Register with thread manager
        if not self.thread_manager.register_thread(ThreadType.UPDATE_CHECK, self.update_check_thread, self.update_check_worker):
            logger.error("Failed to register update check thread")
            self.is_update_check_running = False
            return

        # Connect signals
        self.update_check_thread.started.connect(self.update_check_worker.run)
        self.update_check_worker.updateAvailable.connect(self.show_update_result)
        self.update_check_worker.error.connect(self.show_update_error)
        self.update_check_worker.finished.connect(self.update_check_thread.quit)
        self.update_check_worker.finished.connect(self.update_check_worker.deleteLater)
        self.update_check_thread.finished.connect(self.update_check_thread.deleteLater)
        self.update_check_thread.finished.connect(self._update_check_finished)

        # Start through thread manager
        self.thread_manager.start_thread(ThreadType.UPDATE_CHECK)

    def _update_check_finished(self) -> None:
        """
        Cleanup method called when update check thread finishes.
        """
        self.is_update_check_running = False
        # ThreadManager handles thread cleanup, just clear our references
        self.update_check_thread = None
        self.update_check_worker = None

    def show_update_result(self, is_up_to_date: bool) -> None:
        """
        Displays update result to the user in a message box and handles further actions based
        on the user's response if an update is available.

        Args:
            is_up_to_date: Indicates whether the application is already up to date. If True,
                a message box informs the user that they have the latest version. If False, the
                user is prompted with a choice to visit the update page.
        """
        if is_up_to_date:
            QMessageBox.information(self, "CLASSIC UPDATE", "You have the latest version of CLASSIC!", QMessageBox.StandardButton.Ok)
        else:
            update_popup_text: str = yaml_settings(str, YAML.Main, "CLASSIC_Interface.update_popup_text") or ""
            result = QMessageBox.question(
                self,
                "CLASSIC UPDATE",
                update_popup_text,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.NoButton,
            )
            if result == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl("https://github.com/evildarkarchon/CLASSIC-Fallout4/releases/latest"))

    def show_update_error(self, error_message: str) -> None:
        """
        Displays a warning message with an error description when the application fails to check
        for updates. This method provides user feedback in case of an update failure by showing
        a warning dialog box with the specified error details.

        Args:
            error_message: The error message describing the reason for the update check failure.
        """
        QMessageBox.warning(
            self,
            "Update Check Failed",
            f"Failed to check for updates: {error_message}",
            QMessageBox.StandardButton.NoButton,
            QMessageBox.StandardButton.NoButton,
        )
