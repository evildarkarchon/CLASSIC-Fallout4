"""
FFI Overhead Benchmark Suite for CLASSIC Rust Integration

This benchmark suite provides comprehensive testing of FFI overhead patterns
and performance characteristics for the Phase 6 Rust migration. It focuses
specifically on measuring and optimizing Python↔Rust boundary costs.

Key Benchmark Categories:
1. Call Frequency Patterns - High-frequency vs batch operations
2. Data Transfer Overhead - Different data sizes and types
3. Memory Allocation Patterns - Stack vs heap, small vs large objects
4. Async vs Sync Performance - Event loop overhead
5. Threading and GIL Impact - Concurrent access patterns
6. Real-world Scenarios - Based on actual CLASSIC usage patterns

Performance Targets:
- Individual FFI calls: <1ms overhead per call
- Batch operations: >10x efficiency improvement
- Memory transfers: >1GB/s throughput for large data
- GIL contention: <5% of total execution time

Usage:
    from benchmarks.ffi_overhead_benchmark import FFIBenchmarkSuite

    suite = FFIBenchmarkSuite()
    results = suite.run_all_benchmarks()
    suite.generate_comprehensive_report(results, 'ffi_benchmark_report.html')
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import gc
import json
import logging
import random
import string
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tools.ffi_optimizer import BatchProcessor, DataOptimizer, FFIOptimizer

# Import our profiling and analysis tools
from tools.ffi_profiler import FFIProfiler
from tools.performance_analyzer import ComparisonResult, PerformanceAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class BenchmarkCase:
    """Definition of a single benchmark case."""
    name: str
    description: str
    category: str

    # Test functions
    python_func: Callable
    rust_func: Callable | None = None

    # Test data generation
    data_generator: Callable | None = None
    data_sizes: list[int] = field(default_factory=lambda: [10, 100, 1000])

    # Benchmark parameters
    warmup_runs: int = 3
    measurement_runs: int = 10
    timeout_seconds: float | None = None

    # Expected results
    expected_speedup_min: float = 1.0  # Minimum expected speedup
    expected_memory_improvement: bool = False

@dataclass
class BenchmarkResult:
    """Results from running a benchmark case."""
    case: BenchmarkCase
    comparison_results: dict[int, ComparisonResult]  # data_size -> ComparisonResult
    profiling_data: dict[str, Any]
    optimization_analysis: dict[str, Any]

    # Summary metrics
    avg_speedup: float = 0.0
    max_speedup: float = 0.0
    min_speedup: float = float('inf')

    # Scaling analysis
    scaling_behavior: str = "Unknown"
    optimal_data_size: int | None = None

    # Performance characteristics
    ffi_overhead_pct: float = 0.0
    memory_efficiency: float = 0.0

class DataGenerators:
    """Collection of data generators for different benchmark scenarios."""

    @staticmethod
    def small_strings(size: int) -> list[str]:
        """Generate list of small strings for string processing benchmarks."""
        return [f"item_{i:06d}" for i in range(size)]

    @staticmethod
    def large_strings(size: int) -> list[str]:
        """Generate list of large strings for bulk processing benchmarks."""
        base_string = ''.join(random.choices(string.ascii_letters + string.digits, k=1000))
        return [f"{base_string}_{i}" for i in range(size)]

    @staticmethod
    def numeric_lists(size: int) -> list[list[int]]:
        """Generate lists of numeric data for mathematical operations."""
        return [[random.randint(1, 1000) for _ in range(100)] for _ in range(size)]

    @staticmethod
    def mixed_dictionaries(size: int) -> list[dict[str, Any]]:
        """Generate mixed-type dictionaries for complex data processing."""
        dicts = []
        for i in range(size):
            dicts.append({
                'id': i,
                'name': f'item_{i}',
                'value': random.uniform(0, 1000),
                'active': random.choice([True, False]),
                'tags': [f'tag_{j}' for j in range(random.randint(1, 5))],
                'metadata': {'created': time.time(), 'version': '1.0'}
            })
        return dicts

    @staticmethod
    def formid_patterns(size: int) -> list[str]:
        """Generate FormID patterns similar to CLASSIC crash logs."""
        formids = []
        for i in range(size):
            # Generate hex FormIDs in typical patterns
            formid = f"{random.randint(0x01000000, 0xFF000000):08X}"
            formids.append(f"[{formid}] ({i:02X}) SomePlugin.esp")
        return formids

    @staticmethod
    def crash_log_lines(size: int) -> list[str]:
        """Generate crash log lines for parsing benchmarks."""
        lines = []

        # Add header lines
        lines.extend([
            "Fallout 4 v1.10.163.0",
            "F4SE v0.6.21",
            'Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF7C8B2E1B0 Fallout4.exe+0x08DE1B0',
            ""
        ])

        # Add call stack entries
        for i in range(size // 4):
            lines.append(f"\t[{i:3d}] 0x7FF7C{random.randint(1000000, 9999999):07X}    (void*)")

        lines.append("\nMODULES:")

        # Add module entries
        for i in range(size // 4):
            lines.append(f"\t[{random.randint(0, 255):02X}] SomePlugin{i:03d}.esp")

        lines.append("\nF4SE PLUGINS:")

        # Add F4SE plugin entries
        for i in range(size // 4):
            lines.append(f"\t[{i:02X}] F4SEPlugin{i:02d}.dll")

        lines.append("\nPLUGINS:")

        # Add regular plugins
        for i in range(size // 4):
            lines.append(f"\t[{i:02X}] RegularPlugin{i:03d}.esp")

        return lines

    @staticmethod
    def binary_data(size: int) -> list[bytes]:
        """Generate binary data for file I/O benchmarks."""
        return [bytes(random.getrandbits(8) for _ in range(1024)) for _ in range(size)]

class MockRustFunctions:
    """Mock Rust functions for benchmarking when real Rust code isn't available."""

    @staticmethod
    def mock_string_processor(items: list[str]) -> list[str]:
        """Mock Rust string processing - faster than Python."""
        time.sleep(0.0001)  # Simulate Rust processing time
        return [item.upper().replace('_', '-') for item in items]

    @staticmethod
    def mock_numeric_processor(lists: list[list[int]]) -> list[float]:
        """Mock Rust numeric processing."""
        time.sleep(0.0002)  # Simulate processing
        return [sum(lst) / len(lst) if lst else 0.0 for lst in lists]

    @staticmethod
    def mock_formid_extractor(lines: list[str]) -> list[str]:
        """Mock Rust FormID extraction."""
        time.sleep(0.0005)  # Simulate regex processing
        formids = []
        for line in lines:
            if '[' in line and ']' in line:
                start = line.find('[') + 1
                end = line.find(']')
                if end > start:
                    formids.append(line[start:end])
        return formids

    @staticmethod
    def mock_log_parser(lines: list[str]) -> dict[str, list[str]]:
        """Mock Rust log parsing."""
        time.sleep(0.001)  # Simulate parsing
        sections = {'modules': [], 'plugins': [], 'callstack': []}
        current_section = None

        for line in lines:
            line = line.strip()
            if line.startswith('MODULES:'):
                current_section = 'modules'
            elif line.startswith('PLUGINS:'):
                current_section = 'plugins'
            elif line.startswith('\t['):
                if current_section:
                    sections[current_section].append(line)
            elif line.startswith('\t[') and 'void*' in line:
                sections['callstack'].append(line)

        return sections

    @staticmethod
    def mock_batch_processor(items: list[Any]) -> list[Any]:
        """Mock Rust batch processing."""
        time.sleep(0.0001 * len(items))  # Linear scaling
        return [f"processed_{item}" for item in items]

