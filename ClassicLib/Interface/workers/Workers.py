"""Worker classes for background operations in the CLASSIC interface.

This module contains QObject-based worker classes that run in separate threads
to perform long-running operations without blocking the GUI.
"""

import traceback

from PySide6.QtCore import QObject, Signal, Slot

from ClassicLib.core.logger import logger
from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.support.update import UpdateCheckError, is_latest_version


class CrashLogsScanWorker(QObject):
    """Handle crash log scanning tasks with asynchronous mechanisms and emits relevant signals
    for feedback.

    This class is responsible for executing crash log scans and handling errors.
    It utilizes PyQt's signal-slot system to communicate the success or failure
    of the scanning process and ensures signals are emitted appropriately for user or application
    response. The scanning is performed asynchronously to avoid blocking the main thread.

    Attributes:
        finished (Signal): Signal emitted when the scan process finishes, irrespective of its success
            or failure.
        error_occurred (Signal): Signal emitted when an error occurs in the scanning process. It
            includes title, message, and details as arguments.

    """

    finished: Signal = Signal()
    error_occurred: Signal = Signal(str, str, str)  # (title, message, details)

    # noinspection PyBroadException

    @Slot()
    def run(self) -> None:
        """Execute the main logic of the function, performing a scan for crash logs.

        In case of an error during the scan, the error is handled appropriately.
        Once the process is complete, emits a signal to indicate the operation is finished.

        Raises:
            Exception: Propagates any unexpected exception encountered during
            the execution of the function.

        """
        # noinspection PyShadowingNames
        try:
            self._perform_crash_logs_scan()
        except Exception as e:  # noqa: BLE001
            self._handle_scan_error(e)
        finally:
            self.finished.emit()  # type: ignore[union-attr]  # Qt signal emission

    @staticmethod
    def _perform_crash_logs_scan() -> None:
        """Perform a scan for crash logs using asyncio.run() for thread-safe async execution.

        This method runs in a QThread and uses asyncio.run() directly to:
        - Initialize scanner with Rust acceleration if available
        - Warm up resources asynchronously
        - Execute the scan with Rust acceleration
        - Provide detailed performance metrics

        Note: Do NOT use AsyncBridge here - it's a main-thread singleton and accessing
        it from this worker thread causes cross-thread QObject parenting errors.

        Raises:
            None

        """
        import asyncio
        import time
        from datetime import datetime

        # Dual timer verification (perf_counter vs wall clock)
        perf_start = time.perf_counter()
        wall_start = time.time()
        start_datetime = datetime.now()

        logger.debug(f"Starting crash logs scan at {start_datetime.strftime('%H:%M:%S.%f')[:-3]}")

        # Import here to avoid circular dependency
        from ClassicLib.integration.status import is_rust_accelerated
        from ClassicLib.scanning.logs import FCXModeHandler
        from ClassicLib.scanning.logs.executor import ScanLogsExecutor
        from ClassicLib.scanning.logs.utils import crashlogs_scan_async_pure

        init_start = time.perf_counter()
        # Initialize scanner with eager_load flag for proactive warm-up
        scanner = ScanLogsExecutor(eager_load=True)
        FCXModeHandler.reset_fcx_checks()

        # Log Rust acceleration status
        if is_rust_accelerated("parser"):
            logger.info("Crash log scanning using Rust acceleration (150x speedup)")
        else:
            logger.debug("Crash log scanning using Python implementation")

        logger.debug(f"Scanner initialization took {(time.perf_counter() - init_start) * 1000:.0f}ms")

        async def run_scan() -> None:
            """Execute a scan process asynchronously with resource warm-up and performance logging.

            This coroutine:
            1. Warms up scan resources (YAML data, databases, etc.)
            2. Executes the actual crash log scan with Rust acceleration
            3. Logs performance metrics for both phases

            Raises:
                Any exceptions raised during the warm-up or scanning process
                will propagate to the caller.

            """
            # Warm up resources first
            warmup_start = time.perf_counter()
            logger.debug("Warming up scan resources...")
            await scanner.warm_up()
            logger.debug(f"Resource warm-up complete - took {(time.perf_counter() - warmup_start) * 1000:.0f}ms")

            # Run the scan with Rust acceleration if available
            scan_start = time.perf_counter()
            await crashlogs_scan_async_pure(scanner)
            logger.debug(f"Actual scan took {time.perf_counter() - scan_start:.2f}s")

        # Use asyncio.run() directly since we're in a separate QThread.
        # Do NOT use AsyncBridge here - it's a main-thread singleton and accessing
        # it from this worker thread causes "Cannot set parent, new parent is in
        # a different thread" errors.
        asyncio.run(run_scan())

        # Calculate timings with both methods for verification
        perf_elapsed = time.perf_counter() - perf_start
        wall_elapsed = time.time() - wall_start
        end_datetime = datetime.now()
        datetime_elapsed = (end_datetime - start_datetime).total_seconds()

        logger.info(
            f"Scan completed - perf_counter: {perf_elapsed:.2f}s, wall_clock: {wall_elapsed:.2f}s, datetime: {datetime_elapsed:.2f}s"
        )

    def _handle_scan_error(self, error: Exception) -> None:
        """Handle errors that occur during the crash log scanning process.

        This includes logging the error, preparing detailed error information,
        and emitting signals for dialog display.

        Args:
            error (Exception): The exception instance that triggered the error
                during the scan. This will be used to log the error message and
                prepare dialog details.

        """
        logger.error(f"Crash logs scan failed: {error!s}")

        # Prepare error details for dialog
        title = "Crash Log Scan Failed"
        message = f"An error occurred during crash log scanning:\n\n{error!s}"
        details = traceback.format_exc()

        # Always emit error details for dialog display
        self.error_occurred.emit(title, message, details)  # type: ignore[union-attr]  # Qt signal emission


