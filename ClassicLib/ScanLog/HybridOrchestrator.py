"""
Hybrid orchestrator using Rust for batch parallelism, Python for single-log logic.

This module provides a hybrid implementation that combines the best of both worlds:
- Python OrchestratorCore for single-log processing (complex analysis logic)
- Rust ClassicOrchestrator for batch processing (unbounded parallelism)

When Rust is feature-complete (has plugin analyzer and suspect scanner), the hybrid
orchestrator can use Rust for BOTH single-log and batch processing. The
`is_feature_complete()` method on the Rust orchestrator determines this capability.

The hybrid approach delivers significant performance gains:
- Batch processing: 10-20x speedup via Rust parallelism
- Single-log processing: 5-10x speedup when Rust is feature-complete
"""

import asyncio
import logging
from collections import Counter
from pathlib import Path
from typing import Any

from ClassicLib.integration.status import is_rust_accelerated
from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore

logger = logging.getLogger(__name__)


class HybridOrchestrator:
    """
    Hybrid orchestrator using Rust for batch parallelism, Python for single-log logic.

    This class provides a seamless integration between Python's OrchestratorCore
    (for complex single-log analysis) and Rust's ClassicOrchestrator (for high-
    performance batch processing). It automatically detects Rust availability and
    falls back to pure Python when needed.

    When the Rust orchestrator is "feature-complete" (verified via `is_feature_complete()`),
    it can be used for BOTH single-log and batch processing, providing maximum performance.

    Attributes:
        yamldata: Configuration data for crash log analysis.
        fcx_mode: Whether FCX (File Configuration eXtender) mode is enabled.
        show_formid_values: Whether to display FormID values in reports.
        formid_db_exists: Whether the FormID database is available.
        remove_list: Optional tuple of items to remove during processing.
        _python_orch: Internal Python orchestrator instance.
        _rust_orch: Internal Rust orchestrator instance (None if unavailable).
        _rust_feature_complete: Whether Rust orchestrator has full feature parity.

    Example:
        >>> async with HybridOrchestrator(yamldata, fcx_mode=False,
        ...                               show_formid_values=True,
        ...                               formid_db_exists=True) as orch:
        ...     # Check if Rust can handle single-log processing
        ...     if orch.is_rust_feature_complete():
        ...         print("Using Rust for all processing!")
        ...
        ...     # Single log processing (Rust if feature-complete, else Python)
        ...     result = await orch.process_crash_log(Path("crash.log"))
        ...
        ...     # Batch processing uses Rust (if available)
        ...     results = await orch.process_crash_logs_batch(log_paths)
    """

    def __init__(
        self,
        yamldata: Any,
        fcx_mode: bool,
        show_formid_values: bool,
        formid_db_exists: bool,
        remove_list: tuple[str, ...] | None = None,
    ) -> None:
        """
        Initialize the hybrid orchestrator with Python and optional Rust backends.

        Args:
            yamldata: Configuration data loaded from YAML files.
            fcx_mode: Whether to enable FCX (File Configuration eXtender) mode
                for detecting configuration issues.
            show_formid_values: Whether to display FormID hexadecimal values
                in the analysis reports.
            formid_db_exists: Whether the FormID database file exists and can
                be used for FormID resolution.
            remove_list: Optional tuple of strings to filter out during processing.
                Defaults to None.
        """
        # Initialize Python orchestrator for single-log processing
        self._python_orch = OrchestratorCore(
            yamldata=yamldata,
            fcx_mode=fcx_mode,
            show_formid_values=show_formid_values,
            formid_db_exists=formid_db_exists,
            remove_list=remove_list,
        )

        # Try to initialize Rust orchestrator for batch processing
        self._rust_orch = None
        self._rust_feature_complete = False
        if is_rust_accelerated("orchestrator"):
            try:
                from ClassicLib.rust.orchestrator_api import ClassicOrchestrator

                self._rust_orch = ClassicOrchestrator()

                # Check if Rust orchestrator has full feature parity
                self._rust_feature_complete = self._rust_orch.is_feature_complete()
                if self._rust_feature_complete:
                    logger.debug("Rust orchestrator initialized with FULL feature parity (single-log: 5-10x, batch: 10-20x speedup)")
                else:
                    logger.debug("Rust orchestrator initialized for batch processing (10-20x speedup)")
            except Exception as e:  # noqa: BLE001 - Intentional: graceful fallback if Rust module fails for any reason
                logger.warning(f"Rust orchestrator unavailable, using Python fallback: {e}")

    async def __aenter__(self) -> "HybridOrchestrator":
        """
        Async context manager entry - initializes Python orchestrator resources.

        This method delegates to the Python orchestrator's __aenter__ to initialize
        resources like database pools and locks. The Rust orchestrator doesn't
        require async initialization.

        Returns:
            HybridOrchestrator: The initialized hybrid orchestrator instance.
        """
        await self._python_orch.__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Async context manager exit - cleans up Python orchestrator resources.

        Args:
            exc_type: The exception type if an exception was raised, None otherwise.
            exc_val: The exception value if an exception was raised, None otherwise.
            exc_tb: The exception traceback if an exception was raised, None otherwise.
        """
        await self._python_orch.__aexit__(exc_type, exc_val, exc_tb)

    def is_rust_feature_complete(self) -> bool:
        """
        Check if the Rust orchestrator has full feature parity with Python.

        When Rust is feature-complete, it can be used for single-log processing
        in addition to batch processing, providing maximum performance.

        Returns:
            bool: True if Rust orchestrator can handle all processing tasks.
        """
        return self._rust_feature_complete

    async def process_crash_log(self, crashlog_file: Path) -> tuple[Path, list[str], bool, Counter[str]]:
        """
        Process a single crash log using Rust (if feature-complete) or Python.

        When the Rust orchestrator is feature-complete, this method uses Rust for
        maximum performance (5-10x speedup). Otherwise, it falls back to Python's
        OrchestratorCore which contains the full analysis pipeline.

        Args:
            crashlog_file: Path to the crash log file to analyze.

        Returns:
            tuple[Path, list[str], bool, Counter[str]]: A tuple containing:
                - Path: The crash log file path
                - list[str]: Generated report lines
                - bool: True if scan failed, False otherwise
                - Counter[str]: Statistics (scanned, incomplete, failed counts)

        Raises:
            FileNotFoundError: If the crash log file doesn't exist.
            PermissionError: If the crash log file isn't readable.
        """
        # Use Rust for single-log processing when feature-complete
        if self._rust_feature_complete and self._rust_orch:
            try:
                logger.debug(f"Using Rust for single-log processing: {crashlog_file}")

                # Run Rust processing in thread pool to avoid blocking
                rust_result = await asyncio.to_thread(self._rust_orch.process_single_log, crashlog_file)

                # Convert single Rust result to Python format
                return self._convert_single_rust_result(rust_result)

            except Exception as e:  # noqa: BLE001 - Graceful fallback
                logger.warning(f"Rust single-log processing failed, using Python: {e}")
                # Fall through to Python

        # Default to Python orchestrator
        return await self._python_orch.process_crash_log(crashlog_file)

    async def process_crash_logs_batch(self, crashlog_files: list[Path]) -> list[tuple[Path, list[str], bool, Counter[str]]]:
        """
        Process batch of logs using Rust orchestrator (parallelism) or Python fallback.

        This method uses the Rust ClassicOrchestrator for batch processing when
        available, providing unbounded parallelism (not limited to batch_size=10).
        Falls back to Python OrchestratorCore if Rust is unavailable.

        Args:
            crashlog_files: List of crash log file paths to process.

        Returns:
            list[tuple[Path, list[str], bool, Counter[str]]]: List of results,
            one per log file, each containing:
                - Path: The crash log file path
                - list[str]: Generated report lines
                - bool: True if scan failed, False otherwise
                - Counter[str]: Statistics (scanned, incomplete, failed counts)

        Note:
            Rust orchestrator provides 10-20x speedup for large batches by using
            true parallelism instead of Python's batch_size=10 limitation.
        """
        if self._rust_orch and len(crashlog_files) > 5:
            # Use Rust orchestrator for large batches (5+ logs)
            # Small batches (1-4 logs) use Python to avoid overhead
            try:
                logger.debug(f"Using Rust orchestrator for batch of {len(crashlog_files)} logs (unbounded parallelism)")

                # Process logs with Rust (blocks but has internal parallelism)
                # Use asyncio.to_thread() to run blocking Rust code without blocking the event loop
                batch_result = await asyncio.to_thread(
                    self._rust_orch.process_crash_logs_batch, crashlog_files, max_concurrent=len(crashlog_files)
                )

                # Convert Rust results to Python format
                return self._convert_rust_results(batch_result)

            except Exception as e:  # noqa: BLE001 - Intentional: graceful fallback if Rust batch processing fails
                logger.warning(f"Rust batch processing failed, falling back to Python: {e}")
                # Fall through to Python fallback

        # Fall back to Python orchestrator
        logger.debug(f"Using Python orchestrator for batch of {len(crashlog_files)} logs (batch_size=10)")
        return await self._python_orch.process_crash_logs_batch(crashlog_files)

    @staticmethod
    def _convert_single_rust_result(rust_result: Any) -> tuple[Path, list[str], bool, Counter[str]]:
        """
        Convert a single Rust AnalysisResult to Python orchestrator format.

        Args:
            rust_result: AnalysisResult from Rust orchestrator.

        Returns:
            tuple[Path, list[str], bool, Counter[str]]: Converted result
            in Python orchestrator format.
        """
        log_path = Path(rust_result.log_path)
        report_lines = rust_result.report_lines

        # Use the new trigger_scan_failed field from Rust
        # This matches Python's scan_failed semantics
        scan_failed = rust_result.trigger_scan_failed

        # Use the new statistics fields from Rust AnalysisResult
        # These directly map to Python's Counter semantics
        stats: Counter[str] = Counter(
            scanned=rust_result.scanned,
            incomplete=rust_result.incomplete,
            failed=rust_result.failed,
        )

        return (log_path, report_lines, scan_failed, stats)

    @staticmethod
    def _convert_rust_results(batch_result: Any) -> list[tuple[Path, list[str], bool, Counter[str]]]:
        """
        Convert Rust BatchAnalysisResult to Python orchestrator format.

        This static method transforms Rust's AnalysisResult objects into the
        tuple format expected by Python code. Uses the new statistics fields
        added in Phase 3 for accurate parity with Python output.

        Args:
            batch_result: BatchAnalysisResult from Rust orchestrator containing
                results, total_time_ms, and parallelism_factor.

        Returns:
            list[tuple[Path, list[str], bool, Counter[str]]]: Converted results
            in Python orchestrator format.
        """

        python_results = [HybridOrchestrator._convert_single_rust_result(rust_result) for rust_result in batch_result.results]

        logger.debug(
            f"Converted {len(python_results)} Rust results "
            f"(parallelism: {batch_result.parallelism_factor:.1f}x, "
            f"time: {batch_result.total_time_ms}ms)"
        )

        return python_results

    @staticmethod
    async def write_reports_batch(reports: list[tuple[Path, list[str], bool]]) -> None:
        """
        Write batch reports to files asynchronously.

        Delegates to Python orchestrator's static method for writing reports.

        Args:
            reports: List of tuples containing (log_path, report_lines, scan_failed).
        """
        await OrchestratorCore.write_reports_batch(reports)

    def __repr__(self) -> str:
        """
        String representation for debugging.

        Returns:
            str: Representation showing Python and Rust orchestrator availability
            and feature-completeness status.
        """
        rust_status = ("feature-complete" if self._rust_feature_complete else "batch-only") if self._rust_orch else "unavailable"
        return f"HybridOrchestrator(python=available, rust={rust_status})"
