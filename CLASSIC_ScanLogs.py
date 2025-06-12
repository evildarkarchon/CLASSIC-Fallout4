"""
Refactored CLASSIC_ScanLogs module using the new modular architecture.

This module maintains backward compatibility while delegating to the new
modular components for crash log scanning functionality.
"""

import os
import random
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

from CLASSIC_Main import initialize
from ClassicLib import GlobalRegistry, msg_error, msg_info, msg_progress_context, MessageTarget
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
        self.remove_list: tuple[str] | tuple[Literal[""]] = yaml_settings(tuple[str], YAML.Main, "exclude_log_records") or ("",)
        crashlogs_reformat(self.crashlog_list, self.remove_list)

        # Initialize configuration
        self.yamldata = ClassicScanLogsInfo()
        self.fcx_mode: bool | None = classic_settings(bool, "FCX Mode")
        self.show_formid_values: bool | None = classic_settings(bool, "Show FormID Values")
        self.formid_db_exists: bool = any(db.is_file() for db in DB_PATHS)
        self.move_unsolved_logs: bool | None = classic_settings(bool, "Move Unsolved Logs")

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
    backup_path: Path = cast("Path", GlobalRegistry.get_local_dir()) / "CLASSIC Backup/Unsolved Logs"
    backup_path.mkdir(parents=True, exist_ok=True)
    autoscan_filepath: Path = crashlog_file.with_name(f"{crashlog_file.stem}-AUTOSCAN.md")
    backup_filepath: Path = backup_path / autoscan_filepath.name
    if crashlog_file.exists():
        crashlog_file.rename(backup_filepath)
    else:
        autoscan_filepath.rename(backup_path / autoscan_filepath.name)


def crashlogs_scan() -> None:
    """
    Main entry point for crash log scanning.

    Scans all crash logs using multiple threads for efficient processing.
    """
    scanner = ClassicScanLogs()
    FCXModeHandler.reset_fcx_checks()  # Reset FCX checks for new scan session

    yamldata: ClassicScanLogsInfo = scanner.yamldata
    scan_failed_list: list = []

    # Determine number of worker threads
    max_workers: int = min(os.cpu_count() or 4, 8)  # Default to 4, max of 8

    # Process crash logs in parallel with progress tracking
    total_logs = len(scanner.crashlog_list)
    with msg_progress_context("Processing Crash Logs", total_logs) as progress:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures: list[Future[tuple[Path, list[str], bool, Counter[str]]]] = [
                executor.submit(scanner.process_crashlog, crashlog_file) for crashlog_file in scanner.crashlog_list
            ]

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
    initialize()

    import argparse

    parser = argparse.ArgumentParser(description="Command-line arguments for CLASSIC's Command Line Interface")

    parser.add_argument("--fcx-mode", action="store_true", help="Enable FCX mode")
    parser.add_argument("--show-fid-values", action="store_true", help="Show FormID values")
    parser.add_argument("--stat-logging", action="store_true", help="Enable statistical logging")
    parser.add_argument("--move-unsolved", action="store_true", help="Move unsolved logs")
    parser.add_argument("--ini-path", type=Path, help="Path to the INI file")
    parser.add_argument("--scan-path", type=Path, help="Path to the scan directory")
    parser.add_argument("--mods-folder-path", type=Path, help="Path to the mods folder")
    parser.add_argument("--simplify-logs", action="store_true", help="Simplify the logs (Warning: May remove important information)")

    args = parser.parse_args()

    # Handle command line arguments
    if isinstance(args.fcx_mode, bool) and args.fcx_mode != classic_settings(bool, "FCX Mode"):
        yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.FCX Mode", args.fcx_mode)

    if isinstance(args.show_fid_values, bool) and args.show_fid_values != classic_settings(bool, "Show FormID Values"):
        yaml_settings(bool, YAML.Settings, "Show FormID Values", args.show_fid_values)

    if isinstance(args.move_unsolved, bool) and args.move_unsolved != classic_settings(bool, "Move Unsolved Logs"):
        yaml_settings(bool, YAML.Settings, "CLASSIC_Settings.Move Unsolved", args.move_unsolved)

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
    os.system("pause")