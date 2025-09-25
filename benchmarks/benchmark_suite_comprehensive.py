#!/usr/bin/env python3
"""
Comprehensive benchmarking suite for Phase 6 Rust migration validation.

This suite provides exhaustive performance testing of all Rust components against
their Python implementations, including micro-benchmarks, macro-benchmarks,
memory profiling, and regression testing capabilities.

Performance targets for Phase 6:
- Log parsing: 150x speedup
- FormID analysis: 50x speedup
- Plugin analysis: 30x speedup
- Record scanning: 40x speedup
- Report generation: 75x speedup
- Database operations: 25x speedup
- File I/O operations: 10-20x speedup
- End-to-end processing: 10x overall speedup

Features:
- Comprehensive micro and macro benchmarks
- Memory usage profiling and analysis
- Realistic test data generation
- Regression testing with baseline storage
- Detailed reporting with optimization recommendations
- Batch processing performance validation
- Statistical analysis with confidence intervals
- Performance trend tracking over time
"""

from __future__ import annotations

import asyncio
import gc
import json
import logging
import os
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Dict, List, Optional, Tuple, Union

# Add parent directory to path to import ClassicLib
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging before other imports
logger = logging.getLogger(__name__)

# Import benchmark modules with proper path handling
try:
    # Try absolute imports first
    from benchmarks.micro_benchmarks.benchmark_log_parsing import LogParsingBenchmark
    from benchmarks.micro_benchmarks.benchmark_formid_analysis import FormIDBenchmark
    from benchmarks.micro_benchmarks.benchmark_plugin_analysis import PluginBenchmark
    from benchmarks.micro_benchmarks.benchmark_record_scanning import RecordScanBenchmark
    from benchmarks.micro_benchmarks.benchmark_report_generation import ReportGenBenchmark
    from benchmarks.micro_benchmarks.benchmark_database_ops import DatabaseBenchmark
    from benchmarks.micro_benchmarks.benchmark_file_io import FileIOBenchmark

    from benchmarks.macro_benchmarks.benchmark_end_to_end import EndToEndBenchmark
    from benchmarks.macro_benchmarks.benchmark_batch_processing import BatchProcessingBenchmark

    # Import test data generators
    from benchmarks.test_data.realistic_data_generator import RealisticDataGenerator
except ImportError:
    # Handle relative imports when run from benchmarks directory
    try:
        from micro_benchmarks.benchmark_log_parsing import LogParsingBenchmark
        from micro_benchmarks.benchmark_formid_analysis import FormIDBenchmark
        from micro_benchmarks.benchmark_plugin_analysis import PluginBenchmark
        from micro_benchmarks.benchmark_record_scanning import RecordScanBenchmark
        from micro_benchmarks.benchmark_report_generation import ReportGenBenchmark
        from micro_benchmarks.benchmark_database_ops import DatabaseBenchmark
        from micro_benchmarks.benchmark_file_io import FileIOBenchmark

        from macro_benchmarks.benchmark_end_to_end import EndToEndBenchmark
        from macro_benchmarks.benchmark_batch_processing import BatchProcessingBenchmark

        # Import test data generators
        from test_data.realistic_data_generator import RealisticDataGenerator
    except ImportError as e:
        logger.error(f"Failed to import benchmark modules: {e}")
        logger.error("Please ensure all benchmark modules are available")
        raise

# Import Rust integration for availability checking
from ClassicLib.RustAcceleration import (
    RustAcceleration,
    ComponentType,
    OptimizationLevel,
    get_rust_acceleration,
)
from ClassicLib.integration.status import (
    RUST_AVAILABLE,
    get_rust_component_status,
    print_rust_status,
)


class BenchmarkType(Enum):
    """Types of benchmarks available."""
    MICRO = "micro"
    MACRO = "macro"
    MEMORY = "memory"
    REGRESSION = "regression"
    ALL = "all"


class TestDataSize(Enum):
    """Standard test data sizes for consistent benchmarking."""
    MINIMAL = "minimal"  # 2 files, 20 lines each - Immediate validation
    TINY = "tiny"      # 10 files, 100 lines each - Quick validation
    SMALL = "small"    # 50 files, 500 lines each - Standard testing
    MEDIUM = "medium"  # 100 files, 1000 lines each - Realistic workload
    LARGE = "large"    # 500 files, 2000 lines each - Stress testing
    HUGE = "huge"      # 1000 files, 5000 lines each - Maximum stress


@dataclass
class BenchmarkMetrics:
    """
    Comprehensive metrics for a single benchmark run with statistical analysis.

    This class captures not just timing information but also memory usage,
    cache performance, and error rates to provide a complete picture of
    component performance.
    """
    component_name: str
    implementation: str  # "rust" or "python"
    test_size: TestDataSize

    # Timing metrics (in seconds)
    execution_times: List[float] = field(default_factory=list)
    min_time: float = float('inf')
    max_time: float = 0.0
    mean_time: float = 0.0
    median_time: float = 0.0
    std_dev: float = 0.0

    # Memory metrics (in bytes)
    peak_memory: int = 0
    memory_increase: int = 0
    allocations: int = 0

    # Performance metrics
    throughput: float = 0.0  # operations per second
    cache_hits: int = 0
    cache_misses: int = 0

    # Quality metrics
    errors: int = 0
    warnings: int = 0
    success_rate: float = 100.0

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    test_iterations: int = 0

    def add_execution_time(self, time_seconds: float) -> None:
        """Add a single execution time and update statistics."""
        self.execution_times.append(time_seconds)
        self.test_iterations += 1

        # Update timing statistics
        self.min_time = min(self.min_time, time_seconds)
        self.max_time = max(self.max_time, time_seconds)

        if len(self.execution_times) >= 2:
            self.mean_time = mean(self.execution_times)
            self.median_time = median(self.execution_times)
            self.std_dev = stdev(self.execution_times)
        else:
            self.mean_time = time_seconds
            self.median_time = time_seconds
            self.std_dev = 0.0

        # Calculate throughput (operations per second)
        if self.mean_time > 0:
            self.throughput = 1.0 / self.mean_time

    def calculate_confidence_interval(self, confidence: float = 0.95) -> Tuple[float, float]:
        """
        Calculate confidence interval for execution times.

        Args:
            confidence: Confidence level (default 95%)

        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        if len(self.execution_times) < 2:
            return (self.mean_time, self.mean_time)

        # Use t-distribution for small sample sizes
        import math
        n = len(self.execution_times)

        # For simplicity, use 1.96 (z-score for 95% confidence)
        # In a production system, you'd use scipy.stats.t
        z_score = 1.96
        margin_error = z_score * (self.std_dev / math.sqrt(n))

        return (self.mean_time - margin_error, self.mean_time + margin_error)

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization."""
        lower_ci, upper_ci = self.calculate_confidence_interval()

        return {
            'component_name': self.component_name,
            'implementation': self.implementation,
            'test_size': self.test_size.value,
            'timing': {
                'min_time': self.min_time,
                'max_time': self.max_time,
                'mean_time': self.mean_time,
                'median_time': self.median_time,
                'std_dev': self.std_dev,
                'confidence_interval_95': [lower_ci, upper_ci],
                'execution_times': self.execution_times,
            },
            'memory': {
                'peak_memory': self.peak_memory,
                'memory_increase': self.memory_increase,
                'allocations': self.allocations,
            },
            'performance': {
                'throughput': self.throughput,
                'cache_hit_rate': self.cache_hit_rate,
                'cache_hits': self.cache_hits,
                'cache_misses': self.cache_misses,
            },
            'quality': {
                'errors': self.errors,
                'warnings': self.warnings,
                'success_rate': self.success_rate,
            },
            'metadata': {
                'timestamp': self.timestamp.isoformat(),
                'test_iterations': self.test_iterations,
            }
        }


