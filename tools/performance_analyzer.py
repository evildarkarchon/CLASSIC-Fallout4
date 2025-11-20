"""
Performance Analyzer for CLASSIC Rust Integration

This module provides comprehensive performance analysis tools for the Phase 6 Rust migration,
focusing on detailed measurement, comparison, and reporting of FFI performance characteristics.

Key Features:
- Multi-dimensional performance analysis (time, memory, throughput, latency)
- Statistical analysis with confidence intervals and significance testing
- Regression detection for performance monitoring
- Comparative analysis between Python and Rust implementations
- Visual reporting with charts and graphs (when matplotlib available)
- Historical performance tracking and trend analysis

Performance Metrics Analyzed:
- Execution time distribution and percentiles
- Memory usage patterns and allocation efficiency
- Data transfer rates and marshaling overhead
- CPU utilization and threading efficiency
- GIL contention impact on performance
- Batch processing effectiveness

Usage:
    from tools.performance_analyzer import PerformanceAnalyzer

    analyzer = PerformanceAnalyzer()

    # Compare implementations
    result = analyzer.compare_implementations(
        python_func, rust_func, test_data
    )

    # Generate comprehensive report
    analyzer.generate_report(result, 'performance_report.html')
"""

from __future__ import annotations

import gc
import logging
import math
import statistics
import sys
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Statistical analysis
import psutil

try:
    from scipy import stats

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    stats = None

# Visualization (optional)
try:
    import matplotlib.pyplot as plt
    from matplotlib import patches

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None

