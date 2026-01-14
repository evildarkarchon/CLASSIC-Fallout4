"""Crash log scanning executor for business logic operations.

This module contains the main executor class that orchestrates crash log scanning
operations. It provides a clean interface between CLI/GUI components and the
underlying scanning infrastructure.
"""

import asyncio
import random
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ClassicLib import GlobalRegistry, MessageTarget, msg_info, msg_progress_context
from ClassicLib.AsyncBridge import create_sync_wrapper
from ClassicLib.Constants import DB_PATHS, YAML
from ClassicLib.Logger import logger
from ClassicLib.MessageHandler.progress.context import ProgressContext
from ClassicLib.ScanLog.models import ScanConfig, ScanResult, ScanStatistics
from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo
from ClassicLib.ScanLog.Util import crashlogs_get_files
from ClassicLib.YamlSettings import classic_settings, yaml_settings


class ScanLogsExecutor:
    """Orchestrates crash log scanning operations for CLI usage.

    Provides the main business logic for scanning crash logs, separated
    from CLI-specific code for better testability and modularity.

    Attributes:
        config: ScanConfig object containing scan parameters and settings.
        crashlog_list: List of Path objects to crash log files to scan.
        yamldata: ClassicScanLogsInfo with loaded YAML data (lazily loaded).
        statistics: ScanStatistics tracking scan progress and results.

    Example:
        >>> executor = ScanLogsExecutor()
        >>> result = executor.scan_sync()
        >>> print(f"Scanned {result.statistics.processed} files")

    """

    def __init__(self, config: ScanConfig | None = None, eager_load: bool = False) -> None:
        """Initialize the crash log scanner.

        Args:
            config: Optional ScanConfig with scan-specific settings.
                If not provided, configuration is loaded from defaults.
            eager_load: If True, eagerly loads YAML data and warms up
                the database pool. Increases initialization time but
                eliminates freeze on first scan. Default is False.

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
        """Proactively warm up resources to eliminate freeze on first scan.

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
            from ClassicLib.Database import DatabasePoolManager

            pool_manager = DatabasePoolManager()
            await pool_manager.get_pool()
            logger.debug("Warmed up database connection pool")

        logger.info("Resource warm-up complete - scanning will be smooth")

    @staticmethod
    def _load_config_from_settings() -> ScanConfig:
        """Load and returns the scan configuration from application settings.

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
        """Execute the crash log scanning process asynchronously.

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

        # Initialize resources
        await self._initialize_scan_resources()

        # Create result object
        result = ScanResult(stats=self.statistics)

        msg_info("SCANNING CRASH LOGS, PLEASE WAIT...", target=MessageTarget.CONSOLE)

        # Ensure yamldata is initialized
        if self.yamldata is None:
            msg = "YAML data not initialized after resource setup"
            raise RuntimeError(msg)

        # Create async orchestrator with context manager for proper resource management
        async with OrchestratorCore(
            self.yamldata, self.config.fcx_mode, self.config.show_formid_values, self.config.formid_db_exists, self.config.remove_list
        ) as orchestrator:
            # Run FCX checks if enabled
            if self.config.fcx_mode:
                await orchestrator.fcx_handler.check_fcx_mode_async()

            # Process crash logs with progress tracking
            await self._process_crashlogs_with_progress(orchestrator, result)

        # Update final scan time
        result.scan_time = self.statistics.get_scan_duration()

        # Log completion
        logger.info(f"Completed crash log scan execution in {result.scan_time:.2f} seconds")

        return result

    async def _initialize_scan_resources(self) -> None:
        """Initialize scan resources including YAML data and game paths.

        This method ensures that all necessary resources are loaded before
        starting the scan process.

        Raises:
            RuntimeError: If resource initialization fails.

        """
        # Initialize yamldata here using async factory (no AsyncBridge overhead)
        # If eager_load was set, warm_up() should have been called already
        if self.yamldata is None:
            if self._eager_load:
                logger.warning("Eager load requested but warm_up() was not called - loading now")
            self.yamldata = await ClassicScanLogsInfo.create_async()
            logger.debug("Initialized ClassicScanLogsInfo (async, no blocking)")

        # Ensure game paths are generated before creating orchestrator
        # This is required for FCX mode checks which need Game_Folder_Scripts and other inferred paths
        from ClassicLib.GamePath import game_generate_paths_async, game_path_find_async

        await game_path_find_async()
        await game_generate_paths_async()

    async def _process_crashlogs_with_progress(self, orchestrator: OrchestratorCore, result: ScanResult) -> None:
        """Process all crash logs with progress tracking and concurrency control.

        Args:
            orchestrator: The orchestrator instance for processing logs.
            result: The scan result object to update with processing outcomes.

        Raises:
            asyncio.CancelledError: If the operation is cancelled by the user.

        """
        # Use semaphore to limit concurrent operations
        max_concurrent = min(self.config.max_concurrent, len(self.crashlog_list))
        total_logs = len(self.crashlog_list)
        log_iter = iter(self.crashlog_list)
        active_tasks: set[asyncio.Task[Any]] = set()

        with msg_progress_context("Processing Crash Logs", total_logs) as progress:
            # Start initial batch of tasks
            for _ in range(max_concurrent):
                try:
                    log = next(log_iter)
                    task = asyncio.create_task(self._process_crashlog_async(log, orchestrator))
                    active_tasks.add(task)
                except StopIteration:
                    break

            # Process tasks as they complete, creating new ones on-demand
            while active_tasks:
                # Check for cancellation
                if progress.was_cancelled():
                    logger.info("User cancelled scan operation - stopping immediately")
                    for task in active_tasks:
                        task.cancel()
                    break

                # Wait for next task to complete with short timeout for responsiveness
                done, active_tasks = await asyncio.wait(
                    active_tasks,
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=0.1,  # Check cancellation every 100ms
                )

                # Process completed tasks
                for task in done:
                    await self._handle_task_result(task, result, progress, log_iter, active_tasks, orchestrator)

            # Wait for any remaining tasks to finish (already cancelled if user cancelled)
            if active_tasks:
                logger.info(f"Waiting for {len(active_tasks)} tasks to complete...")
                await asyncio.gather(*active_tasks, return_exceptions=True)

    async def _handle_task_result(
        self,
        task: asyncio.Task[Any],
        result: ScanResult,
        progress: ProgressContext,
        log_iter: Iterator[Path],
        active_tasks: set[asyncio.Task[Any]],
        orchestrator: OrchestratorCore,
    ) -> None:
        """Handle the result of a completed task.

        Args:
            task: The completed asyncio task.
            result: The scan result object to update.
            progress: The progress context for UI updates.
            log_iter: Iterator over remaining crash logs.
            active_tasks: Set of currently active tasks.
            orchestrator: The orchestrator instance for processing new logs.

        Raises:
            None: All exceptions are caught and logged.

        """
        try:
            task_result = task.result()

            # Unpack result
            crashlog_file, autoscan_report, trigger_scan_failed, local_stats = task_result

            # Update statistics
            if isinstance(local_stats, Counter):
                self.statistics.update_from_counter(local_stats)  # pyright: ignore[reportUnknownArgumentType]

            # Add to processed files
            result.add_processed_file(crashlog_file)

            # Write report
            from ClassicLib.ScanLog.ScanLogsUtils import write_report_to_file_async

            await write_report_to_file_async(crashlog_file, autoscan_report, trigger_scan_failed, self)

            # Track failed scans
            if trigger_scan_failed:
                result.add_failed_log(crashlog_file.name)

            progress.update(1, f"Processed: {crashlog_file.name}")

            # Start next task if not cancelled
            if not progress.was_cancelled():
                try:
                    log = next(log_iter)
                    new_task = asyncio.create_task(self._process_crashlog_async(log, orchestrator))
                    active_tasks.add(new_task)
                except StopIteration:
                    pass  # No more logs to process

        except asyncio.CancelledError:
            logger.debug("Task cancelled by user")

        except (RuntimeError, ImportError, OSError) as e:
            error_msg = f"Error processing crash log: {e}"
            logger.error(error_msg)
            result.add_error_message(error_msg)
            self.statistics.increment_failed()
            progress.update(1, "Failed: Error during processing")

    @staticmethod
    async def _process_crashlog_async(crashlog_file: Path, orchestrator: OrchestratorCore) -> tuple[Path, list[str], bool, Counter[str]]:
        """Process a crash log with async database operations for FormID lookups.

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
        """Generate a summary message for the scan results.

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
        if self.yamldata and hasattr(self.yamldata, "classic_game_hints") and self.yamldata.classic_game_hints:
            summary_lines.append(random.choice(self.yamldata.classic_game_hints))

        # Add game-specific text
        if GlobalRegistry.get_game() == "Fallout4":
            summary_lines.extend([
                "",
                "-----",
                "",
            ])
            if self.yamldata and hasattr(self.yamldata, "autoscan_text"):
                summary_lines.append(self.yamldata.autoscan_text)

        return "\n".join(summary_lines)

    def scan_sync(self) -> ScanResult:
        """Execute a synchronous scan - Phase 2 Context-Aware.

        Works in GUI mode (Qt workers), errors in CLI mode.
        For CLI/TUI, use: await executor.scan() or await executor.execute_scan()

        NOTE: Wrapper is created on each call for instance method binding.

        Returns:
            ScanResult: The result of the executed scan.

        Raises:
            RuntimeError: If called in CLI/TUI mode (use async methods)

        """
        # Create wrapper per call for proper instance method binding
        wrapper = create_sync_wrapper(self.execute_scan, strict=True)
        return wrapper()


# Backward compatibility alias
ClassicScanLogs = ScanLogsExecutor
