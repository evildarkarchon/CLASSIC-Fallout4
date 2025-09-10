"""
Async crash log processing pipeline.

This module provides the main AsyncCrashLogPipeline class that integrates
all async components for maximum performance improvement.
"""

import asyncio
import os
import time
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from ClassicLib.Logger import logger
from ClassicLib.MessageHandler import msg_progress_context
from ClassicLib.ScanLog.AsyncFileIO import write_reports_batch
from ClassicLib.ScanLog.AsyncReformat import crashlogs_reformat_async
from ClassicLib.ScanLog.AsyncUtil import load_crash_logs_async
from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
from ClassicLib.ScanLog.ScanLogInfo import ThreadSafeLogCache

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo


class AsyncCrashLogPipeline:
    """Complete async pipeline for crash log processing."""

    def __init__(
        self,
        yamldata: "ClassicScanLogsInfo",
        fcx_mode: bool | None,
        show_formid_values: bool | None,
        formid_db_exists: bool,
    ) -> None:
        """
        Initialize the async pipeline.

        Args:
            yamldata: Configuration data
            fcx_mode: Whether FCX mode is enabled
            show_formid_values: Whether to show FormID values
            formid_db_exists: Whether FormID database exists
        """
        self.yamldata = yamldata
        self.fcx_mode = fcx_mode
        self.show_formid_values = show_formid_values
        self.formid_db_exists = formid_db_exists

        # Performance tracking
        self.performance_stats: dict[str, float] = {}

    async def process_crash_logs_async(
        self, crashlog_list: list[Path], remove_list: tuple[str]
    ) -> tuple[list[tuple[Path, list[str], bool, Counter[str]]], dict[str, float]]:
        """
        Process crash logs using fully async pipeline.

        Args:
            crashlog_list: List of crash log file paths
            remove_list: Tuple of strings to remove during reformatting

        Returns:
            Tuple containing:
            - List of processing results
            - Performance statistics dictionary
        """
        logger.info("Starting async crash log processing pipeline")
        total_start = time.perf_counter()

        # Step 1: Async file reformatting
        reformat_start = time.perf_counter()
        await crashlogs_reformat_async(crashlog_list, remove_list)
        self.performance_stats["reformat_time"] = time.perf_counter() - reformat_start
        logger.debug(f"Async reformatting completed in {self.performance_stats['reformat_time']:.3f}s")

        # Step 2: Async log loading
        load_start = time.perf_counter()
        log_cache_data = await load_crash_logs_async(crashlog_list)

        # Convert to ThreadSafeLogCache format
        cache_dict = {name: "\n".join(lines).encode("utf-8") for name, lines in log_cache_data.items()}
        crashlogs = ThreadSafeLogCache.from_cache(cache_dict)

        self.performance_stats["load_time"] = time.perf_counter() - load_start
        logger.debug(f"Async log loading completed in {self.performance_stats['load_time']:.3f}s")

        # Step 3: Async database processing with orchestrator
        process_start = time.perf_counter()

        # Process logs with progress tracking
        total_logs = len(crashlog_list)
        with msg_progress_context("Processing Crash Logs", total_logs) as progress:
            async with OrchestratorCore(
                self.yamldata,
                crashlogs,
                self.fcx_mode,
                self.show_formid_values,
                self.formid_db_exists,
            ) as orchestrator:
                # Dynamic batch sizing based on CPU count and log count
                cpu_count = os.cpu_count() or 4
                log_count = len(crashlog_list)

                # Calculate optimal batch size
                # - Use more parallelism on systems with more CPUs
                # - Adjust for log count to avoid too many small batches
                if log_count <= 10:
                    batch_size = max(2, log_count)  # Small number of logs
                elif log_count <= 50:
                    batch_size = min(cpu_count * 2, 10)  # Medium number
                else:
                    batch_size = min(cpu_count * 3, 20)  # Large number

                logger.debug(f"Using dynamic batch size: {batch_size} (CPU cores: {cpu_count}, logs: {log_count})")
                all_results = []

                for i in range(0, len(crashlog_list), batch_size):
                    batch = crashlog_list[i : i + batch_size]
                    batch_results = await orchestrator.process_crash_logs_batch(batch)
                    all_results.extend(batch_results)

                    # Update progress with batch results
                    for crashlog_file, _, _, _ in batch_results:
                        progress.update(1, f"Processed {crashlog_file.name}")

                    # Small delay between batches to prevent system overload
                    if i + batch_size < len(crashlog_list):
                        await asyncio.sleep(0.01)

        self.performance_stats["process_time"] = time.perf_counter() - process_start
        logger.debug(f"Async processing completed in {self.performance_stats['process_time']:.3f}s")

        # Step 4: Async report writing
        write_start = time.perf_counter()

        # Prepare reports for batch writing
        reports_to_write = [
            (crashlog_file, autoscan_report, trigger_scan_failed) for crashlog_file, autoscan_report, trigger_scan_failed, _ in all_results
        ]

        await write_reports_batch(reports_to_write)

        self.performance_stats["write_time"] = time.perf_counter() - write_start
        logger.debug(f"Async report writing completed in {self.performance_stats['write_time']:.3f}s")

        # Calculate total time and efficiency metrics
        self.performance_stats["total_time"] = time.perf_counter() - total_start
        self.performance_stats["logs_per_second"] = len(crashlog_list) / self.performance_stats["total_time"]

        logger.info(
            f"Async pipeline completed: {len(crashlog_list)} logs in {self.performance_stats['total_time']:.3f}s "
            f"({self.performance_stats['logs_per_second']:.1f} logs/sec)"
        )

        return all_results, self.performance_stats


async def run_async_crash_log_scan(  # noqa: PLR0913
    crashlog_list: list[Path],
    remove_list: tuple[str],
    yamldata: "ClassicScanLogsInfo",
    fcx_mode: bool | None,
    show_formid_values: bool | None,
    formid_db_exists: bool,
) -> tuple[list[tuple[Path, list[str], bool, Counter[str]]], dict[str, float]]:
    """
    Convenience function to run the full async crash log scanning pipeline.

    Args:
        crashlog_list: List of crash log file paths
        remove_list: Tuple of strings to remove during reformatting
        yamldata: Configuration data
        fcx_mode: Whether FCX mode is enabled
        show_formid_values: Whether to show FormID values
        formid_db_exists: Whether FormID database exists

    Returns:
        Tuple containing processing results and performance statistics
    """
    pipeline = AsyncCrashLogPipeline(yamldata, fcx_mode, show_formid_values, formid_db_exists)

    return await pipeline.process_crash_logs_async(crashlog_list, remove_list)
