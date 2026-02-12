"""Crash log scanning executor for business logic operations.

This module contains the main executor class that orchestrates crash log scanning
operations. It provides a clean interface between CLI/GUI components and the
underlying scanning infrastructure.

Phase 9: Uses Rust Orchestrator directly via ClassicOrchestrator wrapper.
All crash log processing is handled by Rust for maximum performance.
"""

import asyncio
import random
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, cast

from ClassicLib.core.async_bridge import AsyncBridge

if TYPE_CHECKING:
    from classic_scanlog import AnalysisResult

    from ClassicLib.scanning.logs.executor import ScanLogsExecutor as ScanLogsExecutorType

from ClassicLib.core.constants import YAML, get_all_db_paths
from ClassicLib.core.logger import logger
from ClassicLib.core.registry import GlobalRegistry
from ClassicLib.io.yaml import classic_settings, yaml_settings
from ClassicLib.messaging import MessageTarget, msg_info, msg_progress_context
from ClassicLib.scanning.logs.models import ScanConfig, ScanResult, ScanStatistics
from ClassicLib.scanning.logs.scanloginfo import ClassicScanLogsInfo
from ClassicLib.scanning.logs.util_legacy import crashlogs_get_files

# Import Rust orchestrator - required, no Python fallback
try:
    from classic_scanlog import Orchestrator
except ImportError as e:
    raise RuntimeError(
        "Rust orchestrator module not available. CLASSIC requires its Rust extensions. "
        "Please reinstall CLASSIC or rebuild Rust modules with: ./rebuild_rust.ps1"
    ) from e


