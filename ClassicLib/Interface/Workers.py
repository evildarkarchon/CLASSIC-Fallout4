"""
Worker classes for background operations in the CLASSIC interface.

This module contains QObject-based worker classes that run in separate threads
to perform long-running operations without blocking the GUI.
"""

import asyncio
import traceback

from PySide6.QtCore import QObject, Signal, Slot

from ClassicLib.ScanGame import write_combined_results
from ClassicLib import GlobalRegistry
from ClassicLib.Logger import logger
from ClassicLib.Update import UpdateCheckError, is_latest_version
from ClassicLib.YamlSettingsCache import classic_settings


class CrashLogsScanWorker(QObject):
    """
    CrashLogsScanWorker is a QObject-based worker class responsible for scanning crash logs and emitting signals based on the scan's outcome.

    Signals:
        finished: Emitted when the scan completes (success or failure)
        notify_sound_signal: Emitted when scan completes successfully
        error_sound_signal: Emitted when an error occurs (for audio notification)
        error_occurred: Emitted with error details (title, message, details) for dialog display
        custom_sound_signal: Emitted with a path to a custom sound to play
    """

    finished: Signal = Signal()
    notify_sound_signal: Signal = Signal()
    error_sound_signal: Signal = Signal()
    error_occurred: Signal = Signal(str, str, str)  # (title, message, details)
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

    @staticmethod
    def _perform_crash_logs_scan() -> None:
        """
        Performs a crash logs scan with pure async event loop.

        Runs the scan in a clean asyncio event loop without Qt overhead.
        Qt automatically handles cross-thread signals via queued connections.

        Raises:
            Exception: Propagates exceptions from the async tasks if they occur.
        """
        import time
        from datetime import datetime

        # Dual timer verification (perf_counter vs wall clock)
        perf_start = time.perf_counter()
        wall_start = time.time()
        start_datetime = datetime.now()

        logger.debug(f"Starting crash logs scan at {start_datetime.strftime('%H:%M:%S.%f')[:-3]}")

        # Import here to avoid circular dependency
        from ClassicLib.ScanLog.ScanLogsExecutor import ScanLogsExecutor
        from ClassicLib.ScanLog.ScanLogsUtils import crashlogs_scan_async_pure
        from ClassicLib.ScanLog import FCXModeHandler

        init_start = time.perf_counter()
        # Initialize scanner with eager_load flag for proactive warm-up
        scanner = ScanLogsExecutor(eager_load=True)
        FCXModeHandler.reset_fcx_checks()
        logger.debug(f"Scanner initialization took {(time.perf_counter() - init_start)*1000:.0f}ms")

        # Create event loop for this worker thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def run_scan() -> None:
            """Run scan with pure async - no Qt overhead."""
            # Warm up resources first
            warmup_start = time.perf_counter()
            logger.debug("Warming up scan resources...")
            await scanner.warm_up()
            logger.debug(f"Resource warm-up complete - took {(time.perf_counter() - warmup_start)*1000:.0f}ms")

            # Run the scan
            scan_start = time.perf_counter()
            await crashlogs_scan_async_pure(scanner)
            logger.debug(f"Actual scan took {time.perf_counter() - scan_start:.2f}s")

        try:
            # Run scan - pure async, no Qt event processing overhead
            loop.run_until_complete(run_scan())

            # Calculate timings with both methods for verification
            perf_elapsed = time.perf_counter() - perf_start
            wall_elapsed = time.time() - wall_start
            end_datetime = datetime.now()
            datetime_elapsed = (end_datetime - start_datetime).total_seconds()

            logger.info(
                f"Scan completed - perf_counter: {perf_elapsed:.2f}s, "
                f"wall_clock: {wall_elapsed:.2f}s, "
                f"datetime: {datetime_elapsed:.2f}s"
            )
        finally:
            # Clean up event loop
            loop.close()
            asyncio.set_event_loop(None)

    def _play_success_notification(self) -> None:
        """Plays a notification sound for successful scan."""
        self.notify_sound_signal.emit()  # type: ignore

    def _handle_scan_error(self, error: Exception) -> None:
        """
        Handles errors during the scan process based on user settings.

        Emits error details for dialog display and optionally plays error sound.
        Always emits error_occurred signal for user feedback.

        Args:
            error: The exception that occurred during scanning

        Raises:
            Exception: Re-raises the exception if audio notifications are disabled
        """
        logger.error(f"Crash logs scan failed: {error!s}")

        # Prepare error details for dialog
        title = "Crash Log Scan Failed"
        message = f"An error occurred during crash log scanning:\n\n{error!s}"
        details = traceback.format_exc()

        # Always emit error details for dialog display
        self.error_occurred.emit(title, message, details)  # type: ignore

        # Handle audio notification based on user settings
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
        play_error_sound: Emitted when an error occurs (for audio notification)
        error_occurred: Emitted with error details (title, message, details) for dialog display
        play_custom_sound: Emitted with a path to a custom sound to play
    """

    scan_finished: Signal = Signal()
    play_success_sound: Signal = Signal()
    play_error_sound: Signal = Signal()
    error_occurred: Signal = Signal(str, str, str)  # (title, message, details)
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
        """
        Handle exceptions during game files scanning.

        Emits error details for dialog display and optionally plays error sound.
        Always emits error_occurred signal for user feedback.

        Args:
            error: The exception that occurred during processing

        Raises:
            Exception: Re-raises the exception if audio notifications are disabled
        """
        logger.error(f"Game files scan failed: {error!s}")

        # Prepare error details for dialog
        title = "Game Files Scan Failed"
        message = f"An error occurred while processing game files:\n\n{error!s}"
        details = traceback.format_exc()

        # Always emit error details for dialog display
        self.error_occurred.emit(title, message, details)  # type: ignore

        # Handle audio notification based on user settings
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

            # Check if pre-release
            if GlobalRegistry.get(GlobalRegistry.Keys.IS_PRERELEASE):
                if self.explicit:
                    self.error.emit("Software is in pre-release stage, update check skipped.")
                self.finished.emit()
                return

            # Use AsyncBridge context manager for explicit cleanup
            with AsyncBridge.get_instance() as bridge:
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
