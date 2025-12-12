"""Performance monitoring for async pipeline operations.

This module provides the AsyncPerformanceMonitor class for tracking
and comparing async vs sync performance metrics.
"""

from typing import TYPE_CHECKING

from ClassicLib.Logger import logger
from ClassicLib.ScanLog.pipeline.async_crash_log_pipeline import run_async_crash_log_scan

if TYPE_CHECKING:
    from pathlib import Path

    from ClassicLib.ScanLog.scanloginfo import ClassicScanLogsInfo


class AsyncPerformanceMonitor:
    """Monitor and compare asynchronous vs synchronous performance metrics.

    This class provides functionalities for comparing the performance of asynchronous
    and synchronous processes, generating detailed metrics, and logging performance
    summaries, making it useful for analyzing and optimizing the performance of
    asynchronous pipelines.

    Methods defined in this class include:
    - compare_performance: Compares asynchronous and synchronous performance and
      calculates performance metrics.
    - log_performance_summary: Logs a detailed summary of the performance metrics
      for easy analysis.
    """

    @staticmethod
    def compare_performance(async_stats: dict[str, float], sync_time: float, log_count: int) -> dict[str, str | float]:
        """Compare the performance of asynchronous and synchronous logging methods based on provided
        statistics of execution times and the number of processed logs.

        Args:
            async_stats (dict[str, float]): A dictionary containing the timing statistics for the
                asynchronous method. The keys may include "total_time", "reformat_time", "load_time",
                "process_time", and "write_time" with their respective durations.
            sync_time (float): The total execution time for the synchronous method.
            log_count (int): The total number of logs processed during execution.

        Returns:
            dict[str, str | float]: A dictionary summarizing the performance results. Includes keys
                such as:
                    - "async_total_time" (float): The total execution time for the asynchronous method.
                    - "sync_total_time" (float): The total execution time for the synchronous method
                      (only if `sync_time` > 0).
                    - "speedup_factor" (float): Speed-up factor comparing synchronous and asynchronous
                      times (only if `sync_time` and "total_time" > 0).
                    - "improvement_percent" (float): Percentage improvement of asynchronous processing
                      compared to synchronous (only if `sync_time` and "total_time" > 0).
                    - "async_logs_per_sec" (float): Logs processed per second in asynchronous execution.
                    - "sync_logs_per_sec" (float): Logs processed per second in synchronous execution
                      (only if `sync_time` > 0).
                    - "reformat_time" (float): Time spent on reformatting during asynchronous processing.
                    - "load_time" (float): Time spent on loading during asynchronous processing.
                    - "process_time" (float): Time spent on processing during asynchronous processing.
                    - "write_time" (float): Time spent on writing during asynchronous processing.

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
        """Log a summary of asynchronous performance metrics, providing insights into
        processing speed improvements, pipeline stage durations, and overall performance
        comparison against synchronous methods.

        Args:
            comparison (dict[str, str | float]): A dictionary containing performance
                metrics for both asynchronous and synchronous processing. The keys may
                include 'speedup_factor', 'improvement_percent', 'async_logs_per_sec',
                'sync_logs_per_sec', 'reformat_time', 'load_time', 'process_time',
                'write_time', and 'async_total_time'.

        """
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


async def benchmark_async_pipeline(
    crashlog_list: list["Path"],
    remove_list: tuple[str],
    yamldata: "ClassicScanLogsInfo",
    fcx_mode: bool | None,
    show_formid_values: bool | None,
    formid_db_exists: bool,
    sync_baseline: float | None = None,
) -> dict[str, str | float]:
    """Benchmarks the asynchronous pipeline process by running a crash log scan, generating
    performance comparison, and logging the performance summary. This function allows for
    the analysis of asynchronous performance metrics and comparison with a synchronous
    baseline if provided.

    Args:
        crashlog_list (list[Path]): List of paths to crash log files to be scanned.
        remove_list (tuple[str]): Tuple containing strings of items to be removed.
        yamldata (ClassicScanLogsInfo): Data for the classic scan logs configuration.
        fcx_mode (bool | None): Indicates whether the FCX mode is enabled.
        show_formid_values (bool | None): Indicates whether to display form ID values during processing.
        formid_db_exists (bool): Specifies whether the FormID database exists.
        sync_baseline (float | None, optional): Baseline value for synchronous performance comparison.

    Returns:
        dict[str, str | float]: Performance comparison data, including metrics and analysis results.

    """
    logger.info("Starting async pipeline benchmark...")

    # Run async pipeline
    _results, async_stats = await run_async_crash_log_scan(
        crashlog_list, remove_list, yamldata, fcx_mode, show_formid_values, formid_db_exists
    )

    # Generate performance comparison
    comparison = AsyncPerformanceMonitor.compare_performance(async_stats, sync_baseline or 0, len(crashlog_list))

    # Log summary
    AsyncPerformanceMonitor.log_performance_summary(comparison)

    return comparison
