"""
Performance monitoring for async pipeline operations.

This module provides the AsyncPerformanceMonitor class for tracking
and comparing async vs sync performance metrics.
"""

from typing import TYPE_CHECKING

from ClassicLib.Logger import logger
from .async_crash_log_pipeline import run_async_crash_log_scan

if TYPE_CHECKING:
    from pathlib import Path
    from ClassicLib.ScanLog.ScanLogInfo import ClassicScanLogsInfo


class AsyncPerformanceMonitor:
    """Monitor and compare async vs sync performance."""

    @staticmethod
    def compare_performance(async_stats: dict[str, float], sync_time: float, log_count: int) -> dict[str, str | float]:
        """
        Compare async vs sync performance and generate metrics.

        Args:
            async_stats: Performance statistics from async pipeline
            sync_time: Total time for synchronous processing
            log_count: Number of logs processed

        Returns:
            Dictionary containing comparison metrics
        """
        async_total = async_stats.get("total_time", 0)

        if sync_time > 0 and async_total > 0:
            speedup = sync_time / async_total
            improvement = ((sync_time - async_total) / sync_time) * 100

            return {
                "async_total_time": async_total,
                "sync_total_time": sync_time,
                "speedup_factor": speedup,
                "improvement_percent": improvement,
                "async_logs_per_sec": log_count / async_total,
                "sync_logs_per_sec": log_count / sync_time,
                "reformat_time": async_stats.get("reformat_time", 0),
                "load_time": async_stats.get("load_time", 0),
                "process_time": async_stats.get("process_time", 0),
                "write_time": async_stats.get("write_time", 0),
            }

        return {
            "async_total_time": async_total,
            "async_logs_per_sec": log_count / async_total if async_total > 0 else 0,
            "reformat_time": async_stats.get("reformat_time", 0),
            "load_time": async_stats.get("load_time", 0),
            "process_time": async_stats.get("process_time", 0),
            "write_time": async_stats.get("write_time", 0),
        }

    @staticmethod
    def log_performance_summary(comparison: dict[str, str | float]) -> None:
        """Log a detailed performance summary."""
        logger.info("=== ASYNC PERFORMANCE SUMMARY ===")

        if "speedup_factor" in comparison:
            logger.info(f"Speedup: {comparison['speedup_factor']:.2f}x faster")
            logger.info(f"Improvement: {comparison['improvement_percent']:.1f}% faster")
            logger.info(f"Async: {comparison['async_logs_per_sec']:.1f} logs/sec")
            logger.info(f"Sync:  {comparison['sync_logs_per_sec']:.1f} logs/sec")
        else:
            logger.info(f"Async: {comparison['async_logs_per_sec']:.1f} logs/sec")

        logger.info("--- Async Pipeline Breakdown ---")
        logger.info(f"Reformatting: {comparison['reformat_time']:.3f}s")
        logger.info(f"Loading:      {comparison['load_time']:.3f}s")
        logger.info(f"Processing:   {comparison['process_time']:.3f}s")
        logger.info(f"Writing:      {comparison['write_time']:.3f}s")
        logger.info(f"Total:        {comparison['async_total_time']:.3f}s")
        logger.info("=================================")


async def benchmark_async_pipeline(  # noqa: PLR0913
    crashlog_list: list["Path"],
    remove_list: tuple[str],
    yamldata: "ClassicScanLogsInfo",
    fcx_mode: bool | None,
    show_formid_values: bool | None,
    formid_db_exists: bool,
    sync_baseline: float | None = None,
) -> dict[str, str | float]:
    """
    Benchmark the async pipeline and optionally compare with sync baseline.

    Args:
        crashlog_list: List of crash log file paths
        remove_list: Tuple of strings to remove during reformatting
        yamldata: Configuration data
        fcx_mode: Whether FCX mode is enabled
        show_formid_values: Whether to show FormID values
        formid_db_exists: Whether FormID database exists
        sync_baseline: Optional sync processing time for comparison

    Returns:
        Performance comparison metrics
    """
    logger.info("Starting async pipeline benchmark...")

    # Run async pipeline
    results, async_stats = await run_async_crash_log_scan(
        crashlog_list, remove_list, yamldata, fcx_mode, show_formid_values, formid_db_exists
    )

    # Generate performance comparison
    comparison = AsyncPerformanceMonitor.compare_performance(async_stats, sync_baseline or 0, len(crashlog_list))

    # Log summary
    AsyncPerformanceMonitor.log_performance_summary(comparison)

    return comparison
