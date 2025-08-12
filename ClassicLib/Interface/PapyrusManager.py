from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QThread

from ClassicLib.Interface.Papyrus import PapyrusMonitorWorker
from ClassicLib.Interface.PapyrusDialog import PapyrusMonitorDialog
from ClassicLib.Interface.ThreadManager import ThreadType
from ClassicLib.Logger import logger

if TYPE_CHECKING:
    from PySide6.QtWidgets import QPushButton

    from ClassicLib.Interface.ThreadManager import ThreadManager


class PapyrusManagerMixin:
    """
    Mixin class for managing Papyrus monitoring functionality.

    This mixin requires the mixing class to provide:
    - papyrus_button: QPushButton for toggling monitoring
    - thread_manager: ThreadManager for managing worker threads
    - papyrus_monitor_thread: Optional QThread for the monitoring thread
    - papyrus_monitor_worker: Optional PapyrusMonitorWorker instance
    - papyrus_monitor_dialog: Optional PapyrusMonitorDialog instance
    """

    # Type stubs for attributes that must be provided by the mixing class
    if TYPE_CHECKING:
        papyrus_button: QPushButton | None
        thread_manager: ThreadManager
        papyrus_monitor_thread: QThread | None
        papyrus_monitor_worker: PapyrusMonitorWorker | None
        papyrus_monitor_dialog: PapyrusMonitorDialog | None

    def toggle_papyrus_worker(self) -> None:
        """
        Toggles the state of the Papyrus worker based on the state of the `papyrus_button`.

        If the `papyrus_button` is checked, the Papyrus monitoring process is started and
        the custom monitoring dialog is displayed. Otherwise, it stops the Papyrus monitoring
        process and closes the dialog. This function is intended to manage the lifecycle
        of the Papyrus worker efficiently.
        """
        if self.papyrus_button and self.papyrus_button.isChecked():
            self.start_papyrus_monitoring()
        else:
            self.stop_papyrus_monitoring()

    def start_papyrus_monitoring(self) -> None:
        """
        Initializes and starts the Papyrus monitoring process using a separate thread and worker. This allows
        asynchronous monitoring of the Papyrus system, ensuring that updates, errors, and other signals are
        handled efficiently without blocking the main application. Uses ThreadManager for thread lifecycle
        management.

        Raises:
            Any exception or error handling will be caught and managed by connected signals
            such as `error`.
        """
        # Check if already running
        if self.thread_manager.is_thread_running(ThreadType.PAPYRUS_MONITOR):
            return  # Already monitoring

        # Create new thread and worker
        self.papyrus_monitor_thread = QThread()
        self.papyrus_monitor_worker = PapyrusMonitorWorker()
        self.papyrus_monitor_worker.moveToThread(self.papyrus_monitor_thread)

        # Register with thread manager
        if not self.thread_manager.register_thread(ThreadType.PAPYRUS_MONITOR, self.papyrus_monitor_thread, self.papyrus_monitor_worker):
            logger.error("Failed to register Papyrus monitor thread")
            return

        # Create the dialog
        self.papyrus_monitor_dialog = PapyrusMonitorDialog(self)

        # Connect signals
        self.papyrus_monitor_thread.started.connect(self.papyrus_monitor_worker.run)
        self.papyrus_monitor_worker.statsUpdated.connect(self.papyrus_monitor_dialog.update_stats)
        self.papyrus_monitor_worker.error.connect(self.papyrus_monitor_dialog.handle_error)
        self.papyrus_monitor_dialog.stop_monitoring.connect(self.stop_papyrus_monitoring)
        self.papyrus_monitor_thread.finished.connect(self.papyrus_monitor_thread.deleteLater)
        self.papyrus_monitor_worker.finished.connect(self.papyrus_monitor_worker.deleteLater)  # type: ignore

        # Start monitoring
        if self.papyrus_button:
            self.papyrus_button.setText("STOP PAPYRUS MONITORING")
            self.papyrus_button.setStyleSheet(
                """
                QPushButton {
                    color: black;
                    background: rgb(237, 45, 45);  /* Red background */
                    border-radius: 10px;
                    border: 1px solid black;
                    font-weight: bold;
                    font-size: 14px;
                }
                """
            )

        # Show the dialog and start through thread manager
        self.papyrus_monitor_dialog.show()
        self.thread_manager.start_thread(ThreadType.PAPYRUS_MONITOR)

    def stop_papyrus_monitoring(self) -> None:
        """
        Stops the papyrus monitoring process and performs necessary cleanup.

        This function terminates the papyrus monitoring by halting the monitor worker and
        its associated thread using ThreadManager. It also updates the user interface components,
        such as the button, and closes the Papyrus monitoring dialog if it's open.

        Returns:
            None
        """
        # Stop the worker first for clean shutdown
        if self.papyrus_monitor_worker:
            self.papyrus_monitor_worker.stop()

        # Stop thread through ThreadManager
        self.thread_manager.stop_thread(ThreadType.PAPYRUS_MONITOR, wait_ms=2000)

        # Reset references
        self.papyrus_monitor_thread = None
        self.papyrus_monitor_worker = None

        # Close the dialog if it exists
        if self.papyrus_monitor_dialog:
            self.papyrus_monitor_dialog.close()
            self.papyrus_monitor_dialog = None

        # Update UI
        if self.papyrus_button:
            self.papyrus_button.setText("START PAPYRUS MONITORING")
            self.papyrus_button.setStyleSheet(
                """
                QPushButton {
                    color: black;
                    background: rgb(45, 237, 138);  /* Green background */
                    border-radius: 10px;
                    border: 1px solid black;
                    font-weight: bold;
                    font-size: 14px;
                }
                """
            )
            self.papyrus_button.setChecked(False)