@dataclass
class ComparisonResult:
    """
    Results comparing Rust vs Python implementations with detailed analysis.

    This class provides comprehensive comparison data including speedup calculations,
    memory efficiency analysis, and recommendations for optimization.
    """
    component_name: str
    test_size: TestDataSize

    rust_metrics: BenchmarkMetrics
    python_metrics: BenchmarkMetrics

    # Performance comparison
    speedup_factor: float = 0.0
    memory_efficiency: float = 0.0  # Rust memory / Python memory
    throughput_improvement: float = 0.0

    # Statistical significance
    performance_significant: bool = False
    confidence_level: float = 0.95

    # Target achievement
    target_speedup: float = 0.0
    target_achieved: bool = False
    target_percentage: float = 0.0

    # Recommendations
    optimization_recommendations: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Calculate comparison metrics after initialization."""
        self._calculate_comparison_metrics()
        self._generate_recommendations()

    def _calculate_comparison_metrics(self):
        """Calculate speedup and efficiency metrics."""
        # Performance comparison
        if self.python_metrics.mean_time > 0:
            self.speedup_factor = self.python_metrics.mean_time / self.rust_metrics.mean_time

        # Memory efficiency (lower is better)
        if self.python_metrics.peak_memory > 0:
            self.memory_efficiency = self.rust_metrics.peak_memory / self.python_metrics.peak_memory

        # Throughput improvement
        if self.python_metrics.throughput > 0:
            self.throughput_improvement = (
                (self.rust_metrics.throughput - self.python_metrics.throughput)
                / self.python_metrics.throughput * 100
            )

        # Check target achievement
        if self.target_speedup > 0:
            self.target_percentage = (self.speedup_factor / self.target_speedup) * 100
            self.target_achieved = self.speedup_factor >= self.target_speedup

        # Statistical significance (simplified check)
        # In production, use proper statistical tests
        rust_ci_lower, rust_ci_upper = self.rust_metrics.calculate_confidence_interval()
        python_ci_lower, python_ci_upper = self.python_metrics.calculate_confidence_interval()

        # Check if confidence intervals don't overlap
        self.performance_significant = (rust_ci_upper < python_ci_lower) or (python_ci_upper < rust_ci_lower)

    def _generate_recommendations(self):
        """Generate optimization recommendations based on results."""
        recommendations = []

        # Performance recommendations
        if self.speedup_factor < self.target_speedup * 0.8:  # Less than 80% of target
            recommendations.append(
                f"Performance below target ({self.target_percentage:.1f}% achieved). "
                f"Consider algorithm optimizations or parallel processing."
            )

        if self.rust_metrics.std_dev > self.rust_metrics.mean_time * 0.2:  # High variance
            recommendations.append(
                "High performance variance detected. Investigate caching or "
                "memory allocation patterns."
            )

        # Memory recommendations
        if self.memory_efficiency > 1.0:  # Rust uses more memory
            recommendations.append(
                f"Rust implementation uses {self.memory_efficiency:.2f}x more memory. "
                f"Review memory allocation strategies."
            )

        # Cache recommendations
        if self.rust_metrics.cache_hit_rate < 80:
            recommendations.append(
                f"Low cache hit rate ({self.rust_metrics.cache_hit_rate:.1f}%). "
                f"Consider increasing cache sizes or improving cache strategies."
            )

        # Error rate recommendations
        if self.rust_metrics.success_rate < 99:
            recommendations.append(
                f"Error rate concern ({self.rust_metrics.success_rate:.1f}% success). "
                f"Review error handling and edge cases."
            )

        # Statistical significance
        if not self.performance_significant:
            recommendations.append(
                "Performance difference not statistically significant. "
                "Increase test iterations or sample size."
            )

        self.optimization_recommendations = recommendations

    def to_dict(self) -> Dict[str, Any]:
        """Convert comparison to dictionary for JSON serialization."""
        return {
            'component_name': self.component_name,
            'test_size': self.test_size.value,
            'comparison': {
                'speedup_factor': self.speedup_factor,
                'memory_efficiency': self.memory_efficiency,
                'throughput_improvement': self.throughput_improvement,
            },
            'target_analysis': {
                'target_speedup': self.target_speedup,
                'target_achieved': self.target_achieved,
                'target_percentage': self.target_percentage,
            },
            'statistical': {
                'performance_significant': self.performance_significant,
                'confidence_level': self.confidence_level,
            },
            'rust_metrics': self.rust_metrics.to_dict(),
            'python_metrics': self.python_metrics.to_dict(),
            'recommendations': self.optimization_recommendations,
        }


class ComprehensiveBenchmarkSuite:
    """
    Main orchestrator for the comprehensive Rust migration benchmarking suite.

    This class coordinates all benchmark types, manages test data generation,
    handles result collection and analysis, and provides detailed reporting
    with actionable optimization recommendations.
    """

    # Performance targets for each component (speedup factors)
    PERFORMANCE_TARGETS = {
        ComponentType.PARSER: 150.0,
        ComponentType.FORMID_ANALYZER: 50.0,
        ComponentType.PLUGIN_ANALYZER: 30.0,
        ComponentType.RECORD_SCANNER: 40.0,
        ComponentType.REPORT_GENERATION: 75.0,
        ComponentType.DATABASE_POOL: 25.0,
        ComponentType.FILE_IO_CORE: 15.0,  # Middle of 10-20x range
    }

    def __init__(self, output_dir: Optional[Path] = None, baseline_dir: Optional[Path] = None):
        """
        Initialize the comprehensive benchmark suite.

        Args:
            output_dir: Directory for benchmark results (default: ./benchmarks/reports)
            baseline_dir: Directory for baseline storage (default: ./performance_baselines)
        """
        self.output_dir = output_dir or Path("benchmarks/reports")
        self.baseline_dir = baseline_dir or Path("performance_baselines")

        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.baseline_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.rust_acceleration = get_rust_acceleration()
        self.data_generator = RealisticDataGenerator()

        # Initialize benchmark modules
        self.micro_benchmarks = {
            ComponentType.PARSER: LogParsingBenchmark(),
            ComponentType.FORMID_ANALYZER: FormIDBenchmark(),
            ComponentType.PLUGIN_ANALYZER: PluginBenchmark(),
            ComponentType.RECORD_SCANNER: RecordScanBenchmark(),
            ComponentType.REPORT_GENERATION: ReportGenBenchmark(),
            ComponentType.DATABASE_POOL: DatabaseBenchmark(),
            ComponentType.FILE_IO_CORE: FileIOBenchmark(),
        }

        self.macro_benchmarks = {
            'end_to_end': EndToEndBenchmark(),
            'batch_processing': BatchProcessingBenchmark(),
        }

        # Results storage
        self.results: Dict[str, Any] = {}
        self.comparison_results: List[ComparisonResult] = []

        # Configure logging for detailed tracing
        self._setup_logging()

    def _setup_logging(self):
        """Configure detailed logging for benchmark operations."""
        log_file = self.output_dir / f"benchmark_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        # Create file handler with detailed formatting
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Create console handler for important messages
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Create detailed formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Configure logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.setLevel(logging.DEBUG)

    def run_comprehensive_benchmark(
        self,
        benchmark_types: List[BenchmarkType] = None,
        test_sizes: List[TestDataSize] = None,
        iterations: int = 5,
        include_memory_profiling: bool = True,
        parallel_execution: bool = False
    ) -> Dict[str, Any]:
        """
        Run comprehensive benchmarks with detailed performance analysis.

        Args:
            benchmark_types: Types of benchmarks to run (default: all)
            test_sizes: Test data sizes to use (default: small, medium, large)
            iterations: Number of iterations per test (default: 5)
            include_memory_profiling: Enable memory profiling (default: True)
            parallel_execution: Run benchmarks in parallel where possible

        Returns:
            Comprehensive results dictionary with all benchmark data
        """
        logger.info("=" * 80)
        logger.info("🚀 STARTING COMPREHENSIVE BENCHMARK SUITE - Phase 6 Validation")
        logger.info("=" * 80)

        # Set defaults
        if benchmark_types is None:
            benchmark_types = [BenchmarkType.MICRO, BenchmarkType.MACRO]
        if test_sizes is None:
            test_sizes = [TestDataSize.SMALL, TestDataSize.MEDIUM, TestDataSize.LARGE]

        # Check Rust availability
        self._log_rust_status()

        start_time = time.time()
        results = {
            'metadata': {
                'start_time': datetime.now().isoformat(),
                'benchmark_types': [bt.value for bt in benchmark_types],
                'test_sizes': [ts.value for ts in test_sizes],
                'iterations': iterations,
                'memory_profiling': include_memory_profiling,
                'parallel_execution': parallel_execution,
                'rust_status': get_rust_component_status(),
            },
            'micro_benchmarks': {},
            'macro_benchmarks': {},
            'memory_analysis': {},
            'comparisons': [],
            'summary': {},
        }

        try:
            # Generate test data for all sizes
            logger.info("📊 Generating realistic test data...")
            test_data = self._generate_test_data_suite(test_sizes)

            # Run micro-benchmarks
            if BenchmarkType.MICRO in benchmark_types or BenchmarkType.ALL in benchmark_types:
                logger.info("\n🔬 Running micro-benchmarks...")
                micro_results = self._run_micro_benchmarks(
                    test_data, iterations, include_memory_profiling, parallel_execution
                )
                results['micro_benchmarks'] = micro_results

            # Run macro-benchmarks
            if BenchmarkType.MACRO in benchmark_types or BenchmarkType.ALL in benchmark_types:
                logger.info("\n🏗️ Running macro-benchmarks...")
                macro_results = self._run_macro_benchmarks(
                    test_data, iterations, include_memory_profiling
                )
                results['macro_benchmarks'] = macro_results

            # Perform memory analysis
            if include_memory_profiling:
                logger.info("\n💾 Performing memory analysis...")
                memory_results = self._run_memory_analysis(test_data)
                results['memory_analysis'] = memory_results

            # Generate comparisons and analysis
            logger.info("\n📈 Generating performance comparisons...")
            comparison_results = self._generate_comparisons(results)
            results['comparisons'] = [comp.to_dict() for comp in comparison_results]

            # Generate summary
            logger.info("\n📋 Generating benchmark summary...")
            summary = self._generate_summary(results, comparison_results)
            results['summary'] = summary

            # Save results
            self._save_results(results)

            # Generate reports
            self._generate_reports(results, comparison_results)

        except Exception as e:
            logger.error(f"❌ Benchmark suite failed: {e}")
            import traceback
            logger.error(traceback.format_exception(type(e), e, e.__traceback__))
            raise
        finally:
            total_time = time.time() - start_time
            results['metadata']['total_time'] = total_time
            logger.info(f"\n✅ Benchmark suite completed in {total_time:.2f} seconds")

        return results

    def _log_rust_status(self):
        """Log current Rust component status for benchmark context."""
        logger.info("\n📊 Rust Component Status:")
        status = get_rust_component_status()

        active_components = [k for k, v in status['available'].items() if v]
        inactive_components = [k for k, v in status['available'].items() if not v]

        logger.info(f"   Active: {len(active_components)}/{status['total_count']} components")
        if active_components:
            logger.info(f"   ✅ {', '.join(active_components)}")
        if inactive_components:
            logger.info(f"   ❌ {', '.join(inactive_components)}")
            logger.info("   ⚠️  Some benchmarks will use Python fallbacks")

    def _generate_test_data_suite(self, test_sizes: List[TestDataSize]) -> Dict[TestDataSize, Any]:
        """
        Generate comprehensive test data for all benchmark sizes.

        This method creates realistic test scenarios that represent actual
        CLASSIC usage patterns, including various log formats, plugin
        configurations, and file structures.

        Args:
            test_sizes: List of test data sizes to generate

        Returns:
            Dictionary mapping test sizes to generated test data
        """
        logger.info("🏗️ Generating realistic test data suite...")

        test_data = {}

        for size in test_sizes:
            logger.info(f"   Generating {size.value} dataset...")

            # Size parameters
            size_params = {
                TestDataSize.MINIMAL: {'files': 2, 'lines': 20, 'plugins': 10},
                TestDataSize.TINY: {'files': 10, 'lines': 100, 'plugins': 50},
                TestDataSize.SMALL: {'files': 50, 'lines': 500, 'plugins': 100},
                TestDataSize.MEDIUM: {'files': 100, 'lines': 1000, 'plugins': 200},
                TestDataSize.LARGE: {'files': 500, 'lines': 2000, 'plugins': 500},
                TestDataSize.HUGE: {'files': 1000, 'lines': 5000, 'plugins': 1000},
            }[size]

            # Generate comprehensive test data
            # For minimal datasets, skip expensive features
            include_formids = size != TestDataSize.MINIMAL
            include_edge_cases = size not in [TestDataSize.MINIMAL, TestDataSize.TINY]

            dataset = self.data_generator.generate_comprehensive_dataset(
                num_crash_logs=size_params['files'],
                lines_per_log=size_params['lines'],
                num_plugins=size_params['plugins'],
                include_formids=include_formids,
                include_edge_cases=include_edge_cases,
                corruption_probability=0.02 if include_edge_cases else 0.0,  # 2% chance of corrupted data
                vary_formats=size != TestDataSize.MINIMAL  # Include different log formats
            )

            test_data[size] = dataset

            logger.info(f"   ✅ {size.value}: {len(dataset['crash_logs'])} logs, "
                       f"{sum(len(log) for log in dataset['crash_logs'])} total lines, "
                       f"{len(dataset['plugins'])} plugins")

        return test_data

    def _run_micro_benchmarks(
        self,
        test_data: Dict[TestDataSize, Any],
        iterations: int,
        include_memory: bool,
        parallel: bool
    ) -> Dict[str, Any]:
        """
        Execute all micro-benchmarks for individual components.

        Micro-benchmarks test individual components in isolation to measure
        their specific performance characteristics and identify optimization
        opportunities at the component level.

        Args:
            test_data: Generated test data for all sizes
            iterations: Number of iterations per benchmark
            include_memory: Whether to include memory profiling
            parallel: Whether to run benchmarks in parallel

        Returns:
            Dictionary containing all micro-benchmark results
        """
        logger.info("🔬 Executing micro-benchmark suite...")

        micro_results = {}

        # Run benchmarks for each component
        for component_type, benchmark in self.micro_benchmarks.items():
            component_name = component_type.value
            logger.info(f"\n   🧪 Testing {component_name}...")

            component_results = {}

            for test_size, dataset in test_data.items():
                logger.info(f"      📏 Size: {test_size.value}")

                # Setup memory tracing if requested
                if include_memory:
                    tracemalloc.start()

                try:
                    # Run Rust benchmark if available
                    rust_metrics = None
                    if RUST_AVAILABLE.get(component_name, False):
                        rust_metrics = self._run_single_benchmark(
                            benchmark, "rust", dataset, test_size, iterations
                        )
                        logger.info(f"         ✅ Rust: {rust_metrics.mean_time:.4f}s avg")

                    # Run Python benchmark
                    python_metrics = self._run_single_benchmark(
                        benchmark, "python", dataset, test_size, iterations
                    )
                    logger.info(f"         ✅ Python: {python_metrics.mean_time:.4f}s avg")

                    # Store results
                    size_results = {
                        'python': python_metrics.to_dict()
                    }
                    if rust_metrics:
                        size_results['rust'] = rust_metrics.to_dict()

                        # Calculate speedup
                        speedup = python_metrics.mean_time / rust_metrics.mean_time
                        logger.info(f"         🚀 Speedup: {speedup:.1f}x")

                    component_results[test_size.value] = size_results

                except Exception as e:
                    logger.error(f"❌ Benchmark failed for {component_name} {test_size.value}: {e}")
                    component_results[test_size.value] = {'error': str(e)}

                finally:
                    if include_memory:
                        tracemalloc.stop()

            micro_results[component_name] = component_results

        return micro_results

    def _run_single_benchmark(
        self,
        benchmark,
        implementation: str,
        dataset: Any,
        test_size: TestDataSize,
        iterations: int
    ) -> BenchmarkMetrics:
        """
        Run a single benchmark with detailed metrics collection.

        This method handles the actual benchmark execution, timing measurement,
        memory profiling, and error collection for a single component test.

        Args:
            benchmark: Benchmark instance to run
            implementation: "rust" or "python"
            dataset: Test data to use
            test_size: Size of test data
            iterations: Number of iterations to run

        Returns:
            BenchmarkMetrics with comprehensive performance data
        """
        component_name = getattr(benchmark, 'component_name', 'unknown')
        metrics = BenchmarkMetrics(
            component_name=component_name,
            implementation=implementation,
            test_size=test_size
        )

        # Warm-up run (not measured)
        try:
            benchmark.run_benchmark(implementation, dataset, warm_up=True)
        except Exception as e:
            logger.debug(f"Warm-up failed for {component_name} {implementation}: {e}")

        # Measured iterations
        for i in range(iterations):
            # Force garbage collection for consistent measurements
            gc.collect()

            # Start memory tracking
            if tracemalloc.is_tracing():
                snapshot_before = tracemalloc.take_snapshot()

            try:
                # Time the benchmark execution
                start_time = time.perf_counter()

                # Run the actual benchmark
                result = benchmark.run_benchmark(implementation, dataset)

                end_time = time.perf_counter()
                execution_time = end_time - start_time

                # Record timing
                metrics.add_execution_time(execution_time)

                # Record memory usage if tracking
                if tracemalloc.is_tracing():
                    snapshot_after = tracemalloc.take_snapshot()

                    # Calculate memory statistics
                    top_stats = snapshot_after.compare_to(snapshot_before, 'lineno')
                    total_size_diff = sum(stat.size_diff for stat in top_stats)

                    if total_size_diff > metrics.memory_increase:
                        metrics.memory_increase = total_size_diff

                    # Record peak memory
                    current_peak = snapshot_after.statistics('lineno')[0].size
                    if current_peak > metrics.peak_memory:
                        metrics.peak_memory = current_peak

                # Extract additional metrics from benchmark result if available
                if hasattr(result, 'cache_hits'):
                    metrics.cache_hits += getattr(result, 'cache_hits', 0)
                    metrics.cache_misses += getattr(result, 'cache_misses', 0)

            except Exception as e:
                logger.debug(f"Iteration {i+1} failed: {e}")
                metrics.errors += 1

                # Record a penalty time for failed iterations
                metrics.add_execution_time(float('inf'))

        # Calculate success rate
        successful_iterations = iterations - metrics.errors
        metrics.success_rate = (successful_iterations / iterations) * 100

        return metrics

    def _run_macro_benchmarks(
        self,
        test_data: Dict[TestDataSize, Any],
        iterations: int,
        include_memory: bool
    ) -> Dict[str, Any]:
        """
        Execute macro-benchmarks for end-to-end system testing.

        Macro-benchmarks test complete workflows and pipelines to measure
        overall system performance and identify bottlenecks in the integration
        between components.

        Args:
            test_data: Generated test data for all sizes
            iterations: Number of iterations per benchmark
            include_memory: Whether to include memory profiling

        Returns:
            Dictionary containing all macro-benchmark results
        """
        logger.info("🏗️ Executing macro-benchmark suite...")

        macro_results = {}

        for benchmark_name, benchmark in self.macro_benchmarks.items():
            logger.info(f"\n   🎯 Testing {benchmark_name}...")

            benchmark_results = {}

            for test_size, dataset in test_data.items():
                logger.info(f"      📏 Size: {test_size.value}")

                try:
                    # Run end-to-end benchmark
                    if include_memory:
                        tracemalloc.start()

                    # Time the complete workflow
                    times = []
                    memory_peaks = []

                    for i in range(iterations):
                        gc.collect()

                        start_time = time.perf_counter()

                        # Run complete pipeline
                        result = benchmark.run_complete_pipeline(dataset)

                        end_time = time.perf_counter()
                        execution_time = end_time - start_time
                        times.append(execution_time)

                        if tracemalloc.is_tracing():
                            snapshot = tracemalloc.take_snapshot()
                            peak = max(stat.size for stat in snapshot.statistics('lineno'))
                            memory_peaks.append(peak)

                    # Calculate statistics
                    avg_time = mean(times)
                    median_time = median(times)
                    min_time = min(times)
                    max_time = max(times)
                    std_time = stdev(times) if len(times) > 1 else 0

                    # Store results
                    size_results = {
                        'timing': {
                            'avg_time': avg_time,
                            'median_time': median_time,
                            'min_time': min_time,
                            'max_time': max_time,
                            'std_dev': std_time,
                            'all_times': times,
                        },
                        'throughput': len(dataset.get('crash_logs', [])) / avg_time,
                        'metadata': {
                            'iterations': iterations,
                            'data_size': len(dataset.get('crash_logs', [])),
                        }
                    }

                    if memory_peaks:
                        size_results['memory'] = {
                            'peak_memory': max(memory_peaks),
                            'avg_memory': mean(memory_peaks),
                            'memory_variance': stdev(memory_peaks) if len(memory_peaks) > 1 else 0,
                        }

                    logger.info(f"         ⏱️ Avg: {avg_time:.4f}s, "
                               f"Throughput: {size_results['throughput']:.1f} logs/sec")

                    benchmark_results[test_size.value] = size_results

                except Exception as e:
                    logger.error(f"❌ Macro benchmark failed for {benchmark_name} {test_size.value}: {e}")
                    benchmark_results[test_size.value] = {'error': str(e)}

                finally:
                    if tracemalloc.is_tracing():
                        tracemalloc.stop()

            macro_results[benchmark_name] = benchmark_results

        return macro_results

    def _run_memory_analysis(self, test_data: Dict[TestDataSize, Any]) -> Dict[str, Any]:
        """
        Perform detailed memory usage analysis across all components.

        This method provides comprehensive memory profiling to identify
        memory leaks, excessive allocations, and opportunities for
        memory optimization in both Rust and Python implementations.

        Args:
            test_data: Generated test data for analysis

        Returns:
            Dictionary containing detailed memory analysis results
        """
        logger.info("💾 Performing comprehensive memory analysis...")

        memory_results = {}

        # Memory analysis for each component
        for component_type in self.micro_benchmarks:
            component_name = component_type.value
            logger.info(f"   🔍 Analyzing memory usage for {component_name}")

            component_memory = {}

            # Test with medium dataset for detailed analysis
            medium_data = test_data.get(TestDataSize.MEDIUM, {})
            if not medium_data:
                logger.warning(f"   ⚠️ No medium test data for {component_name}")
                continue

            try:
                # Start detailed memory tracing
                tracemalloc.start(10)  # Track top 10 frames

                # Get baseline memory
                baseline_snapshot = tracemalloc.take_snapshot()

                # Run both implementations if available
                implementations = ['python']
                if RUST_AVAILABLE.get(component_name, False):
                    implementations.append('rust')

                for impl in implementations:
                    logger.info(f"      📊 Memory profiling {impl} implementation")

                    # Take pre-execution snapshot
                    gc.collect()
                    pre_snapshot = tracemalloc.take_snapshot()

                    try:
                        # Run benchmark multiple times to detect memory leaks
                        benchmark = self.micro_benchmarks[component_type]

                        for run in range(3):  # 3 runs to check for accumulation
                            benchmark.run_benchmark(impl, medium_data)

                        # Take post-execution snapshot
                        gc.collect()
                        post_snapshot = tracemalloc.take_snapshot()

                        # Analyze memory differences
                        top_stats = post_snapshot.compare_to(pre_snapshot, 'lineno')

                        # Extract key statistics
                        total_allocated = sum(stat.size for stat in top_stats if stat.size > 0)
                        total_freed = abs(sum(stat.size for stat in top_stats if stat.size < 0))
                        net_increase = sum(stat.size for stat in top_stats)
                        peak_memory = max(stat.size for stat in post_snapshot.statistics('lineno')[:10])

                        # Check for potential memory leaks
                        potential_leak = net_increase > (total_allocated * 0.1)  # More than 10% not freed

                        component_memory[impl] = {
                            'total_allocated': total_allocated,
                            'total_freed': total_freed,
                            'net_increase': net_increase,
                            'peak_memory': peak_memory,
                            'potential_memory_leak': potential_leak,
                            'top_allocations': [
                                {
                                    'size': stat.size,
                                    'count': stat.count,
                                    'traceback': stat.traceback.format()[:3]  # Top 3 frames
                                }
                                for stat in top_stats[:5]  # Top 5 allocations
                            ]
                        }

                        logger.info(f"         Peak: {peak_memory // 1024}KB, "
                                   f"Net: {net_increase // 1024}KB")

                    except Exception as e:
                        logger.error(f"❌ Memory analysis failed for {component_name} {impl}: {e}")
                        component_memory[impl] = {'error': str(e)}

            except Exception as e:
                logger.error(f"❌ Memory tracing failed for {component_name}: {e}")
                component_memory = {'error': str(e)}

            finally:
                tracemalloc.stop()

            memory_results[component_name] = component_memory

        return memory_results

    def _generate_comparisons(self, results: Dict[str, Any]) -> List[ComparisonResult]:
        """
        Generate detailed performance comparisons between Rust and Python implementations.

        This method creates comprehensive comparison objects that include statistical
        analysis, target achievement assessment, and optimization recommendations.

        Args:
            results: Complete benchmark results dictionary

        Returns:
            List of ComparisonResult objects with detailed analysis
        """
        logger.info("📈 Generating performance comparisons...")

        comparisons = []
        micro_results = results.get('micro_benchmarks', {})

        for component_name, component_results in micro_results.items():
            # Get component type for target lookup
            component_type = None
            for ct in ComponentType:
                if ct.value == component_name:
                    component_type = ct
                    break

            if not component_type:
                logger.warning(f"Unknown component type: {component_name}")
                continue

            # Generate comparisons for each test size
            for test_size_name, size_results in component_results.items():
                if isinstance(size_results, dict) and 'rust' in size_results and 'python' in size_results:
                    try:
                        test_size = TestDataSize(test_size_name)

                        # Create metrics objects from stored data
                        rust_data = size_results['rust']
                        python_data = size_results['python']

                        # Reconstruct BenchmarkMetrics objects
                        rust_metrics = self._reconstruct_metrics(rust_data)
                        python_metrics = self._reconstruct_metrics(python_data)

                        # Create comparison
                        comparison = ComparisonResult(
                            component_name=component_name,
                            test_size=test_size,
                            rust_metrics=rust_metrics,
                            python_metrics=python_metrics,
                            target_speedup=self.PERFORMANCE_TARGETS.get(component_type, 1.0)
                        )

                        comparisons.append(comparison)

                        logger.info(f"   📊 {component_name} ({test_size_name}): "
                                   f"{comparison.speedup_factor:.1f}x speedup "
                                   f"({comparison.target_percentage:.1f}% of target)")

                    except Exception as e:
                        logger.error(f"❌ Comparison failed for {component_name} {test_size_name}: {e}")

        return comparisons

    def _reconstruct_metrics(self, data: Dict[str, Any]) -> BenchmarkMetrics:
        """Reconstruct BenchmarkMetrics object from stored data."""
        timing = data.get('timing', {})
        memory = data.get('memory', {})
        performance = data.get('performance', {})
        quality = data.get('quality', {})
        metadata = data.get('metadata', {})

        metrics = BenchmarkMetrics(
            component_name=data.get('component_name', 'unknown'),
            implementation=data.get('implementation', 'unknown'),
            test_size=TestDataSize(data.get('test_size', 'small'))
        )

        # Restore timing data
        metrics.execution_times = timing.get('execution_times', [])
        metrics.min_time = timing.get('min_time', 0)
        metrics.max_time = timing.get('max_time', 0)
        metrics.mean_time = timing.get('mean_time', 0)
        metrics.median_time = timing.get('median_time', 0)
        metrics.std_dev = timing.get('std_dev', 0)

        # Restore memory data
        metrics.peak_memory = memory.get('peak_memory', 0)
        metrics.memory_increase = memory.get('memory_increase', 0)
        metrics.allocations = memory.get('allocations', 0)

        # Restore performance data
        metrics.throughput = performance.get('throughput', 0)
        metrics.cache_hits = performance.get('cache_hits', 0)
        metrics.cache_misses = performance.get('cache_misses', 0)

        # Restore quality data
        metrics.errors = quality.get('errors', 0)
        metrics.warnings = quality.get('warnings', 0)
        metrics.success_rate = quality.get('success_rate', 100.0)

        # Restore metadata
        metrics.test_iterations = metadata.get('test_iterations', 0)
        if 'timestamp' in metadata:
            metrics.timestamp = datetime.fromisoformat(metadata['timestamp'])

        return metrics

    def _generate_summary(self, results: Dict[str, Any], comparisons: List[ComparisonResult]) -> Dict[str, Any]:
        """
        Generate comprehensive benchmark summary with actionable insights.

        This method analyzes all benchmark results to provide high-level insights,
        identify critical performance issues, and generate actionable recommendations
        for optimization priorities.

        Args:
            results: Complete benchmark results
            comparisons: List of comparison results

        Returns:
            Comprehensive summary dictionary with insights and recommendations
        """
        logger.info("📋 Generating comprehensive benchmark summary...")

        # Overall statistics
        total_comparisons = len(comparisons)
        targets_achieved = sum(1 for comp in comparisons if comp.target_achieved)
        avg_speedup = mean([comp.speedup_factor for comp in comparisons]) if comparisons else 0

        # Component performance analysis
        component_performance = {}
        for comp in comparisons:
            if comp.component_name not in component_performance:
                component_performance[comp.component_name] = {
                    'speedups': [],
                    'target_achievements': [],
                    'recommendations': []
                }

            component_performance[comp.component_name]['speedups'].append(comp.speedup_factor)
            component_performance[comp.component_name]['target_achievements'].append(comp.target_achieved)
            component_performance[comp.component_name]['recommendations'].extend(comp.optimization_recommendations)

        # Identify high-impact optimization opportunities
        optimization_priorities = []
        for comp_name, perf_data in component_performance.items():
            avg_comp_speedup = mean(perf_data['speedups'])
            target_achieved_pct = mean(perf_data['target_achievements']) * 100

            if target_achieved_pct < 80:  # Less than 80% target achievement
                priority = "HIGH" if target_achieved_pct < 50 else "MEDIUM"
                optimization_priorities.append({
                    'component': comp_name,
                    'priority': priority,
                    'current_speedup': avg_comp_speedup,
                    'target_achievement': target_achieved_pct,
                    'recommendations': list(set(perf_data['recommendations']))  # Unique recommendations
                })

        # Sort by priority and impact
        optimization_priorities.sort(key=lambda x: (
            0 if x['priority'] == 'HIGH' else 1,  # High priority first
            x['target_achievement']  # Then by lowest achievement
        ))

        # Memory efficiency analysis
        memory_issues = []
        memory_analysis = results.get('memory_analysis', {})
        for comp_name, memory_data in memory_analysis.items():
            if 'rust' in memory_data and 'python' in memory_data:
                rust_mem = memory_data['rust'].get('peak_memory', 0)
                python_mem = memory_data['python'].get('peak_memory', 0)

                if python_mem > 0:
                    efficiency_ratio = rust_mem / python_mem
                    if efficiency_ratio > 1.2:  # Rust uses 20% more memory
                        memory_issues.append({
                            'component': comp_name,
                            'efficiency_ratio': efficiency_ratio,
                            'rust_peak_mb': rust_mem // (1024 * 1024),
                            'python_peak_mb': python_mem // (1024 * 1024)
                        })

        # Generate overall assessment
        if targets_achieved / total_comparisons >= 0.8:
            overall_status = "EXCELLENT"
            status_message = "Most performance targets achieved. System ready for production."
        elif targets_achieved / total_comparisons >= 0.6:
            overall_status = "GOOD"
            status_message = "Good performance with room for optimization in key areas."
        elif targets_achieved / total_comparisons >= 0.4:
            overall_status = "FAIR"
            status_message = "Performance improvements needed before production release."
        else:
            overall_status = "NEEDS_IMPROVEMENT"
            status_message = "Significant optimization required across multiple components."

        return {
            'overall_assessment': {
                'status': overall_status,
                'message': status_message,
                'targets_achieved': targets_achieved,
                'total_comparisons': total_comparisons,
                'target_achievement_rate': (targets_achieved / total_comparisons * 100) if total_comparisons > 0 else 0,
                'average_speedup': avg_speedup,
            },
            'component_summary': {
                comp_name: {
                    'avg_speedup': mean(data['speedups']),
                    'target_achievement_rate': mean(data['target_achievements']) * 100,
                    'performance_consistency': 1.0 - (stdev(data['speedups']) / mean(data['speedups'])) if len(data['speedups']) > 1 else 1.0,
                }
                for comp_name, data in component_performance.items()
            },
            'optimization_priorities': optimization_priorities,
            'memory_analysis': {
                'components_with_issues': len(memory_issues),
                'memory_issues': memory_issues,
                'overall_memory_efficiency': mean([
                    issue['efficiency_ratio'] for issue in memory_issues
                ]) if memory_issues else 1.0,
            },
            'recommendations': {
                'immediate_actions': [
                    priority for priority in optimization_priorities[:3] if priority['priority'] == 'HIGH'
                ],
                'medium_term_optimizations': [
                    priority for priority in optimization_priorities if priority['priority'] == 'MEDIUM'
                ],
                'memory_optimizations': [
                    f"Optimize {issue['component']} memory usage (currently {issue['efficiency_ratio']:.1f}x more than Python)"
                    for issue in memory_issues[:3]
                ],
            },
            'rust_acceleration_status': {
                'components_active': sum(1 for v in RUST_AVAILABLE.values() if v),
                'components_total': len(RUST_AVAILABLE),
                'acceleration_percentage': (sum(1 for v in RUST_AVAILABLE.values() if v) / len(RUST_AVAILABLE) * 100),
                'missing_components': [k for k, v in RUST_AVAILABLE.items() if not v],
            }
        }

    def _save_results(self, results: Dict[str, Any]):
        """Save comprehensive benchmark results to JSON files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save complete results
        results_file = self.output_dir / f"benchmark_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"📄 Results saved to: {results_file}")

        # Save summary for quick access
        summary_file = self.output_dir / f"benchmark_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(results['summary'], f, indent=2, default=str)

        # Update latest results link/copy
        latest_file = self.output_dir / "latest_results.json"
        if latest_file.exists():
            latest_file.unlink()

        # On Windows, use copy instead of symlink to avoid permission issues
        import platform
        if platform.system() == "Windows":
            import shutil
            shutil.copy2(results_file, latest_file)
        else:
            latest_file.symlink_to(results_file.name)

    def _generate_reports(self, results: Dict[str, Any], comparisons: List[ComparisonResult]):
        """Generate detailed HTML and markdown reports."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Generate markdown report
        markdown_report = self._generate_markdown_report(results, comparisons)
        markdown_file = self.output_dir / f"benchmark_report_{timestamp}.md"
        with open(markdown_file, 'w') as f:
            f.write(markdown_report)

        logger.info(f"📊 Markdown report generated: {markdown_file}")

        # Generate CSV summary for spreadsheet analysis
        csv_data = self._generate_csv_summary(comparisons)
        csv_file = self.output_dir / f"benchmark_summary_{timestamp}.csv"
        with open(csv_file, 'w') as f:
            f.write(csv_data)

        logger.info(f"📈 CSV summary generated: {csv_file}")

    def _generate_markdown_report(self, results: Dict[str, Any], comparisons: List[ComparisonResult]) -> str:
        """Generate comprehensive markdown report."""
        summary = results['summary']
        metadata = results['metadata']

        report = f"""# CLASSIC Phase 6 Rust Migration Benchmark Report

