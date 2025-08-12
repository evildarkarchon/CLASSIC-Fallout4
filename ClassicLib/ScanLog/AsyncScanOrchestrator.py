"""
DEPRECATED: Async scan orchestrator for crash log processing.

This module is deprecated as of the async-first refactoring.
All functionality has been moved to OrchestratorCore.py.
This module now provides compatibility aliases to maintain backwards compatibility.
"""

from typing import TYPE_CHECKING

from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore

# Import for backwards compatibility with tests and existing code

if TYPE_CHECKING:
    from collections import Counter
    from pathlib import Path

    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo, ThreadSafeLogCache


class AsyncScanOrchestrator(OrchestratorCore):
    """
    DEPRECATED: Use OrchestratorCore instead.

    This class is maintained for backwards compatibility only.
    It simply inherits from OrchestratorCore without modification.
    """

    def __init__(
        self,
        yamldata: "ClassicScanLogsInfo",
        crashlogs: "ThreadSafeLogCache",
        fcx_mode: bool | None,
        show_formid_values: bool | None,
        formid_db_exists: bool,
    ) -> None:
        """Initialize the async orchestrator (deprecated)."""
        super().__init__(yamldata, crashlogs, fcx_mode, show_formid_values, formid_db_exists)

        # These attributes were specific to the old AsyncScanOrchestrator
        # Keep them for backwards compatibility
        self.show_formid_values = show_formid_values
        self.formid_db_exists = formid_db_exists
        self._formid_analyzer = self.formid_analyzer  # Alias for compatibility

    # All async methods are inherited from OrchestratorCore
    # The following are aliases for backwards compatibility

    async def process_crash_log_async(self, crashlog_file: "Path") -> "tuple[Path, list[str], bool, Counter[str]]":
        """
        DEPRECATED: Use process_crash_log() instead.

        Maintained for backwards compatibility.
        """
        return await self.process_crash_log(crashlog_file)

    async def process_crash_logs_batch_async(self, crashlog_files: "list[Path]") -> "list[tuple[Path, list[str], bool, Counter[str]]]":
        """
        DEPRECATED: Use process_crash_logs_batch() instead.

        Maintained for backwards compatibility.
        """
        return await self.process_crash_logs_batch(crashlog_files)


# Module-level function for backwards compatibility
async def write_reports_batch_async(reports: "list[tuple[Path, list[str], bool]]") -> None:
    """
    DEPRECATED: Use OrchestratorCore.write_reports_batch() instead.

    Writes a batch of reports asynchronously.
    Maintained for backwards compatibility.
    """
    # Create a temporary core instance just for writing
    # This is not ideal but maintains backwards compatibility
    import asyncio

    from ClassicLib.ScanLog.AsyncUtil import write_file_async

    write_tasks = []

    for crashlog_file, autoscan_report, _trigger_scan_failed in reports:
        autoscan_path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
        autoscan_output = "".join(autoscan_report)

        # Create write task
        write_tasks.append(write_file_async(autoscan_path, autoscan_output))

    # Execute all writes concurrently
    await asyncio.gather(*write_tasks, return_exceptions=True)
