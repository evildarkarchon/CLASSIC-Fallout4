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
from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo, ThreadSafeLogCache
from ClassicLib.ScanLog.Util import crashlogs_get_files, crashlogs_reformat
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


class ScanLogsExecutor:
    """
    Orchestrates crash log scanning operations for CLI usage.

    This class provides the main business logic for scanning crash logs,
    separated from CLI-specific code for better testability and modularity.
    """

    def __init__(self, config: ScanConfig | None = None) -> None:
        """
        Initialize the crash log scanner with configuration.

        Args:
            config: Scan configuration. If None, loads from settings.
        """
        self.config = config or self._load_config_from_settings()

        # Get crash log files
        self.crashlog_list: list[Path] = crashlogs_get_files()
        msg_info("REFORMATTING CRASH LOGS, PLEASE WAIT...", target=MessageTarget.CLI_ONLY)

        # Load settings if not provided in config
        if not self.config.remove_list:
            self.config.remove_list = yaml_settings(tuple, YAML.Main, "exclude_log_records") or ("",)

        # Optimized reformatting - only writes files that actually change
        crashlogs_reformat(self.crashlog_list, self.config.remove_list)
        logger.debug("Used optimized crash log reformatting")

        # Initialize configuration
        self.yamldata = ClassicScanLogsInfo()

        # Set up database availability
        self.config.formid_db_exists = any(db.is_file() for db in DB_PATHS)

        # Initialize statistics
        self.statistics = ScanStatistics()
        self.statistics.total_files = len(self.crashlog_list)

        # Initialize thread-safe log cache
        self.crashlogs = ThreadSafeLogCache(self.crashlog_list)

        logger.debug(f"Initiated crash log scan for {len(self.crashlog_list)} files")

    def _load_config_from_settings(self) -> ScanConfig:
        """Load scan configuration from YAML settings."""
        return ScanConfig(
            fcx_mode=classic_settings(bool, "FCX Mode"),
            show_formid_values=classic_settings(bool, "Show FormID Values"),
            move_unsolved_logs=classic_settings(bool, "Move Unsolved Logs"),
            simplify_logs=classic_settings(bool, "Simplify Logs"),
        )

    async def execute_scan(self) -> ScanResult:
        """
        Execute the crash log scanning operation.

        Returns:
            ScanResult containing scan outcomes and statistics
        """
        logger.info("Starting crash log scan execution")

        # Create result object
        result = ScanResult(stats=self.statistics)

        msg_info("SCANNING CRASH LOGS, PLEASE WAIT...", target=MessageTarget.CLI_ONLY)

        # Create async orchestrator with context manager for proper resource management
        async with OrchestratorCore(
            self.yamldata,
            self.crashlogs,
            self.config.fcx_mode,
            self.config.show_formid_values,
            self.config.formid_db_exists
        ) as orchestrator:
            # Run FCX checks if enabled
            if self.config.fcx_mode:
                orchestrator.fcx_handler.check_fcx_mode()

            # Use semaphore to limit concurrent operations
            max_concurrent = min(self.config.max_concurrent, len(self.crashlog_list))
            semaphore = asyncio.Semaphore(max_concurrent)

            async def process_with_limit(log_path: Path) -> tuple[Path, list[str], bool, Counter[str]]:
                """Process a single log with concurrency limiting."""
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

    async def _process_crashlog_async(
        self, crashlog_file: Path, orchestrator: OrchestratorCore
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
        if hasattr(self.yamldata, 'classic_game_hints') and self.yamldata.classic_game_hints:
            summary_lines.append(random.choice(self.yamldata.classic_game_hints))

        # Add game-specific text
        if GlobalRegistry.get_game() == "Fallout4":
            summary_lines.extend([
                "",
                "-----",
                "",
            ])
            if hasattr(self.yamldata, 'autoscan_text'):
                summary_lines.append(self.yamldata.autoscan_text)

        return "\n".join(summary_lines)

    def scan_sync(self) -> ScanResult:
        """
        Synchronous wrapper for execute_scan().

        Returns:
            ScanResult from the async scan operation
        """
        return run_async(self.execute_scan())


# Backward compatibility alias
ClassicScanLogs = ScanLogsExecutor
