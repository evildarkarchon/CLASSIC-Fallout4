"""Scan Service for CLASSIC TUI.

Orchestrates crash log and game file scanning via existing backend.
"""

from ClassicLib.core.logger import logger
from ClassicLib.scanning.logs import ScanResult
from ClassicLib.scanning.logs.executor import ScanLogsExecutor
from ClassicLib.scanning.logs.utils import crashlogs_scan_async_pure


class ScanService:
    """Service for managing scan operations.

    This service wraps the existing scan functions from ClassicLib.scanning
    for use with Textual's Worker API. Provides async methods for both
    crash log and game file scanning.
    """

    def __init__(self) -> None:
        """Initialize the ScanService."""
        self._cancel_requested = False

    def request_cancel(self) -> None:
        """Request cancellation of current scan."""
        self._cancel_requested = True

    def reset(self) -> None:
        """Reset cancellation state for a new scan."""
        self._cancel_requested = False

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self._cancel_requested

    async def scan_crash_logs(self) -> ScanResult:
        """Execute a crash logs scan asynchronously.

        Scans crash logs in configured directories and generates
        AUTOSCAN.md reports for each log file found.

        Returns:
            ScanResult containing scan outcomes and statistics.

        """
        self.reset()
        executor = ScanLogsExecutor()
        return await crashlogs_scan_async_pure(executor)

    async def scan_game_files(self) -> bool:
        """Execute a game files scan asynchronously.

        Scans game installation for integrity issues and generates
        a combined results report.

        Returns:
            True if scan completed successfully, False otherwise.

        """
        from ClassicLib.scanning.game import write_combined_results_async

        self.reset()

        try:
            # Generate and write combined results to file
            await write_combined_results_async()
        except (OSError, PermissionError, FileNotFoundError) as e:
            logger.error(f"Game files scan failed: {e}")
            return False
        else:
            return True
