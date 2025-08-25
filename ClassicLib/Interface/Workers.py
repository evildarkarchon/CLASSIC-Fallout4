"""
Worker classes for background operations in the CLASSIC interface.

This module contains QObject-based worker classes that run in separate threads
to perform long-running operations without blocking the GUI.
"""

import asyncio

from PySide6.QtCore import QObject, Signal, Slot

from CLASSIC_ScanGame import write_combined_results
from ClassicLib import GlobalRegistry
from ClassicLib.Logger import logger
from ClassicLib.Update import UpdateCheckError, is_latest_version
from ClassicLib.YamlSettingsCache import classic_settings


class CrashLogsScanWorker(QObject):
    """
    CrashLogsScanWorker is a QObject-based worker class responsible for scanning crash logs and emitting signals based on the scan's outcome.
    Methods:
        run(): Executes the crash logs scan and emits appropriate signals based on the outcome.
    """

    finished: Signal = Signal()
    notify_sound_signal: Signal = Signal()
    error_sound_signal: Signal = Signal()
    custom_sound_signal: Signal = Signal(str)  # In case a custom sound needs to be played

    # noinspection PyBroadException

    @Slot()
    def run(self) -> None:
        """
        Triggers a scan process, determines appropriate audio notification based on the outcome,
        and emits corresponding signals. Upon completion, it ensures the finished signal is emitted
        regardless of the outcome.

        Slot:
            Decorates the method to indicate that it is callable as a slot in the context
            of PyQt/PySide signal-slot mechanism.

        Raises:
            Exception: Propagates any raised exception if audio notifications are disabled.
        """
        # noinspection PyShadowingNames
        try:
            self._perform_crash_logs_scan()
            self._play_success_notification()
        except Exception as e:  # noqa: BLE001
            self._handle_scan_error(e)
        finally:
            self.finished.emit()  # type: ignore

    def _perform_crash_logs_scan(self) -> None:
        """
        Executes the crash logs scan operation with proper async/Qt integration.

        Runs the async scan in a non-blocking way, allowing Qt signals to be
        processed during the operation for real-time progress updates.
        """
        logger.debug("Starting crash logs scan with non-blocking async")

        # Import here to avoid circular dependency
        from CLASSIC_ScanLogs import ClassicScanLogs, crashlogs_scan_async_pure
        from ClassicLib.ScanLog import FCXModeHandler

        # Initialize scanner
        scanner = ClassicScanLogs()
        FCXModeHandler.reset_fcx_checks()

        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Create the main coroutine as a task
            main_task = loop.create_task(crashlogs_scan_async_pure(scanner))

            # Run the event loop in small chunks to allow Qt processing
            while not main_task.done():
                # Run the event loop for a short time
                # This allows async work to progress while yielding periodically
                loop.call_soon(loop.stop)  # Schedule stop after one iteration
                loop.run_forever()  # Run until stop is called

                # Brief yield to allow Qt's cross-thread signal delivery
                # Without this, signals queue up until the entire operation completes
                import time

                time.sleep(0.001)  # 1ms is enough for thread switching

            # Get the result (or raise any exception that occurred)
            main_task.result()

        finally:
            # Clean up the event loop
            loop.close()
            asyncio.set_event_loop(None)

        logger.debug("Crash logs scan completed successfully")

    def _play_success_notification(self) -> None:
        """Plays a notification sound for successful scan."""
        self.notify_sound_signal.emit()  # type: ignore

    def _handle_scan_error(self, error: Exception) -> None:
        """
        Handles errors during the scan process based on user settings.

        Args:
            error: The exception that occurred during scanning

        Raises:
            Exception: Re-raises the exception if audio notifications are disabled
        """
        logger.error(f"Crash logs scan failed: {error!s}")

        audio_notifications_enabled: bool | None = classic_settings(bool, "Audio Notifications")
        if audio_notifications_enabled:
            self.error_sound_signal.emit()  # type: ignore
        else:
            raise error


# noinspection PyBroadException
class GameFilesScanWorker(QObject):
    """
    A worker class responsible for scanning game files in a separate thread.

    This class processes game results and provides audio notifications based on
    the outcome of the scanning process.

    Signals:
        scan_finished: Emitted when the scanning process completes (success or failure)
        play_success_sound: Emitted when processing completes successfully
        play_error_sound: Emitted when an error occurs during processing
        play_custom_sound: Emitted with a path to a custom sound to play
    """

    scan_finished: Signal = Signal()
    play_success_sound: Signal = Signal()
    play_error_sound: Signal = Signal()
    play_custom_sound: Signal = Signal(str)

    @Slot()
    def run(self) -> None:
        """
        Executes the game files scanning process.

        Processes game result data and handles appropriate audio notifications
        based on the outcome and user settings. Always emits the scan_finished
        signal when complete.
        """
        try:
            self._process_game_results()
            self._notify_success()
        except Exception as e:  # noqa: BLE001
            self._handle_error(e)
        finally:
            self.scan_finished.emit()  # type: ignore

    @staticmethod
    def _process_game_results() -> None:
        """Process and write the combined game results data."""
        write_combined_results()

    def _notify_success(self) -> None:
        """Play success notification sound."""
        self.play_success_sound.emit()  # type: ignore

    def _handle_error(self, error: Exception) -> None:
        """Handle exceptions based on user audio notification settings."""
        if classic_settings(bool, "Audio Notifications"):
            self.play_error_sound.emit()  # type: ignore
        else:
            raise error


class UpdateCheckWorker(QObject):
    """
    Worker class to handle update checking in a separate thread using asyncio.

    This replaces the direct asyncio.run() calls that block the Qt event loop.
    """

    # Signals
    finished: Signal = Signal()
    updateAvailable: Signal = Signal(bool)  # True if update available
    error: Signal = Signal(str)

    def __init__(self, explicit: bool = False) -> None:
        """
        Initialize the update check worker.

        Args:
            explicit: Whether this is an explicit user-initiated check
        """
        super().__init__()
        self.explicit = explicit

    @Slot()
    def run(self) -> None:
        """
        Main entry point for the worker thread.
        Uses AsyncBridge for efficient async operations in worker thread.
        """
        try:
            from ClassicLib.AsyncBridge import AsyncBridge

            # Use AsyncBridge instead of creating new event loop
            bridge = AsyncBridge.get_instance()

            # Check if pre-release
            if GlobalRegistry.get(GlobalRegistry.Keys.IS_PRERELEASE):
                if self.explicit:
                    self.error.emit("Software is in pre-release stage, update check skipped.")
                self.finished.emit()
                return

            # Run the async update check using AsyncBridge
            result = bridge.run_async(self._async_check())
            self.updateAvailable.emit(not result)

        except UpdateCheckError as e:
            self.error.emit(str(e))
        except (RuntimeError, OSError, ValueError) as e:
            self.error.emit(f"Unexpected error during update check: {e}")
        finally:
            self.finished.emit()

    async def _async_check(self) -> bool:
        """
        Perform the actual async update check.

        Returns:
            bool: True if up to date, False if update available
        """
        return await is_latest_version(quiet=True, gui_request=self.explicit)
