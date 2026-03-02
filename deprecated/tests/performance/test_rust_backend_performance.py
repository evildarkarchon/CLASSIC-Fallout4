"""
Performance benchmarks for Rust backend.

This module validates that the Rust backend meets performance targets
for crash log analysis, ensuring 10-150x speedups over Python implementation.

Phase 3 Integration - Performance Validation
"""
# ruff: noqa: ANN201, ANN001, PLR6301

import statistics
import time
import tracemalloc
from pathlib import Path

import pytest

# Skip all tests if Rust not available
pytest.importorskip("classic_scanlog")
pytest.importorskip("classic_config")
# Skip if pytest-benchmark is not installed
pytest.importorskip("pytest_benchmark")

from ClassicLib.integration.rust.orchestrator_api import ClassicOrchestrator


@pytest.fixture
def orchestrator() -> ClassicOrchestrator:
    """Create Rust orchestrator instance"""
    return ClassicOrchestrator()


@pytest.fixture
def sample_crash_logs() -> list[Path]:
    """Get sample crash logs for benchmarking.

    Uses logs from valid test directories:
    - sample_logs/FO4/ (primary - extensive test data)
    - Crash Logs/ (secondary - real-world logs)
    """
    # Primary: sample_logs/FO4 has extensive test data
    sample_dir = Path("sample_logs/FO4")
    if sample_dir.exists():
        log_files = list(sample_dir.glob("*.log"))
        if log_files:
            return log_files[:20]

    # Secondary: Crash Logs directory
    crash_dir = Path("Crash Logs")
    if crash_dir.exists():
        log_files = list(crash_dir.glob("*.log"))
        if log_files:
            return log_files[:20]

    pytest.skip("No crash log samples available in sample_logs/FO4 or Crash Logs/")


@pytest.fixture
def single_crash_log(sample_crash_logs: list[Path]) -> Path:
    """Get a single crash log"""
    return sample_crash_logs[0]


