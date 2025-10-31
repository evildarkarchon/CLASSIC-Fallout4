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
from ClassicLib.AsyncBridge import create_sync_wrapper
from ClassicLib.Constants import DB_PATHS, YAML
from ClassicLib.Logger import logger
from ClassicLib.ScanLog.models import ScanConfig, ScanResult, ScanStatistics
from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo
from ClassicLib.ScanLog.Util import crashlogs_get_files
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


class ScanLogsExecutor:
    """
    Orchestrates crash log scanning operations for CLI usage.

    This class provides the main business logic for scanning crash logs,
    separated from CLI-specific code for better testability and modularity.
    """

    def __init__(self, config: ScanConfig | None = None, eager_load: bool = False) -> None:
        """
        Initializes the crash log scan process by setting up configuration, retrieving crash log files,
        and applying settings for crash log reformatting. It also initializes database availability
        and statistics tracking.

        Args:
            config (ScanConfig | None): Optional ScanConfig object containing scan-specific settings.
                If not provided, the configuration will be loaded from default settings.
            eager_load (bool): If True, eagerly loads YAML data and warms up database pool.
                This eliminates the freeze on first scan but increases initialization time.
                Default False for backward compatibility.

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

        # Defer yamldata initialization to execute_scan for faster startup (unless eager_load is True)
        self.yamldata: ClassicScanLogsInfo | None = None
        self._eager_load = eager_load

        # Set up database availability
        self.config.formid_db_exists = any(db.is_file() for db in DB_PATHS)

        # Initialize statistics
        self.statistics = ScanStatistics()
        self.statistics.total_files = len(self.crashlog_list)

        logger.debug(f"Initiated crash log scan for {len(self.crashlog_list)} files")

    async def warm_up(self) -> None:
        """
        Proactively warm up resources to eliminate freeze on first scan.

        This method should be called after initialization to pre-load YAML data
        and warm up the database connection pool. This trades initialization time
        for smooth scanning performance without UI freezes.

        Safe to call multiple times - will skip if already warmed up.
        """
        if self.yamldata is not None:
            logger.debug("Resources already warmed up, skipping")
            return

        logger.info("Warming up scan resources...")

        # Pre-load YAML data
        self.yamldata = await ClassicScanLogsInfo.create_async()
        logger.debug("Pre-loaded ClassicScanLogsInfo")

        # Warm up database pool if database exists
        if self.config.formid_db_exists:
            from ClassicLib.ScanLog.AsyncUtil import DatabasePoolManager
            pool_manager = DatabasePoolManager()
            await pool_manager.get_pool()
            logger.debug("Warmed up database connection pool")

        logger.info("Resource warm-up complete - scanning will be smooth")

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
        import time

        logger.info("Starting crash log scan execution")

        # Initialize timing accumulators for profiling
        total_write_time = 0.0
        total_processing_time = 0.0

        # Initialize yamldata here using async factory (no AsyncBridge overhead)
        # If eager_load was set, warm_up() should have been called already
        if self.yamldata is None:
            if self._eager_load:
                logger.warning("Eager load requested but warm_up() was not called - loading now")
            self.yamldata = await ClassicScanLogsInfo.create_async()
            logger.debug("Initialized ClassicScanLogsInfo (async, no blocking)")

        # Create result object
        result = ScanResult(stats=self.statistics)

        msg_info("SCANNING CRASH LOGS, PLEASE WAIT...", target=MessageTarget.CLI_ONLY)

        # Ensure game paths are generated before creating orchestrator
        # This is required for FCX mode checks which need Game_Folder_Scripts and other inferred paths
        from ClassicLib.GamePath import game_generate_paths, game_path_find
        game_path_find()
        game_generate_paths()

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

                True async - Rust methods return coroutines, no blocking!

                Args:
                    log_path (Path): Path to the log file to be processed.

                Returns:
                    tuple[Path, list[str], bool, Counter[str]]: A tuple containing the log path,
                    list of strings (e.g., messages or findings), a boolean flag indicating a status
                    or result, and a counter of occurrences for specific elements in the log.
                """
                async with semaphore:
                    # Direct async call - Rust returns coroutines, no thread pool needed!
                    # Multiple operations run concurrently via Python's event loop
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
                        # Time the task completion (processing time)
                        task_start = time.perf_counter()
                        task_result = await task
                        task_time = time.perf_counter() - task_start
                        total_processing_time += task_time

                        # Unpack result - the first element is always the log file path
                        crashlog_file, autoscan_report, trigger_scan_failed, local_stats = task_result

                        # Update statistics
                        if isinstance(local_stats, Counter):
                            self.statistics.update_from_counter(local_stats)

                        # Add to processed files
                        result.add_processed_file(crashlog_file)

                        # Write report using utils function
                        from ClassicLib.ScanLog.ScanLogsUtils import write_report_to_file_async

                        write_start = time.perf_counter()
                        await write_report_to_file_async(crashlog_file, autoscan_report, trigger_scan_failed, self)
                        write_time = time.perf_counter() - write_start
                        total_write_time += write_time

                        # Track failed scans
                        if trigger_scan_failed:
                            result.add_failed_log(crashlog_file.name)

                        completed += 1
                        progress.update(1, f"Processed: {crashlog_file.name}")

                    except (RuntimeError, ImportError, OSError, asyncio.CancelledError) as e:
                        # Handle specific exceptions that can occur during async processing
                        error_msg = f"Error processing crash log: {e}"
                        logger.error(error_msg)
                        result.add_error_message(error_msg)
                        self.statistics.increment_failed()

                        # Update progress even on error
                        progress.update(1, "Failed: Error during processing")

        # Update final scan time
        result.scan_time = self.statistics.get_scan_duration()

        # Log aggregate timing breakdown
        logger.info(f"Completed crash log scan execution in {result.scan_time:.2f} seconds")
        logger.debug(
            f"Aggregate timing breakdown: "
            f"total_processing={total_processing_time:.2f}s, "
            f"total_writing={total_write_time:.2f}s, "
            f"avg_per_log={(total_processing_time + total_write_time) / max(completed, 1):.3f}s"
        )

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
        Executes a synchronous scan - Phase 2 Context-Aware.

        Works in GUI mode (Qt workers), errors in CLI mode.
        For CLI/TUI, use: await executor.scan() or await executor.execute_scan()

        NOTE: Wrapper is created on each call for instance method binding.

        Returns:
            ScanResult: The result of the executed scan.

        Raises:
            RuntimeError: If called in CLI/TUI mode (use async methods)
        """
        # Create wrapper per call for proper instance method binding
        wrapper = create_sync_wrapper(self.execute_scan)
        return wrapper()


# Backward compatibility alias
ClassicScanLogs = ScanLogsExecutor
