"""
Performance testing fixtures and utilities.

This module provides fixtures and utilities specifically designed for
performance testing of Rust components, including benchmarking utilities,
performance data generators, and validation helpers.
"""

import statistics
import time
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any


class PerformanceTestFixtures:
    """
    Collection of fixtures and utilities for performance testing.

    This class provides methods to generate performance test data,
    measure execution times, validate performance targets, and
    analyze performance characteristics of Rust components.
    """

    @staticmethod
    def generate_scalable_crash_data(base_size: int = 100,
                                   scale_factors: list[int] = None) -> dict[str, list[str]]:
        """
        Generate crash log data at multiple scales for performance testing.

        Args:
            base_size: Base number of lines to generate
            scale_factors: List of multipliers to create different sized datasets

        Returns:
            Dictionary mapping scale names to crash log data
        """
        if scale_factors is None:
            scale_factors = [1, 5, 10, 20, 50]

        datasets = {}

        for factor in scale_factors:
            size = base_size * factor
            scale_name = f"scale_{factor}x"

            # Generate crash log data
            data = [
                "Fallout 4 v1.10.163",
                "Buffout 4 v1.28.6",
                "",
                "PROBABLE CALL STACK:"
            ]

            # Generate call stack entries
            for i in range(size):
                addr = 0x7FF66DF19300 + (i * 0x100)
                formid = f"0x{(i % 0xFFFFFF):08X}"
                plugin = f"TestPlugin{(i % 100):03d}.esp"
                data.append(f"\t[{i}] {addr:#018X} -> FormID: {formid} ({plugin})")

            data.extend([
                "",
                "PLUGINS:"
            ])

            # Generate plugin list
            for i in range(min(size // 4, 255)):  # Quarter as many plugins as FormIDs
                data.append(f"\t[{i:02X}] TestPlugin{i:03d}.esp")

            datasets[scale_name] = data

        return datasets

    @staticmethod
    def create_performance_benchmark(
        operation_name: str,
        target_function: Callable,
        test_data: Any,
        iterations: int = 5,
        warmup_iterations: int = 2
    ) -> dict[str, Any]:
        """
        Create a performance benchmark for a specific operation.

        Args:
            operation_name: Name of the operation being benchmarked
            target_function: Function to benchmark
            test_data: Data to pass to the function
            iterations: Number of timing iterations
            warmup_iterations: Number of warmup iterations (not timed)

        Returns:
            Dictionary containing benchmark results
        """
        # Warmup runs
        for _ in range(warmup_iterations):
            try:
                target_function(test_data)
            except Exception:
                pass  # Ignore warmup errors

        # Timed runs
        times = []
        results = []
        errors = []

        for i in range(iterations):
            start_time = time.perf_counter()
            try:
                result = target_function(test_data)
                end_time = time.perf_counter()

                elapsed = end_time - start_time
                times.append(elapsed)
                results.append(result)

            except Exception as e:
                end_time = time.perf_counter()
                elapsed = end_time - start_time
                times.append(elapsed)  # Still record time for failed operations
                errors.append(str(e))

        # Calculate statistics
        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            std_time = statistics.stdev(times) if len(times) > 1 else 0.0
        else:
            avg_time = min_time = max_time = std_time = 0.0

        return {
            "operation_name": operation_name,
            "iterations": iterations,
            "times": times,
            "results": results,
            "errors": errors,
            "statistics": {
                "avg_time": avg_time,
                "min_time": min_time,
                "max_time": max_time,
                "std_time": std_time,
                "success_rate": (iterations - len(errors)) / iterations if iterations > 0 else 0.0
            }
        }

    @staticmethod
    def validate_performance_targets(
        benchmark_results: dict[str, Any],
        performance_targets: dict[str, float],
        scale_factor: float | None = None
    ) -> dict[str, bool]:
        """
        Validate benchmark results against performance targets.

        Args:
            benchmark_results: Results from create_performance_benchmark
            performance_targets: Dictionary of target times by operation name
            scale_factor: Optional scaling factor for targets

        Returns:
            Dictionary of validation results for each target
        """
        operation_name = benchmark_results["operation_name"]
        avg_time = benchmark_results["statistics"]["avg_time"]

        validation_results = {}

        if operation_name in performance_targets:
            target_time = performance_targets[operation_name]

            # Apply scale factor if provided
            if scale_factor is not None:
                target_time *= scale_factor

            validation_results[f"{operation_name}_meets_target"] = avg_time <= target_time
            validation_results[f"{operation_name}_target_time"] = target_time
            validation_results[f"{operation_name}_actual_time"] = avg_time
            validation_results[f"{operation_name}_performance_ratio"] = avg_time / target_time

        return validation_results

    @staticmethod
    def analyze_scaling_characteristics(
        benchmark_results: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Analyze scaling characteristics across different data sizes.

        Args:
            benchmark_results: Dictionary of benchmark results by scale

        Returns:
            Analysis of scaling behavior
        """
        if len(benchmark_results) < 2:
            return {"error": "Need at least 2 different scales for analysis"}

        # Extract data points
        scale_factors = []
        avg_times = []

        for scale_name, results in benchmark_results.items():
            if scale_name.startswith("scale_"):
                try:
                    factor = int(scale_name.split("_")[1].rstrip("x"))
                    avg_time = results["statistics"]["avg_time"]

                    scale_factors.append(factor)
                    avg_times.append(avg_time)
                except (ValueError, KeyError):
                    continue

        if len(scale_factors) < 2:
            return {"error": "Could not extract scaling data"}

        # Sort by scale factor
        paired_data = sorted(zip(scale_factors, avg_times))
        scale_factors, avg_times = zip(*paired_data)

        # Calculate scaling metrics
        scaling_ratios = []
        for i in range(1, len(avg_times)):
            size_ratio = scale_factors[i] / scale_factors[i-1]
            time_ratio = avg_times[i] / avg_times[i-1]
            scaling_ratio = time_ratio / size_ratio
            scaling_ratios.append(scaling_ratio)

        avg_scaling_ratio = statistics.mean(scaling_ratios) if scaling_ratios else 1.0

        # Determine scaling behavior
        if avg_scaling_ratio < 0.8:
            scaling_type = "sub_linear"  # Better than linear (caching, etc.)
        elif avg_scaling_ratio <= 1.2:
            scaling_type = "linear"  # Roughly linear
        elif avg_scaling_ratio <= 2.0:
            scaling_type = "super_linear"  # Worse than linear but reasonable
        else:
            scaling_type = "poor"  # Poor scaling

        return {
            "scale_factors": scale_factors,
            "avg_times": avg_times,
            "scaling_ratios": scaling_ratios,
            "avg_scaling_ratio": avg_scaling_ratio,
            "scaling_type": scaling_type,
            "throughput_at_base": 1.0 / avg_times[0] if avg_times[0] > 0 else 0.0,
            "throughput_at_max": 1.0 / avg_times[-1] if avg_times[-1] > 0 else 0.0
        }

    @staticmethod
    def create_memory_usage_tracker():
        """
        Create a memory usage tracking context manager.

        Returns:
            Context manager that tracks memory usage during execution
        """
        try:
            import os

            import psutil

            @contextmanager
            def memory_tracker():
                process = psutil.Process(os.getpid())

                initial_memory = process.memory_info()
                peak_memory = initial_memory
                samples = []

                memory_info = {
                    "initial_rss": initial_memory.rss,
                    "initial_vms": initial_memory.vms,
                    "peak_rss": initial_memory.rss,
                    "peak_vms": initial_memory.vms,
                    "samples": samples
                }

                try:
                    yield memory_info
                finally:
                    final_memory = process.memory_info()
                    memory_info.update({
                        "final_rss": final_memory.rss,
                        "final_vms": final_memory.vms,
                        "rss_growth": final_memory.rss - initial_memory.rss,
                        "vms_growth": final_memory.vms - initial_memory.vms
                    })

            return memory_tracker

        except ImportError:
            # Fallback if psutil not available
            @contextmanager
            def mock_memory_tracker():
                memory_info = {
                    "initial_rss": 50 * 1024 * 1024,  # 50MB mock
                    "initial_vms": 100 * 1024 * 1024,  # 100MB mock
                    "peak_rss": 55 * 1024 * 1024,  # 55MB mock
                    "peak_vms": 105 * 1024 * 1024,  # 105MB mock
                    "final_rss": 52 * 1024 * 1024,  # 52MB mock
                    "final_vms": 102 * 1024 * 1024,  # 102MB mock
                    "rss_growth": 2 * 1024 * 1024,  # 2MB growth mock
                    "vms_growth": 2 * 1024 * 1024,  # 2MB growth mock
                    "samples": []
                }
                yield memory_info

            return mock_memory_tracker

    @staticmethod
    def create_throughput_calculator(data_size_func: Callable[[Any], int]):
        """
        Create a throughput calculator for benchmark results.

        Args:
            data_size_func: Function that returns the size of test data

        Returns:
            Function that calculates throughput from benchmark results
        """
        def calculate_throughput(test_data: Any, benchmark_results: dict[str, Any]) -> dict[str, float]:
            """Calculate throughput metrics from benchmark results."""
            data_size = data_size_func(test_data)
            avg_time = benchmark_results["statistics"]["avg_time"]

            if avg_time <= 0:
                return {
                    "items_per_second": 0.0,
                    "data_size": data_size,
                    "processing_time": avg_time
                }

            return {
                "items_per_second": data_size / avg_time,
                "data_size": data_size,
                "processing_time": avg_time,
                "throughput_mbps": (data_size * 8) / (avg_time * 1024 * 1024) if avg_time > 0 else 0.0
            }

        return calculate_throughput

    @staticmethod
    def create_performance_regression_detector(baseline_results: dict[str, Any]):
        """
        Create a performance regression detector.

        Args:
            baseline_results: Baseline benchmark results to compare against

        Returns:
            Function that detects performance regressions
        """
        def detect_regression(
            current_results: dict[str, Any],
            regression_threshold: float = 1.2  # 20% slowdown threshold
        ) -> dict[str, Any]:
            """Detect performance regression compared to baseline."""

            baseline_time = baseline_results["statistics"]["avg_time"]
            current_time = current_results["statistics"]["avg_time"]

            if baseline_time <= 0:
                return {
                    "regression_detected": False,
                    "reason": "Invalid baseline time"
                }

            performance_ratio = current_time / baseline_time
            regression_detected = performance_ratio > regression_threshold

            return {
                "regression_detected": regression_detected,
                "baseline_time": baseline_time,
                "current_time": current_time,
                "performance_ratio": performance_ratio,
                "regression_threshold": regression_threshold,
                "performance_change_percent": (performance_ratio - 1.0) * 100,
                "regression_severity": (
                    "critical" if performance_ratio > 2.0 else
                    "major" if performance_ratio > 1.5 else
                    "minor" if performance_ratio > regression_threshold else
                    "none"
                )
            }

        return detect_regression

    @staticmethod
    def generate_concurrent_test_scenarios(
        base_operation: Callable,
        thread_counts: list[int] = None,
        iterations_per_thread: int = 10
    ) -> dict[str, Callable]:
        """
        Generate concurrent test scenarios for performance testing.

        Args:
            base_operation: Base operation to run concurrently
            thread_counts: List of thread counts to test
            iterations_per_thread: Number of iterations per thread

        Returns:
            Dictionary mapping scenario names to test functions
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        if thread_counts is None:
            thread_counts = [1, 2, 4, 8]

        scenarios = {}

        for num_threads in thread_counts:
            def create_concurrent_test(threads):
                def concurrent_test(test_data):
                    def worker(thread_id, data):
                        results = []
                        for i in range(iterations_per_thread):
                            try:
                                result = base_operation(data)
                                results.append(result)
                            except Exception as e:
                                results.append(f"Error: {e}")
                        return results

                    if threads == 1:
                        # Sequential execution
                        return worker(0, test_data)
                    # Concurrent execution
                    with ThreadPoolExecutor(max_workers=threads) as executor:
                        futures = [
                            executor.submit(worker, i, test_data)
                            for i in range(threads)
                        ]
                        all_results = []
                        for future in as_completed(futures):
                            all_results.extend(future.result())
                        return all_results

                return concurrent_test

            scenarios[f"threads_{num_threads}"] = create_concurrent_test(num_threads)

        return scenarios

    @staticmethod
    def create_performance_report_generator():
        """
        Create a performance report generator.

        Returns:
            Function that generates formatted performance reports
        """
        def generate_report(
            benchmark_results: dict[str, dict[str, Any]],
            scaling_analysis: dict[str, Any] | None = None,
            regression_results: dict[str, Any] | None = None
        ) -> str:
            """Generate a formatted performance report."""

            report_lines = [
                "=" * 60,
                "PERFORMANCE TEST REPORT",
                "=" * 60,
                ""
            ]

            # Summary section
            report_lines.append("SUMMARY:")
            total_operations = len(benchmark_results)
            avg_times = []

            for operation_name, results in benchmark_results.items():
                avg_time = results["statistics"]["avg_time"]
                avg_times.append(avg_time)
                success_rate = results["statistics"]["success_rate"]

                report_lines.append(
                    f"  {operation_name:<30}: {avg_time:.3f}s avg, {success_rate*100:.1f}% success"
                )

            if avg_times:
                overall_avg = statistics.mean(avg_times)
                report_lines.append(f"  {'Overall Average':<30}: {overall_avg:.3f}s")

            report_lines.append("")

            # Detailed results section
            report_lines.append("DETAILED RESULTS:")
            for operation_name, results in benchmark_results.items():
                report_lines.append(f"  {operation_name}:")
                stats = results["statistics"]
                report_lines.append(f"    Avg: {stats['avg_time']:.3f}s")
                report_lines.append(f"    Min: {stats['min_time']:.3f}s")
                report_lines.append(f"    Max: {stats['max_time']:.3f}s")
                report_lines.append(f"    Std: {stats['std_time']:.3f}s")

                if results["errors"]:
                    report_lines.append(f"    Errors: {len(results['errors'])}")
                    for error in results["errors"][:3]:  # Show first 3 errors
                        report_lines.append(f"      - {error}")

                report_lines.append("")

            # Scaling analysis section
            if scaling_analysis:
                report_lines.append("SCALING ANALYSIS:")
                if "error" in scaling_analysis:
                    report_lines.append(f"  Error: {scaling_analysis['error']}")
                else:
                    scaling_type = scaling_analysis["scaling_type"]
                    avg_ratio = scaling_analysis["avg_scaling_ratio"]

                    report_lines.append(f"  Scaling Type: {scaling_type}")
                    report_lines.append(f"  Avg Scaling Ratio: {avg_ratio:.2f}")

                    base_throughput = scaling_analysis.get("throughput_at_base", 0)
                    max_throughput = scaling_analysis.get("throughput_at_max", 0)

                    if base_throughput > 0:
                        report_lines.append(f"  Base Throughput: {base_throughput:.1f} ops/sec")
                    if max_throughput > 0:
                        report_lines.append(f"  Max Scale Throughput: {max_throughput:.1f} ops/sec")

                report_lines.append("")

            # Regression analysis section
            if regression_results:
                report_lines.append("REGRESSION ANALYSIS:")
                if regression_results.get("regression_detected", False):
                    severity = regression_results.get("regression_severity", "unknown")
                    change_percent = regression_results.get("performance_change_percent", 0)

                    report_lines.append(f"  REGRESSION DETECTED: {severity.upper()}")
                    report_lines.append(f"  Performance Change: {change_percent:+.1f}%")
                    report_lines.append(f"  Baseline: {regression_results.get('baseline_time', 0):.3f}s")
                    report_lines.append(f"  Current: {regression_results.get('current_time', 0):.3f}s")
                else:
                    report_lines.append("  No performance regression detected")

                report_lines.append("")

            report_lines.append("=" * 60)

            return "\n".join(report_lines)

        return generate_report
