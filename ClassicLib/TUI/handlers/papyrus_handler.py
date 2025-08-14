"""Papyrus log monitoring handler for TUI."""

import asyncio
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ClassicLib.MessageHandler import init_message_handler
from ClassicLib.PapyrusLog import papyrus_logging

# Module-level cache for Unicode detection result
_UNICODE_SUPPORT_CACHE: bool | None = None


@dataclass(slots=True)  # Add slots for memory optimization
class PapyrusStats:
    """Statistics from Papyrus log analysis."""

    timestamp: datetime
    dumps: int
    stacks: int
    warnings: int
    errors: int
    ratio: float
    raw_output: str

    def get_status_symbol(self, use_unicode: bool = True) -> str:
        """Get status symbol based on stats.

        Args:
            use_unicode: Whether to use Unicode symbols

        Returns:
            Status symbol (Unicode or ASCII)
        """
        if self.errors > 10:
            return "❌" if use_unicode else "[X]"
        if self.warnings > 20:
            return "⚠️" if use_unicode else "[!]"
        if self.dumps > 0:
            return "✓" if use_unicode else "[v]"
        return "✅" if use_unicode else "[OK]"

    def get_status_color(self) -> str:
        """Get status color based on stats.

        Returns:
            Color name for Textual styling
        """
        if self.errors > 10:
            return "red"
        if self.warnings > 20:
            return "yellow"
        return "green"


class TuiPapyrusHandler:
    """Handles Papyrus log monitoring for TUI."""

    def __init__(
        self,
        stats_callback: Callable[[PapyrusStats], None] | None = None,
        error_callback: Callable[[str], None] | None = None,
        use_unicode: bool = True,
    ):
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


def _detect_unicode_support_impl() -> bool:
    """Detect if terminal supports Unicode (implementation).

    Returns:
        True if Unicode is likely supported, False for ASCII fallback
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
        if any(t in term for t in ["xterm", "vt100", "linux", "screen", "tmux"]):
            # Most modern versions support Unicode
            return True

        # Windows Console Host (older Windows terminals)
        if sys.platform == "win32":
            try:
                # Try to get console output code page
                import ctypes

                kernel32 = ctypes.windll.kernel32
                cp = kernel32.GetConsoleOutputCP()
                # UTF-8 code page
                return cp == 65001
            except:
                # Default to ASCII on Windows if we can't detect
                return False

        # Default to True if we got this far without errors
        return True

    except (UnicodeEncodeError, AttributeError):
        # If we can't encode Unicode, fall back to ASCII
        return False


def _get_unicode_support_cached() -> bool:
    """Get cached Unicode support detection result.

    Returns:
        Cached result of Unicode support detection
    """
    global _UNICODE_SUPPORT_CACHE
    if _UNICODE_SUPPORT_CACHE is None:
        _UNICODE_SUPPORT_CACHE = _detect_unicode_support_impl()
    return _UNICODE_SUPPORT_CACHE


class TuiPapyrusHandler:
    """Handles Papyrus log monitoring for TUI."""

    def __init__(
        self,
        stats_callback: Callable[[PapyrusStats], None] | None = None,
        error_callback: Callable[[str], None] | None = None,
        use_unicode: bool = True,
    ):
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
        """Set the stats callback function."""
        self.stats_callback = callback

    def set_error_callback(self, callback: Callable[[str], None]) -> None:
        """Set the error callback function."""
        self.error_callback = callback

    def _parse_papyrus_output(self, output: str, dumps_count: int) -> PapyrusStats:
        """Parse papyrus_logging output into stats.

        Args:
            output: Raw output from papyrus_logging
            dumps_count: Number of dumps from papyrus_logging

        Returns:
            Parsed PapyrusStats object
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
                try:
                    stats.stacks = int(line.split(":")[1].strip())
                except (IndexError, ValueError):
                    pass
            elif "DUMPS/STACKS RATIO" in line:
                try:
                    stats.ratio = float(line.split(":")[1].strip())
                except (IndexError, ValueError):
                    pass
            elif "NUMBER OF WARNINGS" in line:
                try:
                    stats.warnings = int(line.split(":")[1].strip())
                except (IndexError, ValueError):
                    pass
            elif "NUMBER OF ERRORS" in line:
                try:
                    stats.errors = int(line.split(":")[1].strip())
                except (IndexError, ValueError):
                    pass

        return stats

    async def _monitor_loop(self) -> None:
        """Main monitoring loop that polls papyrus_logging."""
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

                except Exception as e:
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
        """Start Papyrus log monitoring.

        Returns:
            True if monitoring started successfully, False otherwise
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

                return True

            except Exception as e:
                self.is_monitoring = False
                if self.error_callback:
                    self.error_callback(f"Failed to start monitoring: {e!s}")
                return False

    async def stop_monitoring(self) -> None:
        """Stop Papyrus log monitoring."""
        async with self._monitor_lock:
            if not self.is_monitoring:
                return

            if self.monitor_task and not self.monitor_task.done():
                self._stop_event.set()
                self.monitor_task.cancel()
                try:
                    # Wait for the task to complete cancellation with timeout
                    await asyncio.wait_for(self.monitor_task, timeout=5.0)
                except (TimeoutError, asyncio.CancelledError):
                    # Expected when task is cancelled or takes too long
                    pass
                finally:
                    self.monitor_task = None
            self.is_monitoring = False

    def is_monitoring_active(self) -> bool:
        """Check if monitoring is currently active."""
        return self.is_monitoring

    def get_last_stats(self) -> PapyrusStats | None:
        """Get the last recorded stats."""
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
