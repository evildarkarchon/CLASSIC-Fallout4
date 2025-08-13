"""
Refactored CLASSIC_ScanLogs module using the new modular architecture.

This module maintains backward compatibility while delegating to the new
modular components for crash log scanning functionality.
"""

import asyncio
import os
import random
import sys
import time
from collections import Counter

# Removed ThreadPoolExecutor - using pure async instead
from pathlib import Path
from typing import cast

from ClassicLib import GlobalRegistry, MessageTarget, msg_error, msg_info
from ClassicLib.Constants import DB_PATHS, YAML
from ClassicLib.Logger import logger
from ClassicLib.ScanLog import (
    FCXModeHandler,
    ThreadSafeLogCache,
    crashlogs_get_files,
    crashlogs_reformat,
)
from ClassicLib.ScanLog.AsyncScanOrchestrator import AsyncScanOrchestrator
from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo
from ClassicLib.SetupCoordinator import SetupCoordinator
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


class ClassicScanLogs:
    """
    Refactored ClassicScanLogs that delegates to modular components.

    This class maintains the same interface as the original implementation
    but uses the new modular architecture internally.
    """

    def __init__(self) -> None:
        """Initialize the crash log scanner with new modular components."""
        # Get crash log files
        self.crashlog_list: list[Path] = crashlogs_get_files()
        msg_info("REFORMATTING CRASH LOGS, PLEASE WAIT...", target=MessageTarget.CLI_ONLY)

        # Load settings
        self.remove_list: tuple[str] = yaml_settings(tuple, YAML.Main, "exclude_log_records") or ("",)

        # Always use sync version for initialization to avoid event loop issues
        # The async reformatting will be done in the main scan process
        crashlogs_reformat(self.crashlog_list, self.remove_list)
        logger.debug("Used sync file I/O for crash log reformatting during init")

        # Initialize configuration
        self.yamldata = ClassicScanLogsInfo()
        self.fcx_mode: bool | None = classic_settings(bool, "FCX Mode")
        self.show_formid_values: bool | None = classic_settings(bool, "Show FormID Values")
        self.formid_db_exists: bool = any(db.is_file() for db in DB_PATHS)
        self.move_unsolved_logs: bool | None = classic_settings(bool, "Move Unsolved Logs")

        # Async database operations are handled by AsyncScanOrchestrator

        msg_info("SCANNING CRASH LOGS, PLEASE WAIT...", target=MessageTarget.CLI_ONLY)
        self.scan_start_time: float = time.perf_counter()

        # Initialize thread-safe log cache
        self.crashlogs = ThreadSafeLogCache(self.crashlog_list)

        # We'll initialize the async orchestrator in the async context

        # Statistics tracking
        self.crashlog_stats: Counter[str] = Counter(scanned=0, incomplete=0, failed=0)

        logger.debug(f"Initiated crash log scan for {len(self.crashlog_list)} files")

        # FCX checks will be done in the async orchestrator

    # Removed synchronous process_crashlog method - using async version instead

    async def process_crashlog_async(
        self, crashlog_file: Path, orchestrator: AsyncScanOrchestrator
    ) -> tuple[Path, list[str], bool, Counter[str]]:
        """
        Process a crash log with async database operations for FormID lookups.

        This method is now fully async and doesn't create nested event loops.

        Args:
            crashlog_file: Path to the crash log file
            orchestrator: The async orchestrator instance

        Returns:
            Tuple containing file path, report, failure status, and statistics
        """
        try:
            # Use the async orchestrator directly
            return await orchestrator.process_crash_log_async(crashlog_file)
        except (RuntimeError, ImportError, OSError) as e:
            logger.error(f"Error processing crash log {crashlog_file}: {e}")
            # Return failure result
            return crashlog_file, [f"Error processing log: {e}"], True, Counter(failed=1)

    # Removed _process_crashlog_async - now using AsyncScanOrchestrator directly

    # Removed _check_async_db_availability - AsyncScanOrchestrator handles this internally


