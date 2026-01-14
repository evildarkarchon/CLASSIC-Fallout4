"""Utility functions for crash log scanning operations.

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
from ClassicLib.Logger import logger
from ClassicLib.ScanLog.models import ScanResult
from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo

if TYPE_CHECKING:
    from ClassicLib.ScanLog.ScanLogsExecutor import ScanLogsExecutor


async def write_report_to_file_async(
    crashlog_file: Path, autoscan_report: list[str], trigger_scan_failed: bool, executor: "ScanLogsExecutor"
) -> None:
    """Write an autoscan report to a file asynchronously.

    This function handles writing the autoscan report to a file, with an optional
    fallback to a synchronous approach if `aiofiles` is unavailable. If the
    `trigger_scan_failed` flag is set to True and the executor configuration
    allows moving unsolved logs, it will trigger the `move_unsolved_logs`
    operation in a separate thread.

    Args:
        crashlog_file: The crash log file to process and write the autoscan report for.
        autoscan_report: A list containing strings of the autoscan report to be concatenated.
        trigger_scan_failed: A boolean indicating whether the unsolved logs operation should be triggered.
        executor: An instance of `ScanLogsExecutor` to manage configurations and operations.

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


def write_report_to_file(crashlog_file: Path, autoscan_report: list[str], trigger_scan_failed: bool, executor: "ScanLogsExecutor") -> None:
    """Write the autoscan report to a file, generates a properly named output file, and moves
    unsolved logs if required.

    Args:
        crashlog_file (Path): The path of the crash log file to scan.
        autoscan_report (list[str]): A list of strings representing the autoscan report content.
        trigger_scan_failed (bool): A flag indicating if trigger scan has failed.
        executor (ScanLogsExecutor): An instance of the ScanLogsExecutor class to handle configurations.

    """
    autoscan_path: Path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
    with autoscan_path.open("w", encoding="utf-8", errors="ignore") as autoscan_file:
        logger.debug(f"- - -> RUNNING CRASH LOG FILE SCAN >>> SCANNED {crashlog_file.name}")
        autoscan_output: str = "".join(autoscan_report)
        autoscan_file.write(autoscan_output)

    if trigger_scan_failed and executor.config.move_unsolved_logs:
        move_unsolved_logs(crashlog_file)


def move_unsolved_logs(crashlog_file: Path) -> None:
    """Move unsolved crash logs and their associated autoscan reports to a backup directory.

    This function ensures that unsolved crash logs are properly archived by transferring them
    to a designated "Unsolved Logs" backup folder. It handles both the original crash log and
    its associated autoscan report file (if available). The function creates the backup folder
    if it does not exist and logs the success or failure of each file operation.

    Args:
        crashlog_file (Path): The file path of the crash log to be moved to the backup directory.

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


def complete_scan_with_summary(result: ScanResult, yamldata: ClassicScanLogsInfo, scan_start_time: float) -> None:
    """Complete the scanning process by performing final checks, displaying completion information, and
    providing relevant scan statistics and hints.

    This function processes the scan results and handles any failed or invalid logs. It generates summary
    messages, computes the scan duration, and provides detailed feedback on the scan's outcome.
    Additionally, it may display random hints or game-specific information based on the provided data.

    Args:
        result (ScanResult): The object containing information about the scanning process, such as the
            number of scanned logs, incomplete logs, and failed logs.
        yamldata (ClassicScanLogsInfo): The object containing additional scan configuration information,
            hints, or game-specific data required for processing and displaying scan results.
        scan_start_time (float): The timestamp indicating when the scan process started. Used to calculate
            the total duration of the scanning process.

    Raises:
        None

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
        if hasattr(yamldata, "classic_game_hints") and yamldata.classic_game_hints:
            msg_info(f"{random.choice(yamldata.classic_game_hints)}", target=MessageTarget.CONSOLE)

        # Show game-specific information
        if GlobalRegistry.get_game() == "Fallout4":
            msg_info("\n-----\n", target=MessageTarget.CONSOLE)
            if hasattr(yamldata, "autoscan_text"):
                msg_info(yamldata.autoscan_text, target=MessageTarget.CONSOLE)


async def crashlogs_scan_async_pure(executor: "ScanLogsExecutor") -> ScanResult:
    """Pure async crash log scanning with controlled concurrency.

    This is the main async entry point that orchestrates the entire scanning process
    using the executor pattern for clean separation of concerns.

    Args:
        executor: The configured scan executor

    Returns:
        ScanResult containing scan outcomes and statistics

    Raises:
        RuntimeError: If YAML data is not initialized after scan execution.

    """
    logger.info("Starting pure async crash log scanning")

    # Reset FCX checks for new scan session
    from ClassicLib.ScanLog.FCXModeHandler import FCXModeHandlerFragments

    FCXModeHandlerFragments.reset_fcx_checks()

    # Execute the scan
    result = await executor.execute_scan()

    # Ensure yamldata is initialized (execute_scan guarantees this)
    if executor.yamldata is None:
        msg = "YAML data should be initialized after execute_scan"
        raise RuntimeError(msg)

    # Complete with summary
    complete_scan_with_summary(result, executor.yamldata, executor.statistics.scan_start_time)

    return result


def crashlogs_scan() -> ScanResult:
    """Sync wrapper for crashlogs_scan_async_pure. GUI workers only.

    WARNING: This function uses AsyncBridge internally and creates additional event loop overhead.
    Not for CLI use.

    For CLI usage, use crashlogs_scan_async_pure() directly with await.

    Returns:
        ScanResult: The result of the crash log scan.

    """
    from ClassicLib.AsyncBridge import run_async
    from ClassicLib.ScanLog.ScanLogsExecutor import ScanLogsExecutor

    executor = ScanLogsExecutor()

    # Use async processing
    return run_async(crashlogs_scan_async_pure(executor))


async def crashlogs_scan_async_pure_with_qt(executor: "ScanLogsExecutor") -> ScanResult:
    """Asynchronously scans crash logs using the provided executor.

    This function delegates the crash logs scanning task to the main logic, and
    is intended to allow for Qt-specific handling to be added in the future, if
    required. The scanning process retrieves and analyzes crash logs, returning
    the results encapsulated in a ScanResult instance.

    Args:
        executor (ScanLogsExecutor): The execution object that manages and performs
            the crash logs scanning process.

    Returns:
        ScanResult: The result of the crash logs scanning operation.

    """
    # For now, delegate to the main function - Qt-specific handling can be added later
    return await crashlogs_scan_async_pure(executor)
