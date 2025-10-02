"""
Crash log scanning executor for business logic operations.

This module contains the main executor class that orchestrates crash log scanning
operations. It provides a clean interface between CLI/GUI components and the
underlying scanning infrastructure.
"""

import asyncio
import random
from collections import Counter
from pathlib import Path

from ClassicLib import GlobalRegistry, MessageTarget, msg_info, msg_progress_context
from ClassicLib.AsyncBridge import run_async
from ClassicLib.Constants import DB_PATHS, YAML
from ClassicLib.Logger import logger
from ClassicLib.ScanLog.models import ScanConfig, ScanResult, ScanStatistics
from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo
from ClassicLib.ScanLog.Util import crashlogs_get_files
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


class ScanLogsExecutor:
    """
    Orchestrates crash log scanning operations for CLI usage.

    This class provides the main business logic for scanning crash logs,
    separated from CLI-specific code for better testability and modularity.
    """

    def __init__(self, config: ScanConfig | None = None) -> None:
        """
        Initializes the crash log scan process by setting up configuration, retrieving crash log files,
        and applying settings for crash log reformatting. It also initializes database availability
        and statistics tracking.

        Args:
            config (ScanConfig | None): Optional ScanConfig object containing scan-specific settings.
                If not provided, the configuration will be loaded from default settings.

        Raises:
            None
        """
        self.config = config or self._load_config_from_settings()

        # Get crash log files
        self.crashlog_list: list[Path] = crashlogs_get_files()

        # Load settings if not provided in config
        if not self.config.remove_list:
            self.config.remove_list = yaml_settings(tuple, YAML.Main, "exclude_log_records") or ("",)

        # Reformatting now happens inline during processing for zero-delay startup
        logger.debug("Reformatting will happen inline during log processing")

        # Defer yamldata initialization to execute_scan for faster startup
        self.yamldata: ClassicScanLogsInfo | None = None

        # Set up database availability
        self.config.formid_db_exists = any(db.is_file() for db in DB_PATHS)

        # Initialize statistics
        self.statistics = ScanStatistics()
        self.statistics.total_files = len(self.crashlog_list)

        logger.debug(f"Initiated crash log scan for {len(self.crashlog_list)} files")

    @staticmethod
    def _load_config_from_settings() -> ScanConfig:
        """
        Loads and returns the scan configuration from application settings.

        This static method retrieves various settings required for scan configuration using
        classic settings function calls. The retrieved values are then used to
        construct and return a `ScanConfig` object.

        Returns:
            ScanConfig: An object containing the scan configuration settings.
        """
        return ScanConfig(
            fcx_mode=classic_settings(bool, "FCX Mode"),
            show_formid_values=classic_settings(bool, "Show FormID Values"),
            move_unsolved_logs=classic_settings(bool, "Move Unsolved Logs"),
            simplify_logs=classic_settings(bool, "Simplify Logs"),
        )

    async def execute_scan(self) -> ScanResult:
        """
        Executes the crash log scanning process asynchronously.

        This method handles the entire lifecycle of crash log scanning, including setup,
        processing, and cleanup. It creates an `OrchestratorCore` to manage resources,
        implements concurrency limitations for processing crash logs, and updates
        statistics and progress tracking during execution. It also generates reports
        for each processed crash log and handles errors that occur during the process.

        Crash logs are now read directly from disk using native Python I/O for optimal
        performance on small files (performance analysis showed this is faster than
        caching or async I/O due to lower overhead).

        Returns:
            ScanResult: An object containing results of the scan, including processed
                logs, failed logs, error messages, and scan duration.

        Raises:
            RuntimeError: If an error occurs during the execution of the process.
            ImportError: If an import fails during the operation.
            OSError: If a file system-related error is encountered during scanning.
            asyncio.CancelledError: If the asynchronous task is cancelled during execution.

        """
        logger.info("Starting crash log scan execution")

        # Initialize yamldata here using async factory (no AsyncBridge overhead)
        if self.yamldata is None:
            self.yamldata = await ClassicScanLogsInfo.create_async()
            logger.debug("Initialized ClassicScanLogsInfo (async, no blocking)")

        # Create result object
        result = ScanResult(stats=self.statistics)

        msg_info("SCANNING CRASH LOGS, PLEASE WAIT...", target=MessageTarget.CLI_ONLY)

        # Create async orchestrator with context manager for proper resource management
        # Reformatting happens inline during processing - no blocking preload
        async with OrchestratorCore(
            self.yamldata, self.config.fcx_mode, self.config.show_formid_values, self.config.formid_db_exists, self.config.remove_list
        ) as orchestrator:
            # Run FCX checks if enabled
            if self.config.fcx_mode:
                orchestrator.fcx_handler.check_fcx_mode()

            # Use semaphore to limit concurrent operations
            max_concurrent = min(self.config.max_concurrent, len(self.crashlog_list))
            semaphore = asyncio.Semaphore(max_concurrent)

            async def process_with_limit(log_path: Path) -> tuple[Path, list[str], bool, Counter[str]]:
                """
                Processes a crash log file asynchronously while respecting a semaphore limit.

                Args:
                    log_path (Path): Path to the log file to be processed.

                Returns:
                    tuple[Path, list[str], bool, Counter[str]]: A tuple containing the log path,
                    list of strings (e.g., messages or findings), a boolean flag indicating a status
                    or result, and a counter of occurrences for specific elements in the log.
                """
                async with semaphore:
                    return await self._process_crashlog_async(log_path, orchestrator)

            # Create tasks for all crash logs
            tasks = [asyncio.create_task(process_with_limit(log)) for log in self.crashlog_list]

            # Process with progress tracking
            total_logs = len(self.crashlog_list)
            completed = 0

            with msg_progress_context("Processing Crash Logs", total_logs) as progress:
                # Process tasks as they complete for real-time progress updates
                for task in asyncio.as_completed(tasks):
                    try:
                        task_result = await task

                        # Unpack result - the first element is always the log file path
                        crashlog_file, autoscan_report, trigger_scan_failed, local_stats = task_result

                        # Update statistics
                        if isinstance(local_stats, Counter):
                            self.statistics.update_from_counter(local_stats)

                        # Add to processed files
                        result.add_processed_file(crashlog_file)

                        # Write report using utils function
                        from ClassicLib.ScanLog.ScanLogsUtils import write_report_to_file_async

                        await write_report_to_file_async(crashlog_file, autoscan_report, trigger_scan_failed, self)

                        # Track failed scans
                        if trigger_scan_failed:
                            result.add_failed_log(crashlog_file.name)

                        completed += 1
                        progress.update(1, f"Processed: {crashlog_file.name}")

                        # Yield to allow Qt signals to be processed
                        await asyncio.sleep(0)

                    except (RuntimeError, ImportError, OSError, asyncio.CancelledError) as e:
                        # Handle specific exceptions that can occur during async processing
                        error_msg = f"Error processing crash log: {e}"
                        logger.error(error_msg)
                        result.add_error_message(error_msg)
                        self.statistics.increment_failed()

                        # Update progress even on error
                        progress.update(1, "Failed: Error during processing")

                        # Yield even on error
                        await asyncio.sleep(0)

        # Update final scan time
        result.scan_time = self.statistics.get_scan_duration()

        logger.info(f"Completed crash log scan execution in {result.scan_time:.2f} seconds")
        return result

    @staticmethod
    async def _process_crashlog_async(
            crashlog_file: Path, orchestrator: OrchestratorCore
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
            # OrchestratorCore uses the base method name
            return await orchestrator.process_crash_log(crashlog_file)
        except (RuntimeError, ImportError, OSError) as e:
            logger.error(f"Error processing crash log {crashlog_file}: {e}")
            # Return failure result
            return crashlog_file, [f"Error processing log: {e}"], True, Counter(failed=1)

    def generate_summary(self, result: ScanResult) -> str:
        """
        Generate a summary message for the scan results.

        Args:
            result: The scan result to summarize

        Returns:
            Formatted summary string
        """
        if result.stats.scanned == 0 and result.stats.incomplete == 0:
            return "CLASSIC found no crash logs to scan or the scan failed.\n    There are no statistics to show (at this time)."

        # Build success message
        summary_lines = [
            "SCAN COMPLETE! (IT MIGHT TAKE SEVERAL SECONDS FOR SCAN RESULTS TO APPEAR)",
            "SCAN RESULTS ARE AVAILABLE IN FILES NAMED crash-date-and-time-AUTOSCAN.md",
            "",
            f"Scanned all available logs in {result.scan_time:.2f} seconds.",
            f"Number of Scanned Logs (No Autoscan Errors): {result.stats.scanned}",
            f"Number of Incomplete Logs (No Plugins List): {result.stats.incomplete}",
            f"Number of Failed Logs (Autoscan Can't Scan): {result.stats.failed}",
            "-----",
        ]

        # Add random hint
        if hasattr(self.yamldata, "classic_game_hints") and self.yamldata.classic_game_hints:
            summary_lines.append(random.choice(self.yamldata.classic_game_hints))

        # Add game-specific text
        if GlobalRegistry.get_game() == "Fallout4":
            summary_lines.extend([
                "",
                "-----",
                "",
            ])
            if hasattr(self.yamldata, "autoscan_text"):
                summary_lines.append(self.yamldata.autoscan_text)

        return "\n".join(summary_lines)

    def scan_sync(self) -> ScanResult:
        """
        Executes a synchronous scan by running the associated asynchronous scan
        function and collecting the results.

        Returns:
            ScanResult: The result of the executed scan.
        """
        return run_async(self.execute_scan())


# Backward compatibility alias
ClassicScanLogs = ScanLogsExecutor
