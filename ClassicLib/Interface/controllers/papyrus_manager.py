"""Papyrus monitoring controller for CLASSIC interface.

This module provides the PapyrusManager class that handles the lifecycle
of Papyrus log monitoring.

Example:
    >>> from ClassicLib.Interface.controllers.papyrus_manager import PapyrusManager
    >>> papyrus_mgr = PapyrusManager(context)
    >>> papyrus_mgr.start_monitoring()

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QThread

from ClassicLib.core.logger import logger
from ClassicLib.Interface.dialogs.PapyrusDialog import PapyrusMonitorDialog
from ClassicLib.Interface.widgets.Papyrus import PapyrusMonitorWorker
from ClassicLib.Interface.workers.ThreadManager import ThreadType

if TYPE_CHECKING:
    from ClassicLib.Interface.shared.context import FeatureContext


class PapyrusManager:
    """Controller for Papyrus monitoring functionality.

    This controller manages the Papyrus monitoring lifecycle:
    - Starting the monitoring worker thread
    - Displaying the monitoring dialog
    - Stopping monitoring and cleanup
    - Updating the monitoring button state

    Attributes:
        _ctx: The FeatureContext providing access to shared dependencies.
        _monitor_thread: Current monitoring thread (or None).
        _monitor_worker: Current monitoring worker (or None).
        _monitor_dialog: Current monitoring dialog (or None).

    Example:
        >>> manager = PapyrusManager(context)
        >>> manager.toggle_monitoring()  # Based on button state
        >>> manager.start_monitoring()  # Explicitly start
        >>> manager.stop_monitoring()  # Explicitly stop

    """

    # Button styles
    START_STYLE = """
        QPushButton {
            color: black;
            background: rgb(45, 237, 138);  /* Green background */
            border-radius: 10px;
            border: 1px solid black;
            font-weight: bold;
            font-size: 14px;
        }
    """

    STOP_STYLE = """
        QPushButton {
            color: black;
            background: rgb(237, 45, 45);  /* Red background */
            border-radius: 10px;
            border: 1px solid black;
            font-weight: bold;
            font-size: 14px;
        }
    """

    def __init__(self, context: FeatureContext) -> None:
        """Initialize the PapyrusManager.

        Args:
            context: FeatureContext providing access to main_window, thread_manager,
                signal_hub, and ui_widgets.

        """
        self._ctx = context
        self._monitor_thread: QThread | None = None
        self._monitor_worker: PapyrusMonitorWorker | None = None
        self._monitor_dialog: PapyrusMonitorDialog | None = None

        # Connect to SignalHub signals
        self._ctx.signal_hub.start_papyrus_monitoring.connect(self.start_monitoring)
        self._ctx.signal_hub.stop_papyrus_monitoring.connect(self.stop_monitoring)

    def toggle_monitoring(self) -> None:
        """Toggle monitoring based on the papyrus button state.

        If the button is checked, starts monitoring. Otherwise, stops it.
        """
        papyrus_button = self._ctx.ui_widgets.papyrus_button
        if papyrus_button and papyrus_button.isChecked():
            self.start_monitoring()
        else:
            self.stop_monitoring()

    def start_monitoring(self) -> None:
        """Start Papyrus monitoring.

        Creates the worker thread and monitoring dialog, connects signals,
        and starts the monitoring process.
        """
        # Check if already running
        if self._ctx.thread_manager.is_thread_running(ThreadType.PAPYRUS_MONITOR):
            return

        # Create new thread and worker
        self._monitor_thread = QThread()
        self._monitor_worker = PapyrusMonitorWorker()
        self._monitor_worker.moveToThread(self._monitor_thread)

        # Register with thread manager
        if not self._ctx.thread_manager.register_thread(
            ThreadType.PAPYRUS_MONITOR,
            self._monitor_thread,
            self._monitor_worker,
        ):
            logger.error("Failed to register Papyrus monitor thread")
            return

        # Create the dialog
        self._monitor_dialog = PapyrusMonitorDialog(self._ctx.main_window)

        # Connect signals
        self._monitor_thread.started.connect(self._monitor_worker.run)
        self._monitor_worker.statsUpdated.connect(self._monitor_dialog.update_stats)
        self._monitor_worker.error.connect(self._monitor_dialog.handle_error)
        self._monitor_dialog.stop_monitoring.connect(self.stop_monitoring)
        self._monitor_thread.finished.connect(self._monitor_thread.deleteLater)
        self._monitor_worker.finished.connect(self._monitor_worker.deleteLater)

        # Update UI
        self._update_button_style(monitoring=True)

        # Show the dialog and start through thread manager
        self._monitor_dialog.show()
        self._ctx.thread_manager.start_thread(ThreadType.PAPYRUS_MONITOR)

        # Emit state change signal
        self._ctx.signal_hub.papyrus_monitoring_state_changed.emit(True)

        logger.info("Papyrus monitoring started")

    def stop_monitoring(self) -> None:
        """Stop Papyrus monitoring.

        Stops the worker, waits for thread completion, closes the dialog,
        and updates the UI.
        """
        # Stop the worker first for clean shutdown
        if self._monitor_worker:
            self._monitor_worker.stop()

        # Stop thread through ThreadManager
        self._ctx.thread_manager.stop_thread(ThreadType.PAPYRUS_MONITOR, wait_ms=2000)

        # Reset references
        self._monitor_thread = None
        self._monitor_worker = None

        # Close the dialog if it exists
        if self._monitor_dialog:
            self._monitor_dialog.close()
            self._monitor_dialog = None

        # Update UI
        self._update_button_style(monitoring=False)

        # Emit state change signal
        self._ctx.signal_hub.papyrus_monitoring_state_changed.emit(False)

        logger.info("Papyrus monitoring stopped")

    def _update_button_style(self, monitoring: bool) -> None:
        """Update the papyrus button text and style.

        Args:
            monitoring: True if monitoring is active, False otherwise.

        """
        papyrus_button = self._ctx.ui_widgets.papyrus_button
        if papyrus_button is None:
            return

        if monitoring:
            papyrus_button.setText("STOP PAPYRUS MONITORING")
            papyrus_button.setStyleSheet(self.STOP_STYLE)
        else:
            papyrus_button.setText("START PAPYRUS MONITORING")
            papyrus_button.setStyleSheet(self.START_STYLE)
            papyrus_button.setChecked(False)

        # Also emit signal for other listeners
        self._ctx.signal_hub.papyrus_button_style_update.emit(monitoring)

    def is_monitoring(self) -> bool:
        """Check if Papyrus monitoring is currently active.

        Returns:
            True if monitoring is running, False otherwise.

        """
        return self._ctx.thread_manager.is_thread_running(ThreadType.PAPYRUS_MONITOR)