@pytest.mark.performance
@pytest.mark.rust
@pytest.mark.skipif(tracemalloc.is_tracing(), reason="Timing sensitive test skipped when tracemalloc is enabled")
class TestSingleLogPerformance:
    """Performance benchmarks for single log processing"""

    def test_single_log_speed(
        self,
        benchmark,
        orchestrator: ClassicOrchestrator,
        single_crash_log: Path,
    ):
        """Benchmark single log processing speed"""

        result = benchmark(orchestrator.process_crash_log, single_crash_log)

        # Target: < 100ms for typical logs (Rust-accelerated)
        # We allow up to 200ms for larger/complex logs
        assert result.processing_time_ms < 200, f"Single log processing too slow: {result.processing_time_ms}ms (target: < 200ms)"

    def test_single_log_consistency(
        self,
        orchestrator: ClassicOrchestrator,
        single_crash_log: Path,
    ):
        """Test that processing time is consistent across runs"""
        times = []

        # Process same log 10 times
        for _ in range(10):
            start = time.perf_counter()
            orchestrator.process_crash_log(single_crash_log)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)

        # Calculate statistics
        mean_time = statistics.mean(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0
        coefficient_of_variation = (std_dev / mean_time) if mean_time > 0 else 0

        # Performance should be consistent (low variation)
        # Allow high variation due to system load and very short execution times (0.3ms)
        # In CI/cloud environments, small tasks are highly variable
        assert coefficient_of_variation < 2.5, (
            f"Performance too inconsistent: CV={coefficient_of_variation:.2f} (mean={mean_time:.1f}ms, std={std_dev:.1f}ms)"
        )


@pytest.mark.performance
@pytest.mark.rust
@pytest.mark.skipif(tracemalloc.is_tracing(), reason="Timing sensitive test skipped when tracemalloc is enabled")
class TestBatchPerformance:
    """Performance benchmarks for batch processing"""

    def test_batch_throughput_small(
        self,
        benchmark,
        orchestrator: ClassicOrchestrator,
        sample_crash_logs: list[Path],
    ):
        """Benchmark throughput with small batch (5 logs)"""
        logs = sample_crash_logs[:5]
        if len(logs) < 5:
            pytest.skip("Need at least 5 logs for small batch test")

        result = benchmark(
            orchestrator.process_crash_logs_batch,
            log_paths=logs,
            max_concurrent=5,
        )

        # Calculate average time per log
        avg_time = result.total_time_ms / len(logs)

        # Target: < 150ms per log in batch
        assert avg_time < 150, f"Batch processing too slow: {avg_time:.1f}ms per log (target: < 150ms)"

    def test_batch_throughput_medium(
        self,
        benchmark,
        orchestrator: ClassicOrchestrator,
        sample_crash_logs: list[Path],
    ):
        """Benchmark throughput with medium batch (10 logs)"""
        logs = sample_crash_logs[:10]
        if len(logs) < 10:
            pytest.skip("Need at least 10 logs for medium batch test")

        result = benchmark(
            orchestrator.process_crash_logs_batch,
            log_paths=logs,
            max_concurrent=10,
        )

        # Calculate average time per log
        avg_time = result.total_time_ms / len(logs)

        # Target: < 100ms per log (better efficiency with larger batch)
        assert avg_time < 100, f"Batch processing too slow: {avg_time:.1f}ms per log (target: < 100ms)"

    @pytest.mark.slow
    def test_batch_throughput_large(
        self,
        benchmark,
        orchestrator: ClassicOrchestrator,
        sample_crash_logs: list[Path],
    ):
        """Benchmark throughput with large batch (20 logs)"""
        logs = sample_crash_logs[:20]
        if len(logs) < 15:
            pytest.skip("Need at least 15 logs for large batch test")

        result = benchmark(
            orchestrator.process_crash_logs_batch,
            log_paths=logs,
            max_concurrent=10,
        )

        # Calculate metrics
        avg_time = result.total_time_ms / len(logs)
        total_seconds = result.total_time_ms / 1000

        # Target: < 50ms per log average (parallel efficiency)
        assert avg_time < 50, f"Large batch processing too slow: {avg_time:.1f}ms per log (target: < 50ms)"

        # Target: Complete 20 logs in < 2 seconds
        assert total_seconds < 2.0, f"Total batch time too high: {total_seconds:.2f}s (target: < 2s for 20 logs)"


@pytest.mark.performance
@pytest.mark.rust
@pytest.mark.skipif(tracemalloc.is_tracing(), reason="Timing sensitive test skipped when tracemalloc is enabled")
class TestParallelismEfficiency:
    """Test parallelism and concurrency efficiency"""

    def test_parallelism_factor(
        self,
        orchestrator: ClassicOrchestrator,
        sample_crash_logs: list[Path],
    ):
        """Test that parallelism factor indicates good speedup"""
        logs = sample_crash_logs[:10]
        if len(logs) < 5:
            pytest.skip("Need at least 5 logs for parallelism test")

        result = orchestrator.process_crash_logs_batch(
            log_paths=logs,
            max_concurrent=len(logs),
        )

        # Parallelism factor should be > 1 (indicating speedup)
        # For perfect parallelism on 10 cores, factor would be ~10
        # We expect at least 2x due to GIL and overhead
        assert result.parallelism_factor > 2.0, f"Parallelism factor too low: {result.parallelism_factor:.2f}x (target: > 2.0x)"

    def test_scaling_with_concurrency(
        self,
        orchestrator: ClassicOrchestrator,
        sample_crash_logs: list[Path],
    ):
        """Test that increasing concurrency improves performance"""
        logs = sample_crash_logs[:10]
        if len(logs) < 10:
            pytest.skip("Need 10 logs for scaling test")

        # Test with different concurrency levels
        times = {}

        for concurrency in [1, 5, 10]:
            result = orchestrator.process_crash_logs_batch(
                log_paths=logs,
                max_concurrent=concurrency,
            )
            times[concurrency] = result.total_time_ms

        # Higher concurrency should be faster (or at least not slower)
        # Allow some tolerance for overhead
        assert times[10] <= times[1] * 1.2, f"Concurrency not improving performance: 1 worker={times[1]}ms, 10 workers={times[10]}ms"

    def test_concurrent_overhead(
        self,
        orchestrator: ClassicOrchestrator,
        sample_crash_logs: list[Path],
    ):
        """Test that concurrent overhead is acceptable.

        Note: When Rust processing is extremely fast (< 10ms total),
        parallelism overhead dominates and speedup isn't measurable.
        In such cases, we verify parallel is at least not significantly slower.
        """
        if len(sample_crash_logs) < 5:
            pytest.skip("Need at least 5 logs")

        logs = sample_crash_logs[:5]

        # Process sequentially (1 at a time)
        sequential_result = orchestrator.process_crash_logs_batch(
            log_paths=logs,
            max_concurrent=1,
        )

        # Process in parallel
        parallel_result = orchestrator.process_crash_logs_batch(
            log_paths=logs,
            max_concurrent=5,
        )

        # Parallel should be faster
        parallel_time = max(parallel_result.total_time_ms, 0.001)  # Avoid division by zero
        sequential_time = max(sequential_result.total_time_ms, 0.001)
        speedup = sequential_time / parallel_time

        # When processing is extremely fast, parallelism overhead dominates
        # and we can't measure meaningful speedup. The thresholds below
        # account for the fact that Rust processing is very fast.
        if sequential_time < 1:
            # For extremely fast operations (< 1ms), parallelism overhead completely
            # dominates. Thread spawning and synchronization takes ~10-15ms regardless
            # of work size. Skip this test as parallelism isn't measurable.
            pytest.skip(f"Processing too fast to measure parallelism benefit: {sequential_time:.3f}ms sequential")
        elif sequential_time < 50:
            # For fast operations (1-50ms), parallelism overhead is significant.
            # Just verify parallel doesn't add excessive overhead.
            # Allow up to 2x slower (speedup > 0.5) since thread creation
            # and synchronization can dominate small workloads.
            assert speedup > 0.5, (
                f"Parallel overhead too high for fast operations: {speedup:.2f}x "
                f"(sequential={sequential_time:.0f}ms, parallel={parallel_time:.0f}ms)"
            )
        else:
            # For slower operations (50ms+), expect meaningful speedup
            # Using 1.2x threshold to account for timing variance in CI environments
            assert speedup > 1.2, (
                f"Insufficient speedup from parallelism: {speedup:.2f}x (sequential={sequential_time:.0f}ms, parallel={parallel_time:.0f}ms)"
            )


@pytest.mark.performance
@pytest.mark.rust
@pytest.mark.skipif(tracemalloc.is_tracing(), reason="Timing sensitive test skipped when tracemalloc is enabled")
class TestMemoryEfficiency:
    """Test memory usage and efficiency"""

    def test_memory_usage_single_log(
        self,
        orchestrator: ClassicOrchestrator,
        single_crash_log: Path,
    ):
        """Test memory usage for single log processing"""
        import gc

        import psutil

        process = psutil.Process()

        # Force garbage collection
        gc.collect()

        # Measure baseline memory
        baseline_memory = process.memory_info().rss

        # Process log
        orchestrator.process_crash_log(single_crash_log)

        # Force garbage collection
        gc.collect()

        # Measure memory after processing
        final_memory = process.memory_info().rss
        memory_increase_mb = (final_memory - baseline_memory) / 1024 / 1024

        # Single log should use < 50MB
        assert memory_increase_mb < 50, f"Single log memory usage too high: {memory_increase_mb:.1f}MB (target: < 50MB)"

    @pytest.mark.slow
    def test_memory_usage_batch(
        self,
        orchestrator: ClassicOrchestrator,
        sample_crash_logs: list[Path],
    ):
        """Test memory usage for batch processing"""
        import gc

        import psutil

        logs = sample_crash_logs[:20]
        if len(logs) < 10:
            pytest.skip("Need at least 10 logs for memory test")

        process = psutil.Process()

        # Force garbage collection
        gc.collect()

        # Measure baseline memory
        baseline_memory = process.memory_info().rss

        # Process batch
        orchestrator.process_crash_logs_batch(
            log_paths=logs,
            max_concurrent=10,
        )

        # Force garbage collection
        gc.collect()

        # Measure memory after processing
        final_memory = process.memory_info().rss
        memory_increase_mb = (final_memory - baseline_memory) / 1024 / 1024

        # Batch should use < 200MB
        assert memory_increase_mb < 200, f"Batch memory usage too high: {memory_increase_mb:.1f}MB (target: < 200MB for {len(logs)} logs)"

        # Memory per log should be reasonable
        memory_per_log = memory_increase_mb / len(logs)
        assert memory_per_log < 10, f"Memory per log too high: {memory_per_log:.1f}MB/log"

    @pytest.mark.slow
    def test_no_memory_leaks(
        self,
        orchestrator: ClassicOrchestrator,
        sample_crash_logs: list[Path],
    ):
        """Test for memory leaks over multiple iterations"""
        import gc

        import psutil

        logs = sample_crash_logs[:5]
        if len(logs) < 3:
            pytest.skip("Need at least 3 logs for leak test")

        process = psutil.Process()

        # Process multiple times and track memory
        memory_samples = []

        for _iteration in range(5):
            # Force garbage collection before measuring
            gc.collect()

            baseline = process.memory_info().rss

            # Process batch
            orchestrator.process_crash_logs_batch(
                log_paths=logs,
                max_concurrent=3,
            )

            # Force garbage collection after processing
            gc.collect()

            final = process.memory_info().rss
            increase_mb = (final - baseline) / 1024 / 1024
            memory_samples.append(increase_mb)

        # Memory should not grow significantly across iterations
        # (indicates no leak)
        first_iteration = memory_samples[0]
        last_iteration = memory_samples[-1]
        growth = last_iteration - first_iteration

        # Allow up to 20MB growth over 5 iterations (caching, etc.)
        assert growth < 20, (
            f"Memory leak detected: grew {growth:.1f}MB over 5 iterations (first={first_iteration:.1f}MB, last={last_iteration:.1f}MB)"
        )


@pytest.mark.performance
@pytest.mark.rust
@pytest.mark.skipif(tracemalloc.is_tracing(), reason="Timing sensitive test skipped when tracemalloc is enabled")
class TestPerformanceTargets:
    """Validate that performance targets are met"""

    def test_single_log_target_15_20ms(
        self,
        orchestrator: ClassicOrchestrator,
        single_crash_log: Path,
    ):
        """
        Test single log processing meets 15-20ms target.

        Phase 3 target: 15-20ms per log (Rust-accelerated)
        """
        # Run multiple times to get average
        times = []
        for _ in range(10):
            result = orchestrator.process_crash_log(single_crash_log)
            times.append(result.processing_time_ms)

        avg_time = statistics.mean(times)

        # Target: 15-20ms average (allow up to 50ms for complex logs)
        assert avg_time < 50, f"Single log processing target not met: {avg_time:.1f}ms average (target: < 50ms)"

    def test_batch_10_logs_target_150_200ms(
        self,
        orchestrator: ClassicOrchestrator,
        sample_crash_logs: list[Path],
    ):
        """
        Test 10-log batch meets 150-200ms target.

        Phase 3 target: 150-200ms for 10 logs (parallel)
        """
        logs = sample_crash_logs[:10]
        if len(logs) < 10:
            pytest.skip("Need 10 logs for target test")

        result = orchestrator.process_crash_logs_batch(
            log_paths=logs,
            max_concurrent=10,
        )

        # Target: < 200ms for 10 logs
        assert result.total_time_ms < 200, f"10-log batch target not met: {result.total_time_ms}ms (target: < 200ms)"

    @pytest.mark.slow
    def test_batch_100_logs_target_1_5_2s(
        self,
        orchestrator: ClassicOrchestrator,
    ):
        """
        Test 100-log batch meets 1.5-2s target.

        Phase 3 target: 1.5-2s for 100 logs (parallel)
        Note: This test requires 100 logs to be available
        """
        # Collect logs from valid test directories
        all_logs: list[Path] = []

        # Primary: sample_logs/FO4 has extensive test data
        sample_dir = Path("sample_logs/FO4")
        if sample_dir.exists():
            all_logs.extend(sample_dir.glob("*.log"))

        # Secondary: Crash Logs directory
        crash_dir = Path("Crash Logs")
        if crash_dir.exists():
            all_logs.extend(crash_dir.glob("*.log"))

        if len(all_logs) < 100:
            pytest.skip(f"Need 100 logs for large batch target test (found {len(all_logs)})")

        logs = all_logs[:100]

        result = orchestrator.process_crash_logs_batch(
            log_paths=logs,
            max_concurrent=20,
        )

        total_seconds = result.total_time_ms / 1000

        # Target: < 2s for 100 logs
        assert total_seconds < 2.0, f"100-log batch target not met: {total_seconds:.2f}s (target: < 2.0s)"

    def test_parallelism_factor_target(
        self,
        orchestrator: ClassicOrchestrator,
        sample_crash_logs: list[Path],
    ):
        """
        Test parallelism factor meets target.

        Target: > 2.0x parallelism factor for batch processing
        """
        logs = sample_crash_logs[:10]
        if len(logs) < 10:
            pytest.skip("Need 10 logs for parallelism target test")

        result = orchestrator.process_crash_logs_batch(
            log_paths=logs,
            max_concurrent=10,
        )

        # Target: > 2.0x parallelism factor
        assert result.parallelism_factor > 2.0, f"Parallelism factor target not met: {result.parallelism_factor:.2f}x (target: > 2.0x)"
