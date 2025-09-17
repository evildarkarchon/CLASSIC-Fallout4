"""
Provides functionality to detect Unicode support, handle Papyrus statistics, and manage
asynchronous monitoring tasks.

This module includes methods for determining Unicode support in the current environment,
parsing Papyrus tool output into structured statistics, and supporting callbacks for
statistics and error data. Additionally, it provides a monitoring loop for tracking
statistics updates asynchronously.
"""

import asyncio
import contextlib
import os
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from ClassicLib.MessageHandler import init_message_handler
from ClassicLib.PapyrusLog import papyrus_logging
from ClassicLib.TUI.handlers.papyrus.papyrus_stats import PapyrusStats

# Module-level cache for Unicode detection result
_UNICODE_SUPPORT_CACHE: bool | None = None


# noinspection PyUnresolvedReferences
def _detect_unicode_support_impl() -> bool:
    """
    Detects Unicode support in the current environment.

    This function checks whether the current terminal or console environment
    supports Unicode output. It tries to output a Unicode character, checks
    environment variables such as `TERM` and `LANG` to determine terminal
    capabilities, and handles platform-specific cases like Windows console hosts.
    The function defaults to assuming the presence or absence of Unicode support
    based on the best available heuristics.

    Returns:
        bool: True if Unicode support is detected, False otherwise.

    Raises:
        UnicodeEncodeError: Raised if Unicode output cannot be encoded in the current
            environment encoding.
        AttributeError: Raised if required attributes are missing during encoding or
            environment detection.
        ImportError: Raised if platform-specific modules such as `ctypes` are
            unavailable.
        ValueError: Raised if invalid values are encountered during code page detection.
    """
    # Try to actually output a Unicode character to test support
    try:
        test_char = "✓"
        # Try to encode the test character
        test_char.encode(sys.stdout.encoding if hasattr(sys.stdout, "encoding") else "utf-8")

        # Check environment variables for terminal type
        term = os.environ.get("TERM", "").lower()
        lang = os.environ.get("LANG", "").lower()

        # Windows Terminal and modern terminals support Unicode
        if os.environ.get("WT_SESSION"):  # Windows Terminal
            return True

        # Check for UTF-8 locale
        if "utf-8" in lang or "utf8" in lang:
            return True

        # Check if running in common modern terminals
        from ClassicLib.TUI.constants import UNICODE_TERMINAL_TYPES

        if any(t in term for t in UNICODE_TERMINAL_TYPES):
            # Most modern versions support Unicode
            return True

        # Windows Console Host (older Windows terminals)
        if sys.platform == "win32":
            try:
                # Try to get console output code page
                import ctypes

                # Safely access Windows API
                if not hasattr(ctypes, "windll"):
                    return False

                kernel32 = ctypes.windll.kernel32
                if not hasattr(kernel32, "GetConsoleOutputCP"):
                    return False

                # Get console code page with error handling
                cp = kernel32.GetConsoleOutputCP()
                # UTF-8 code page
                return cp == 65001  # noqa: TRY300
            except (ImportError, AttributeError, OSError, ValueError):
                # ctypes not available, attribute error, OS error, or invalid value
                # Default to ASCII on Windows if we can't detect
                return False

    except (UnicodeEncodeError, AttributeError):
        # If we can't encode Unicode, fall back to ASCII
        return False
    else:
        # Default to True if we got this far without errors
        return True


def _get_unicode_support_cached() -> bool:
    """
    Determines if Unicode support is available, using a cached value for efficiency.

    This function checks for Unicode support and caches the result globally to avoid
    repeated checks. If the cached value is not yet initialized, it performs the
    detection operation and stores the result.

    Returns:
        bool: True if Unicode support is available, False otherwise.
    """
    global _UNICODE_SUPPORT_CACHE  # noqa: PLW0603
    if _UNICODE_SUPPORT_CACHE is None:
        _UNICODE_SUPPORT_CACHE = _detect_unicode_support_impl()
    return _UNICODE_SUPPORT_CACHE