# noinspection PyBroadException
class GameFilesScanWorker(QObject):
    """Worker class responsible for scanning game files.

    This class handles the game files scanning process and error handling.
    Its primary purpose is to manage the workflow for scanning game files
    and emitting associated signals for user interfaces or other subscribers.

    Attributes:
        scan_finished (Signal): Signal emitted when the scanning process is
            completed, regardless of success or failure.
        error_occurred (Signal): Signal emitted when an error occurs, providing
            error details (title, message, and traceback details).

    """

    scan_finished: Signal = Signal()
    error_occurred: Signal = Signal(str, str, str)  # (title, message, details)

    @Slot()
    def run(self) -> None:
        """Execute the main process for running game file scanning.

        Handles any exceptions that occur during the execution, ensuring
        that errors are properly managed. Always emits a signal indicating the scan
        has finished, regardless of success or error.

        Raises:
            Exception: Propagates any unhandled exception that occurs during the
                processing of the game results.

        """
        try:
            self._process_game_results_scan()
        except Exception as e:  # noqa: BLE001
            self._handle_error(e)
        finally:
            self.scan_finished.emit()  # type: ignore[union-attr]  # Qt signal emission

    @staticmethod
    def _process_game_results_scan() -> None:
        """Process game results scan using asyncio.run() for thread-safe async execution.

        This method runs in a QThread and uses asyncio.run() directly to:
        - Generate game integrity reports asynchronously
        - Generate mod scan reports asynchronously
        - Combine and write results with Rust file I/O if available
        - Provide detailed performance metrics

        Note: Do NOT use AsyncBridge here - it's a main-thread singleton and accessing
        it from this worker thread causes cross-thread QObject parenting errors.
        This matches the pattern used by CrashLogsScanWorker for consistency.
        """
        import asyncio
        import time
        from datetime import datetime

        # Dual timer verification (perf_counter vs wall clock)
        perf_start = time.perf_counter()
        wall_start = time.time()
        start_datetime = datetime.now()

        logger.debug(f"Starting game files scan at {start_datetime.strftime('%H:%M:%S.%f')[:-3]}")

        # Import here to avoid circular dependency
        from ClassicLib.integration.status import is_rust_accelerated
        from ClassicLib.scanning.game import write_combined_results_async

        # Check for Rust acceleration (prepare for future classic_scangame module)
        if is_rust_accelerated("scangame"):
            logger.info("Game file scanning using Rust acceleration")
        else:
            logger.debug("Game file scanning using Python implementation")

        # Use asyncio.run() directly since we're in a separate QThread.
        # Do NOT use AsyncBridge here - it's a main-thread singleton and accessing
        # it from this worker thread causes "Cannot set parent, new parent is in
        # a different thread" errors. This matches CrashLogsScanWorker's pattern.
        asyncio.run(write_combined_results_async())

        # Calculate timings with both methods for verification
        perf_elapsed = time.perf_counter() - perf_start
        wall_elapsed = time.time() - wall_start
        end_datetime = datetime.now()
        datetime_elapsed = (end_datetime - start_datetime).total_seconds()

        logger.info(
            f"Game files scan completed - perf_counter: {perf_elapsed:.2f}s, "
            f"wall_clock: {wall_elapsed:.2f}s, "
            f"datetime: {datetime_elapsed:.2f}s"
        )

    def _handle_error(self, error: Exception) -> None:
        """Handle errors that occur during the game files scanning process.

        This method logs the error details, prepares them for display in a dialog,
        and emits the error information.

        Args:
            error (Exception): The exception that occurred during the game files
                scanning process.

        """
        logger.error(f"Game files scan failed: {error!s}")

        # Prepare error details for dialog
        title = "Game Files Scan Failed"
        message = f"An error occurred while processing game files:\n\n{error!s}"
        details = traceback.format_exc()

        # Always emit error details for dialog display
        self.error_occurred.emit(title, message, details)  # type: ignore[union-attr]  # Qt signal emission


