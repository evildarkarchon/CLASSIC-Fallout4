"""Async crash log processing pipeline.

This module provides the main AsyncCrashLogPipeline class that integrates
all async components for maximum performance improvement.

Phase 9: Uses Rust Orchestrator directly for all processing.
"""

import asyncio
import os
import time
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from ClassicLib.core.logger import logger
from ClassicLib.integration.factory import get_file_io
from ClassicLib.messaging import msg_progress_context
from ClassicLib.scanning.logs.async_reformat import crashlogs_reformat_async

# Import Rust orchestrator - required, no Python fallback
try:
    from classic_scanlog import Orchestrator, AnalysisConfig
except ImportError as e:
    raise RuntimeError(
        "Rust orchestrator module not available. CLASSIC requires its Rust extensions. "
        "Please reinstall CLASSIC or rebuild Rust modules with: ./rebuild_rust.ps1"
    ) from e

# ThreadSafeLogCache and load_crash_logs_async removed - using direct file I/O for better performance

if TYPE_CHECKING:
    from ClassicLib.scanning.logs.scanloginfo import ClassicScanLogsInfo


async def write_reports_batch(reports: list[tuple[Path, list[str], bool]]) -> None:
    """Write batch reports to their respective files asynchronously.

    Args:
        reports (list[tuple[Path, list[str], bool]]): A list of tuples, where each
            tuple contains:
            - A Path object pointing to the crash log file.
            - A list of strings representing the autoscan report content.
            - A boolean indicating whether a scan failure occurred.

    """
    io_core = get_file_io()
    tasks = []
    for crashlog_file, autoscan_report, _ in reports:
        report_path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
        content = "".join(autoscan_report)
        tasks.append(io_core.write_file(report_path, content))

    await asyncio.gather(*tasks, return_exceptions=True)  # pyright: ignore[reportUnknownArgumentType]
    logger.debug(f"Wrote {len(reports)} reports using batch I/O")


class AsyncCrashLogPipeline:
    """Handle the asynchronous processing of crash logs.

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
        """Initialize an instance for managing and processing classic scan logs information.

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
        self, crashlog_list: list[Path], remove_list: tuple[str, ...]
    ) -> tuple[list[tuple[Path, list[str], bool, Counter[str]]], dict[str, float]]:
        """Process a list of crash log files asynchronously, performing reformatting, loading,
        database processing, and report writing within an optimized pipeline. Tracks performance
        metrics throughout the pipeline, including reformatting time, log loading time,
        processing time, report writing time, and overall throughput.

        Args:
            crashlog_list (list[Path]): List of crash log file paths to be processed.
            remove_list (tuple[str, ...]): Tuple of strings specifying patterns to be removed
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

        # Process logs with progress tracking using Rust Orchestrator
        total_logs = len(crashlog_list)
        with msg_progress_context("Processing Crash Logs", total_logs) as progress:
            # Initialize Rust orchestrator with YamlData configuration
            from ClassicLib.integration.factory import get_yamldata

            rust_yamldata = get_yamldata()
            rust_config = AnalysisConfig.from_yamldata(rust_yamldata)

            # Apply configuration
            rust_config.fcx_mode = self.fcx_mode or False
            rust_config.show_formid_values = self.show_formid_values or False

            orchestrator = Orchestrator(rust_config)
            logger.debug(f"Initialized Rust orchestrator (feature_complete={orchestrator.is_feature_complete()})")

            # Convert paths to strings for Rust
            log_paths = [str(p) for p in crashlog_list]

            # Progress callback for Rust orchestrator
            def progress_callback(current: int, total: int, filename: str) -> None:
                progress.update(1, f"Processed {filename}")

            # Process all logs in parallel using Rust orchestrator
            # Run in thread pool to avoid blocking the event loop
            rust_results = await asyncio.to_thread(
                orchestrator.process_logs_batch,
                log_paths,
                None,  # max_concurrent = auto
                progress_callback,
            )

            # Convert Rust results to Python format
            all_results = []
            for rust_result in rust_results:
                crashlog_file = Path(rust_result.log_path)
                local_stats: Counter[str] = Counter(
                    scanned=rust_result.scanned,
                    incomplete=rust_result.incomplete,
                    failed=rust_result.failed,
                )
                all_results.append((crashlog_file, rust_result.report_lines, rust_result.trigger_scan_failed, local_stats))

        self.performance_stats["process_time"] = time.perf_counter() - process_start
        logger.debug(f"Async processing completed in {self.performance_stats['process_time']:.3f}s")

        # Step 4: Async report writing
        write_start = time.perf_counter()

        # Prepare reports for batch writing
        reports_to_write = [  # pyright: ignore[reportUnknownVariableType]
            (crashlog_file, autoscan_report, trigger_scan_failed)
            for crashlog_file, autoscan_report, trigger_scan_failed, _ in all_results  # pyright: ignore[reportUnknownVariableType]
        ]

        await write_reports_batch(reports_to_write)  # pyright: ignore[reportUnknownArgumentType]

        self.performance_stats["write_time"] = time.perf_counter() - write_start
        logger.debug(f"Async report writing completed in {self.performance_stats['write_time']:.3f}s")

        # Calculate total time and efficiency metrics
        self.performance_stats["total_time"] = time.perf_counter() - total_start
        self.performance_stats["logs_per_second"] = len(crashlog_list) / self.performance_stats["total_time"]

        logger.info(
            f"Async pipeline completed: {len(crashlog_list)} logs in {self.performance_stats['total_time']:.3f}s "
            f"({self.performance_stats['logs_per_second']:.1f} logs/sec)"
        )

        return all_results, self.performance_stats  # pyright: ignore[reportUnknownVariableType]


async def run_async_crash_log_scan(
    crashlog_list: list[Path],
    remove_list: tuple[str, ...],
    yamldata: "ClassicScanLogsInfo",
    fcx_mode: bool | None,
    show_formid_values: bool | None,
    formid_db_exists: bool,
) -> tuple[list[tuple[Path, list[str], bool, Counter[str]]], dict[str, float]]:
    """Execute an asynchronous scan of crash logs and processes them based on the specified parameters.

    This function utilizes an asynchronous pipeline to perform a comprehensive analysis of crash log files.
    The function prepares and processes provided crash logs and applies necessary filtration and decoding
    specified through other parameters. Finally, it returns the processed log details and summary statistics.

    Args:
        crashlog_list (list[Path]): A list of paths pointing to the crash log files.
        remove_list (tuple[str, ...]): A tuple containing identifiers or patterns that need to be filtered out
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
