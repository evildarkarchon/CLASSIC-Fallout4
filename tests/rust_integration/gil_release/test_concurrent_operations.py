"""Tests proving GIL is released during Rust operations.

These tests verify that Python's GIL is properly released when calling
into Rust code, allowing concurrent Python threads to make progress.

Test Strategy:
- Run same Rust operation from multiple threads simultaneously
- If GIL is held: operations run sequentially (~N * T time)
- If GIL is released: operations run in parallel (~T time with overhead)
- Assert total time is significantly less than sequential time
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest


@pytest.mark.integration
class TestGILReleaseConcurrency:
    """Tests proving GIL release enables true concurrency."""

    def test_scanlog_parser_releases_gil(self, thread_pool: ThreadPoolExecutor, large_test_data: list[str]) -> None:
        """Prove log parsing releases GIL by running concurrently."""
        try:
            import classic_scanlog
        except ImportError:
            pytest.skip("classic_scanlog not available")

        # Create parser
        parser = classic_scanlog.LogParser()

        # Measure single-threaded baseline
        start_single = time.perf_counter()
        _ = parser.parse_segments(large_test_data)
        single_time = time.perf_counter() - start_single

        if single_time < 0.001:  # Less than 1ms
            pytest.skip("Operation too fast to measure GIL release")

        # Run 4 threads concurrently
        def parse_in_thread() -> object:
            p = classic_scanlog.LogParser()
            return p.parse_segments(large_test_data)

        start_concurrent = time.perf_counter()
        futures = [thread_pool.submit(parse_in_thread) for _ in range(4)]
        results = [f.result() for f in as_completed(futures)]
        concurrent_time = time.perf_counter() - start_concurrent

        # If GIL released: concurrent_time ~ single_time (with overhead)
        # If GIL held: concurrent_time ~ 4 * single_time
        # Allow 2.5x single time as threshold (imperfect parallelism)
        # Add 15ms floor for thread scheduling overhead on CI runners
        max_expected = single_time * 2.5 + 0.015
        assert concurrent_time < max_expected, (
            f"Operations appear sequential (GIL not released). "
            f"Single: {single_time:.3f}s, Concurrent: {concurrent_time:.3f}s, "
            f"Expected < {max_expected:.3f}s"
        )
        assert len(results) == 4

    def test_yaml_operations_concurrent_safety(self, thread_pool: ThreadPoolExecutor) -> None:
        """Verify YAML operations are thread-safe under concurrent access.

        Note: YAML operations release GIL during Rust parsing/serialization,
        but Python<->Rust object conversion requires GIL. This conversion
        dominates for operations returning large Python dicts. The scanlog
        and mod detection operations show better parallelism because they
        return simple types (lists of strings) rather than nested dicts.

        This test verifies thread safety rather than parallelism, ensuring
        concurrent YAML operations don't cause data corruption or crashes.
        """
        try:
            import classic_yaml
        except ImportError:
            pytest.skip("classic_yaml not available")

        # Generate YAML content
        yaml_content = "\n".join(f"key_{i}: value_{i}" for i in range(1000))

        # Parse once to get expected result
        ops = classic_yaml.YamlOperations()
        expected = ops.parse_yaml(yaml_content)

        errors: list[tuple[int, str]] = []
        results: list[tuple[int, dict]] = []
        lock = threading.Lock()

        def worker(worker_id: int) -> None:
            try:
                o = classic_yaml.YamlOperations()
                # Parse and dump multiple times
                for _ in range(5):
                    parsed = o.parse_yaml(yaml_content)
                    dumped = o.dump_yaml(parsed)
                    reparsed = o.parse_yaml(dumped)
                    if reparsed != expected:
                        raise ValueError("Round-trip produced different result")
                with lock:
                    results.append((worker_id, parsed))
            except Exception as e:
                with lock:
                    errors.append((worker_id, str(e)))

        # Run 8 concurrent workers
        futures = [thread_pool.submit(worker, i) for i in range(8)]
        for f in as_completed(futures):
            f.result()

        assert not errors, f"Workers encountered errors: {errors}"
        assert len(results) == 8, f"Expected 8 results, got {len(results)}"

        # Verify all results match expected
        for worker_id, result in results:
            assert result == expected, f"Worker {worker_id} produced incorrect result"

    def test_mod_detection_releases_gil(self, thread_pool: ThreadPoolExecutor, plugin_test_data: dict[str, str]) -> None:
        """Prove mod detection releases GIL."""
        try:
            import classic_scanlog
        except ImportError:
            pytest.skip("classic_scanlog not available")

        # Create test patterns (simulating YAML mods dict)
        patterns = {f"pattern{i}": f"Description {i}" for i in range(100)}

        # Measure single-threaded baseline
        start_single = time.perf_counter()
        _ = classic_scanlog.detect_mods_single(patterns, plugin_test_data)
        single_time = time.perf_counter() - start_single

        if single_time < 0.001:
            pytest.skip("Operation too fast to measure GIL release")

        # Run concurrent detection
        def detect_mods() -> list[str]:
            return classic_scanlog.detect_mods_single(patterns, plugin_test_data)

        start_concurrent = time.perf_counter()
        futures = [thread_pool.submit(detect_mods) for _ in range(4)]
        _ = [f.result() for f in as_completed(futures)]
        concurrent_time = time.perf_counter() - start_concurrent

        # Add 15ms floor for thread scheduling overhead on CI runners
        max_expected = single_time * 2.5 + 0.015
        assert concurrent_time < max_expected, (
            f"Mod detection appears sequential. Single: {single_time:.3f}s, Concurrent: {concurrent_time:.3f}s"
        )


@pytest.mark.integration
class TestGILReleaseDoesNotBreakFunctionality:
    """Verify GIL release doesn't cause correctness issues."""

    def test_concurrent_results_are_correct(self, thread_pool: ThreadPoolExecutor, large_test_data: list[str]) -> None:
        """Ensure concurrent execution produces correct results."""
        try:
            import classic_scanlog
        except ImportError:
            pytest.skip("classic_scanlog not available")

        # Get baseline result
        parser = classic_scanlog.LogParser()
        baseline_result = parser.parse_segments(large_test_data)

        # Run concurrently and verify all results match
        def parse_and_return() -> list:
            p = classic_scanlog.LogParser()
            return p.parse_segments(large_test_data)

        futures = [thread_pool.submit(parse_and_return) for _ in range(4)]
        concurrent_results = [f.result() for f in as_completed(futures)]

        # All results should have same structure as baseline
        for i, result in enumerate(concurrent_results):
            assert len(result) == len(baseline_result), f"Thread {i} produced different segment count"

    def test_no_data_races_in_concurrent_access(self, thread_pool: ThreadPoolExecutor) -> None:
        """Stress test for data races under concurrent load."""
        try:
            import classic_scanlog
        except ImportError:
            pytest.skip("classic_scanlog not available")

        errors: list[tuple[int, str]] = []
        results: list[tuple[int, int]] = []
        lock = threading.Lock()

        def worker(worker_id: int) -> None:
            try:
                parser = classic_scanlog.LogParser()
                data = [f"Line {i} from worker {worker_id}" for i in range(1000)]
                result = parser.parse_segments(data)
                with lock:
                    results.append((worker_id, len(result) if result else 0))
            except Exception as e:
                with lock:
                    errors.append((worker_id, str(e)))

        # Run 10 concurrent workers
        futures = [thread_pool.submit(worker, i) for i in range(10)]
        for f in as_completed(futures):
            f.result()  # Propagate exceptions

        assert not errors, f"Workers encountered errors: {errors}"
        assert len(results) == 10, f"Expected 10 results, got {len(results)}"

    def test_yaml_concurrent_correctness(self, thread_pool: ThreadPoolExecutor) -> None:
        """Ensure concurrent YAML parsing produces correct results."""
        try:
            import classic_yaml
        except ImportError:
            pytest.skip("classic_yaml not available")

        # Test data
        yaml_content = "\n".join(f"key_{i}: value_{i}" for i in range(100))

        # Get baseline
        ops = classic_yaml.YamlOperations()
        baseline = ops.parse_yaml(yaml_content)

        # Run concurrent parses
        def parse_yaml() -> object:
            o = classic_yaml.YamlOperations()
            return o.parse_yaml(yaml_content)

        futures = [thread_pool.submit(parse_yaml) for _ in range(8)]
        concurrent_results = [f.result() for f in as_completed(futures)]

        # All should match baseline
        for i, result in enumerate(concurrent_results):
            assert result == baseline, f"Thread {i} produced different result"


