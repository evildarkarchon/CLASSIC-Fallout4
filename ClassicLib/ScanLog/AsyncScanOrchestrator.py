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
            self.yamldata,
            self.show_formid_values or False,
            self.formid_db_exists,
            self._db_pool
        )
        return self
        
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._db_pool:
            await self._db_pool.close()
            
    async def process_crash_logs_batch_async(
        self, crashlog_files: list[Path]
    ) -> list[tuple[Path, list[str], bool, Counter[str]]]:
        """
        Process multiple crash logs concurrently in batches.
        
        Args:
            crashlog_files: List of crash log file paths
            
        Returns:
            List of results for each crash log
        """
        # Process logs in batches to avoid overwhelming the system
        batch_size = 10
        results = []
        
        for i in range(0, len(crashlog_files), batch_size):
            batch = crashlog_files[i:i + batch_size]
            
            # Process batch concurrently
            batch_tasks = [
                self.process_crash_log_async(log_file) 
                for log_file in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Handle results
            for result in batch_results:
                if isinstance(result, Exception):
                    # Create error result
                    results.append((
                        Path("error.log"),
                        [f"Error: {result}"],
                        True,
                        Counter(scanned=0, incomplete=0, failed=1)
                    ))
                else:
                    results.append(result)
                    
        return results
        
    async def process_crash_log_async(
        self, crashlog_file: Path
    ) -> tuple[Path, list[str], bool, Counter[str]]:
        """
        Async version of crash log processing.
        
        This method processes most of the log synchronously but uses async
        for I/O-bound operations like database lookups.
        
        Args:
            crashlog_file: Path to the crash log file
            
        Returns:
            Tuple containing file path, report, failure status, and statistics
        """
        # Use the existing synchronous processing
        
        # Process the log synchronously up to FormID analysis
        # (This includes parsing, plugin processing, etc.)
        result = super().process_crash_log(crashlog_file)
        
        # If we have FormIDs to look up, use async version
        if self._async_formid_analyzer and hasattr(self, '_last_formids'):
            # Extract the report that was generated
            _, original_report, fail_status, stats = result
            
            # Re-process with async FormID lookups
            formids_matches = getattr(self, '_last_formids', [])
            crashlog_plugins = getattr(self, '_last_plugins', {})
            
            if formids_matches and crashlog_plugins:
                # Clear the FormID section from report and regenerate it async
                new_report = []
                in_formid_section = False
                
                for line in original_report:
                    if "FORM IDs" in line:
                        in_formid_section = True
                        new_report.append(line)
                        # Run async FormID analysis
                        await self._async_formid_analyzer.formid_match_async(
                            formids_matches, crashlog_plugins, new_report
                        )
                    elif in_formid_section and line.startswith("- Form ID:"):
                        # Skip original FormID lines
                        continue
                    else:
                        if in_formid_section and not line.startswith("-"):
                            in_formid_section = False
                        new_report.append(line)
                        
                return crashlog_file, new_report, fail_status, stats
                
        return result


async def write_reports_batch_async(
    reports: list[tuple[Path, list[str], bool]]
) -> None:
    """
    Write multiple crash log reports concurrently.
    
    Args:
        reports: List of (crashlog_file, report_lines, scan_failed) tuples
    """
    write_tasks = []
    
    for crashlog_file, autoscan_report, _trigger_scan_failed in reports:
        autoscan_path: Path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
        autoscan_output: str = "".join(autoscan_report)
        
        # Create write task
        write_tasks.append(write_file_async(autoscan_path, autoscan_output))
        
    # Execute all writes concurrently
    await asyncio.gather(*write_tasks, return_exceptions=True)