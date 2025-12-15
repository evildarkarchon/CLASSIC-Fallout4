"""Scan operations controller for CLASSIC interface.

This module provides the ScanController class that handles crash logs and
game files scanning operations with thread-safe execution.

Example:
    >>> from ClassicLib.Interface.controllers.scan_controller import ScanController
    >>> scan_ctrl = ScanController(context)
    >>> scan_ctrl.crash_logs_scan()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QMutex, QThread, Slot
from PySide6.QtWidgets import QMessageBox

from ClassicLib.Constants import YAML
from ClassicLib.Interface.Dialogs import CustomErrorDialog
from ClassicLib.Interface.ThreadManager import ThreadType
from ClassicLib.Interface.Workers import CrashLogsScanWorker, GameFilesScanWorker
from ClassicLib.Logger import logger
from ClassicLib.YamlSettings import yaml_settings

if TYPE_CHECKING:
    from ClassicLib.Interface.context import FeatureContext


class ScanController:
    """Controller for scan operations (crash logs and game files).

    This controller manages scan-related operations including:
    - Starting crash logs scans in a separate thread
    - Starting game files scans in a separate thread
    - Thread-safe tracking of running scans
    - Managing scan button enable/disable states
    - Coordinating with other controllers via SignalHub signals

    Attributes:
        _ctx: The FeatureContext providing access to shared dependencies.
        _scan_mutex: QMutex for thread-safe operations.
        _running_scans: Set of currently running scan types.
        _crash_logs_thread: Current crash logs scan thread (or None).
        _crash_logs_worker: Current crash logs scan worker (or None).
        _game_files_thread: Current game files scan thread (or None).
        _game_files_worker: Current game files scan worker (or None).

    Example:
        >>> controller = ScanController(context)
        >>> controller.crash_logs_scan()  # Start crash logs scan
        >>> controller.game_files_scan()  # Start game files scan
    """

    def __init__(self, context: FeatureContext) -> None:
        """Initialize the ScanController.

        Args:
            context: FeatureContext providing access to main_window, thread_manager,
                signal_hub, and ui_widgets.
        """
        self._ctx = context
        self._scan_mutex = QMutex()
        self._running_scans: set[str] = set()

        # Thread and worker references
        self._crash_logs_thread: QThread | None = None
        self._crash_logs_worker: CrashLogsScanWorker | None = None
        self._game_files_thread: QThread | None = None
        self._game_files_worker: GameFilesScanWorker | None = None

        # Connect to SignalHub signals for button state management
        self._ctx.signal_hub.scan_buttons_enable.connect(self._set_buttons_enabled)

    def crash_logs_scan(self) -> None:
        """Initiate a crash logs scan in a thread-safe manner.

        Creates a dedicated worker thread for the scan, ensuring only one
        crash logs scan runs at a time. Pauses file watching during scan
        to prevent I/O bottlenecks.

        Emits signals for pausing file watching and refreshing reports on completion.
        """
        # Thread-safe check and update
        self._scan_mutex.lock()
        try:
            if "crash_logs" in self._running_scans or self._ctx.thread_manager.is_thread_running(
                ThreadType.CRASH_LOGS_SCAN
            ):
                QMessageBox.warning(
                    self._ctx.main_window,
                    "Scan in Progress",
                    "A crash logs scan is already in progress.",
                )
                return
            self._running_scans.add("crash_logs")
        finally:
            self._scan_mutex.unlock()

        # Create thread and worker
        self._crash_logs_thread = QThread()
        self._crash_logs_worker = CrashLogsScanWorker()
        self._crash_logs_worker.moveToThread(self._crash_logs_thread)

        # Register with thread manager
        if not self._ctx.thread_manager.register_thread(
            ThreadType.CRASH_LOGS_SCAN,
            self._crash_logs_thread,
            self._crash_logs_worker,
        ):
            logger.error("Failed to register crash logs scan thread")
            self._scan_mutex.lock()
            self._running_scans.discard("crash_logs")
            self._scan_mutex.unlock()
            return

        # Connect signals
        self._crash_logs_worker.error_occurred.connect(self._show_scan_error_dialog)
        self._crash_logs_thread.started.connect(self._crash_logs_worker.run)
        self._crash_logs_worker.finished.connect(self._crash_logs_thread.quit)
        self._crash_logs_worker.finished.connect(self._crash_logs_worker.deleteLater)
        self._crash_logs_thread.finished.connect(self._crash_logs_thread.deleteLater)
        self._crash_logs_thread.finished.connect(self._crash_logs_scan_finished)

        # Disable buttons
        self._disable_scan_buttons()

        # Pause file watching during scan to prevent I/O bottleneck
        self._ctx.signal_hub.pause_file_watching.emit()
        logger.debug("Paused file watching during scan to avoid I/O bottleneck")

        # Start through thread manager
        self._ctx.thread_manager.start_thread(ThreadType.CRASH_LOGS_SCAN)

        # Emit scan started signal
        self._ctx.signal_hub.scan_started.emit("crash_logs")

    def game_files_scan(self) -> None:
        """Initiate a game files scan in a thread-safe manner.

        Creates a dedicated worker thread for the scan, ensuring only one
        game files scan runs at a time.

        On completion, starts or stops Papyrus monitoring based on button state.
        """
        # Thread-safe check and update
        self._scan_mutex.lock()
        try:
            if "game_files" in self._running_scans or self._ctx.thread_manager.is_thread_running(
                ThreadType.GAME_FILES_SCAN
            ):
                QMessageBox.warning(
                    self._ctx.main_window,
                    "Scan in Progress",
                    "A game files scan is already in progress.",
                )
                return
            self._running_scans.add("game_files")
        finally:
            self._scan_mutex.unlock()

        # Create thread and worker
        self._game_files_thread = QThread()
        self._game_files_worker = GameFilesScanWorker()
        self._game_files_worker.moveToThread(self._game_files_thread)

        # Register with thread manager
        if not self._ctx.thread_manager.register_thread(
            ThreadType.GAME_FILES_SCAN,
            self._game_files_thread,
            self._game_files_worker,
        ):
            logger.error("Failed to register game files scan thread")
            self._scan_mutex.lock()
            self._running_scans.discard("game_files")
            self._scan_mutex.unlock()
            return

        # Connect signals
        self._game_files_worker.error_occurred.connect(self._show_scan_error_dialog)
        self._game_files_thread.started.connect(self._game_files_worker.run)
        self._game_files_worker.scan_finished.connect(self._game_files_thread.quit)
        self._game_files_worker.scan_finished.connect(self._game_files_worker.deleteLater)
        self._game_files_thread.finished.connect(self._game_files_thread.deleteLater)
        self._game_files_thread.finished.connect(self._game_files_scan_finished)

        # Disable buttons
        self._disable_scan_buttons()

        # Start through thread manager
        self._ctx.thread_manager.start_thread(ThreadType.GAME_FILES_SCAN)

        # Emit scan started signal
        self._ctx.signal_hub.scan_started.emit("game_files")

    def _disable_scan_buttons(self) -> None:
        """Disable all scan buttons to prevent user interaction during scanning.

        Uses mutex lock for thread-safe button state changes.
        """
        self._scan_mutex.lock()
        try:
            scan_button_group = self._ctx.ui_widgets.scan_button_group
            if scan_button_group is not None:
                for button in scan_button_group.buttons():
                    button.setEnabled(False)
        finally:
            self._scan_mutex.unlock()

    def _enable_scan_buttons(self) -> None:
        """Enable scan buttons when no scans are running.

        Uses mutex lock for thread-safe button state changes.
        """
        self._scan_mutex.lock()
        try:
            # Only enable buttons if no scans are running
            if not self._running_scans:
                scan_button_group = self._ctx.ui_widgets.scan_button_group
                if scan_button_group is not None:
                    for button in scan_button_group.buttons():
                        button.setEnabled(True)
        finally:
            self._scan_mutex.unlock()

    def _set_buttons_enabled(self, enabled: bool) -> None:
        """Set scan buttons enabled/disabled state.

        This method is connected to the scan_buttons_enable signal for
        external control of button states.

        Args:
            enabled: Whether buttons should be enabled.
        """
        if enabled:
            self._enable_scan_buttons()
        else:
            self._disable_scan_buttons()

    def _crash_logs_scan_finished(self) -> None:
        """Handle crash logs scan completion.

        Cleans up thread references, enables buttons, resumes file watching,
        refreshes reports, and switches to Results tab if configured.
        """
        self._crash_logs_thread = None
        self._crash_logs_worker = None

        # Thread-safe removal from running scans
        self._scan_mutex.lock()
        try:
            self._running_scans.discard("crash_logs")
        finally:
            self._scan_mutex.unlock()

        self._enable_scan_buttons()

        # Resume file watching and request final refresh via signals
        self._ctx.signal_hub.resume_file_watching.emit()
        logger.debug("Resumed file watching after scan completion")

        # Request a single final refresh to show all new reports
        self._ctx.signal_hub.refresh_reports_requested.emit()
        logger.debug("Requested final refresh after scan completion")

        # Emit scan completed signal
        self._ctx.signal_hub.scan_completed.emit("crash_logs")

        # Switch to Results tab if configured
        self._switch_to_results_tab_if_enabled()

    def _game_files_scan_finished(self) -> None:
        """Handle game files scan completion.

        Cleans up thread references, enables buttons, and starts/stops
        Papyrus monitoring based on button state.
        """
        self._game_files_thread = None
        self._game_files_worker = None

        # Thread-safe removal from running scans
        self._scan_mutex.lock()
        try:
            self._running_scans.discard("game_files")
        finally:
            self._scan_mutex.unlock()

        self._enable_scan_buttons()

        # Emit scan completed signal
        self._ctx.signal_hub.scan_completed.emit("game_files")

        # Check papyrus button state and emit appropriate signal
        papyrus_button = self._ctx.ui_widgets.papyrus_button
        if papyrus_button is not None and papyrus_button.isChecked():
            self._ctx.signal_hub.start_papyrus_monitoring.emit()
        else:
            self._ctx.signal_hub.stop_papyrus_monitoring.emit()

    def _switch_to_results_tab_if_enabled(self) -> None:
        """Switch to the Results tab after scan completion if configured.

        Checks if automatic tab switching is enabled in settings and
        switches to the Results tab if available.
        """
        try:
            tab_widget = self._ctx.ui_widgets.tab_widget
            results_tab = self._ctx.ui_widgets.results_tab

            if tab_widget is None or results_tab is None:
                return

            # Check if auto-switch is enabled (default to True for better UX)
            auto_switch = yaml_settings(bool, YAML.Settings, "ResultsViewer.AutoSwitchAfterScan", True)

            if auto_switch:
                # Find the index of the Results tab
                for i in range(tab_widget.count()):
                    if tab_widget.widget(i) == results_tab:
                        # Switch to Results tab
                        tab_widget.setCurrentIndex(i)
                        logger.debug("Switched to Results tab after scan completion")
                        break

        except (AttributeError, ImportError, KeyError) as e:
            # Don't let tab switching errors break the scan completion
            logger.debug(f"Could not switch to Results tab: {e}")

    @Slot(str, str, str)
    def _show_scan_error_dialog(self, title: str, message: str, details: str) -> None:
        """Display an error dialog with scan failure details.

        Args:
            title: The title of the error dialog.
            message: The main error message to display.
            details: Detailed error information (e.g., traceback).
        """
        logger.debug(f"Showing error dialog: {title}")

        error_dialog = CustomErrorDialog(
            title=title,
            message=message,
            details=details,
            parent=self._ctx.main_window,
        )
        error_dialog.exec()

        # Emit scan failed signal
        self._ctx.signal_hub.scan_failed.emit(title, message)

    def is_scan_running(self, scan_type: str | None = None) -> bool:
        """Check if a scan is currently running.

        Args:
            scan_type: Specific scan type to check ("crash_logs" or "game_files"),
                or None to check if any scan is running.

        Returns:
            True if the specified scan (or any scan) is running.
        """
        self._scan_mutex.lock()
        try:
            if scan_type is None:
                return bool(self._running_scans)
            return scan_type in self._running_scans
        finally:
            self._scan_mutex.unlock()
