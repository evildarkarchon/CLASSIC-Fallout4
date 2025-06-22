"""
Async scan orchestrator for crash log processing.

This module provides an async version of the scan orchestrator that uses
asyncio for concurrent I/O operations and batch processing.
"""

import asyncio
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ClassicLib.ScanLog.AsyncFormIDAnalyzer import AsyncFormIDAnalyzer
from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool, write_file_async
from ClassicLib.ScanLog.ScanOrchestrator import ScanOrchestrator

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo, ThreadSafeLogCache


class AsyncScanOrchestrator(ScanOrchestrator):
    """Async version of scan orchestrator with concurrent I/O operations."""

    def __init__(
        self,
        yamldata: "ClassicScanLogsInfo",
        crashlogs: "ThreadSafeLogCache",
        fcx_mode: bool | None,
        show_formid_values: bool | None,
        formid_db_exists: bool,
    ) -> None:
        """Initialize the async orchestrator."""
        super().__init__(yamldata, crashlogs, fcx_mode, show_formid_values, formid_db_exists)

        # Store attributes for async operations
        self.show_formid_values = show_formid_values
        self.formid_db_exists = formid_db_exists

        # Replace FormID analyzer with async version when we have a db pool
        self._db_pool: AsyncDatabasePool | None = None
        self._async_formid_analyzer: AsyncFormIDAnalyzer | None = None

    async def __aenter__(self) -> "AsyncScanOrchestrator":
        """Async context manager entry."""
        # Initialize database pool
        self._db_pool = AsyncDatabasePool()
        await self._db_pool.initialize()

        # Create async FormID analyzer
        self._async_formid_analyzer = AsyncFormIDAnalyzer(
            self.yamldata, self.show_formid_values or False, self.formid_db_exists, self._db_pool
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._db_pool:
            await self._db_pool.close()

    async def process_crash_logs_batch_async(self, crashlog_files: list[Path]) -> list[tuple[Path, list[str], bool, Counter[str]]]:
        """
        Processes a batch of crash log files asynchronously in manageable groups to prevent system
        overload. This method divides the provided files into smaller batches, processes them
        concurrently, and handles potential exceptions during processing.

        Args:
            crashlog_files (list[Path]): A list of paths representing the crash log files to be processed.

        Returns:
            list[tuple[Path, list[str], bool, Counter[str]]]: A list of tuples containing information
            about each processed crash log file. Each tuple includes:
            - Path: The path of the log file or an error log identifier.
            - list[str]: A list of processed log content or error messages.
            - bool: A flag indicating if the processing encountered issues.
            - Counter[str]: A counter with keys 'scanned', 'incomplete', and 'failed' representing
              the status of the processing operation.
        """
        # Process logs in batches to avoid overwhelming the system
        batch_size = 10
        results = []

        for i in range(0, len(crashlog_files), batch_size):
            batch = crashlog_files[i : i + batch_size]

            # Process batch concurrently
            batch_tasks = [self.process_crash_log_async(log_file) for log_file in batch]

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Handle results
            for result in batch_results:
                if isinstance(result, Exception):
                    # Create error result
                    results.append((Path("error.log"), [f"Error: {result}"], True, Counter(scanned=0, incomplete=0, failed=1)))
                elif isinstance(result, tuple):
                    results.append(result)

        return results

    async def process_crash_log_async(self, crashlog_file: Path) -> tuple[Path, list[str], bool, Counter[str]]:
        """
        Processes a crash log asynchronously, including FormID analysis if an asynchronous
        FormID analyzer is available. The method first utilizes synchronous processing to handle
        parsing, plugin processing, and other steps. If FormIDs are identified for further
        analysis and the asynchronous FormID analyzer is enabled, the FormID section in the
        crash report is reprocessed asynchronously.

        Args:
            crashlog_file (Path): The path to the crash log file that needs processing.

        Returns:
            tuple[Path, list[str], bool, Counter[str]]: A tuple containing the crash log file path,
            the processed crash report as a list of strings, a boolean indicating the processing fail
            status, and a Counter object with statistics derived during the processing.

        Raises:
            Does not explicitly describe raised errors.
        """
        # Use the existing synchronous processing

        # Process the log synchronously up to FormID analysis
        # (This includes parsing, plugin processing, etc.)
        result = super().process_crash_log(crashlog_file)

        # If we have FormIDs to look up, use async version
        if self._async_formid_analyzer and hasattr(self, "_last_formids"):
            # Extract the report that was generated
            _, original_report, fail_status, stats = result

            # Re-process with async FormID lookups
            formids_matches = getattr(self, "_last_formids", [])
            crashlog_plugins = getattr(self, "_last_plugins", {})

            if formids_matches and crashlog_plugins:
                # Clear the FormID section from report and regenerate it async
                new_report = []
                in_formid_section = False

                for line in original_report:
                    if "FORM IDs" in line:
                        in_formid_section = True
                        new_report.append(line)
                        # Run async FormID analysis
                        await self._async_formid_analyzer.formid_match_async(formids_matches, crashlog_plugins, new_report)
                    elif in_formid_section and line.startswith("- Form ID:"):
                        # Skip original FormID lines
                        continue
                    else:
                        if in_formid_section and not line.startswith("-"):
                            in_formid_section = False
                        new_report.append(line)

                return crashlog_file, new_report, fail_status, stats

        return result


async def write_reports_batch_async(reports: list[tuple[Path, list[str], bool]]) -> None:
    """
    Writes a batch of reports asynchronously. This function processes a batch of
    reporting tasks where each task comprises a file path, content to be written,
    and a boolean trigger. The reports are written asynchronously to improve
    performance when handling multiple write operations.

    Arguments:
        reports (list[tuple[Path, list[str], bool]]): A list of tuples where each
            tuple contains:
            - Path object pointing to the destination file.
            - List of strings constituting the report content to be written.
            - Boolean flag potentially used to signify a specific condition or
              trigger (not utilized within this implementation).

    Raises:
        The function does not propagate exceptions from individual write tasks,
        as it uses `asyncio.gather` with `return_exceptions=True`. Any exceptions
        occurring during the write process are captured silently.

    Returns:
        None
    """
    write_tasks = []

    for crashlog_file, autoscan_report, _trigger_scan_failed in reports:
        autoscan_path: Path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
        autoscan_output: str = "".join(autoscan_report)

        # Create write task
        write_tasks.append(write_file_async(autoscan_path, autoscan_output))

    # Execute all writes concurrently
    await asyncio.gather(*write_tasks, return_exceptions=True)
