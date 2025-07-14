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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, cast

from CLASSIC_Main import initialize
from ClassicLib import GlobalRegistry, MessageTarget, msg_error, msg_info, msg_progress_context
from ClassicLib.Constants import DB_PATHS, YAML
from ClassicLib.Logger import logger
from ClassicLib.ScanLog import (
    FCXModeHandler,
    ScanOrchestrator,
    ThreadSafeLogCache,
    crashlogs_get_files,
    crashlogs_reformat,
)
from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings

if TYPE_CHECKING:
    from concurrent.futures._base import Future


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

        # Use async file I/O for better performance
        try:
            # noinspection PyUnresolvedReferences
            from ClassicLib.ScanLog.AsyncFileIO import crashlogs_reformat_with_async

            crashlogs_reformat_with_async(self.crashlog_list, self.remove_list)
            logger.debug("Used async file I/O for crash log reformatting")
        except ImportError:
            # Fallback to sync version if async dependencies are not available
            crashlogs_reformat(self.crashlog_list, self.remove_list)
            logger.debug("Used sync file I/O for crash log reformatting")

        # Initialize configuration
        self.yamldata = ClassicScanLogsInfo()
        self.fcx_mode: bool | None = classic_settings(bool, "FCX Mode")
        self.show_formid_values: bool | None = classic_settings(bool, "Show FormID Values")
        self.formid_db_exists: bool = any(db.is_file() for db in DB_PATHS)
        self.move_unsolved_logs: bool | None = classic_settings(bool, "Move Unsolved Logs")

        # Check if async operations should be used
        self.use_async_db: bool = self._check_async_db_availability()
        self.use_async_pipeline: bool = self._check_async_pipeline_availability()

        msg_info("SCANNING CRASH LOGS, PLEASE WAIT...", target=MessageTarget.CLI_ONLY)
        self.scan_start_time: float = time.perf_counter()

        # Initialize thread-safe log cache
        self.crashlogs = ThreadSafeLogCache(self.crashlog_list)

        # Initialize the orchestrator with all modules
        self.orchestrator = ScanOrchestrator(self.yamldata, self.crashlogs, self.fcx_mode, self.show_formid_values, self.formid_db_exists)

        # Statistics tracking
        self.crashlog_stats: Counter[str] = Counter(scanned=0, incomplete=0, failed=0)

        logger.debug(f"Initiated crash log scan for {len(self.crashlog_list)} files")

        # Run FCX checks if enabled
        if self.fcx_mode:
            self.orchestrator.fcx_handler.check_fcx_mode()

    def process_crashlog(self, crashlog_file: Path) -> tuple[Path, list[str], bool, Counter[str]]:
        """
        Process a single crash log file using the orchestrator.

        Args:
            crashlog_file: Path to the crash log file

        Returns:
            Tuple containing file path, report, failure status, and statistics
        """
        return self.orchestrator.process_crash_log(crashlog_file)

    def process_crashlog_with_async_db(self, crashlog_file: Path) -> tuple[Path, list[str], bool, Counter[str]]:
        """
        Process a crash log with async database operations for FormID lookups.

        This method uses async database operations when available, falling back
        to synchronous operations if async dependencies are not available.

        Args:
            crashlog_file: Path to the crash log file

        Returns:
            Tuple containing file path, report, failure status, and statistics
        """
        try:
            # Try async processing first (imports moved to function to avoid unused import warnings)
            return asyncio.run(self._process_crashlog_async(crashlog_file))
        except ImportError:
            # Fallback to sync processing
            logger.debug(f"Async database dependencies not available, using sync processing for {crashlog_file.name}")
            return self.orchestrator.process_crash_log(crashlog_file)

    async def _process_crashlog_async(self, crashlog_file: Path) -> tuple[Path, list[str], bool, Counter[str]]:
        """
        Async version of crash log processing with database operations.

        Args:
            crashlog_file: Path to the crash log file

        Returns:
            Tuple containing file path, report, failure status, and statistics
        """
        from ClassicLib.ScanLog.AsyncFormIDAnalyzer import AsyncFormIDAnalyzer
        from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool

        # Process most of the log synchronously (this is still fast)
        result = self.orchestrator.process_crash_log(crashlog_file)
        crashlog_path, autoscan_report, failure_status, stats = result

        # If we have FormIDs and database exists, enhance with async lookups
        if (
            hasattr(self.orchestrator, "_last_formids")
            and hasattr(self.orchestrator, "_last_plugins")
            and self.formid_db_exists
            and self.orchestrator.last_formids
        ):
            async with AsyncDatabasePool() as db_pool:
                # Create async FormID analyzer
                async_analyzer = AsyncFormIDAnalyzer(self.yamldata, self.show_formid_values or False, self.formid_db_exists, db_pool)

                # Find and replace FormID section in report
                new_report = []
                in_formid_section = False
                formid_section_start = -1

                for i, line in enumerate(autoscan_report):
                    if "FORM IDs" in line and "=" in line:
                        in_formid_section = True
                        formid_section_start = i
                        new_report.append(line)
                        break
                    new_report.append(line)

                if in_formid_section and formid_section_start >= 0:
                    # Add async FormID analysis
                    formid_section: list[str] = []
                    await async_analyzer.formid_match_async(self.orchestrator.last_formids, self.orchestrator.last_plugins, formid_section)
                    new_report.extend(formid_section)

                    # Add the rest of the report after FormID section
                    skip_until_next_section = True
                    for line in autoscan_report[formid_section_start + 1 :]:
                        if skip_until_next_section:
                            # Skip until we find the next major section
                            if (line.startswith("=") and "RECORDS" in line) or line.startswith("\n---"):
                                skip_until_next_section = False
                                new_report.append(line)
                        else:
                            new_report.append(line)

                    return crashlog_path, new_report, failure_status, stats

        return result

    def _check_async_db_availability(self) -> bool:
        """
        Check if async database operations are available and beneficial.

        Returns:
            bool: True if async DB operations should be used
        """
        # Only use async DB if FormID databases exist and we're showing FormID values
        if not (self.formid_db_exists and self.show_formid_values):
            return False

        try:
            import aiosqlite  # noqa: F401

            from ClassicLib.ScanLog.AsyncFormIDAnalyzer import AsyncFormIDAnalyzer  # noqa: F401
            from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool  # noqa: F401
        except ImportError:
            logger.debug("Async database dependencies not available")
            return False
        else:
            logger.debug("Async database operations available")
            return True

    def _check_async_pipeline_availability(self) -> bool:
        """
        Check if the full async pipeline is available and should be used.

        Returns:
            bool: True if async pipeline should be used
        """
        # Check for async pipeline setting (could be added to settings later)
        use_async_pipeline = classic_settings(bool, "Use Async Pipeline")
        if use_async_pipeline is False:
            logger.debug("Async pipeline disabled in settings")
            return False

        # Only use async pipeline if we have a reasonable number of logs
        if len(self.crashlog_list) < 3:
            logger.debug("Too few crash logs for async pipeline benefit")
            return False

        try:
            import aiofiles  # noqa: F401

            from ClassicLib.ScanLog.AsyncPipeline import AsyncCrashLogPipeline  # noqa: F401
            from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool  # noqa: F401
        except ImportError as e:
            logger.debug(f"Async pipeline dependencies not available: {e}")
            return False
        else:
            logger.debug("Async pipeline operations available")
            return True


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

    Automatically chooses between async pipeline and threaded processing
    based on availability and log count.
    """
    scanner = ClassicScanLogs()
    FCXModeHandler.reset_fcx_checks()  # Reset FCX checks for new scan session

    # Check if async pipeline should be used
    if scanner.use_async_pipeline:
        asyncio.run(crashlogs_scan_async(scanner))
    else:
        crashlogs_scan_threaded(scanner)


async def crashlogs_scan_async(scanner: ClassicScanLogs) -> None:
    """
    Async crash log scanning using the full async pipeline.

    Args:
        scanner: ClassicScanLogs instance with configuration
    """
    from ClassicLib.ScanLog.AsyncPipeline import AsyncPerformanceMonitor, run_async_crash_log_scan

    logger.info("Using async pipeline for crash log processing")
    yamldata: ClassicScanLogsInfo = scanner.yamldata
    scan_failed_list: list = []

    try:
        # Run the full async pipeline
        results, async_stats = await run_async_crash_log_scan(
            scanner.crashlog_list,
            scanner.remove_list,
            scanner.yamldata,
            scanner.fcx_mode,
            scanner.show_formid_values,
            scanner.formid_db_exists,
        )

        # Process results and update statistics
        for crashlog_file, _autoscan_report, trigger_scan_failed, local_stats in results:
            # Update statistics
            for key, value in local_stats.items():
                scanner.crashlog_stats[key] += value

            # Track failed scans (reports are already written by async pipeline)
            if trigger_scan_failed:
                scan_failed_list.append(crashlog_file.name)

                # Handle unsolved logs if needed
                if scanner.move_unsolved_logs:
                    move_unsolved_logs(crashlog_file)

        # Log performance summary
        comparison = AsyncPerformanceMonitor.compare_performance(async_stats, 0, len(scanner.crashlog_list))
        AsyncPerformanceMonitor.log_performance_summary(comparison)

    except (ImportError, RuntimeError, OSError) as e:
        logger.error(f"Async pipeline failed, falling back to threaded processing: {e}")
        crashlogs_scan_threaded(scanner)
        return

    # Complete with standard error checking and summary
    _complete_scan_with_summary(scanner, scan_failed_list, yamldata)


def crashlogs_scan_threaded(scanner: ClassicScanLogs) -> None:
    """
    Traditional threaded crash log scanning.

    Args:
        scanner: ClassicScanLogs instance with configuration
    """
    logger.info("Using threaded processing for crash log scanning")
    yamldata: ClassicScanLogsInfo = scanner.yamldata
    scan_failed_list: list = []

    max_workers: int = 4

    # Process crash logs in parallel with progress tracking
    total_logs = len(scanner.crashlog_list)
    with msg_progress_context("Processing Crash Logs", total_logs) as progress, ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks - use async DB operations if available
        futures: list[Future[tuple[Path, list[str], bool, Counter[str]]]]
        if scanner.use_async_db:
            logger.debug("Using async database operations for FormID lookups")
            futures = [executor.submit(scanner.process_crashlog_with_async_db, crashlog_file) for crashlog_file in scanner.crashlog_list]
        else:
            logger.debug("Using synchronous database operations")
            futures = [executor.submit(scanner.process_crashlog, crashlog_file) for crashlog_file in scanner.crashlog_list]

        # Process results as they complete
        for future in as_completed(futures):
            try:
                crashlog_file, autoscan_report, trigger_scan_failed, local_stats = future.result()

                # Update statistics
                for key, value in local_stats.items():
                    scanner.crashlog_stats[key] += value

                # Write report
                write_report_to_file(crashlog_file, autoscan_report, trigger_scan_failed, scanner)

                # Track failed scans
                if trigger_scan_failed:
                    scan_failed_list.append(crashlog_file.name)

                # Update progress
                progress.update(1, f"Processed {crashlog_file.name}")

            except Exception as e:  # noqa: BLE001
                logger.debug(f"Error processing crash log: {e!s}")
                msg_error(f"Failed to process crash log: {e!s}")
                scanner.crashlog_stats["failed"] += 1
                progress.update(1)

    # Complete with standard error checking and summary
    _complete_scan_with_summary(scanner, scan_failed_list, yamldata)


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

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)

    initialize()

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
    parser.add_argument("--disable-progress", action=argparse.BooleanOptionalAction, help="Disable progress bars in CLI mode")

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

    if isinstance(args.disable_progress, bool) and args.disable_progress != classic_settings(bool, "Disable CLI Progress"):
        yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Disable CLI Progress", args.disable_progress)

    crashlogs_scan()
    # Ensure all output is flushed before pause
    sys.stdout.flush()
    sys.stderr.flush()
    os.system("pause")
