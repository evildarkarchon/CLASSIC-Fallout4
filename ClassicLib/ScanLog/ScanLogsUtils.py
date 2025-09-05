"""
Utility functions for crash log scanning operations.

This module contains utility functions that support crash log scanning,
including report writing, file management, and scan completion tasks.
"""

import asyncio
import random
import shutil
import time
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, cast

from ClassicLib import GlobalRegistry, MessageTarget, msg_error, msg_info
from ClassicLib.AsyncBridge import run_async
from ClassicLib.Logger import logger
from ClassicLib.ScanLog.models import ScanResult
from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogsExecutor import ScanLogsExecutor


async def write_report_to_file_async(
    crashlog_file: Path,
    autoscan_report: list[str],
    trigger_scan_failed: bool,
    executor: "ScanLogsExecutor"
) -> None:
    """
    Async version of write_report_to_file using aiofiles.

    Args:
        crashlog_file: Path to the crash log file
        autoscan_report: Generated report lines
        trigger_scan_failed: Whether the scan failed
        executor: The executor instance with configuration
    """
    try:
        import aiofiles

        autoscan_path: Path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
        async with aiofiles.open(autoscan_path, "w", encoding="utf-8", errors="ignore") as autoscan_file:
            logger.debug(f"- - -> RUNNING CRASH LOG FILE SCAN >>> SCANNED {crashlog_file.name}")
            autoscan_output: str = "".join(autoscan_report)
            await autoscan_file.write(autoscan_output)

        if trigger_scan_failed and executor.config.move_unsolved_logs:
            # Run in executor since move_unsolved_logs uses sync I/O
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, partial(move_unsolved_logs, crashlog_file))

    except ImportError:
        # Fallback to sync write if aiofiles not available
        loop = asyncio.get_running_loop()
        # Use partial to properly bind arguments for better type inference
        write_func = partial(write_report_to_file, crashlog_file, autoscan_report, trigger_scan_failed, executor)
        await loop.run_in_executor(None, write_func)


def write_report_to_file(
    crashlog_file: Path,
    autoscan_report: list[str],
    trigger_scan_failed: bool,
    executor: "ScanLogsExecutor"
) -> None:
    """
    Write report to file and handle unsolved logs.

    Args:
        crashlog_file: Path to the crash log file
        autoscan_report: Generated report lines
        trigger_scan_failed: Whether the scan failed
        executor: The executor instance with configuration
    """
    autoscan_path: Path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
    with autoscan_path.open("w", encoding="utf-8", errors="ignore") as autoscan_file:
        logger.debug(f"- - -> RUNNING CRASH LOG FILE SCAN >>> SCANNED {crashlog_file.name}")
        autoscan_output: str = "".join(autoscan_report)
        autoscan_file.write(autoscan_output)

    if trigger_scan_failed and executor.config.move_unsolved_logs:
        move_unsolved_logs(crashlog_file)


def move_unsolved_logs(crashlog_file: Path) -> None:
    """
    Move unsolved logs to backup location.

    Args:
        crashlog_file: Path to the crash log file to move
    """
    backup_path: Path = cast("Path", GlobalRegistry.get_local_dir()) / "CLASSIC Backup/Unsolved Logs"
    backup_path.mkdir(parents=True, exist_ok=True)
    autoscan_filepath: Path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")

    # Move the original crash log file
    if crashlog_file.exists():
        backup_crashlog_path: Path = backup_path / crashlog_file.name
        try:
            shutil.move(str(crashlog_file), str(backup_crashlog_path))
            logger.info(f"Moved unsolved crash log to backup: {crashlog_file.name}")
        except OSError as e:
            logger.error(f"Failed to move crash log {crashlog_file} to backup: {e}")

    # Move the autoscan report file
    if autoscan_filepath.exists():
        backup_autoscan_path: Path = backup_path / autoscan_filepath.name
        try:
            shutil.move(str(autoscan_filepath), str(backup_autoscan_path))
            logger.info(f"Moved autoscan report to backup: {autoscan_filepath.name}")
        except OSError as e:
            logger.error(f"Failed to move autoscan report {autoscan_filepath} to backup: {e}")


