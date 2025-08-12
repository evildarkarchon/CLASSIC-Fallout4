"""
Scan operations mixin for the CLASSIC interface.

This module contains a mixin class with methods for managing scan operations,
including crash logs and game files scanning functionality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QMessageBox

from ClassicLib.Interface.ThreadManager import ThreadType
from ClassicLib.Interface.Workers import CrashLogsScanWorker, GameFilesScanWorker
from ClassicLib.Logger import logger

if TYPE_CHECKING:
    from PySide6.QtCore import QMutex
    from PySide6.QtWidgets import QButtonGroup, QPushButton

    from ClassicLib.Interface.Audio import AudioPlayer
    from ClassicLib.Interface.ThreadManager import ThreadManager


class ScanOperationsMixin:
    """
    Mixin class providing scan operation methods for the MainWindow.

    This class requires the following attributes to be present in the class it's mixed into:
    - _scan_mutex: QMutex for thread safety
    - _running_scans: Set tracking running scan operations
    - thread_manager: ThreadManager instance
    - audio_player: AudioPlayer instance
    - scan_button_group: QButtonGroup containing scan buttons
    - papyrus_button: QPushButton for Papyrus monitoring
    - crash_logs_thread: QThread for crash logs scanning
    - crash_logs_worker: CrashLogsScanWorker instance
    - game_files_thread: QThread for game files scanning
    - game_files_worker: GameFilesScanWorker instance
    """

    # Type stubs for attributes that must be provided by the mixing class
    if TYPE_CHECKING:
        _scan_mutex: QMutex
        _running_scans: set[str]
        thread_manager: ThreadManager
        audio_player: AudioPlayer
        scan_button_group: QButtonGroup
        papyrus_button: QPushButton | None
        crash_logs_thread: QThread | None
        crash_logs_worker: CrashLogsScanWorker | None
        game_files_thread: QThread | None
        game_files_worker: GameFilesScanWorker | None

        # Required methods that must be implemented by the mixing class
        def start_papyrus_monitoring(self) -> None: ...
        def stop_papyrus_monitoring(self) -> None: ...

    def crash_logs_scan(self) -> None:
        """
        Initializes and starts the crash logs scanning process by setting up a worker thread.

        This function is responsible for scanning crash logs asynchronously through a worker
        handled in a separate thread managed by ThreadManager. The worker emits signals when
        certain events occur, like notifying or error alerts, which are connected to appropriate
        handlers. Upon completion, the worker and thread are cleaned up, and a callback is invoked
        to indicate the end of the scanning process. Additionally, the UI elements related to
        scanning are disabled during the operation to prevent multiple concurrent scans.

        Returns:
            None
        """
        # Thread-safe check and update
        self._scan_mutex.lock()
        try:
            if "crash_logs" in self._running_scans or self.thread_manager.is_thread_running(ThreadType.CRASH_LOGS_SCAN):
                QMessageBox.warning(self, "Scan in Progress", "A crash logs scan is already in progress.")
                return
            self._running_scans.add("crash_logs")
        finally:
            self._scan_mutex.unlock()

        # Create thread and worker
        self.crash_logs_thread = QThread()
        self.crash_logs_worker = CrashLogsScanWorker()
        self.crash_logs_worker.moveToThread(self.crash_logs_thread)

        # Register with thread manager
        if not self.thread_manager.register_thread(ThreadType.CRASH_LOGS_SCAN, self.crash_logs_thread, self.crash_logs_worker):
            logger.error("Failed to register crash logs scan thread")
            self._scan_mutex.lock()
            self._running_scans.discard("crash_logs")
            self._scan_mutex.unlock()
            return

        # Connect signals
        self.crash_logs_worker.notify_sound_signal.connect(self.audio_player.play_notify_signal.emit)  # type: ignore
        self.crash_logs_worker.error_sound_signal.connect(self.audio_player.play_error_signal.emit)  # type: ignore

        self.crash_logs_thread.started.connect(self.crash_logs_worker.run)
        self.crash_logs_worker.finished.connect(self.crash_logs_thread.quit)  # type: ignore
        self.crash_logs_worker.finished.connect(self.crash_logs_worker.deleteLater)  # type: ignore
        self.crash_logs_thread.finished.connect(self.crash_logs_thread.deleteLater)
        self.crash_logs_thread.finished.connect(self.crash_logs_scan_finished)

        # Disable buttons and update text
        self.disable_scan_buttons()

        # Start through thread manager
        self.thread_manager.start_thread(ThreadType.CRASH_LOGS_SCAN)

    def game_files_scan(self) -> None:
        """
        Scans game files using a separate thread and handles thread setup, worker connections, and signal
        communication to ensure non-blocking UI updates during the operation.

        Starts a scanning process by initializing a worker and a thread managed by ThreadManager.
        The worker emits signals for notifying or handling errors in the scanning process. The scanning
        process disables UI scan buttons until the operation is complete.
        """
        # Thread-safe check and update
        self._scan_mutex.lock()
        try:
            if "game_files" in self._running_scans or self.thread_manager.is_thread_running(ThreadType.GAME_FILES_SCAN):
                QMessageBox.warning(self, "Scan in Progress", "A game files scan is already in progress.")
                return
            self._running_scans.add("game_files")
        finally:
            self._scan_mutex.unlock()

        # Create thread and worker
        self.game_files_thread = QThread()
        self.game_files_worker = GameFilesScanWorker()
        self.game_files_worker.moveToThread(self.game_files_thread)

        # Register with thread manager
        if not self.thread_manager.register_thread(ThreadType.GAME_FILES_SCAN, self.game_files_thread, self.game_files_worker):
            logger.error("Failed to register game files scan thread")
            self._scan_mutex.lock()
            self._running_scans.discard("game_files")
            self._scan_mutex.unlock()
            return

        # Connect signals
        self.game_files_worker.error_sound_signal.connect(self.audio_player.play_error_signal.emit)  # type: ignore

        self.game_files_thread.started.connect(self.game_files_worker.run)
        self.game_files_worker.finished.connect(self.game_files_thread.quit)  # type: ignore
        self.game_files_worker.finished.connect(self.game_files_worker.deleteLater)  # type: ignore
        self.game_files_thread.finished.connect(self.game_files_thread.deleteLater)
        self.game_files_thread.finished.connect(self.game_files_scan_finished)

        # Disable buttons and update text
        self.disable_scan_buttons()

        # Start through thread manager
        self.thread_manager.start_thread(ThreadType.GAME_FILES_SCAN)

    def disable_scan_buttons(self) -> None:
        """
        Disables all buttons in the scan button group.

        This method iterates through the buttons in the scan button group and
        disables them, ensuring they cannot be clicked or interacted with.
        Thread-safe implementation using mutex.

        Returns:
            None
        """
        self._scan_mutex.lock()
        try:
            for button_id in self.scan_button_group.buttons():
                button_id.setEnabled(False)
        finally:
            self._scan_mutex.unlock()

    def enable_scan_buttons(self) -> None:
        """
        Enables all scan buttons within a button group.

        This method iterates through all the scan buttons in a specified button group
        and enables them, allowing user interaction. Only enables buttons if no scans
        are currently running. Thread-safe implementation using mutex.

        Returns:
            None
        """
        self._scan_mutex.lock()
        try:
            # Only enable buttons if no scans are running
            if not self._running_scans:
                for button_id in self.scan_button_group.buttons():
                    button_id.setEnabled(True)
        finally:
            self._scan_mutex.unlock()

    def crash_logs_scan_finished(self) -> None:
        """
        Marks the completion of the crash logs scanning process and resets the relevant UI components.

        This method is executed when the scan for crash logs is finished. It ensures the reset of
        internal state and re-enables UI buttons that were disabled during the scan process.
        Thread-safe implementation using mutex.

        Returns:
            None: This method does not return any value.
        """
        self.crash_logs_thread = None

        # Thread-safe removal from running scans
        self._scan_mutex.lock()
        try:
            self._running_scans.discard("crash_logs")
        finally:
            self._scan_mutex.unlock()

        self.enable_scan_buttons()  # noinspection PyUnresolvedReferences

    def game_files_scan_finished(self) -> None:
        """
        Marks the completion of the game files scanning process.

        This method is invoked when the game files scanning operation is finished. It appropriately
        resets the state by clearing the scanning thread reference and re-enables the buttons
        associated with scanning operations. Thread-safe implementation using mutex.

        Returns:
            None
        """
        self.game_files_thread = None

        # Thread-safe removal from running scans
        self._scan_mutex.lock()
        try:
            self._running_scans.discard("game_files")
        finally:
            self._scan_mutex.unlock()

        self.enable_scan_buttons()

        # Check papyrus button state
        if self.papyrus_button is not None and self.papyrus_button.isChecked():
            self.start_papyrus_monitoring()
        else:
            self.stop_papyrus_monitoring()