class ScanLogsExecutor:
    """Orchestrates crash log scanning operations for CLI usage.

    Provides the main business logic for scanning crash logs, separated
    from CLI-specific code for better testability and modularity.

    Phase 9: Uses Rust Orchestrator directly for all processing.
    The Rust orchestrator provides maximum performance with parallel
    processing and SIMD-optimized parsing.

    Attributes:
        config: ScanConfig object containing scan parameters and settings.
        crashlog_list: List of Path objects to crash log files to scan.
        yamldata: ClassicScanLogsInfo with loaded YAML data (lazily loaded).
        statistics: ScanStatistics tracking scan progress and results.
        _rust_orchestrator: Rust Orchestrator instance for crash log processing.

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

        Note:
            crashlog_list is initialized lazily during execute_scan() to avoid
            calling sync settings functions from async context. See
            _ensure_crashlog_list_async() for the lazy loading implementation.

        """
        self.config = config or self._load_config_from_settings()

        # Crash log files and remove_list loaded lazily in execute_scan() via _ensure_crashlog_list_async()
        # This avoids calling sync functions (classic_settings, yaml_settings) from async context
        self.crashlog_list: list[Path] = []
        # Note: remove_list also loaded lazily if not provided - see _ensure_crashlog_list_async()

        # Reformatting now happens inline during processing for zero-delay startup
        logger.debug("Reformatting will happen inline during log processing")

        # Defer yamldata initialization to execute_scan for faster startup (unless eager_load is True)
        self.yamldata: ClassicScanLogsInfo | None = None
        self._eager_load = eager_load

        # Rust orchestrator - initialized lazily in execute_scan
        self._rust_orchestrator: Orchestrator | None = None

        # Set up database availability
        self.config.formid_db_exists = any(db.is_file() for db in get_all_db_paths())

        # Initialize statistics (total_files set during _ensure_crashlog_list_async)
        self.statistics = ScanStatistics()

        logger.debug("Initiated crash log scanner (crash logs loaded lazily)")

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
            from ClassicLib.io.database import DatabasePoolManager

            pool_manager = DatabasePoolManager()
            await pool_manager.get_pool()
            logger.debug("Warmed up database connection pool")

        logger.info("Resource warm-up complete - scanning will be smooth")

    async def _ensure_crashlog_list_async(self) -> None:
        """Lazily load crash log files and remove_list using async-safe method.

        This method is called during execute_scan() to avoid sync settings
        calls from async context. Uses asyncio.to_thread() to run the sync
        crashlogs_get_files() in a thread pool, avoiding async context detection.

        The sync function runs in a thread pool worker which does NOT have an
        event loop running, so the async context detection in yaml_settings()
        returns False, allowing the sync function to execute safely.
        """
        if self.crashlog_list:
            return  # Already loaded

        # Helper function to run sync operations in thread pool
        def _load_sync_resources() -> tuple[list[Path], tuple[str, ...]]:
            """Load crash logs and remove_list synchronously in thread pool."""
            logs = crashlogs_get_files()
            remove_list = yaml_settings(tuple, YAML.Main, "exclude_log_records") or ("",)
            return logs, remove_list

        # Run sync functions in thread pool to avoid async context detection
        logs, remove_list = await asyncio.to_thread(_load_sync_resources)

        self.crashlog_list = logs
        self.statistics.total_files = len(self.crashlog_list)

        # Only set remove_list if not already provided in config
        if not self.config.remove_list:
            self.config.remove_list = remove_list

        logger.debug(f"Lazily loaded {len(self.crashlog_list)} crash log files")

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
            max_concurrent=classic_settings(int, "Max Concurrent Scans") or 0,
        )

    async def execute_scan(self) -> ScanResult:
        """Execute the crash log scanning process asynchronously.

        This method handles the entire lifecycle of crash log scanning using the
        Rust Orchestrator for maximum performance. It implements progress tracking,
        statistics collection, and report generation.

        Phase 9: Uses Rust Orchestrator directly for all processing.
        The Rust orchestrator provides 10-150x speedups through:
        - SIMD-optimized log parsing
        - True parallel processing (not limited by Python GIL)
        - Efficient memory management

        Returns:
            ScanResult: An object containing results of the scan, including processed
                logs, failed logs, error messages, and scan duration.

        Raises:
            RuntimeError: If Rust orchestrator is not available or initialization fails.
            asyncio.CancelledError: If the asynchronous task is cancelled during execution.

        """
        logger.info("Starting crash log scan execution (Rust-accelerated)")

        # Initialize resources including Rust orchestrator
        await self._initialize_scan_resources()

        # Create result object
        result = ScanResult(stats=self.statistics)

        msg_info("SCANNING CRASH LOGS, PLEASE WAIT...", target=MessageTarget.CONSOLE)

        # Ensure Rust orchestrator is initialized
        if self._rust_orchestrator is None:
            msg = "Rust orchestrator not initialized after resource setup"
            raise RuntimeError(msg)

        # Run FCX checks if enabled (using Rust FCX handler via factory)
        if self.config.fcx_mode:
            from ClassicLib.integration.factory import get_fcx_handler

            fcx_handler = get_fcx_handler(self.config.fcx_mode)
            await fcx_handler.check_fcx_mode_async()

        # Process crash logs with Rust orchestrator
        await self._process_crashlogs_with_rust(result)

        # Update final scan time
        result.scan_time = self.statistics.get_scan_duration()

        # Log completion
        logger.info(f"Completed crash log scan execution in {result.scan_time:.2f} seconds (Rust-accelerated)")

        return result

    async def _initialize_scan_resources(self) -> None:
        """Initialize scan resources including YAML data, game paths, and Rust orchestrator.

        This method ensures that all necessary resources are loaded before
        starting the scan process, including the Rust orchestrator.

        Raises:
            RuntimeError: If resource initialization fails.

        """
        # Load crash log files first (uses asyncio.to_thread to avoid async context issues)
        await self._ensure_crashlog_list_async()

        # Initialize yamldata here using async factory (no AsyncBridge overhead)
        # If eager_load was set, warm_up() should have been called already
        if self.yamldata is None:
            if self._eager_load:
                logger.warning("Eager load requested but warm_up() was not called - loading now")
            self.yamldata = await ClassicScanLogsInfo.create_async()
            logger.debug("Initialized ClassicScanLogsInfo (async, no blocking)")

        # Ensure game paths are generated before creating orchestrator
        # This is required for FCX mode checks which need Game_Folder_Scripts and other inferred paths
        from ClassicLib.support.game_path import game_generate_paths_async, game_path_find_async

        await game_path_find_async()
        await game_generate_paths_async()

        # Initialize Rust orchestrator with YamlData configuration
        if self._rust_orchestrator is None:
            # Use the bridge method on ClassicScanLogsInfo to create Rust AnalysisConfig
            rust_config = self.yamldata.to_rust_config()

            # Apply configuration from ScanConfig (only override if not None)
            # rust_config already has defaults from AnalysisConfig.from_yamldata()
            if self.config.fcx_mode is not None:
                rust_config.fcx_mode = self.config.fcx_mode
            if self.config.show_formid_values is not None:
                rust_config.show_formid_values = self.config.show_formid_values
            if self.config.simplify_logs is not None:
                rust_config.simplify_logs = self.config.simplify_logs
            if self.config.remove_list:
                rust_config.remove_list = list(self.config.remove_list)

            self._rust_orchestrator = Orchestrator(rust_config)
            logger.debug(f"Initialized Rust orchestrator (feature_complete={self._rust_orchestrator.is_feature_complete()})")

            # Attach database pool for FormID value lookups if available
            if self.config.formid_db_exists and self.config.show_formid_values:
                db_paths_str = [str(p) for p in get_all_db_paths() if p.is_file()]
                if db_paths_str:
                    game = GlobalRegistry.get_game()
                    self._rust_orchestrator.attach_database(db_paths_str, game)
                    logger.debug(f"Attached database pool with {len(db_paths_str)} database(s) for FormID lookups")

    async def _process_crashlogs_with_rust(self, result: ScanResult) -> None:
        """Process all crash logs using Rust orchestrator with progress tracking.

        Uses Rust's parallel processing capabilities for maximum performance.
        Progress is tracked and cancellation is supported via progress context.

        Args:
            result: The scan result object to update with processing outcomes.

        Raises:
            RuntimeError: If Rust orchestrator is not initialized.
            asyncio.CancelledError: If the operation is cancelled by the user.

        """
        if self._rust_orchestrator is None:
            msg = "Rust orchestrator not initialized"
            raise RuntimeError(msg)

        total_logs = len(self.crashlog_list)
        if total_logs == 0:
            logger.info("No crash logs to process")
            return

        # Determine max concurrent from config (None = automatic in Rust)
        max_concurrent = None if self.config.max_concurrent == 0 else self.config.max_concurrent

        # Convert paths to strings for Rust
        log_paths = [str(p) for p in self.crashlog_list]

        with msg_progress_context("Processing Crash Logs", total_logs) as progress:
            # Define progress callback for Rust orchestrator
            def progress_callback(_current: int, _total: int, filename: str) -> None:
                progress.update(1, f"Processed: {filename}")
                # Check for cancellation
                if progress.was_cancelled():
                    logger.info("User cancelled scan operation")

            # Process all logs in parallel using Rust orchestrator
            # Run in thread pool to avoid blocking the event loop
            rust_results = await asyncio.to_thread(
                self._rust_orchestrator.process_logs_batch,
                log_paths,
                max_concurrent,
                progress_callback,
            )

            # Process results
            for rust_result in rust_results:
                await self._handle_rust_result(rust_result, result)

    async def _handle_rust_result(self, rust_result: "AnalysisResult", result: ScanResult) -> None:
        """Handle a single result from Rust orchestrator.

        Converts Rust AnalysisResult to Python format and updates statistics.

        Args:
            rust_result: AnalysisResult from Rust orchestrator.
            result: The scan result object to update.

        """
        crashlog_file = Path(rust_result.log_path)

        # Update statistics from Rust result
        local_stats: Counter[str] = Counter(
            scanned=rust_result.scanned,
            incomplete=rust_result.incomplete,
            failed=rust_result.failed,
        )
        self.statistics.update_from_counter(local_stats)

        # Add to processed files
        result.add_processed_file(crashlog_file)

        # Write report
        from ClassicLib.scanning.logs.utils import write_report_to_file_async

        await write_report_to_file_async(
            crashlog_file,
            rust_result.report_lines,
            rust_result.trigger_scan_failed,
            cast("ScanLogsExecutorType", self),
        )

        # Track failed scans
        if rust_result.trigger_scan_failed:
            result.add_failed_log(crashlog_file.name)

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
        # Use AsyncBridge directly for GUI sync contexts
        bridge = AsyncBridge.get_instance()
        return bridge.run_async(self.execute_scan())


# Backward compatibility alias
ClassicScanLogs = ScanLogsExecutor