def complete_scan_with_summary(
    result: ScanResult,
    yamldata: ClassicScanLogsInfo,
    scan_start_time: float
) -> None:
    """
    Complete the scan with error checking and summary display.

    Args:
        result: The scan result containing statistics and failed logs
        yamldata: Configuration data for hints and messages
        scan_start_time: When the scan started (for timing calculations)
    """
    # Check for failed or invalid crash logs
    scan_invalid_list: list[Path] = sorted(Path.cwd().glob("crash-*.txt"))

    if result.failed_logs or scan_invalid_list:
        error_msg = "NOTICE : CLASSIC WAS UNABLE TO PROPERLY SCAN THE FOLLOWING LOG(S):\n"
        if result.failed_logs:
            error_msg += "\n".join(result.failed_logs) + "\n"
        if scan_invalid_list:
            error_msg += "\n"
            for file in scan_invalid_list:
                error_msg += f"{file}\n"
        error_msg += "===============================================================================\n"
        error_msg += "Most common reason for this are logs being incomplete or in the wrong format.\n"
        error_msg += "Make sure that your crash log files have the .log file format, NOT .txt!"
        msg_error(error_msg)

    # Display completion information
    logger.debug("Completed crash log file scan")

    if result.stats.scanned == 0 and result.stats.incomplete == 0:
        msg_error("CLASSIC found no crash logs to scan or the scan failed.\n    There are no statistics to show (at this time).")
    else:
        success_message = "SCAN COMPLETE! (IT MIGHT TAKE SEVERAL SECONDS FOR SCAN RESULTS TO APPEAR)\n"
        success_message += "SCAN RESULTS ARE AVAILABLE IN FILES NAMED crash-date-and-time-AUTOSCAN.md\n"

        # Display hint and statistics
        scan_duration = time.perf_counter() - 0.5 - scan_start_time
        success_message += f"Scanned all available logs in {str(scan_duration)[:5]} seconds.\n"
        success_message += f"Number of Scanned Logs (No Autoscan Errors): {result.stats.scanned}\n"
        success_message += f"Number of Incomplete Logs (No Plugins List): {result.stats.incomplete}\n"
        success_message += f"Number of Failed Logs (Autoscan Can't Scan): {result.stats.failed}\n-----"

        msg_info(success_message)

        # Show random hint
        if hasattr(yamldata, 'classic_game_hints') and yamldata.classic_game_hints:
            msg_info(f"{random.choice(yamldata.classic_game_hints)}", target=MessageTarget.CLI_ONLY)

        # Show game-specific information
        if GlobalRegistry.get_game() == "Fallout4":
            msg_info("\n-----\n", target=MessageTarget.CLI_ONLY)
            if hasattr(yamldata, 'autoscan_text'):
                msg_info(yamldata.autoscan_text, target=MessageTarget.CLI_ONLY)


async def crashlogs_scan_async_pure(executor: "ScanLogsExecutor") -> ScanResult:
    """
    Pure async crash log scanning with controlled concurrency.

    This is the main async entry point that orchestrates the entire scanning process
    using the executor pattern for clean separation of concerns.

    Args:
        executor: The configured scan executor

    Returns:
        ScanResult containing scan outcomes and statistics
    """
    logger.info("Starting pure async crash log scanning")

    # Reset FCX checks for new scan session
    from ClassicLib.ScanLog.FCXModeHandler import FCXModeHandlerFragments
    FCXModeHandlerFragments.reset_fcx_checks()

    # Execute the scan
    result = await executor.execute_scan()

    # Complete with summary
    complete_scan_with_summary(result, executor.yamldata, executor.statistics.scan_start_time)

    return result


def crashlogs_scan() -> ScanResult:
    """
    Main entry point for crash log scanning.

    Uses pure async processing for better resource management and thread safety.

    Returns:
        ScanResult from the scanning operation
    """
    from ClassicLib.ScanLog.ScanLogsExecutor import ScanLogsExecutor

    executor = ScanLogsExecutor()

    # Use async processing
    return run_async(crashlogs_scan_async_pure(executor))


# Legacy function names for backward compatibility
def _complete_scan_with_summary(
    executor: "ScanLogsExecutor",
    scan_failed_list: list[str],
    yamldata: ClassicScanLogsInfo
) -> None:
    """
    Legacy wrapper for complete_scan_with_summary.

    Args:
        executor: The scan executor instance
        scan_failed_list: List of failed log names
        yamldata: Configuration data
    """
    # Convert executor state to ScanResult for new function
    result = ScanResult()
    result.stats = executor.statistics
    result.failed_logs = scan_failed_list
    result.scan_time = executor.statistics.get_scan_duration()

    complete_scan_with_summary(result, yamldata, executor.statistics.scan_start_time)


async def crashlogs_scan_async_pure_with_qt(executor: "ScanLogsExecutor") -> ScanResult:
    """
    Pure async crash log scanning with Qt event processing for GUI mode.

    This version is specifically for GUI mode and allows Qt signals to be
    processed during async operations for real-time progress updates.

    Args:
        executor: ClassicScanLogs instance with configuration

    Returns:
        ScanResult from the scanning operation
    """
    # For now, delegate to the main function - Qt-specific handling can be added later
    return await crashlogs_scan_async_pure(executor)