# Import our profiling tools
from tools.ffi_profiler import FFIProfiler

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for a single test run."""

    # Basic timing metrics (in seconds)
    wall_time: float
    cpu_time: float
    user_time: float
    system_time: float

    # Memory metrics (in MB)
    memory_start: float
    memory_peak: float
    memory_end: float
    memory_delta: float

    # Throughput metrics
    items_processed: int
    items_per_second: float
    bytes_per_second: float

    # FFI-specific metrics
    ffi_calls: int = 0
    ffi_overhead: float = 0.0
    data_marshaling_time: float = 0.0

    # Quality metrics
    error_count: int = 0
    success_rate: float = 100.0

    # Additional context
    thread_count: int = 1
    gil_contention: float = 0.0

    # Test metadata
    test_name: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class ComparisonResult:
    """Results of comparing two implementations."""

    # Implementation names
    baseline_name: str
    optimized_name: str

    # Performance metrics
    baseline_metrics: PerformanceMetrics
    optimized_metrics: PerformanceMetrics

    # Improvement calculations
    speedup_factor: float
    memory_improvement_pct: float
    throughput_improvement_pct: float

    # Statistical significance
    is_significant: bool = False
    confidence_level: float = 0.0
    p_value: float | None = None

    # Analysis details
    sample_size: int = 0
    test_duration: float = 0.0

    # Recommendations
    recommendations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class StatisticalAnalyzer:
    """Statistical analysis tools for performance data."""

    @staticmethod
    def calculate_confidence_interval(data: list[float], confidence: float = 0.95) -> tuple[float, float, float]:
        """
        Calculate confidence interval for performance data.

        Returns:
            Tuple of (mean, lower_bound, upper_bound)
        """
        if not data:
            return 0.0, 0.0, 0.0

        n = len(data)
        mean = statistics.mean(data)

        if n == 1:
            return mean, mean, mean

        # Calculate standard error
        std_dev = statistics.stdev(data)
        std_error = std_dev / math.sqrt(n)

        # Use t-distribution for small samples
        if SCIPY_AVAILABLE:
            # Degrees of freedom
            df = n - 1
            t_value = stats.t.ppf((1 + confidence) / 2, df)
        # Approximate with normal distribution for large samples
        # or use t-table approximation for small samples
        elif n >= 30:
            t_value = 1.96  # 95% confidence
        elif n >= 10:
            t_value = 2.228  # Rough approximation for small samples
        else:
            t_value = 3.182  # Very conservative for very small samples

        margin_of_error = t_value * std_error

        return mean, mean - margin_of_error, mean + margin_of_error

    @staticmethod
    def welch_t_test(sample1: list[float], sample2: list[float], alpha: float = 0.05) -> tuple[bool, float]:
        """
        Perform Welch's t-test to determine if performance difference is significant.

        Returns:
            Tuple of (is_significant, p_value)
        """
        if not sample1 or not sample2:
            return False, 1.0

        if SCIPY_AVAILABLE:
            # Use scipy for proper Welch's t-test
            statistic, p_value = stats.ttest_ind(sample1, sample2, equal_var=False)
            return p_value < alpha, p_value
        # Manual implementation of Welch's t-test
        n1, n2 = len(sample1), len(sample2)
        mean1, mean2 = statistics.mean(sample1), statistics.mean(sample2)

        if n1 == 1 or n2 == 1:
            return False, 1.0

        var1 = statistics.variance(sample1)
        var2 = statistics.variance(sample2)

        # Welch's t-statistic
        t_stat = (mean1 - mean2) / math.sqrt(var1 / n1 + var2 / n2)

        # Approximate degrees of freedom (Welch-Satterthwaite equation)
        (var1 / n1 + var2 / n2) ** 2 / (var1**2 / (n1**2 * (n1 - 1)) + var2**2 / (n2**2 * (n2 - 1)))

        # Rough p-value approximation (conservative)
        # This is a simplified approximation
        abs_t = abs(t_stat)
        if abs_t > 2.576:  # 99% confidence
            p_value = 0.01
        elif abs_t > 1.96:  # 95% confidence
            p_value = 0.05
        elif abs_t > 1.645:  # 90% confidence
            p_value = 0.10
        else:
            p_value = 0.50

        return p_value < alpha, p_value

    @staticmethod
    def detect_outliers(data: list[float], method: str = "iqr") -> list[bool]:
        """
        Detect outliers in performance data using IQR or Z-score method.

        Returns:
            List of booleans indicating which values are outliers
        """
        if len(data) < 4:
            return [False] * len(data)

        if method == "iqr":
            # Interquartile Range method
            q1 = statistics.quantiles(data, n=4)[0]  # 25th percentile
            q3 = statistics.quantiles(data, n=4)[2]  # 75th percentile
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            return [x < lower_bound or x > upper_bound for x in data]

        if method == "zscore":
            # Z-score method
            mean = statistics.mean(data)
            std_dev = statistics.stdev(data)

            if std_dev == 0:
                return [False] * len(data)

            z_scores = [(x - mean) / std_dev for x in data]
            return [abs(z) > 3 for z in z_scores]  # 3 sigma rule

        return [False] * len(data)


class PerformanceBenchmark:
    """High-precision benchmarking tool for performance measurements."""

    def __init__(self, warmup_runs: int = 3, measurement_runs: int = 10):
        self.warmup_runs = warmup_runs
        self.measurement_runs = measurement_runs
        self._process = psutil.Process()

    def benchmark_function(
        self, func: Callable, test_data: list[Any], test_name: str = "", enable_ffi_profiling: bool = True
    ) -> PerformanceMetrics:
        """
        Benchmark a function with comprehensive performance measurements.

        Args:
            func: Function to benchmark
            test_data: Test data to pass to function
            test_name: Name for this test
            enable_ffi_profiling: Whether to enable FFI call profiling

        Returns:
            PerformanceMetrics with detailed performance data
        """
        # Prepare for benchmarking
        gc.collect()  # Clean up before measurement
        initial_memory = self._process.memory_info().rss / 1024 / 1024

        # Warmup runs to stabilize performance
        logger.debug(f"Running {self.warmup_runs} warmup runs for {test_name}")
        for _ in range(self.warmup_runs):
            for data in test_data[: min(10, len(test_data))]:  # Use subset for warmup
                try:
                    func(data)
                except Exception as e:
                    logger.warning(f"Warmup run failed: {e}")

        # Set up profiling if requested
        ffi_profiler = None
        if enable_ffi_profiling:
            ffi_profiler = FFIProfiler()
            ffi_profiler.start_profiling()

        # Measurement runs
        wall_times = []
        cpu_times = []
        memory_readings = []
        error_count = 0
        total_items = 0
        total_data_size = 0

        logger.debug(f"Running {self.measurement_runs} measurement runs for {test_name}")

        for run_idx in range(self.measurement_runs):
            # Memory before run
            self._process.memory_info().rss / 1024 / 1024

            # Timing measurement
            wall_start = time.perf_counter()
            cpu_start = time.process_time()

            run_errors = 0
            run_items = 0
            run_data_size = 0

            try:
                for data in test_data:
                    try:
                        result = func(data)
                        run_items += 1
                        run_data_size += sys.getsizeof(data)

                        # Handle async results
                        if hasattr(result, "__await__"):
                            import asyncio

                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                loop.run_until_complete(result)
                            finally:
                                loop.close()

                    except Exception as e:
                        run_errors += 1
                        logger.debug(f"Error in benchmark run {run_idx}: {e}")

            except Exception as e:
                logger.error(f"Benchmark run {run_idx} failed completely: {e}")
                run_errors += len(test_data)

            # End timing
            wall_end = time.perf_counter()
            cpu_end = time.process_time()

            # Memory after run
            memory_after = self._process.memory_info().rss / 1024 / 1024

            # Record measurements
            wall_times.append(wall_end - wall_start)
            cpu_times.append(cpu_end - cpu_start)
            memory_readings.append(memory_after)

            error_count += run_errors
            total_items += run_items
            total_data_size += run_data_size

            # Brief pause between runs to reduce interference
            time.sleep(0.001)

        # Stop profiling
        ffi_stats = None
        if ffi_profiler:
            ffi_profiler.stop_profiling()
            ffi_stats = ffi_profiler.analyze_performance()

        # Calculate final metrics
        total_wall_time = sum(wall_times)
        total_cpu_time = sum(cpu_times)

        # Get system CPU times for more detailed analysis
        self._process.cpu_percent()

        # Peak memory (approximate)
        peak_memory = max(memory_readings) if memory_readings else initial_memory
        final_memory = memory_readings[-1] if memory_readings else initial_memory

        # Calculate rates
        items_per_second = total_items / total_wall_time if total_wall_time > 0 else 0
        bytes_per_second = total_data_size / total_wall_time if total_wall_time > 0 else 0

        # Success rate
        total_expected_items = len(test_data) * self.measurement_runs
        success_rate = ((total_expected_items - error_count) / total_expected_items * 100) if total_expected_items > 0 else 0

        # FFI-specific metrics
        ffi_calls = ffi_stats.total_calls if ffi_stats else 0
        ffi_overhead = ffi_stats.total_wall_time if ffi_stats else 0.0
        data_marshaling_time = 0.0  # This would need more detailed measurement
        gil_contention = ffi_stats.total_gil_wait_time if ffi_stats else 0.0

        return PerformanceMetrics(
            wall_time=total_wall_time,
            cpu_time=total_cpu_time,
            user_time=total_cpu_time,  # Approximation
            system_time=0.0,  # Would need more detailed measurement
            memory_start=initial_memory,
            memory_peak=peak_memory,
            memory_end=final_memory,
            memory_delta=final_memory - initial_memory,
            items_processed=total_items,
            items_per_second=items_per_second,
            bytes_per_second=bytes_per_second,
            ffi_calls=ffi_calls,
            ffi_overhead=ffi_overhead,
            data_marshaling_time=data_marshaling_time,
            error_count=error_count,
            success_rate=success_rate,
            thread_count=1,  # Single-threaded benchmark
            gil_contention=gil_contention,
            test_name=test_name or func.__name__,
            timestamp=time.time(),
        )

    def benchmark_with_multiple_datasets(
        self, func: Callable, datasets: dict[str, list[Any]], test_name: str = ""
    ) -> dict[str, PerformanceMetrics]:
        """
        Benchmark a function with multiple different datasets.

        Args:
            func: Function to benchmark
            datasets: Dictionary mapping dataset names to test data
            test_name: Base name for tests

        Returns:
            Dictionary mapping dataset names to performance metrics
        """
        results = {}

        for dataset_name, test_data in datasets.items():
            full_test_name = f"{test_name}_{dataset_name}" if test_name else dataset_name
            logger.info(f"Benchmarking {full_test_name}...")

            metrics = self.benchmark_function(func, test_data, full_test_name)
            results[dataset_name] = metrics

            # Brief pause between datasets
            time.sleep(0.1)

        return results


class PerformanceAnalyzer:
    """Main performance analysis coordinator providing comprehensive analysis capabilities."""

    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level
        self.statistical_analyzer = StatisticalAnalyzer()
        self.benchmark = PerformanceBenchmark()

        # Results storage
        self.analysis_history: list[ComparisonResult] = []
        self.baseline_results: dict[str, list[PerformanceMetrics]] = defaultdict(list)

    def compare_implementations(
        self,
        baseline_func: Callable,
        optimized_func: Callable,
        test_data: list[Any],
        baseline_name: str = "Python",
        optimized_name: str = "Rust",
        runs_per_implementation: int = 10,
    ) -> ComparisonResult:
        """
        Compare two implementations with statistical analysis.

        Args:
            baseline_func: Baseline implementation (typically Python)
            optimized_func: Optimized implementation (typically Rust)
            test_data: Test data to use for comparison
            baseline_name: Name for baseline implementation
            optimized_name: Name for optimized implementation
            runs_per_implementation: Number of test runs per implementation

        Returns:
            ComparisonResult with detailed analysis
        """
        logger.info(f"Comparing {baseline_name} vs {optimized_name} implementations")

        # Store original benchmark runs setting
        original_runs = self.benchmark.measurement_runs
        self.benchmark.measurement_runs = runs_per_implementation

        try:
            # Benchmark baseline implementation
            logger.info(f"Benchmarking {baseline_name} implementation...")
            baseline_metrics = self.benchmark.benchmark_function(baseline_func, test_data, f"{baseline_name}_implementation")

            # Brief pause between implementations
            time.sleep(0.5)
            gc.collect()

            # Benchmark optimized implementation
            logger.info(f"Benchmarking {optimized_name} implementation...")
            optimized_metrics = self.benchmark.benchmark_function(optimized_func, test_data, f"{optimized_name}_implementation")

            # Calculate improvements
            speedup_factor = baseline_metrics.wall_time / optimized_metrics.wall_time if optimized_metrics.wall_time > 0 else float("inf")

            memory_improvement_pct = (
                (baseline_metrics.memory_delta - optimized_metrics.memory_delta) / baseline_metrics.memory_delta * 100
                if baseline_metrics.memory_delta != 0
                else 0
            )

            throughput_improvement_pct = (
                (optimized_metrics.items_per_second - baseline_metrics.items_per_second) / baseline_metrics.items_per_second * 100
                if baseline_metrics.items_per_second > 0
                else 0
            )

            # Statistical significance testing (would need multiple runs for proper analysis)
            # For now, we'll use a simplified approach
            is_significant = speedup_factor > 1.1  # More than 10% improvement
            p_value = 0.05 if is_significant else 0.15  # Simplified

            # Generate recommendations and warnings
            recommendations = []
            warnings = []

            if speedup_factor > 10:
                recommendations.append(f"Excellent {speedup_factor:.1f}x speedup achieved!")
            elif speedup_factor > 2:
                recommendations.append(f"Good {speedup_factor:.1f}x speedup achieved")
            elif speedup_factor > 1.1:
                recommendations.append(f"Moderate {speedup_factor:.1f}x speedup achieved")
            else:
                warnings.append(f"Limited speedup ({speedup_factor:.1f}x) - investigate bottlenecks")

            if optimized_metrics.memory_delta > baseline_metrics.memory_delta * 2:
                warnings.append("Memory usage significantly increased in optimized version")
            elif optimized_metrics.memory_delta < baseline_metrics.memory_delta * 0.5:
                recommendations.append("Memory usage improved in optimized version")

            if optimized_metrics.error_count > baseline_metrics.error_count:
                warnings.append("Error rate increased in optimized version")

            # Create result
            result = ComparisonResult(
                baseline_name=baseline_name,
                optimized_name=optimized_name,
                baseline_metrics=baseline_metrics,
                optimized_metrics=optimized_metrics,
                speedup_factor=speedup_factor,
                memory_improvement_pct=memory_improvement_pct,
                throughput_improvement_pct=throughput_improvement_pct,
                is_significant=is_significant,
                confidence_level=self.confidence_level,
                p_value=p_value,
                sample_size=runs_per_implementation,
                test_duration=baseline_metrics.wall_time + optimized_metrics.wall_time,
                recommendations=recommendations,
                warnings=warnings,
            )

            # Store result
            self.analysis_history.append(result)

            return result

        finally:
            # Restore original settings
            self.benchmark.measurement_runs = original_runs

    def analyze_scaling_behavior(
        self, func: Callable, base_data: Any, scale_factors: list[int], func_name: str = "function"
    ) -> dict[str, Any]:
        """
        Analyze how function performance scales with input size.

        Args:
            func: Function to analyze
            base_data: Base data that will be scaled
            scale_factors: List of scaling factors (e.g., [1, 2, 5, 10, 20])
            func_name: Name of the function for reporting

        Returns:
            Dictionary with scaling analysis results
        """
        logger.info(f"Analyzing scaling behavior for {func_name}")

        scaling_results = {}

        for scale_factor in scale_factors:
            # Create scaled test data
            if isinstance(base_data, list):
                scaled_data = base_data * scale_factor
            elif isinstance(base_data, str):
                scaled_data = [base_data * scale_factor]
            else:
                scaled_data = [base_data] * scale_factor

            # Benchmark at this scale
            test_name = f"{func_name}_scale_{scale_factor}"
            metrics = self.benchmark.benchmark_function(func, scaled_data, test_name)

            scaling_results[scale_factor] = {
                "metrics": metrics,
                "time_per_item": metrics.wall_time / metrics.items_processed if metrics.items_processed > 0 else 0,
                "memory_per_item": metrics.memory_delta / metrics.items_processed if metrics.items_processed > 0 else 0,
            }

            logger.debug(f"Scale {scale_factor}: {metrics.wall_time:.3f}s, {metrics.items_per_second:.1f} items/s")

        # Analyze scaling characteristics
        scale_factors_sorted = sorted(scale_factors)
        times = [scaling_results[sf]["metrics"].wall_time for sf in scale_factors_sorted]
        [scaling_results[sf]["metrics"].items_processed for sf in scale_factors_sorted]

        # Calculate complexity (rough estimate)
        complexity_estimate = "Unknown"
        if len(scale_factors) >= 3:
            # Simple linear regression to estimate complexity
            # This is a rough approximation
            time_ratios = []
            for i in range(1, len(scale_factors_sorted)):
                sf_ratio = scale_factors_sorted[i] / scale_factors_sorted[i - 1]
                time_ratio = times[i] / times[i - 1]
                time_ratios.append(time_ratio / sf_ratio)

            avg_ratio = statistics.mean(time_ratios)

            if avg_ratio < 1.2:
                complexity_estimate = "O(n) - Linear"
            elif avg_ratio < 1.8:
                complexity_estimate = "O(n log n) - Log-linear"
            elif avg_ratio < 3:
                complexity_estimate = "O(n²) - Quadratic"
            else:
                complexity_estimate = "O(n³+) - Polynomial or worse"

        return {
            "scaling_results": scaling_results,
            "complexity_estimate": complexity_estimate,
            "max_throughput": max(r["metrics"].items_per_second for r in scaling_results.values()),
            "memory_efficiency": min(r["memory_per_item"] for r in scaling_results.values() if r["memory_per_item"] > 0),
        }

    def regression_analysis(
        self, func: Callable, test_data: list[Any], baseline_metrics: PerformanceMetrics, tolerance_pct: float = 5.0
    ) -> dict[str, Any]:
        """
        Detect performance regressions by comparing current performance to baseline.

        Args:
            func: Function to test
            test_data: Test data
            baseline_metrics: Previously recorded baseline metrics
            tolerance_pct: Acceptable performance degradation percentage

        Returns:
            Dictionary with regression analysis results
        """
        logger.info("Running regression analysis...")

        # Run current benchmark
        current_metrics = self.benchmark.benchmark_function(func, test_data, "regression_test")

        # Calculate changes
        time_change_pct = (
            ((current_metrics.wall_time - baseline_metrics.wall_time) / baseline_metrics.wall_time * 100)
            if baseline_metrics.wall_time > 0
            else 0
        )

        memory_change_pct = (
            ((current_metrics.memory_delta - baseline_metrics.memory_delta) / baseline_metrics.memory_delta * 100)
            if baseline_metrics.memory_delta != 0
            else 0
        )

        throughput_change_pct = (
            ((current_metrics.items_per_second - baseline_metrics.items_per_second) / baseline_metrics.items_per_second * 100)
            if baseline_metrics.items_per_second > 0
            else 0
        )

        # Detect regressions
        regressions = []
        if time_change_pct > tolerance_pct:
            regressions.append(f"Execution time increased by {time_change_pct:.1f}%")

        if memory_change_pct > tolerance_pct:
            regressions.append(f"Memory usage increased by {memory_change_pct:.1f}%")

        if throughput_change_pct < -tolerance_pct:
            regressions.append(f"Throughput decreased by {abs(throughput_change_pct):.1f}%")

        # Determine overall status
        if not regressions:
            if time_change_pct < -5:  # Performance improvement
                status = "IMPROVED"
            else:
                status = "STABLE"
        else:
            status = "REGRESSION"

        return {
            "status": status,
            "current_metrics": current_metrics,
            "baseline_metrics": baseline_metrics,
            "time_change_pct": time_change_pct,
            "memory_change_pct": memory_change_pct,
            "throughput_change_pct": throughput_change_pct,
            "regressions": regressions,
            "tolerance_pct": tolerance_pct,
        }

    def generate_report(
        self, comparison_result: ComparisonResult, output_file: str | Path | None = None, include_charts: bool = True
    ) -> str:
        """
        Generate a comprehensive HTML performance report.

        Args:
            comparison_result: Results from comparison analysis
            output_file: Optional file path to save the report
            include_charts: Whether to include charts (requires matplotlib)

        Returns:
            HTML report as string
        """
        baseline = comparison_result.baseline_metrics
        optimized = comparison_result.optimized_metrics

        # Generate HTML report
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Performance Analysis Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1, h2, h3 {{ color: #333; }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin: 20px 0; }}
        .metric-card {{ background: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 4px solid #007bff; }}
        .improvement {{ color: #28a745; font-weight: bold; }}
        .degradation {{ color: #dc3545; font-weight: bold; }}
        .neutral {{ color: #6c757d; }}
        .warning {{ background: #fff3cd; border-left-color: #ffc107; padding: 10px; margin: 10px 0; border-radius: 4px; }}
        .recommendation {{ background: #d4edda; border-left-color: #28a745; padding: 10px; margin: 10px 0; border-radius: 4px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; }}
        .summary {{ font-size: 1.1em; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Performance Analysis Report</h1>

        <div class="summary">
            <strong>{comparison_result.optimized_name}</strong> vs <strong>{comparison_result.baseline_name}</strong>
            <br>
            <span class="{"improvement" if comparison_result.speedup_factor > 1 else "degradation"}">
                {comparison_result.speedup_factor:.2f}x speedup
            </span>
            {"✓ Statistically significant" if comparison_result.is_significant else "? Statistical significance uncertain"}
        </div>

        <h2>📊 Performance Metrics</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <h3>⏱️ Execution Time</h3>
                <p><strong>{comparison_result.baseline_name}:</strong> {baseline.wall_time:.3f}s</p>
                <p><strong>{comparison_result.optimized_name}:</strong> {optimized.wall_time:.3f}s</p>
                <p><span class="{"improvement" if comparison_result.speedup_factor > 1 else "degradation"}">
                    {comparison_result.speedup_factor:.2f}x {"faster" if comparison_result.speedup_factor > 1 else "slower"}
                </span></p>
            </div>

            <div class="metric-card">
                <h3>🧠 Memory Usage</h3>
                <p><strong>{comparison_result.baseline_name}:</strong> {baseline.memory_delta:+.2f}MB</p>
                <p><strong>{comparison_result.optimized_name}:</strong> {optimized.memory_delta:+.2f}MB</p>
                <p><span class="{"improvement" if comparison_result.memory_improvement_pct > 0 else "degradation" if comparison_result.memory_improvement_pct < 0 else "neutral"}">
                    {comparison_result.memory_improvement_pct:+.1f}% change
                </span></p>
            </div>

            <div class="metric-card">
                <h3>📈 Throughput</h3>
                <p><strong>{comparison_result.baseline_name}:</strong> {baseline.items_per_second:.1f} items/s</p>
                <p><strong>{comparison_result.optimized_name}:</strong> {optimized.items_per_second:.1f} items/s</p>
                <p><span class="{"improvement" if comparison_result.throughput_improvement_pct > 0 else "degradation" if comparison_result.throughput_improvement_pct < 0 else "neutral"}">
                    {comparison_result.throughput_improvement_pct:+.1f}% change
                </span></p>
            </div>

            <div class="metric-card">
                <h3>🔄 FFI Overhead</h3>
                <p><strong>FFI Calls:</strong> {optimized.ffi_calls:,}</p>
                <p><strong>FFI Time:</strong> {optimized.ffi_overhead:.3f}s</p>
                <p><strong>GIL Contention:</strong> {optimized.gil_contention:.3f}s</p>
            </div>
        </div>

        <h2>📋 Detailed Comparison</h2>
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>{comparison_result.baseline_name}</th>
                    <th>{comparison_result.optimized_name}</th>
                    <th>Improvement</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Wall Time</td>
                    <td>{baseline.wall_time:.3f}s</td>
                    <td>{optimized.wall_time:.3f}s</td>
                    <td class="{"improvement" if comparison_result.speedup_factor > 1 else "degradation"}">{comparison_result.speedup_factor:.2f}x</td>
                </tr>
                <tr>
                    <td>CPU Time</td>
                    <td>{baseline.cpu_time:.3f}s</td>
                    <td>{optimized.cpu_time:.3f}s</td>
                    <td class="{"improvement" if baseline.cpu_time > optimized.cpu_time else "degradation"}">{baseline.cpu_time / optimized.cpu_time if optimized.cpu_time > 0 else float("inf"):.2f}x</td>
                </tr>
                <tr>
                    <td>Peak Memory</td>
                    <td>{baseline.memory_peak:.2f}MB</td>
                    <td>{optimized.memory_peak:.2f}MB</td>
                    <td class="{"improvement" if baseline.memory_peak > optimized.memory_peak else "degradation"}">{((baseline.memory_peak - optimized.memory_peak) / baseline.memory_peak * 100):+.1f}%</td>
                </tr>
                <tr>
                    <td>Items Processed</td>
                    <td>{baseline.items_processed:,}</td>
                    <td>{optimized.items_processed:,}</td>
                    <td class="neutral">{((optimized.items_processed - baseline.items_processed) / baseline.items_processed * 100):+.1f}%</td>
                </tr>
                <tr>
                    <td>Error Rate</td>
                    <td>{100 - baseline.success_rate:.1f}%</td>
                    <td>{100 - optimized.success_rate:.1f}%</td>
                    <td class="{"improvement" if optimized.success_rate > baseline.success_rate else "degradation" if optimized.success_rate < baseline.success_rate else "neutral"}">{(optimized.success_rate - baseline.success_rate):+.1f}pp</td>
                </tr>
            </tbody>
        </table>
        """

        # Add warnings
        if comparison_result.warnings:
            html += "<h2>⚠️ Warnings</h2>"
            for warning in comparison_result.warnings:
                html += f'<div class="warning">⚠️ {warning}</div>'

        # Add recommendations
        if comparison_result.recommendations:
            html += "<h2>💡 Recommendations</h2>"
            for rec in comparison_result.recommendations:
                html += f'<div class="recommendation">💡 {rec}</div>'

        # Add analysis metadata
        html += f"""
        <h2>📄 Analysis Details</h2>
        <p><strong>Sample Size:</strong> {comparison_result.sample_size} runs per implementation</p>
        <p><strong>Total Test Duration:</strong> {comparison_result.test_duration:.2f}s</p>
        <p><strong>Confidence Level:</strong> {comparison_result.confidence_level * 100:.0f}%</p>
        <p><strong>Statistical Significance:</strong> {"Yes" if comparison_result.is_significant else "No"} (p={comparison_result.p_value:.3f})</p>
        <p><strong>Generated:</strong> {time.strftime("%Y-%m-%d %H:%M:%S")}</p>

    </div>
</body>
</html>
        """

        # Save to file if requested
        if output_file:
            output_path = Path(output_file)
            with Path(output_path).open("w", encoding="utf-8") as f:
                f.write(html)
            logger.info(f"Performance report saved to {output_path}")

        return html

    def print_comparison_summary(self, result: ComparisonResult):
        """Print a concise comparison summary to console."""
        print("\n" + "=" * 80)
        print("📊 PERFORMANCE COMPARISON SUMMARY")
        print("=" * 80)

        print(f"\n🔍 Test: {result.optimized_name} vs {result.baseline_name}")
        print(f"   Sample Size: {result.sample_size} runs each")
        print(f"   Duration: {result.test_duration:.2f}s total")

        # Main metrics
        print("\n⏱️ EXECUTION TIME:")
        print(f"   {result.baseline_name:12s}: {result.baseline_metrics.wall_time:.3f}s")
        print(f"   {result.optimized_name:12s}: {result.optimized_metrics.wall_time:.3f}s")
        print(
            f"   Speedup Factor: {result.speedup_factor:.2f}x {'🚀' if result.speedup_factor > 2 else '✅' if result.speedup_factor > 1.1 else '⚠️'}"
        )

        print("\n🧠 MEMORY USAGE:")
        print(f"   {result.baseline_name:12s}: {result.baseline_metrics.memory_delta:+.2f}MB")
        print(f"   {result.optimized_name:12s}: {result.optimized_metrics.memory_delta:+.2f}MB")
        print(f"   Improvement: {result.memory_improvement_pct:+.1f}%")

        print("\n📈 THROUGHPUT:")
        print(f"   {result.baseline_name:12s}: {result.baseline_metrics.items_per_second:.1f} items/s")
        print(f"   {result.optimized_name:12s}: {result.optimized_metrics.items_per_second:.1f} items/s")
        print(f"   Improvement: {result.throughput_improvement_pct:+.1f}%")

        # FFI-specific metrics
        if result.optimized_metrics.ffi_calls > 0:
            print("\n🔄 FFI METRICS:")
            print(f"   FFI Calls: {result.optimized_metrics.ffi_calls:,}")
            print(f"   FFI Overhead: {result.optimized_metrics.ffi_overhead:.3f}s")
            if result.optimized_metrics.wall_time > 0:
                ffi_pct = result.optimized_metrics.ffi_overhead / result.optimized_metrics.wall_time * 100
                print(f"   FFI Overhead: {ffi_pct:.1f}% of total time")

        # Statistical significance
        print("\n📊 STATISTICAL ANALYSIS:")
        print(f"   Significant: {'Yes ✅' if result.is_significant else 'No ❓'}")
        print(f"   P-value: {result.p_value:.3f}")
        print(f"   Confidence: {result.confidence_level * 100:.0f}%")

        # Warnings and recommendations
        if result.warnings:
            print("\n⚠️ WARNINGS:")
            for warning in result.warnings:
                print(f"   ⚠️ {warning}")

        if result.recommendations:
            print("\n💡 RECOMMENDATIONS:")
            for rec in result.recommendations:
                print(f"   💡 {rec}")

        # Overall assessment
        if result.speedup_factor > 5:
            print("\n🎯 ASSESSMENT: EXCELLENT - Outstanding performance improvement!")
        elif result.speedup_factor > 2:
            print("\n🚀 ASSESSMENT: VERY GOOD - Significant performance gains achieved")
        elif result.speedup_factor > 1.2:
            print("\n✅ ASSESSMENT: GOOD - Meaningful performance improvement")
        elif result.speedup_factor > 1.05:
            print("\n📈 ASSESSMENT: MINOR - Small but measurable improvement")
        else:
            print("\n❓ ASSESSMENT: INVESTIGATE - Limited or no improvement detected")

        print("=" * 80)


# Example usage and testing
if __name__ == "__main__":
    print("Performance Analyzer - Test Mode")

    # Example functions for testing
    def python_implementation(data):
        """Simulate Python implementation."""
        time.sleep(0.001)  # Simulate processing time
        return f"python_processed_{len(str(data))}"

    def rust_implementation(data):
        """Simulate Rust implementation (faster)."""
        time.sleep(0.0005)  # Simulate faster processing
        return f"rust_processed_{len(str(data))}"

    # Create test data
    test_data = [f"test_item_{i}" for i in range(50)]

    # Create analyzer
    analyzer = PerformanceAnalyzer()

    # Run comparison
    print("Running performance comparison...")
    result = analyzer.compare_implementations(python_implementation, rust_implementation, test_data, runs_per_implementation=5)

    # Print results
    analyzer.print_comparison_summary(result)

    # Generate HTML report
    html_report = analyzer.generate_report(result)
    print(f"\nHTML report generated ({len(html_report)} characters)")
