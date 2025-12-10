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
        Updates the popup display by initiating an update check if one is not already running.

        This method ensures that the update checking process is initiated only
        if no other update check is currently ongoing. It flags the update as
        running and starts the update timer immediately.

        Raises:
            None
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
        Performs an update check by initializing and starting a worker thread.

        This method stops any existing update check timer, verifies if an update
        check is already in progress, and then proceeds to create a new thread
        and worker for performing the update check. It registers the worker
        thread with a thread manager, connects appropriate signals for handling
        the worker's operations and results, and starts the worker through
        the thread manager.

        Raises:
            None
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
        Performs a force update check by initiating a new thread and worker to handle
        the update process explicitly. This method bypasses the typical settings and
        ensures an immediate update check is started if no other update check is already
        running. Handles proper thread and worker lifecycle management, including signal
        connections for success, error, and completion of the update process.

        Raises:
            QMessageBox: Provides information if an update check is already in progress.
        """
        # Directly perform the update check without reading from settings
        self.is_update_check_running = True
        self.update_check_timer.stop()

        # Check if update check is already running
        if self.thread_manager.is_thread_running(ThreadType.UPDATE_CHECK):
            QMessageBox.information(self, "Update Check", "An update check is already in progress.") # pyright: ignore[reportArgumentType]
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
        Marks the update check as finished by resetting relevant flags and clearing
        references to worker and thread objects.

        Resets the `is_update_check_running` flag to `False` and clears the references
        to the worker and thread instances associated with the update check process.

        Raises:
            None
        """
        self.is_update_check_running = False
        # ThreadManager handles thread cleanup, just clear our references
        self.update_check_thread = None
        self.update_check_worker = None

    def show_update_result(self, is_up_to_date: bool) -> None:
        """
        Display results of an update check to the user and prompts for further action if an update is available.

        Args:
            is_up_to_date: A boolean value indicating whether the current version is up to date.
        """
        if is_up_to_date:
            QMessageBox.information(self, "CLASSIC UPDATE", "You have the latest version of CLASSIC!", QMessageBox.StandardButton.Ok) # pyright: ignore[reportArgumentType]
        else:
            update_popup_text: str = yaml_settings(str, YAML.Main, "CLASSIC_Interface.update_popup_text") or ""
            result = QMessageBox.question(
                self, # pyright: ignore[reportArgumentType]
                "CLASSIC UPDATE",
                update_popup_text,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.NoButton,
            )
            if result == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl("https://github.com/evildarkarchon/CLASSIC-Fallout4/releases/latest"))

    def show_update_error(self, error_message: str) -> None:
        """
        Displays a warning message box indicating a failure to check for updates.

        This method uses a QMessageBox to show an error message to the user when
        a check for updates fails, providing the supplied error message in the
        dialog.

        Args:
            error_message (str): The error message to be displayed in the warning
                dialog.
        """
        QMessageBox.warning(
            self, # pyright: ignore[reportArgumentType]
            "Update Check Failed",
            f"Failed to check for updates: {error_message}",
            QMessageBox.StandardButton.NoButton,
            QMessageBox.StandardButton.NoButton,
        )
