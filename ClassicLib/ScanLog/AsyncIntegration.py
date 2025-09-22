"""
Module for asynchronous crash log scanning.

This module provides improved performance for processing crash logs by leveraging
asynchronous capabilities. It includes functions for concurrent file reformatting,
batch processing, and report writing, along with coordination of async database
lookups and other operations.
"""

import asyncio
import time
from typing import TYPE_CHECKING

from ClassicLib import MessageTarget, msg_info, msg_progress_context
from ClassicLib.AsyncBridge import AsyncBridge
from ClassicLib.Logger import logger
from ClassicLib.ScanLog.AsyncReformat import crashlogs_reformat_async
from ClassicLib.ScanLog.AsyncUtil import load_crash_logs_async
from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo, ThreadSafeLogCache
from ClassicLib.ScanLog.Util import crashlogs_get_files

if TYPE_CHECKING:
    from pathlib import Path


async def async_crashlogs_scan() -> None:
    """
    Scans and processes crash logs asynchronously.

    This function handles the asynchronous retrieval, reformatting, caching,
    processing, and reporting of crash logs. It supports batch processing, utilizes
    settings from a configuration cache, and dynamically handles unsolved logs
    based on settings. Timing of different stages (reformatting, loading,
    processing, and report writing) for performance insights is logged.

    The expected workflow includes:
    1. Retrieving all crash log files.
    2. Loading and utilizing cached user settings for various log-handling
       configurations.
    3. Asynchronous reformatting of crash logs.
    4. Loading crash logs into an asynchronous in-memory cache.
    5. Processing crash logs in batches using an orchestrator.
    6. Writing reports in batch asynchronously following processing.
    7. Optionally moving unsolved logs if configured.

    The function ensures thread-safe access to crash logs and manages progress and
    error reporting through logging and CLI messages.
    """
    from ClassicLib.Constants import DB_PATHS, YAML
    from ClassicLib.YamlSettingsCache import yaml_cache

    # Get crash log files
    crashlog_list: list[Path] = crashlogs_get_files()
    msg_info("REFORMATTING CRASH LOGS ASYNC, PLEASE WAIT...", target=MessageTarget.CLI_ONLY)

    # Batch load all settings at once
    requests = [
        (tuple, YAML.Main, "exclude_log_records"),
        (bool, YAML.Settings, "CLASSIC_Settings.FCX Mode"),
        (bool, YAML.Settings, "CLASSIC_Settings.Show FormID Values"),
        (bool, YAML.Settings, "CLASSIC_Settings.Move Unsolved Logs"),
    ]

    values = yaml_cache.batch_get_settings(requests)

    # Unpack settings
    remove_list: tuple[str] = values[0] or ("",)
    fcx_mode: bool | None = values[1]
    show_formid_values: bool | None = values[2]
    move_unsolved_logs: bool | None = values[3]

    # Reformat logs asynchronously
    reformat_start = time.perf_counter()
    await crashlogs_reformat_async(crashlog_list, remove_list)
    reformat_time = time.perf_counter() - reformat_start
    logger.info(f"Async reformatting completed in {reformat_time:.2f} seconds")

    # Initialize configuration
    yamldata = ClassicScanLogsInfo()
    formid_db_exists: bool = any(db.is_file() for db in DB_PATHS)

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

    # Initialize scan_failed_list early to avoid UnboundLocalError if cancelled
    scan_failed_list = []

    # Process crash logs with async orchestrator
    async with OrchestratorCore(yamldata, crashlogs, fcx_mode, show_formid_values, formid_db_exists) as orchestrator:
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
            # scan_failed_list already initialized above for proper error handling

            for crashlog_file, autoscan_report, trigger_scan_failed, _stats in results:
                reports_to_write.append((crashlog_file, autoscan_report, trigger_scan_failed))

                if trigger_scan_failed:
                    scan_failed_list.append(crashlog_file.name)

                # Update progress
                progress.update(1, f"Processed {crashlog_file.name}")

            # Write all reports concurrently
            write_start = time.perf_counter()
            await OrchestratorCore.write_reports_batch(reports_to_write)
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
    Executes an asynchronous scan operation using an asynchronous bridge.

    This function retrieves an instance of the asynchronous bridge and triggers
    an asynchronous scan operation to detect crash logs.

    Raises:
        No specific errors are individually raised by this function, but it relies
        on external components that potentially might raise exceptions that should
        be handled by the caller.
    """
    bridge = AsyncBridge.get_instance()
    bridge.run_async(async_crashlogs_scan())


__all__ = ['async_crashlogs_scan', 'run_async_scan']
