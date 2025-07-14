"""
Example integration of async components for crash log scanning.

This module demonstrates how to integrate the async components into the
existing crash log scanning workflow for improved performance.
"""

import asyncio
import time
from typing import TYPE_CHECKING

from ClassicLib import MessageTarget, msg_info, msg_progress_context
from ClassicLib.Logger import logger
from ClassicLib.ScanLog.AsyncReformat import crashlogs_reformat_async
from ClassicLib.ScanLog.AsyncScanOrchestrator import AsyncScanOrchestrator, write_reports_batch_async
from ClassicLib.ScanLog.AsyncUtil import load_crash_logs_async
from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo, ThreadSafeLogCache
from ClassicLib.ScanLog.Util import crashlogs_get_files

if TYPE_CHECKING:
    from pathlib import Path


async def async_crashlogs_scan() -> None:
    """
    Async version of crash log scanning with improved performance.

    This function demonstrates how to use async components for:
    1. Concurrent file reformatting
    2. Batch crash log processing
    3. Concurrent report writing
    4. Async database lookups
    """
    from ClassicLib.Constants import DB_PATHS, YAML
    from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings

    # Get crash log files
    crashlog_list: list[Path] = crashlogs_get_files()
    msg_info("REFORMATTING CRASH LOGS ASYNC, PLEASE WAIT...", target=MessageTarget.CLI_ONLY)

    # Load settings
    remove_list: tuple[str] = yaml_settings(tuple, YAML.Main, "exclude_log_records") or ("",)

    # Reformat logs asynchronously
    reformat_start = time.perf_counter()
    await crashlogs_reformat_async(crashlog_list, remove_list)
    reformat_time = time.perf_counter() - reformat_start
    logger.info(f"Async reformatting completed in {reformat_time:.2f} seconds")

    # Initialize configuration
    yamldata = ClassicScanLogsInfo()
    fcx_mode: bool | None = classic_settings(bool, "FCX Mode")
    show_formid_values: bool | None = classic_settings(bool, "Show FormID Values")
    formid_db_exists: bool = any(db.is_file() for db in DB_PATHS)
    move_unsolved_logs: bool | None = classic_settings(bool, "Move Unsolved Logs")

    msg_info("SCANNING CRASH LOGS ASYNC, PLEASE WAIT...", target=MessageTarget.CLI_ONLY)
    scan_start_time: float = time.perf_counter()

    # Load crash logs asynchronously
    cache_start = time.perf_counter()
    crash_log_cache = await load_crash_logs_async(crashlog_list)
    cache_time = time.perf_counter() - cache_start
    logger.info(f"Async cache loading completed in {cache_time:.2f} seconds")

    # Create thread-safe cache wrapper
    crashlogs = ThreadSafeLogCache(crashlog_list)
    # Replace the synchronous cache with our async-loaded cache
    crashlogs.cache = {name: "\n".join(lines).encode("utf-8") for name, lines in crash_log_cache.items()}

    # Process crash logs with async orchestrator
    async with AsyncScanOrchestrator(yamldata, crashlogs, fcx_mode, show_formid_values, formid_db_exists) as orchestrator:
        # Process in batches with progress tracking
        total_logs = len(crashlog_list)
        with msg_progress_context("Processing Crash Logs Async", total_logs) as progress:
            # Process all logs
            process_start = time.perf_counter()
            results = await orchestrator.process_crash_logs_batch_async(crashlog_list)
            process_time = time.perf_counter() - process_start
            logger.info(f"Async processing completed in {process_time:.2f} seconds")

            # Prepare reports for batch writing
            reports_to_write = []
            scan_failed_list = []

            for crashlog_file, autoscan_report, trigger_scan_failed, _stats in results:
                reports_to_write.append((crashlog_file, autoscan_report, trigger_scan_failed))

                if trigger_scan_failed:
                    scan_failed_list.append(crashlog_file.name)

                # Update progress
                progress.update(1, f"Processed {crashlog_file.name}")

            # Write all reports concurrently
            write_start = time.perf_counter()
            await write_reports_batch_async(reports_to_write)
            write_time = time.perf_counter() - write_start
            logger.info(f"Async report writing completed in {write_time:.2f} seconds")

            # Handle unsolved logs if move_unsolved_logs is enabled
            if move_unsolved_logs:
                from CLASSIC_ScanLogs import move_unsolved_logs as move_unsolved_logs_func

                for crashlog_file, _autoscan_report, trigger_scan_failed, _stats in results:
                    if trigger_scan_failed:
                        move_unsolved_logs_func(crashlog_file)

    # Calculate total time
    total_time = time.perf_counter() - scan_start_time
    logger.info(f"Total async scan time: {total_time:.2f} seconds")

    # Report any failures
    if scan_failed_list:
        error_msg = "NOTICE : CLASSIC WAS UNABLE TO PROPERLY SCAN THE FOLLOWING LOG(S):\n"
        error_msg += "\n".join(scan_failed_list)
        msg_info(error_msg)


def run_async_scan() -> None:
    """
    Run the async crash log scan.

    This function can be called from synchronous code to run the async scan.
    """
    asyncio.run(async_crashlogs_scan())