def write_report_to_file(crashlog_file: Path, autoscan_report: list[str], trigger_scan_failed: bool, scanner: ClassicScanLogs) -> None:
    """
    Write report to file and handle unsolved logs.

    Args:
        crashlog_file: Path to the crash log file
        autoscan_report: Generated report lines
        trigger_scan_failed: Whether the scan failed
        scanner: The scanner instance
    """
    autoscan_path: Path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
    with autoscan_path.open("w", encoding="utf-8", errors="ignore") as autoscan_file:
        logger.debug(f"- - -> RUNNING CRASH LOG FILE SCAN >>> SCANNED {crashlog_file.name}")
        autoscan_output: str = "".join(autoscan_report)
        autoscan_file.write(autoscan_output)

    if trigger_scan_failed and scanner.move_unsolved_logs:
        move_unsolved_logs(crashlog_file)


def move_unsolved_logs(crashlog_file: Path) -> None:
    """Move unsolved logs to backup location."""
    import shutil

    backup_path: Path = cast("Path", GlobalRegistry.get_local_dir()) / "CLASSIC Backup/Unsolved Logs"
    backup_path.mkdir(parents=True, exist_ok=True)
    autoscan_filepath: Path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")

    # Move the original crash log file
    if crashlog_file.exists():
        backup_crashlog_path: Path = backup_path / crashlog_file.name
        try:
            shutil.move(str(crashlog_file), str(backup_crashlog_path))
        except OSError as e:
            logger.error(f"Failed to move crash log {crashlog_file} to backup: {e}")

    # Move the autoscan report file
    if autoscan_filepath.exists():
        backup_autoscan_path: Path = backup_path / autoscan_filepath.name
        try:
            shutil.move(str(autoscan_filepath), str(backup_autoscan_path))
        except OSError as e:
            logger.error(f"Failed to move autoscan report {autoscan_filepath} to backup: {e}")


def crashlogs_scan() -> None:
    """
    Main entry point for crash log scanning.

    Uses pure async processing for better resource management and thread safety.
    """
    scanner = ClassicScanLogs()
    FCXModeHandler.reset_fcx_checks()  # Reset FCX checks for new scan session

    # Always use pure async processing
    asyncio.run(crashlogs_scan_async_pure(scanner))


async def crashlogs_scan_async_pure(scanner: ClassicScanLogs) -> None:
    """
    Pure async crash log scanning with controlled concurrency.

    This implementation uses Option A from the audit recommendations,
    providing proper resource management and thread safety.

    Args:
        scanner: ClassicScanLogs instance with configuration
    """
    logger.info("Using pure async processing for crash log scanning")
    yamldata: ClassicScanLogsInfo = scanner.yamldata
    scan_failed_list: list = []

    # Create async orchestrator with context manager for proper resource management
    async with AsyncScanOrchestrator(
        scanner.yamldata, scanner.crashlogs, scanner.fcx_mode, scanner.show_formid_values, scanner.formid_db_exists
    ) as orchestrator:
        # Run FCX checks if enabled
        if scanner.fcx_mode:
            orchestrator.fcx_handler.check_fcx_mode()

        # Use semaphore to limit concurrent operations
        max_concurrent = min(10, len(scanner.crashlog_list))  # Limit to 10 concurrent operations
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_limit(log_path: Path) -> tuple[Path, list[str], bool, Counter[str]]:
            """Process a single log with concurrency limiting."""
            async with semaphore:
                return await scanner.process_crashlog_async(log_path, orchestrator)

        # Create tasks for all crash logs
        tasks = [process_with_limit(log) for log in scanner.crashlog_list]

        # Process all crash logs without progress tracking
        len(scanner.crashlog_list)
        completed = 0

        # Use asyncio.gather with return_exceptions=True for robust error handling
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for i, result in enumerate(results):
            result: Exception | tuple[Path, list[str], bool, Counter[str]]
            if isinstance(result, Exception):
                # Handle exceptions
                logger.error(f"Error processing crash log: {result}")
                scanner.crashlog_stats["failed"] += 1
                scan_failed_list.append(scanner.crashlog_list[i].name)
            else:
                # Unpack successful result
                try:
                    crashlog_file, autoscan_report, trigger_scan_failed, local_stats = result
                except (ValueError, TypeError) as e:
                    logger.error(f"Error unpacking result: {e}")
                    scanner.crashlog_stats["failed"] += 1
                    continue

                # Update statistics
                if isinstance(local_stats, Counter):
                    for key, value in local_stats.items():
                        scanner.crashlog_stats[key] += value

                # Write report asynchronously
                await write_report_to_file_async(crashlog_file, autoscan_report, trigger_scan_failed, scanner)

                # Track failed scans
                if trigger_scan_failed:
                    scan_failed_list.append(crashlog_file.name)

                completed += 1

    # Complete with standard error checking and summary
    _complete_scan_with_summary(scanner, scan_failed_list, yamldata)