class UpdateCheckWorker(QObject):
    """Worker class for checking software updates.

    This class enables background checking of software updates, utilizing
    asynchronous operations. It is specifically designed to work as a part
    of a threaded environment. Update statuses, errors, and completion
    states are communicated via PyQt signals, allowing seamless integration
    with UI components.

    Attributes:
        finished (Signal): Signal emitted when the worker thread concludes
            its execution.
        updateAvailable (Signal): Signal emitted indicating whether an
            update is available. Emits a boolean value where True indicates
            an update is available.
        error (Signal): Signal emitted when an error occurs during the
            update check. Emits a string containing the error message.

    """

    # Signals
    finished: Signal = Signal()
    updateAvailable: Signal = Signal(bool)  # True if update available
    error: Signal = Signal(str)

    def __init__(self, explicit: bool = False) -> None:
        """Initialize the object with the option to specify explicit behavior.

        Args:
            explicit (bool): Determines whether the behavior should be explicit. Defaults to False.

        """
        super().__init__()
        self.explicit = explicit

    @Slot()
    def run(self) -> None:
        """Execute the process of checking for software updates, handling various
        errors and states.

        This method checks whether the software update process should proceed
        based on the current stage of the application (e.g., pre-release).
        It uses asyncio.run() directly since this worker runs in its own QThread,
        avoiding cross-thread issues with the main thread's AsyncBridge singleton.

        Raises:
            UpdateCheckError: If a specific error occurs during the update check.
            RuntimeError: If a runtime-related error occurs.
            OSError: If an operating system-related error occurs.
            ValueError: If a value-related error occurs.

        """
        import asyncio

        try:
            # Check if pre-release
            if GlobalRegistry.get(GlobalRegistry.Keys.IS_PRERELEASE):
                if self.explicit:
                    self.error.emit("Software is in pre-release stage, update check skipped.")
                self.finished.emit()
                return

            # Use asyncio.run() directly since we're in a separate QThread.
            # Do NOT use AsyncBridge here - it's a main-thread singleton and accessing
            # it from this worker thread causes "Cannot set parent, new parent is in
            # a different thread" errors.
            result = asyncio.run(self._async_check())
            self.updateAvailable.emit(not result)

        except UpdateCheckError as e:
            self.error.emit(str(e))
        except (RuntimeError, OSError, ValueError) as e:
            self.error.emit(f"Unexpected error during update check: {e}")
        finally:
            self.finished.emit()

    async def _async_check(self) -> bool:
        """Check asynchronously whether the current version is the latest.

        This method uses an external utility to determine if the application is up-to-date.
        It runs the check in a quiet mode and can optionally consider GUI-specific requests.

        Returns:
            bool: A boolean indicating whether the current version is the latest.

        """
        return await is_latest_version(quiet=True, gui_request=self.explicit)