class TuiPapyrusHandler:
    """
    Formats the provided PapyrusStats object into a human-readable string.

    Converts the given statistics data into a structured string suitable for
    display or logging purposes. The output includes information such as the
    timestamp, number of dumps, stacks, warnings, errors, and the dumps/stacks
    ratio.

    Returns:
        str: A formatted string representation of the provided statistics.
    """

    def __init__(
        self,
        stats_callback: Callable[[PapyrusStats], None] | None = None,
        error_callback: Callable[[str], None] | None = None,
        use_unicode: bool = True,
    ) -> None:
        """Initialize the Papyrus handler.

        Args:
            stats_callback: Function to call with updated stats
            error_callback: Function to call with error messages
            use_unicode: Whether to use Unicode symbols (auto-detected if not specified)
        """
        self.stats_callback = stats_callback
        self.error_callback = error_callback
        self.use_unicode = _get_unicode_support_cached() if use_unicode else False
        self.is_monitoring = False
        self.monitor_task: asyncio.Task | None = None
        self.last_stats: PapyrusStats | None = None
        self._stop_event = asyncio.Event()
        self._monitor_lock = asyncio.Lock()

    def set_unicode_mode(self, use_unicode: bool) -> None:
        """Manually set Unicode mode.

        Args:
            use_unicode: Whether to use Unicode symbols
        """
        self.use_unicode = use_unicode

    def set_stats_callback(self, callback: Callable[[PapyrusStats], None]) -> None:
        """
        Sets the statistic callback function to be invoked with updated statistics.

        Args:
            callback (Callable[[PapyrusStats], None]): A callback function that accepts
                a PapyrusStats instance as its argument and performs desired actions
                on the statistics data.
        """
        self.stats_callback = callback

    def set_error_callback(self, callback: Callable[[str], None]) -> None:
        """
        Sets a callback function to handle error messages.

        The provided callback function will be invoked when an error occurs. It must
        accept a single string parameter representing the error message and return no
        value.

        Args:
            callback (Callable[[str], None]): A function that handles error messages.
                The function should take a string as input and return nothing.
        """
        self.error_callback = callback

    @staticmethod
    def _parse_papyrus_output(output: str, dumps_count: int) -> PapyrusStats:
        """
        Parses the output of Papyrus and extracts statistical data such as the number of
        dumps, stacks, warnings, errors, and ratio. If parsing fails for certain metrics,
        default values are used or fallback values are applied.

        Args:
            output (str): The raw output string from the Papyrus tool.
            dumps_count (int): The default number of dumps to use if parsing the output
                fails.

        Returns:
            PapyrusStats: An instance of PapyrusStats containing the parsed statistics,
            including timestamp, dumps, stacks, warnings, errors, ratio, and the raw
            output.
        """
        stats = PapyrusStats(timestamp=datetime.now(), dumps=0, stacks=0, warnings=0, errors=0, ratio=0.0, raw_output=output)

        # Parse the output string
        lines = output.split("\n")
        for line in lines:
            if "NUMBER OF DUMPS" in line:
                try:
                    stats.dumps = int(line.split(":")[1].strip())
                except (IndexError, ValueError):
                    stats.dumps = dumps_count
            elif "NUMBER OF STACKS" in line:
                with contextlib.suppress(IndexError, ValueError):
                    stats.stacks = int(line.split(":")[1].strip())
            elif "DUMPS/STACKS RATIO" in line:
                with contextlib.suppress(IndexError, ValueError):
                    stats.ratio = float(line.split(":")[1].strip())
            elif "NUMBER OF WARNINGS" in line:
                with contextlib.suppress(IndexError, ValueError):
                    stats.warnings = int(line.split(":")[1].strip())
            elif "NUMBER OF ERRORS" in line:
                with contextlib.suppress(IndexError, ValueError):
                    stats.errors = int(line.split(":")[1].strip())

        return stats

    async def _monitor_loop(self) -> None:
        """
        Performs asynchronous monitoring operations and maintains statistics updates based on
        the output of the `papyrus_logging` function. The monitoring loop continues until the
        stop event is triggered or cancellation is requested.

        Args:
            self: Instance of the class containing the monitoring logic.

        Raises:
            asyncio.CancelledError: Indicates that the monitoring loop was cancelled.
        """
        try:
            # Initialize message handler for monitoring
            init_message_handler(parent=None, is_gui_mode=False)

            while self.is_monitoring:
                try:
                    # Check if we should stop
                    if self._stop_event.is_set():
                        break

                    # Run papyrus_logging in a thread to avoid blocking
                    output, dumps = await asyncio.to_thread(papyrus_logging)

                    # Parse the output
                    stats = self._parse_papyrus_output(output, dumps)

                    # Only update if stats changed
                    if self.last_stats is None or stats != self.last_stats:
                        self.last_stats = stats
                        if self.stats_callback:
                            self.stats_callback(stats)

                    # Wait before next poll (1 second)
                    await asyncio.sleep(1.0)

                except (OSError, ValueError, AttributeError, RuntimeError) as e:
                    if self.error_callback:
                        self.error_callback(f"Monitor error: {e!s}")
                    # Continue monitoring despite errors
                    await asyncio.sleep(1.0)

        except asyncio.CancelledError:
            # Monitoring was cancelled
            pass
        finally:
            self.is_monitoring = False

    async def start_monitoring(self) -> bool:
        """
        Starts the monitoring process asynchronously, ensuring only one monitoring instance runs at a
        time. If monitoring is already active, it will notify via the error callback. On success, it
        sets up the monitoring task and performs an initial check for stats retrieval. Handles various
        exceptions that might occur during setup and appropriately notifies via the error callback.

        Returns:
            bool: True if monitoring starts successfully, False otherwise.

        Raises:
            OSError: If there is an operating system-related error.
            ValueError: If an invalid value is encountered.
            AttributeError: If accessing an undefined attribute.
            RuntimeError: If a runtime error occurs.
            asyncio.CancelledError: If the asyncio task is cancelled.
        """
        async with self._monitor_lock:
            if self.is_monitoring:
                if self.error_callback:
                    self.error_callback("Monitoring already active")
                return False

            try:
                self.is_monitoring = True
                self._stop_event.clear()

                # Create and start the monitoring task
                self.monitor_task = asyncio.create_task(self._monitor_loop())

                # Do an initial check
                output, dumps = await asyncio.to_thread(papyrus_logging)
                stats = self._parse_papyrus_output(output, dumps)
                self.last_stats = stats

                if self.stats_callback:
                    self.stats_callback(stats)

            except (OSError, ValueError, AttributeError, RuntimeError, asyncio.CancelledError) as e:
                self.is_monitoring = False
                if self.error_callback:
                    self.error_callback(f"Failed to start monitoring: {e!s}")
                return False
            else:
                return True

    async def stop_monitoring(self) -> None:
        """
        Stops the ongoing monitoring process and cleans up associated resources.

        This method ensures that the monitoring process is stopped gracefully. It signals the
        monitoring loop to stop, clears the internal state related to monitoring, and handles
        cancellation of the associated task. It provides timeout protection when waiting for
        task cancellation to complete and ensures no exceptions from the cancelled task propagate.

        Raises:
            asyncio.TimeoutError: If the cancellation of the monitoring task exceeds the specified
                timeout.
            asyncio.CancelledError: If the task is cancelled during execution.
        """
        async with self._monitor_lock:
            if not self.is_monitoring:
                return

            # Set stop event first to signal the loop
            self._stop_event.set()

            # Store reference to task before clearing
            task_to_cancel = self.monitor_task

            # Clear state first
            self.is_monitoring = False
            self.monitor_task = None

            # Now handle task cancellation outside of state management
            if task_to_cancel and not task_to_cancel.done():
                task_to_cancel.cancel()
                try:
                    # Wait for the task to complete cancellation with timeout
                    await asyncio.wait_for(asyncio.shield(task_to_cancel), timeout=5.0)
                except (TimeoutError, asyncio.CancelledError):
                    # Expected when task is cancelled or takes too long
                    # Force collection of the task
                    try:  # noqa: SIM105
                        await task_to_cancel
                    except (asyncio.CancelledError, Exception):  # noqa: BLE001
                        # Ignore any exceptions from the cancelled task
                        pass

    def is_monitoring_active(self) -> bool:
        """
        Determines whether monitoring is currently active.

        This method checks the status of monitoring by evaluating the
        property `is_monitoring`.

        Returns:
            bool: True if monitoring is active, False otherwise.
        """
        return self.is_monitoring

    def get_last_stats(self) -> PapyrusStats | None:
        """
        Returns the last recorded statistics.

        This method retrieves the last available instance of statistics if it exists.
        If no statistics have been recorded, it returns None. Used to access the most
        recent PapyrusStats object.

        Returns:
            PapyrusStats | None: The last recorded statistics if available, otherwise
            None.
        """
        return self.last_stats

    def format_stats(self, stats: PapyrusStats) -> str:
        """Format stats for display.

        Args:
            stats: The stats to format

        Returns:
            Formatted string for display
        """
        symbol = stats.get_status_symbol(self.use_unicode)

        if self.use_unicode:
            return (
                f"{symbol} Papyrus Monitor\n"
                f"├─ Dumps: {stats.dumps}\n"
                f"├─ Stacks: {stats.stacks}\n"
                f"├─ Ratio: {stats.ratio:.3f}\n"
                f"├─ Warnings: {stats.warnings}\n"
                f"└─ Errors: {stats.errors}"
            )
        return (
            f"{symbol} Papyrus Monitor\n"
            f"+- Dumps: {stats.dumps}\n"
            f"+- Stacks: {stats.stacks}\n"
            f"+- Ratio: {stats.ratio:.3f}\n"
            f"+- Warnings: {stats.warnings}\n"
            f"+- Errors: {stats.errors}"
        )