Generated: {metadata['start_time']}
Duration: {metadata.get('total_time', 0):.2f} seconds
Iterations: {metadata['iterations']}

## Executive Summary

**Overall Status:** {summary['overall_assessment']['status']}
**Message:** {summary['overall_assessment']['message']}

- **Targets Achieved:** {summary['overall_assessment']['targets_achieved']}/{summary['overall_assessment']['total_comparisons']} ({summary['overall_assessment']['target_achievement_rate']:.1f}%)
- **Average Speedup:** {summary['overall_assessment']['average_speedup']:.2f}x
- **Rust Components Active:** {summary['rust_acceleration_status']['components_active']}/{summary['rust_acceleration_status']['components_total']} ({summary['rust_acceleration_status']['acceleration_percentage']:.1f}%)

## Component Performance Summary

| Component | Avg Speedup | Target Achievement | Consistency |
|-----------|-------------|-------------------|-------------|
"""

        for comp_name, comp_data in summary['component_summary'].items():
            report += f"| {comp_name} | {comp_data['avg_speedup']:.1f}x | {comp_data['target_achievement_rate']:.1f}% | {comp_data['performance_consistency']:.2f} |\n"

        report += f"""
## Optimization Priorities

### Immediate Actions Required
"""

        for action in summary['recommendations']['immediate_actions']:
            report += f"""