async def write_report_to_file_async(
    crashlog_file: Path, autoscan_report: list[str], trigger_scan_failed: bool, scanner: ClassicScanLogs
) -> None:
    """
    Async version of write_report_to_file using aiofiles.

    Args:
        crashlog_file: Path to the crash log file
        autoscan_report: Generated report lines
        trigger_scan_failed: Whether the scan failed
        scanner: The scanner instance
    """
    try:
        import aiofiles

        autoscan_path: Path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
        async with aiofiles.open(autoscan_path, "w", encoding="utf-8", errors="ignore") as autoscan_file:
            logger.debug(f"- - -> RUNNING CRASH LOG FILE SCAN >>> SCANNED {crashlog_file.name}")
            autoscan_output: str = "".join(autoscan_report)
            await autoscan_file.write(autoscan_output)

        if trigger_scan_failed and scanner.move_unsolved_logs:
            # Run in executor since move_unsolved_logs uses sync I/O
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, move_unsolved_logs, crashlog_file)

    except ImportError:
        # Fallback to sync write if aiofiles not available
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, write_report_to_file, crashlog_file, autoscan_report, trigger_scan_failed, scanner)


# Removed old async pipeline function - using pure async pattern instead


# Removed threaded implementation - using pure async pattern instead


def _complete_scan_with_summary(scanner: ClassicScanLogs, scan_failed_list: list, yamldata: ClassicScanLogsInfo) -> None:
    """
    Complete the scan with error checking and summary display.

    Args:
        scanner: ClassicScanLogs instance
        scan_failed_list: List of failed log names
        yamldata: Configuration data
    """
    # Check for failed or invalid crash logs
    scan_invalid_list: list[Path] = sorted(Path.cwd().glob("crash-*.txt"))
    if scan_failed_list or scan_invalid_list:
        error_msg = "NOTICE : CLASSIC WAS UNABLE TO PROPERLY SCAN THE FOLLOWING LOG(S):\n"
        if scan_failed_list:
            error_msg += "\n".join(scan_failed_list) + "\n"
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

    if scanner.crashlog_stats["scanned"] == 0 and scanner.crashlog_stats["incomplete"] == 0:
        msg_error("CLASSIC found no crash logs to scan or the scan failed.\n    There are no statistics to show (at this time).")
    else:
        success_message = "SCAN COMPLETE! (IT MIGHT TAKE SEVERAL SECONDS FOR SCAN RESULTS TO APPEAR)\n"
        success_message += "SCAN RESULTS ARE AVAILABLE IN FILES NAMED crash-date-and-time-AUTOSCAN.md\n"

        # Display hint and statistics
        success_message += f"Scanned all available logs in {str(time.perf_counter() - 0.5 - scanner.scan_start_time)[:5]} seconds.\n"
        success_message += f"Number of Scanned Logs (No Autoscan Errors): {scanner.crashlog_stats['scanned']}\n"
        success_message += f"Number of Incomplete Logs (No Plugins List): {scanner.crashlog_stats['incomplete']}\n"
        success_message += f"Number of Failed Logs (Autoscan Can't Scan): {scanner.crashlog_stats['failed']}\n-----"
        msg_info(success_message)
        msg_info(f"{random.choice(yamldata.classic_game_hints)}", target=MessageTarget.CLI_ONLY)

        if GlobalRegistry.get_game() == "Fallout4":
            msg_info("\n-----\n", target=MessageTarget.CLI_ONLY)
            msg_info(yamldata.autoscan_text, target=MessageTarget.CLI_ONLY)


