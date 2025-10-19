"""
Scan operations mixin for the CLASSIC interface.

This module contains a mixin class with methods for managing scan operations,
including crash logs and game files scanning functionality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QThread, Slot
from PySide6.QtWidgets import QMessageBox

from ClassicLib.Interface.Dialogs import CustomErrorDialog
from ClassicLib.Interface.ThreadManager import ThreadType
from ClassicLib.Interface.Workers import CrashLogsScanWorker, GameFilesScanWorker
from ClassicLib.Logger import logger

if TYPE_CHECKING:
    from PySide6.QtCore import QMutex
    from PySide6.QtWidgets import QButtonGroup, QPushButton, QTabWidget

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
        tab_widget: QTabWidget | None  # For switching to Results tab
        results_tab: object | None  # Results tab widget

        # Required methods that must be implemented by the mixing class
        def start_papyrus_monitoring(self) -> None: ...  # noqa: D102
        def stop_papyrus_monitoring(self) -> None: ...  # noqa: D102
        def refresh_reports_list(self) -> None: ...  # From ResultsViewerMixin  # noqa: D102

    def crash_logs_scan(self) -> None:
        """
        Initiates a crash logs scan in a thread-safe manner, creating a dedicated worker for the scan.

        This method ensures that only one crash logs scan is executed at a time by acquiring a mutex lock
        and checking the current state of scans. If a scan is already in progress, it shows a warning message
        to the user. Otherwise, it creates a new thread and associated worker, registers them with the thread manager,
        and starts the scan process.

        Additionally, it connects various signals between the worker and other components to handle notifications
        and cleanup actions when the scan is completed.
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
        self.crash_logs_worker.error_occurred.connect(self._show_scan_error_dialog)  # type: ignore

        self.crash_logs_thread.started.connect(self.crash_logs_worker.run)
        self.crash_logs_worker.finished.connect(self.crash_logs_thread.quit)  # type: ignore
        self.crash_logs_worker.finished.connect(self.crash_logs_worker.deleteLater)  # type: ignore
        self.crash_logs_thread.finished.connect(self.crash_logs_thread.deleteLater)
        self.crash_logs_thread.finished.connect(self.crash_logs_scan_finished)

        # Disable buttons and update text
        self.disable_scan_buttons()

        # Pause file watching during scan to prevent 60+ refreshes reading ALL reports
        # This prevents the massive I/O bottleneck discovered via cProfile
        if hasattr(self, "file_watcher") and hasattr(self, "_pause_file_watching"):
            self._pause_file_watching()
            logger.debug("Paused file watching during scan to avoid I/O bottleneck")

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
        self.game_files_worker.error_occurred.connect(self._show_scan_error_dialog)  # type: ignore

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
        Disables all scan buttons in the button group to prevent user interaction during a
        scanning operation.

        This method ensures thread-safe interaction with the scan buttons by using a mutex
        lock. It disables all buttons within the scan button group to prevent user actions
        such as initiating scans when the system is already processing.

        Raises:
            Any exception raised during button group iteration or setting button states
            will be propagated to the caller.
        """
        self._scan_mutex.lock()
        try:
            for button_id in self.scan_button_group.buttons():
                button_id.setEnabled(False)
        finally:
            self._scan_mutex.unlock()

    def enable_scan_buttons(self) -> None:
        """
        Enables scan buttons when no scans are running.

        This method ensures that scan buttons within a button group are enabled
        only if there are no active scans currently running. It uses a mutex to
        ensure thread-safe access to the running scans state and button group.

        Raises:
            Any error that might arise from locking or unlocking the mutex.
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
        Handles the completion of the crash logs scan operation. This method is executed
        when the crash logs scan thread finishes its work. It ensures the safe removal of
        the scan from active scans, manages scan button states, and optionally switches the
        interface to the Results tab if configured to do so.
        """
        self.crash_logs_thread = None

        # Thread-safe removal from running scans
        self._scan_mutex.lock()
        try:
            self._running_scans.discard("crash_logs")
        finally:
            self._scan_mutex.unlock()

        self.enable_scan_buttons()  # noinspection PyUnresolvedReferences

        # Resume file watching and do final refresh
        if hasattr(self, "file_watcher") and hasattr(self, "_resume_file_watching"):
            self._resume_file_watching()
            logger.debug("Resumed file watching after scan completion")

            # Do a single final refresh to show all new reports
            if hasattr(self, "refresh_reports_list"):
                self.refresh_reports_list()
                logger.debug("Performed final refresh after scan completion")

        # Switch to Results tab if configured and available
        self._switch_to_results_tab_if_enabled()

    def game_files_scan_finished(self) -> None:
        """
        Handles the completion process of the game files scanning thread.

        This method is called when the game files scanning thread finishes its execution.
        It resets the thread instance, safely removes the "game_files" entry from the list of
        currently running scans, re-enables the scan buttons in the user interface,
        and adjusts the state of Papyrus monitoring based on the Papyrus button state.

        Raises:
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

    def _switch_to_results_tab_if_enabled(self) -> None:
        """
        Switch to the Results tab after scan completion if configured.

        This method checks if automatic tab switching is enabled in settings
        and switches to the Results tab if available. Also refreshes the
        reports list to ensure latest results are displayed.
        """
        try:
            # Check if we have a tab widget and results tab
            if not hasattr(self, "tab_widget") or not hasattr(self, "results_tab"):
                return

            # Check if auto-switch is enabled (default to True for better UX)
            from ClassicLib.Constants import YAML
            from ClassicLib.YamlSettingsCache import yaml_settings

            auto_switch = yaml_settings(bool, YAML.Settings, "ResultsViewer.AutoSwitchAfterScan", True)

            if auto_switch and self.tab_widget and self.results_tab:
                # Find the index of the Results tab
                for i in range(self.tab_widget.count()):
                    if self.tab_widget.widget(i) == self.results_tab:
                        # Switch to Results tab
                        self.tab_widget.setCurrentIndex(i)

                        # Refresh the reports list to show new results
                        if hasattr(self, "refresh_reports_list"):
                            self.refresh_reports_list()

                        logger.debug("Switched to Results tab after scan completion")
                        break

        except (AttributeError, ImportError, KeyError) as e:
            # Don't let tab switching errors break the scan completion
            logger.debug(f"Could not switch to Results tab: {e}")

    @Slot(str, str, str)
    def _show_scan_error_dialog(self, title: str, message: str, details: str) -> None:
        """
        Display an error dialog with scan failure details and copy-to-clipboard functionality.

        This method is called when a scan operation encounters an error.
        It displays a CustomErrorDialog with the error information, including
        an optional detailed text section with traceback information that can
        be copied to the clipboard for easy reporting.

        Args:
            title: The title of the error dialog
            message: The main error message to display
            details: Detailed error information (e.g., traceback)
        """
        logger.debug(f"Showing error dialog: {title}")

        # Create and show custom error dialog with copy functionality
        error_dialog = CustomErrorDialog(
            title=title,
            message=message,
            details=details,
            parent=self,  # type: ignore[arg-type]
        )
        error_dialog.exec()