#### {action['component']} - {action['priority']} Priority
- **Current Speedup:** {action['current_speedup']:.1f}x
- **Target Achievement:** {action['target_achievement']:.1f}%
- **Recommendations:**
"""
            for rec in action['recommendations']:
                report += f"  - {rec}\n"

        report += f"""
### Medium-Term Optimizations
"""

        for opt in summary['recommendations']['medium_term_optimizations']:
            report += f"""
#### {opt['component']}
- **Current Speedup:** {opt['current_speedup']:.1f}x
- **Target Achievement:** {opt['target_achievement']:.1f}%
"""

        report += f"""
## Memory Analysis

- **Components with Memory Issues:** {summary['memory_analysis']['components_with_issues']}
- **Overall Memory Efficiency:** {summary['memory_analysis']['overall_memory_efficiency']:.2f}x

### Memory Optimization Recommendations
"""

        for mem_rec in summary['recommendations']['memory_optimizations']:
            report += f"- {mem_rec}\n"

        report += """
## Detailed Component Results

"""

        # Add detailed results for each component
        for comparison in comparisons:
            report += f"""
### {comparison.component_name} ({comparison.test_size.value})

- **Speedup:** {comparison.speedup_factor:.2f}x
- **Target:** {comparison.target_speedup:.0f}x ({comparison.target_percentage:.1f}% achieved)
- **Memory Efficiency:** {comparison.memory_efficiency:.2f}x
- **Statistical Significance:** {'Yes' if comparison.performance_significant else 'No'}