class PythonReferenceFunctions:
    """Reference Python implementations for benchmarking comparison."""

    @staticmethod
    def python_string_processor(items: list[str]) -> list[str]:
        """Python string processing."""
        return [item.upper().replace('_', '-') for item in items]

    @staticmethod
    def python_numeric_processor(lists: list[list[int]]) -> list[float]:
        """Python numeric processing."""
        return [sum(lst) / len(lst) if lst else 0.0 for lst in lists]

    @staticmethod
    def python_formid_extractor(lines: list[str]) -> list[str]:
        """Python FormID extraction using regex."""
        import re
        formid_pattern = re.compile(r'\[([0-9A-F]{8})\]')
        formids = []
        for line in lines:
            matches = formid_pattern.findall(line)
            formids.extend(matches)
        return formids

    @staticmethod
    def python_log_parser(lines: list[str]) -> dict[str, list[str]]:
        """Python log parsing."""
        sections = {'modules': [], 'plugins': [], 'callstack': []}
        current_section = None

        for line in lines:
            line = line.strip()
            if line.startswith('MODULES:'):
                current_section = 'modules'
            elif line.startswith('PLUGINS:'):
                current_section = 'plugins'
            elif line.startswith('\t['):
                if current_section:
                    sections[current_section].append(line)
                elif 'void*' in line:
                    sections['callstack'].append(line)

        return sections

    @staticmethod
    def python_batch_processor(items: list[Any]) -> list[Any]:
        """Python batch processing."""
        return [f"processed_{item}" for item in items]

