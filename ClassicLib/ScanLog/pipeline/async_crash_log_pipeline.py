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
from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
# ThreadSafeLogCache and load_crash_logs_async removed - using direct file I/O for better performance

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo


class AsyncCrashLogPipeline:
    """
    Handles the asynchronous processing of crash logs.

    This class provides methods to process crash log files using a fully asynchronous pipeline. It operates in various stages:
    reformatting log files, loading logs asynchronously, orchestrating processing using an external core system, and finally
    writing the processing results as reports. The implementation allows for dynamic batching and leverages concurrency for
    improved performance on systems with higher CPU counts.

    Attributes:
        yamldata (ClassicScanLogsInfo): Configuration data for processing.
        fcx_mode (bool | None): Indicates whether FCX mode is enabled.
        show_formid_values (bool | None): Indicates whether FormID values are displayed in the results.
        formid_db_exists (bool): Indicates whether the FormID database is present for use during processing.
        performance_stats (dict): Tracks performance metrics including processing times for different stages of the pipeline.
    """

    def __init__(
        self,
        yamldata: "ClassicScanLogsInfo",
        fcx_mode: bool | None,
        show_formid_values: bool | None,
        formid_db_exists: bool,
    ) -> None:
        """
        Initializes an instance for managing and processing classic scan logs information.

        This constructor sets up various attributes related to scan logs, modes, and database
        status. It prepares the object for performance tracking by initializing a dictionary
        to store performance statistics.

        Args:
            yamldata: ClassicScanLogsInfo-like object representing scan log data.
            fcx_mode: Boolean or None indicating whether the FCX mode is active or unset.
            show_formid_values: Boolean or None to specify whether to display form ID values.
            formid_db_exists: Boolean indicating whether the form ID database already exists.
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
        Processes a list of crash log files asynchronously, performing reformatting, loading,
        database processing, and report writing within an optimized pipeline. Tracks performance
        metrics throughout the pipeline, including reformatting time, log loading time,
        processing time, report writing time, and overall throughput.

        Args:
            crashlog_list (list[Path]): List of crash log file paths to be processed.
            remove_list (tuple[str]): Tuple of strings specifying patterns to be removed
                during reformatting.

        Returns:
            tuple: A tuple containing:
                - A list of tuples, each representing the result for a crash log file:
                  (file path, autoscan report, trigger scan result, error counts).
                - A dictionary with performance statistics including times for each stage
                  and logs processed per second.

        Raises:
            Various exceptions may be raised depending on failures in file access,
            asynchronous tasks, or processing errors, which should be handled by the caller.
        """
        logger.info("Starting async crash log processing pipeline")
        total_start = time.perf_counter()

        # Step 1: Async file reformatting
        reformat_start = time.perf_counter()
        await crashlogs_reformat_async(crashlog_list, remove_list)
        self.performance_stats["reformat_time"] = time.perf_counter() - reformat_start
        logger.debug(f"Async reformatting completed in {self.performance_stats['reformat_time']:.3f}s")

        # Step 2: Skip loading - using direct file I/O for better performance
        # Performance analysis showed that reading files directly is faster than
        # caching for small crash log files (typically <100KB)
        logger.debug("Using direct file I/O instead of cache (better performance for small files)")

        # Step 3: Async database processing with orchestrator
        process_start = time.perf_counter()

        # Process logs with progress tracking
        total_logs = len(crashlog_list)
        with msg_progress_context("Processing Crash Logs", total_logs) as progress:
            # OrchestratorCore now reads files directly - no cache needed
            async with OrchestratorCore(
                self.yamldata,
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


async def run_async_crash_log_scan(
    crashlog_list: list[Path],
    remove_list: tuple[str],
    yamldata: "ClassicScanLogsInfo",
    fcx_mode: bool | None,
    show_formid_values: bool | None,
    formid_db_exists: bool,
) -> tuple[list[tuple[Path, list[str], bool, Counter[str]]], dict[str, float]]:
    """
    Executes an asynchronous scan of crash logs and processes them based on the specified parameters.

    This function utilizes an asynchronous pipeline to perform a comprehensive analysis of crash log files.
    The function prepares and processes provided crash logs and applies necessary filtration and decoding
    specified through other parameters. Finally, it returns the processed log details and summary statistics.

    Args:
        crashlog_list (list[Path]): A list of paths pointing to the crash log files.
        remove_list (tuple[str]): A tuple containing identifiers or patterns that need to be filtered out
            while processing the logs.
        yamldata (ClassicScanLogsInfo): An object containing configuration data and parsing rules for the log
            scanning process.
        fcx_mode (bool | None): A flag indicating whether the processing should operate in FCX mode.
        show_formid_values (bool | None): A flag to decide if "formid" values in the logs should be displayed.
        formid_db_exists (bool): A flag indicating if the "formid" database exists.

    Returns:
        tuple: A tuple consisting of two elements:
            - A list of tuples containing processed log details:
                - Path: The path of the processed crash log.
                - list[str]: A list of decoded log strings.
                - bool: A flag indicating the status of the processing for that log.
                - Counter[str]: A counter object containing statistical data of processed elements in the log.
            - dict[str, float]: A dictionary containing performance statistics or other summary metrics from
              the scan process.
    """
    pipeline = AsyncCrashLogPipeline(yamldata, fcx_mode, show_formid_values, formid_db_exists)

    return await pipeline.process_crash_logs_async(crashlog_list, remove_list)