if __name__ == "__main__":
    # Ensure UTF-8 encoding for Windows console
    if sys.platform == "win32":
        import io

        # noinspection PyTypeChecker
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
        # noinspection PyTypeChecker
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)

    # Initialize application using SetupCoordinator
    coordinator = SetupCoordinator()
    coordinator.initialize_application(is_gui=False)

    import argparse

    parser = argparse.ArgumentParser(description="Command-line arguments for CLASSIC's Command Line Interface")

    parser.add_argument("--fcx-mode", action=argparse.BooleanOptionalAction, help="Enable FCX mode")
    parser.add_argument("--show-fid-values", action=argparse.BooleanOptionalAction, help="Show FormID values")
    parser.add_argument("--stat-logging", action=argparse.BooleanOptionalAction, help="Enable statistical logging")
    parser.add_argument("--move-unsolved", action=argparse.BooleanOptionalAction, help="Move unsolved logs")
    parser.add_argument("--ini-path", type=Path, help="Path to the INI file")
    parser.add_argument("--scan-path", type=Path, help="Path to the scan directory")
    parser.add_argument("--mods-folder-path", type=Path, help="Path to the mods folder")
    parser.add_argument(
        "--simplify-logs", action=argparse.BooleanOptionalAction, help="Simplify the logs (Warning: May remove important information)"
    )

    args = parser.parse_args()

    # Handle command line arguments
    if isinstance(args.fcx_mode, bool) and args.fcx_mode != classic_settings(bool, "FCX Mode"):
        yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.FCX Mode", args.fcx_mode)

    if isinstance(args.show_fid_values, bool) and args.show_fid_values != classic_settings(bool, "Show FormID Values"):
        yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Show FormID Values", args.show_fid_values)

    if isinstance(args.move_unsolved, bool) and args.move_unsolved != classic_settings(bool, "Move Unsolved Logs"):
        yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Move Unsolved Logs", args.move_unsolved)

    if (
        isinstance(args.ini_path, Path)
        and args.ini_path.resolve().is_dir()
        and str(args.ini_path) != classic_settings(str, "INI Folder Path")
    ):
        yaml_settings(str, YAML.Settings, "CLASSIC_Settings.INI Folder Path", str(args.ini_path.resolve()))

    if (
        isinstance(args.scan_path, Path)
        and args.scan_path.resolve().is_dir()
        and str(args.scan_path) != classic_settings(str, "SCAN Custom Path")
    ):
        from ClassicLib.ScanLog.Util import is_valid_custom_scan_path

        if is_valid_custom_scan_path(args.scan_path):
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", str(args.scan_path.resolve()))
        else:
            msg_error(
                "WARNING: The specified scan path cannot be used as a custom scan directory.\n"
                "The 'Crash Logs' folder and its subfolders are managed by CLASSIC and cannot be set as custom scan directories.\n"
                "Resetting custom scan path."
            )
            yaml_settings(str, YAML.Settings, "CLASSIC_Settings.SCAN Custom Path", "")

    if (
        isinstance(args.mods_folder_path, Path)
        and args.mods_folder_path.resolve().is_dir()
        and str(args.mods_folder_path) != classic_settings(str, "MODS Folder Path")
    ):
        yaml_settings(str, YAML.Settings, "CLASSIC_Settings.MODS Folder Path", str(args.mods_folder_path.resolve()))

    if isinstance(args.simplify_logs, bool) and args.simplify_logs != classic_settings(bool, "Simplify Logs"):
        yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Simplify Logs", args.simplify_logs)

    crashlogs_scan()
    # Ensure all output is flushed before pause
    sys.stdout.flush()
    sys.stderr.flush()
    os.system("pause")