**Performance Details:**
- Rust: {comparison.rust_metrics.mean_time:.4f}s (±{comparison.rust_metrics.std_dev:.4f}s)
- Python: {comparison.python_metrics.mean_time:.4f}s (±{comparison.python_metrics.std_dev:.4f}s)
- Cache Hit Rate: {comparison.rust_metrics.cache_hit_rate:.1f}%
- Success Rate: {comparison.rust_metrics.success_rate:.1f}%

"""

            if comparison.optimization_recommendations:
                report += "**Recommendations:**\n"
                for rec in comparison.optimization_recommendations:
                    report += f"- {rec}\n"

        report += f"""
## System Information

- **Rust Status:** {summary['rust_acceleration_status']['acceleration_percentage']:.1f}% components active
- **Missing Components:** {', '.join(summary['rust_acceleration_status']['missing_components']) if summary['rust_acceleration_status']['missing_components'] else 'None'}
- **Test Sizes:** {', '.join(metadata['test_sizes'])}
- **Benchmark Types:** {', '.join(metadata['benchmark_types'])}

---
*Generated by CLASSIC Comprehensive Benchmark Suite*
"""

        return report

    def _generate_csv_summary(self, comparisons: List[ComparisonResult]) -> str:
        """Generate CSV summary for spreadsheet analysis."""
        csv_lines = [
            "Component,Test Size,Rust Time (s),Python Time (s),Speedup,Target,Target Achieved,Memory Efficiency,Cache Hit Rate,Success Rate"
        ]

        for comp in comparisons:
            csv_lines.append(
                f"{comp.component_name},"
                f"{comp.test_size.value},"
                f"{comp.rust_metrics.mean_time:.6f},"
                f"{comp.python_metrics.mean_time:.6f},"
                f"{comp.speedup_factor:.2f},"
                f"{comp.target_speedup:.0f},"
                f"{'Yes' if comp.target_achieved else 'No'},"
                f"{comp.memory_efficiency:.3f},"
                f"{comp.rust_metrics.cache_hit_rate:.1f},"
                f"{comp.rust_metrics.success_rate:.1f}"
            )

        return "\n".join(csv_lines)

    def compare_with_baseline(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare current results with stored baseline for regression testing.

        This method enables regression testing by comparing current benchmark
        results with previously stored baseline performance data.

        Args:
            results: Current benchmark results

        Returns:
            Regression analysis results
        """
        logger.info("📊 Performing regression analysis against baseline...")

        baseline_file = self.baseline_dir / "performance_baseline.json"

        if not baseline_file.exists():
            logger.warning("⚠️ No baseline found, storing current results as baseline")
            with open(baseline_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            return {'status': 'baseline_created', 'file': str(baseline_file)}

        # Load baseline
        with open(baseline_file, 'r') as f:
            baseline = json.load(f)

        # Compare results
        regression_analysis = {
            'baseline_date': baseline['metadata']['start_time'],
            'current_date': results['metadata']['start_time'],
            'components': {},
            'regressions_detected': [],
            'improvements_detected': [],
            'overall_status': 'STABLE'
        }

        # Component-by-component comparison
        current_micro = results.get('micro_benchmarks', {})
        baseline_micro = baseline.get('micro_benchmarks', {})

        for component_name in current_micro:
            if component_name not in baseline_micro:
                continue

            component_analysis = {
                'performance_change': {},
                'memory_change': {},
                'status': 'STABLE'
            }

            # Compare each test size
            for test_size in current_micro[component_name]:
                current_data = current_micro[component_name][test_size]
                baseline_data = baseline_micro[component_name].get(test_size, {})

                if 'rust' in current_data and 'rust' in baseline_data:
                    current_time = current_data['rust']['timing']['mean_time']
                    baseline_time = baseline_data['rust']['timing']['mean_time']

                    performance_change = ((current_time - baseline_time) / baseline_time) * 100

                    component_analysis['performance_change'][test_size] = performance_change

                    # Detect significant regressions (>10% slower)
                    if performance_change > 10:
                        regression_analysis['regressions_detected'].append({
                            'component': component_name,
                            'test_size': test_size,
                            'performance_change': performance_change,
                            'current_time': current_time,
                            'baseline_time': baseline_time
                        })
                        component_analysis['status'] = 'REGRESSION'

                    # Detect improvements (>5% faster)
                    elif performance_change < -5:
                        regression_analysis['improvements_detected'].append({
                            'component': component_name,
                            'test_size': test_size,
                            'performance_change': performance_change,
                            'current_time': current_time,
                            'baseline_time': baseline_time
                        })
                        if component_analysis['status'] == 'STABLE':
                            component_analysis['status'] = 'IMPROVED'

            regression_analysis['components'][component_name] = component_analysis

        # Determine overall status
        if regression_analysis['regressions_detected']:
            regression_analysis['overall_status'] = 'REGRESSION_DETECTED'
        elif regression_analysis['improvements_detected']:
            regression_analysis['overall_status'] = 'IMPROVED'

        # Save regression report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        regression_file = self.output_dir / f"regression_analysis_{timestamp}.json"
        with open(regression_file, 'w') as f:
            json.dump(regression_analysis, f, indent=2, default=str)

        logger.info(f"📈 Regression analysis saved to: {regression_file}")

        return regression_analysis


def main():
    """Main entry point for running the comprehensive benchmark suite."""
    import argparse

    parser = argparse.ArgumentParser(description="CLASSIC Phase 6 Comprehensive Benchmark Suite")
    parser.add_argument("--benchmark-types", nargs="+", choices=['micro', 'macro', 'memory', 'regression', 'all'],
                       default=['micro', 'macro'], help="Types of benchmarks to run")
    parser.add_argument("--test-sizes", nargs="+", choices=['minimal', 'tiny', 'small', 'medium', 'large', 'huge'],
                       default=['small', 'medium', 'large'], help="Test data sizes to use")
    parser.add_argument("--iterations", type=int, default=5, help="Number of iterations per test")
    parser.add_argument("--no-memory", action="store_true", help="Disable memory profiling")
    parser.add_argument("--parallel", action="store_true", help="Enable parallel execution")
    parser.add_argument("--output-dir", type=Path, help="Output directory for results")
    parser.add_argument("--baseline-dir", type=Path, help="Baseline directory for regression testing")
    parser.add_argument("--regression-only", action="store_true", help="Run regression testing only")

    args = parser.parse_args()

    # Convert string arguments to enums
    benchmark_types = [BenchmarkType(bt) for bt in args.benchmark_types]
    test_sizes = [TestDataSize(ts) for ts in args.test_sizes]

    # Initialize benchmark suite
    suite = ComprehensiveBenchmarkSuite(
        output_dir=args.output_dir,
        baseline_dir=args.baseline_dir
    )

    if args.regression_only:
        # Load latest results and run regression analysis
        latest_file = suite.output_dir / "latest_results.json"
        if not latest_file.exists():
            logger.error("❌ No results found for regression testing. Run benchmarks first.")
            sys.exit(1)

        with open(latest_file, 'r') as f:
            results = json.load(f)

        regression_results = suite.compare_with_baseline(results)

        print("\n" + "=" * 60)
        print("📊 REGRESSION ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"Status: {regression_results['overall_status']}")
        print(f"Regressions: {len(regression_results['regressions_detected'])}")
        print(f"Improvements: {len(regression_results['improvements_detected'])}")

        if regression_results['regressions_detected']:
            print("\n❌ REGRESSIONS DETECTED:")
            for reg in regression_results['regressions_detected']:
                print(f"   {reg['component']} ({reg['test_size']}): {reg['performance_change']:+.1f}%")

        if regression_results['improvements_detected']:
            print("\n✅ IMPROVEMENTS DETECTED:")
            for imp in regression_results['improvements_detected']:
                print(f"   {imp['component']} ({imp['test_size']}): {imp['performance_change']:+.1f}%")

    else:
        # Run comprehensive benchmarks
        results = suite.run_comprehensive_benchmark(
            benchmark_types=benchmark_types,
            test_sizes=test_sizes,
            iterations=args.iterations,
            include_memory_profiling=not args.no_memory,
            parallel_execution=args.parallel
        )

        # Print summary
        summary = results['summary']

        print("\n" + "=" * 80)
        print("🚀 COMPREHENSIVE BENCHMARK RESULTS")
        print("=" * 80)

        print(f"\n📊 Overall Assessment: {summary['overall_assessment']['status']}")
        print(f"    {summary['overall_assessment']['message']}")
        print(f"    Targets Achieved: {summary['overall_assessment']['targets_achieved']}/{summary['overall_assessment']['total_comparisons']}")
        print(f"    Average Speedup: {summary['overall_assessment']['average_speedup']:.2f}x")

        print(f"\n🔧 Optimization Priorities:")
        for priority in summary['optimization_priorities'][:3]:
            print(f"    {priority['priority']}: {priority['component']} ({priority['target_achievement']:.1f}% of target)")

        print(f"\n💾 Memory Efficiency:")
        if summary['memory_analysis']['components_with_issues']:
            print(f"    ⚠️ {summary['memory_analysis']['components_with_issues']} components need memory optimization")
        else:
            print("    ✅ Memory usage is efficient across all components")

        print(f"\n🦀 Rust Acceleration: {summary['rust_acceleration_status']['acceleration_percentage']:.1f}% components active")

        if args.regression_only or 'regression' in args.benchmark_types:
            regression_results = suite.compare_with_baseline(results)
            print(f"\n📈 Regression Status: {regression_results['overall_status']}")


if __name__ == "__main__":
    main()