class FFIBenchmarkSuite:
    """
    Comprehensive benchmark suite for FFI overhead analysis.
    """

    def __init__(self):
        self.analyzer = PerformanceAnalyzer()
        self.optimizer = FFIOptimizer()
        self.profiler = FFIProfiler()

        # Results storage
        self.benchmark_results: dict[str, BenchmarkResult] = {}

        # Configuration
        self.enable_optimization_testing = True
        self.enable_scaling_analysis = True
        self.enable_threading_tests = True

        # Initialize benchmark cases
        self.benchmark_cases = self._create_benchmark_cases()

    def _create_benchmark_cases(self) -> list[BenchmarkCase]:
        """Create all benchmark test cases."""
        cases = []

        # String Processing Benchmarks
        cases.append(BenchmarkCase(
            name="string_processing",
            description="String manipulation with small strings",
            category="String Processing",
            python_func=PythonReferenceFunctions.python_string_processor,
            rust_func=MockRustFunctions.mock_string_processor,
            data_generator=DataGenerators.small_strings,
            data_sizes=[10, 100, 1000, 10000],
            expected_speedup_min=2.0
        ))

        # Numeric Processing Benchmarks
        cases.append(BenchmarkCase(
            name="numeric_processing",
            description="Mathematical operations on numeric data",
            category="Numeric Processing",
            python_func=PythonReferenceFunctions.python_numeric_processor,
            rust_func=MockRustFunctions.mock_numeric_processor,
            data_generator=DataGenerators.numeric_lists,
            data_sizes=[10, 100, 1000],
            expected_speedup_min=5.0
        ))

        # FormID Extraction (CLASSIC-specific)
        cases.append(BenchmarkCase(
            name="formid_extraction",
            description="FormID extraction from crash log lines",
            category="CLASSIC Core",
            python_func=PythonReferenceFunctions.python_formid_extractor,
            rust_func=MockRustFunctions.mock_formid_extractor,
            data_generator=DataGenerators.formid_patterns,
            data_sizes=[100, 1000, 5000],
            expected_speedup_min=10.0
        ))

        # Log Parsing (CLASSIC-specific)
        cases.append(BenchmarkCase(
            name="log_parsing",
            description="Full crash log parsing into structured data",
            category="CLASSIC Core",
            python_func=PythonReferenceFunctions.python_log_parser,
            rust_func=MockRustFunctions.mock_log_parser,
            data_generator=DataGenerators.crash_log_lines,
            data_sizes=[1000, 5000, 10000],
            expected_speedup_min=20.0
        ))

        # Batch Processing
        cases.append(BenchmarkCase(
            name="batch_processing",
            description="Batch processing with different batch sizes",
            category="Optimization",
            python_func=PythonReferenceFunctions.python_batch_processor,
            rust_func=MockRustFunctions.mock_batch_processor,
            data_generator=DataGenerators.small_strings,
            data_sizes=[100, 1000, 10000],
            expected_speedup_min=3.0
        ))

        # Large Data Transfer
        cases.append(BenchmarkCase(
            name="large_data_transfer",
            description="Transfer of large data structures across FFI",
            category="Data Transfer",
            python_func=PythonReferenceFunctions.python_string_processor,
            rust_func=MockRustFunctions.mock_string_processor,
            data_generator=DataGenerators.large_strings,
            data_sizes=[10, 100, 500],  # Large strings, so fewer items
            expected_speedup_min=1.5,
            expected_memory_improvement=True
        ))

        return cases

    def run_single_benchmark(self, case: BenchmarkCase) -> BenchmarkResult:
        """Run a single benchmark case with comprehensive analysis."""
        logger.info(f"Running benchmark: {case.name}")

        comparison_results = {}
        profiling_data = {}

        # Test each data size
        for data_size in case.data_sizes:
            logger.info(f"  Testing data size: {data_size}")

            # Generate test data
            if case.data_generator:
                test_data = case.data_generator(data_size)
            else:
                test_data = list(range(data_size))

            # Skip if no Rust function available
            if case.rust_func is None:
                logger.warning(f"No Rust function available for {case.name}, skipping")
                continue

            # Run performance comparison
            try:
                comparison = self.analyzer.compare_implementations(
                    case.python_func,
                    case.rust_func,
                    test_data,
                    baseline_name="Python",
                    optimized_name="Rust",
                    runs_per_implementation=case.measurement_runs
                )
                comparison_results[data_size] = comparison

            except Exception as e:
                logger.error(f"Benchmark {case.name} failed for size {data_size}: {e}")
                continue

        # Calculate summary metrics
        if comparison_results:
            speedups = [result.speedup_factor for result in comparison_results.values()]
            avg_speedup = sum(speedups) / len(speedups)
            max_speedup = max(speedups)
            min_speedup = min(speedups)
        else:
            avg_speedup = max_speedup = 0.0
            min_speedup = float('inf')

        # Analyze scaling behavior
        scaling_behavior = self._analyze_scaling_behavior(comparison_results)

        # Calculate FFI overhead percentage
        ffi_overhead_pct = self._calculate_ffi_overhead(comparison_results)

        # Calculate memory efficiency
        memory_efficiency = self._calculate_memory_efficiency(comparison_results)

        return BenchmarkResult(
            case=case,
            comparison_results=comparison_results,
            profiling_data=profiling_data,
            optimization_analysis={},
            avg_speedup=avg_speedup,
            max_speedup=max_speedup,
            min_speedup=min_speedup,
            scaling_behavior=scaling_behavior,
            ffi_overhead_pct=ffi_overhead_pct,
            memory_efficiency=memory_efficiency
        )

    def _analyze_scaling_behavior(self, results: dict[int, ComparisonResult]) -> str:
        """Analyze how performance scales with data size."""
        if len(results) < 2:
            return "Insufficient data"

        sizes = sorted(results.keys())
        speedups = [results[size].speedup_factor for size in sizes]

        # Simple trend analysis
        if all(speedups[i] >= speedups[i-1] for i in range(1, len(speedups))):
            if speedups[-1] > speedups[0] * 2:
                return "Improving with scale"
            return "Stable scaling"
        if all(speedups[i] <= speedups[i-1] for i in range(1, len(speedups))):
            return "Degrading with scale"
        return "Variable scaling"

    def _calculate_ffi_overhead(self, results: dict[int, ComparisonResult]) -> float:
        """Calculate average FFI overhead percentage."""
        if not results:
            return 0.0

        total_overhead = 0.0
        count = 0

        for result in results.values():
            if result.optimized_metrics.ffi_overhead > 0 and result.optimized_metrics.wall_time > 0:
                overhead_pct = result.optimized_metrics.ffi_overhead / result.optimized_metrics.wall_time * 100
                total_overhead += overhead_pct
                count += 1

        return total_overhead / count if count > 0 else 0.0

    def _calculate_memory_efficiency(self, results: dict[int, ComparisonResult]) -> float:
        """Calculate memory efficiency score."""
        if not results:
            return 0.0

        total_improvement = 0.0
        count = 0

        for result in results.values():
            if result.memory_improvement_pct != 0:
                total_improvement += result.memory_improvement_pct
                count += 1

        return total_improvement / count if count > 0 else 0.0

    def run_optimization_analysis(self, case: BenchmarkCase) -> dict[str, Any]:
        """Run optimization analysis for a benchmark case."""
        if case.rust_func is None:
            return {}

        logger.info(f"Running optimization analysis for {case.name}")

        # Test with medium-size data
        data_size = case.data_sizes[len(case.data_sizes) // 2]
        test_data = case.data_generator(data_size) if case.data_generator else list(range(data_size))

        # Analyze different optimization strategies
        optimization_results = {}

        try:
            # Test batching optimization
            batch_processor = BatchProcessor()
            batched_func = batch_processor.batch_operation(f"{case.name}_batch")(case.rust_func)

            # Run async batch test (simplified)
            async def test_batching():
                futures = []
                for item in test_data[:100]:  # Limit for testing
                    future = batched_func(item)
                    futures.append(future)

                results = await asyncio.gather(*futures)
                return results

            # Time the batching approach
            start_time = time.perf_counter()
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                batch_results = loop.run_until_complete(test_batching())
                optimization_results['batching_viable'] = True
            except Exception as e:
                logger.debug(f"Batching test failed: {e}")
                optimization_results['batching_viable'] = False
            finally:
                loop.close()

            batch_time = time.perf_counter() - start_time
            optimization_results['batch_time'] = batch_time

            # Test data optimization
            data_optimizer = DataOptimizer()
            optimized_data = []
            optimization_metadata = []

            for item in test_data[:10]:  # Sample optimization
                opt_item, metadata = data_optimizer.optimize_for_rust_transfer(item)
                optimized_data.append(opt_item)
                optimization_metadata.append(metadata)

            # Calculate data optimization benefits
            original_sizes = [metadata['original_size'] for metadata in optimization_metadata]
            optimized_sizes = [metadata['optimized_size'] for metadata in optimization_metadata]

            if original_sizes:
                avg_reduction = sum(metadata['size_reduction_pct'] for metadata in optimization_metadata) / len(optimization_metadata)
                optimization_results['data_optimization_benefit'] = avg_reduction
            else:
                optimization_results['data_optimization_benefit'] = 0.0

        except Exception as e:
            logger.error(f"Optimization analysis failed for {case.name}: {e}")
            optimization_results['error'] = str(e)

        return optimization_results

    def run_threading_benchmark(self, case: BenchmarkCase) -> dict[str, Any]:
        """Test threading performance and GIL impact."""
        if case.rust_func is None or not self.enable_threading_tests:
            return {}

        logger.info(f"Running threading benchmark for {case.name}")

        # Use medium data size
        data_size = case.data_sizes[len(case.data_sizes) // 2]
        test_data = case.data_generator(data_size) if case.data_generator else list(range(data_size))

        threading_results = {}

        try:
            # Single-threaded baseline
            start_time = time.perf_counter()
            for item in test_data[:50]:  # Limited sample
                case.rust_func(item)
            single_thread_time = time.perf_counter() - start_time

            # Multi-threaded test
            def worker_thread(items):
                for item in items:
                    case.rust_func(item)

            # Split data across threads
            thread_count = 4
            chunk_size = len(test_data[:50]) // thread_count
            chunks = [test_data[i:i+chunk_size] for i in range(0, len(test_data[:50]), chunk_size)]

            start_time = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = [executor.submit(worker_thread, chunk) for chunk in chunks]
                concurrent.futures.wait(futures)
            multi_thread_time = time.perf_counter() - start_time

            # Calculate threading efficiency
            threading_speedup = single_thread_time / multi_thread_time if multi_thread_time > 0 else 0
            threading_efficiency = threading_speedup / thread_count * 100  # Percentage of ideal speedup

            threading_results.update({
                'single_thread_time': single_thread_time,
                'multi_thread_time': multi_thread_time,
                'threading_speedup': threading_speedup,
                'threading_efficiency': threading_efficiency,
                'gil_impact_low': threading_efficiency > 70  # Good threading performance
            })

        except Exception as e:
            logger.error(f"Threading benchmark failed for {case.name}: {e}")
            threading_results['error'] = str(e)

        return threading_results

    def run_all_benchmarks(self, categories: list[str] | None = None) -> dict[str, BenchmarkResult]:
        """Run all benchmark cases with comprehensive analysis."""
        logger.info("Starting comprehensive FFI benchmark suite")

        # Filter by categories if specified
        cases_to_run = self.benchmark_cases
        if categories:
            cases_to_run = [case for case in self.benchmark_cases if case.category in categories]

        results = {}

        for case in cases_to_run:
            try:
                # Run main benchmark
                result = self.run_single_benchmark(case)

                # Add optimization analysis
                if self.enable_optimization_testing:
                    result.optimization_analysis = self.run_optimization_analysis(case)

                # Add threading analysis
                if self.enable_threading_tests:
                    threading_data = self.run_threading_benchmark(case)
                    result.profiling_data['threading'] = threading_data

                results[case.name] = result

                # Brief pause between benchmarks
                time.sleep(0.5)
                gc.collect()

            except Exception as e:
                logger.error(f"Benchmark {case.name} failed completely: {e}")
                continue

        self.benchmark_results = results
        logger.info(f"Completed {len(results)} benchmarks")

        return results

    def generate_comprehensive_report(self,
                                    results: dict[str, BenchmarkResult],
                                    output_file: str | Path | None = None) -> str:
        """Generate a comprehensive HTML benchmark report."""

        # Calculate overall statistics
        all_speedups = []
        category_stats = {}

        for result in results.values():
            if result.comparison_results:
                all_speedups.extend([cr.speedup_factor for cr in result.comparison_results.values()])

                # Group by category
                category = result.case.category
                if category not in category_stats:
                    category_stats[category] = []
                category_stats[category].append(result.avg_speedup)

        overall_avg_speedup = sum(all_speedups) / len(all_speedups) if all_speedups else 0
        overall_max_speedup = max(all_speedups) if all_speedups else 0

        # Generate HTML report
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FFI Overhead Benchmark Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f7fa; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 30px; }}
        .header h1 {{ margin: 0; font-size: 2.5em; }}
        .header .subtitle {{ opacity: 0.9; font-size: 1.2em; margin-top: 10px; }}

        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .summary-card {{ background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .summary-card h3 {{ margin: 0 0 15px 0; color: #333; font-size: 1.1em; }}
        .summary-card .metric {{ font-size: 2.2em; font-weight: bold; }}
        .summary-card .metric.excellent {{ color: #28a745; }}
        .summary-card .metric.good {{ color: #17a2b8; }}
        .summary-card .metric.warning {{ color: #ffc107; }}
        .summary-card .metric.poor {{ color: #dc3545; }}

        .benchmark-section {{ background: white; margin-bottom: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden; }}
        .section-header {{ background: #f8f9fa; padding: 20px; border-bottom: 1px solid #e9ecef; }}
        .section-content {{ padding: 25px; }}

        .benchmark-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 25px; }}
        .benchmark-card {{ border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; }}
        .benchmark-card h4 {{ margin: 0 0 15px 0; color: #495057; }}
        .benchmark-card .description {{ color: #6c757d; margin-bottom: 15px; font-style: italic; }}

        .metrics-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        .metrics-table th, .metrics-table td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #dee2e6; }}
        .metrics-table th {{ background: #f8f9fa; font-weight: 600; }}
        .metrics-table .size-col {{ text-align: center; }}
        .metrics-table .number-col {{ text-align: right; font-family: 'SF Mono', 'Monaco', 'Consolas', monospace; }}

        .speedup {{ font-weight: bold; }}
        .speedup.excellent {{ color: #28a745; }}
        .speedup.good {{ color: #17a2b8; }}
        .speedup.fair {{ color: #ffc107; }}
        .speedup.poor {{ color: #dc3545; }}

        .optimization-section {{ background: #f8f9fa; padding: 15px; border-radius: 6px; margin-top: 15px; }}
        .optimization-section h5 {{ margin: 0 0 10px 0; color: #495057; }}
        .optimization-list {{ margin: 0; padding-left: 20px; }}

        .category-summary {{ background: #e3f2fd; padding: 15px; border-radius: 6px; margin-bottom: 20px; }}
        .category-summary h4 {{ margin: 0 0 10px 0; color: #1976d2; }}

        .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 6px; margin: 15px 0; }}
        .recommendation {{ background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 6px; margin: 15px 0; }}

        .footer {{ text-align: center; margin-top: 40px; color: #6c757d; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 FFI Overhead Benchmark Report</h1>
            <div class="subtitle">CLASSIC Rust Integration - Phase 6 Performance Analysis</div>
            <div class="subtitle">Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>

        <div class="summary-grid">
            <div class="summary-card">
                <h3>📊 Overall Performance</h3>
                <div class="metric {'excellent' if overall_avg_speedup > 5 else 'good' if overall_avg_speedup > 2 else 'warning' if overall_avg_speedup > 1.1 else 'poor'}">
                    {overall_avg_speedup:.1f}x
                </div>
                <div>Average Speedup</div>
            </div>

            <div class="summary-card">
                <h3>🎯 Peak Performance</h3>
                <div class="metric {'excellent' if overall_max_speedup > 10 else 'good' if overall_max_speedup > 5 else 'warning'}">
                    {overall_max_speedup:.1f}x
                </div>
                <div>Maximum Speedup</div>
            </div>

            <div class="summary-card">
                <h3>🧪 Benchmarks Run</h3>
                <div class="metric good">{len(results)}</div>
                <div>Test Cases</div>
            </div>

            <div class="summary-card">
                <h3>📂 Categories</h3>
                <div class="metric good">{len(category_stats)}</div>
                <div>Performance Areas</div>
            </div>
        </div>
        """

        # Category performance summary
        if category_stats:
            html += '<div class="benchmark-section"><div class="section-header"><h2>📂 Performance by Category</h2></div><div class="section-content">'

            for category, speedups in category_stats.items():
                avg_speedup = sum(speedups) / len(speedups)
                max_speedup = max(speedups)

                status_class = 'excellent' if avg_speedup > 5 else 'good' if avg_speedup > 2 else 'warning' if avg_speedup > 1.1 else 'poor'

                html += f"""
                <div class="category-summary">
                    <h4>{category}</h4>
                    <p>Average Speedup: <span class="speedup {status_class}">{avg_speedup:.1f}x</span> |
                       Peak Speedup: <span class="speedup {status_class}">{max_speedup:.1f}x</span> |
                       Tests: {len(speedups)}</p>
                </div>
                """

            html += '</div></div>'

        # Individual benchmark results
        html += '<div class="benchmark-section"><div class="section-header"><h2>🔬 Detailed Benchmark Results</h2></div><div class="section-content">'

        html += '<div class="benchmark-grid">'

        for name, result in results.items():
            case = result.case

            html += f"""
            <div class="benchmark-card">
                <h4>{case.name.replace('_', ' ').title()}</h4>
                <div class="description">{case.description}</div>
                <p><strong>Category:</strong> {case.category}</p>

                <table class="metrics-table">
                    <thead>
                        <tr>
                            <th class="size-col">Data Size</th>
                            <th class="number-col">Speedup</th>
                            <th class="number-col">Time (ms)</th>
                            <th class="number-col">Throughput</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for size, comparison in result.comparison_results.items():
                speedup_class = 'excellent' if comparison.speedup_factor > 10 else 'good' if comparison.speedup_factor > 3 else 'fair' if comparison.speedup_factor > 1.2 else 'poor'

                html += f"""
                        <tr>
                            <td class="size-col">{size:,}</td>
                            <td class="number-col"><span class="speedup {speedup_class}">{comparison.speedup_factor:.1f}x</span></td>
                            <td class="number-col">{comparison.optimized_metrics.wall_time*1000:.1f}</td>
                            <td class="number-col">{comparison.optimized_metrics.items_per_second:.0f}/s</td>
                        </tr>
                """

            html += """
                    </tbody>
                </table>
            """

            # Add scaling behavior and optimization info
            html += f"""
                <p><strong>Scaling Behavior:</strong> {result.scaling_behavior}</p>
                <p><strong>FFI Overhead:</strong> {result.ffi_overhead_pct:.1f}%</p>
            """

            # Add optimization analysis if available
            if result.optimization_analysis:
                html += '<div class="optimization-section"><h5>🛠️ Optimization Opportunities</h5><ul class="optimization-list">'

                if result.optimization_analysis.get('batching_viable', False):
                    html += '<li>✅ Batching optimization viable</li>'
                else:
                    html += '<li>❌ Batching not beneficial</li>'

                data_opt_benefit = result.optimization_analysis.get('data_optimization_benefit', 0)
                if data_opt_benefit > 10:
                    html += f'<li>✅ Data optimization: {data_opt_benefit:.1f}% size reduction</li>'
                elif data_opt_benefit > 0:
                    html += f'<li>⚡ Minor data optimization: {data_opt_benefit:.1f}% size reduction</li>'
                else:
                    html += '<li>❌ Data optimization not beneficial</li>'

                html += '</ul></div>'

            html += '</div>'

        html += '</div>'  # End benchmark-grid

        # Overall recommendations
        html += '<div style="margin-top: 30px;">'

        # Warnings
        poor_performers = [name for name, result in results.items() if result.avg_speedup < 1.5]
        if poor_performers:
            html += f"""
            <div class="warning">
                ⚠️ <strong>Low Performance Warning:</strong> The following benchmarks showed limited speedup: {', '.join(poor_performers)}.
                Consider investigating FFI overhead or algorithm efficiency.
            </div>
            """

        # Recommendations
        excellent_performers = [name for name, result in results.items() if result.avg_speedup > 10]
        if excellent_performers:
            html += f"""
            <div class="recommendation">
                🎯 <strong>Excellent Results:</strong> Outstanding performance in: {', '.join(excellent_performers)}.
                These patterns should be prioritized for Rust migration.
            </div>
            """

        html += '</div></div></div>'  # End section content and section

        # Footer
        html += f"""
        <div class="footer">
            <p>Report generated by CLASSIC FFI Benchmark Suite</p>
            <p>Python {sys.version} | Benchmarks completed in {len(results)} test cases</p>
        </div>

    </div>
</body>
</html>
        """

        # Save to file if requested
        if output_file:
            output_path = Path(output_file)
            with Path(output_path).open('w', encoding='utf-8') as f:
                f.write(html)
            logger.info(f"Comprehensive benchmark report saved to {output_path}")

        return html

    def export_results(self, results: dict[str, BenchmarkResult], filepath: str | Path):
        """Export benchmark results to JSON for further analysis."""
        export_data = {
            'metadata': {
                'timestamp': time.time(),
                'python_version': sys.version,
                'benchmark_count': len(results)
            },
            'results': {}
        }

        for name, result in results.items():
            result_data = {
                'case': {
                    'name': result.case.name,
                    'description': result.case.description,
                    'category': result.case.category,
                    'data_sizes': result.case.data_sizes
                },
                'performance': {
                    'avg_speedup': result.avg_speedup,
                    'max_speedup': result.max_speedup,
                    'min_speedup': result.min_speedup,
                    'scaling_behavior': result.scaling_behavior,
                    'ffi_overhead_pct': result.ffi_overhead_pct,
                    'memory_efficiency': result.memory_efficiency
                },
                'comparison_results': {}
            }

            # Export comparison results
            for size, comparison in result.comparison_results.items():
                result_data['comparison_results'][str(size)] = {
                    'speedup_factor': comparison.speedup_factor,
                    'memory_improvement_pct': comparison.memory_improvement_pct,
                    'throughput_improvement_pct': comparison.throughput_improvement_pct,
                    'is_significant': comparison.is_significant,
                    'baseline_time': comparison.baseline_metrics.wall_time,
                    'optimized_time': comparison.optimized_metrics.wall_time
                }

            export_data['results'][name] = result_data

        with Path(filepath).open('w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info(f"Benchmark results exported to {filepath}")

# Command-line interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Run FFI overhead benchmarks for CLASSIC Rust integration')
    parser.add_argument('--categories', nargs='*', help='Specific categories to benchmark')
    parser.add_argument('--output', '-o', help='Output file for HTML report')
    parser.add_argument('--export', help='Export results to JSON file')
    parser.add_argument('--no-optimization', action='store_true', help='Skip optimization analysis')
    parser.add_argument('--no-threading', action='store_true', help='Skip threading tests')

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Create benchmark suite
    suite = FFIBenchmarkSuite()

    if args.no_optimization:
        suite.enable_optimization_testing = False
    if args.no_threading:
        suite.enable_threading_tests = False

    print("🚀 Starting CLASSIC FFI Overhead Benchmark Suite")
    print("=" * 60)

    # Run benchmarks
    results = suite.run_all_benchmarks(categories=args.categories)

    # Print summary
    if results:
        all_speedups = []
        for result in results.values():
            if result.comparison_results:
                all_speedups.extend([cr.speedup_factor for cr in result.comparison_results.values()])

        if all_speedups:
            avg_speedup = sum(all_speedups) / len(all_speedups)
            max_speedup = max(all_speedups)

            print("\n📊 BENCHMARK SUMMARY:")
            print(f"   Benchmarks completed: {len(results)}")
            print(f"   Average speedup: {avg_speedup:.1f}x")
            print(f"   Maximum speedup: {max_speedup:.1f}x")

            if avg_speedup > 5:
                print("   🎯 EXCELLENT: Outstanding FFI performance!")
            elif avg_speedup > 2:
                print("   ✅ GOOD: Strong performance improvements")
            elif avg_speedup > 1.2:
                print("   📈 FAIR: Moderate improvements")
            else:
                print("   ⚠️ INVESTIGATE: Limited performance gains")

    # Generate reports
    if args.output:
        report = suite.generate_comprehensive_report(results, args.output)
        print(f"📄 HTML report saved to: {args.output}")

    if args.export:
        suite.export_results(results, args.export)
        print(f"💾 Results exported to: {args.export}")

    print("✅ Benchmark suite completed!")