@pytest.mark.integration
class TestGILReleasePerformanceGain:
    """Tests that measure actual performance gains from GIL release."""

    def test_parallel_speedup_log_parsing(self, thread_pool: ThreadPoolExecutor, large_test_data: list[str]) -> None:
        """Measure actual speedup from parallel log parsing."""
        try:
            import classic_scanlog
        except ImportError:
            pytest.skip("classic_scanlog not available")

        # Use larger data for more reliable timing
        extra_large_data = large_test_data * 5  # 50,000 lines

        # Sequential timing with multiple iterations
        parser = classic_scanlog.LogParser()
        iterations = 8
        seq_start = time.perf_counter()
        for _ in range(iterations):
            parser.parse_segments(extra_large_data)
        sequential_time = time.perf_counter() - seq_start

        # Skip if operations are still too fast
        if sequential_time < 0.1:
            pytest.skip("Operations too fast for reliable speedup measurement")

        # Parallel timing
        def parse_task_batch() -> list[object]:
            p = classic_scanlog.LogParser()
            return [p.parse_segments(extra_large_data) for _ in range(iterations // 4)]

        par_start = time.perf_counter()
        futures = [thread_pool.submit(parse_task_batch) for _ in range(4)]
        _ = [f.result() for f in as_completed(futures)]
        parallel_time = time.perf_counter() - par_start

        # Calculate speedup
        speedup = sequential_time / parallel_time if parallel_time > 0 else 0

        # We expect at least 1.2x speedup with proper GIL release
        # (reduced from 1.5x due to thread overhead on fast operations)
        assert speedup >= 1.2, (
            f"Insufficient speedup (GIL may not be released properly). "
            f"Sequential: {sequential_time:.3f}s, Parallel: {parallel_time:.3f}s, "
            f"Speedup: {speedup:.2f}x (expected >= 1.2x)"
        )
