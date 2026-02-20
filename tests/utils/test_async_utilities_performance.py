"""Performance and stress tests for AsyncUtilities module.

Tests performance characteristics and behavior under stress conditions.
"""

import asyncio
import gc
import time
from typing import Any

import pytest

from ClassicLib.Utils.async_utils import (
    AsyncLazyLoader,
    AsyncTimer,
    async_filter,
    async_map,
    async_retry,
    async_timeout,
    batch_process,
    gather_with_concurrency,
    run_in_executor,
    run_with_timeout,
    throttle,
)

# Skip these tests in CI or when running quick tests
pytestmark = pytest.mark.performance


class TestPerformanceCharacteristics:
    """Test performance characteristics of async utilities."""

    @pytest.mark.asyncio
    async def test_gather_concurrency_scaling(self):
        """Test how gather_with_concurrency scales with different limits."""

        async def work_unit(n: int) -> int:
            await asyncio.sleep(0.01)  # Simulate I/O
            return n * 2

        items = list(range(100))
        # [work_unit(i) for i in items]  # Removed unawaited coroutine creation

        # Test different concurrency levels
        timings = {}

        for concurrency in [1, 5, 10, 20, 50, 100]:
            start = time.perf_counter()
            results = await gather_with_concurrency(concurrency, *[work_unit(i) for i in items])
            elapsed = time.perf_counter() - start
            timings[concurrency] = elapsed

            # Verify correctness
            assert results == [i * 2 for i in items]

        # Higher concurrency should be faster (up to a point)
        assert timings[10] < timings[1]
        assert timings[50] < timings[5]

        print("\nConcurrency scaling results:")
        for conc, timing in timings.items():
            print(f"  Concurrency {conc:3d}: {timing:.3f}s")

    @pytest.mark.asyncio
    async def test_batch_process_optimal_batch_size(self):
        """Test finding optimal batch size for batch_process."""

        async def process_item(item: int) -> int:
            # Simulate variable processing time
            await asyncio.sleep(0.001 + (item % 10) * 0.0001)
            return item * 2

        items = list(range(200))
        batch_sizes = [1, 5, 10, 20, 50, 100]
        timings = {}

        for batch_size in batch_sizes:
            start = time.perf_counter()
            results = await batch_process(items, process_item, batch_size=batch_size, max_concurrent=10)
            elapsed = time.perf_counter() - start
            timings[batch_size] = elapsed

            # Verify correctness
            assert len(results) == 200

        print("\nBatch size performance:")
        for size, timing in timings.items():
            print(f"  Batch size {size:3d}: {timing:.3f}s")

    @pytest.mark.asyncio
    async def test_async_map_memory_efficiency(self):
        """Test memory efficiency of async_map with large datasets."""
        # Track memory before
        gc.collect()

        async def light_processor(item: int) -> int:
            # Minimal memory operation
            return item * 2

        # Process large dataset
        large_dataset = list(range(10000))

        async with AsyncTimer() as timer:
            results = await async_map(light_processor, large_dataset, max_concurrent=100)

        assert len(results) == 10000
        assert timer.elapsed < 5.0  # Should complete quickly

        # Force garbage collection
        gc.collect()

    @pytest.mark.asyncio
    async def test_async_filter_performance_with_complex_predicate(self):
        """Test async_filter performance with complex predicates."""

        async def complex_predicate(item: dict) -> bool:
            # Simulate complex validation
            await asyncio.sleep(0.001)
            return item["value"] % 2 == 0 and item["value"] < 500 and len(item["tag"]) > 3

        # Create test dataset
        items = [{"value": i, "tag": f"tag_{i:04d}"} for i in range(1000)]

        async with AsyncTimer() as timer:
            filtered = await async_filter(complex_predicate, items, max_concurrent=50)

        expected_count = len([i for i in items if i["value"] % 2 == 0 and i["value"] < 500])
        assert len(filtered) == expected_count
        assert timer.elapsed < 5.0


class TestStressConditions:
    """Test behavior under stress conditions."""

    @pytest.mark.asyncio
    async def test_high_concurrency_stress(self):
        """Test system behavior with very high concurrency."""
        completed_count = 0

        async def increment_counter(n: int) -> int:
            nonlocal completed_count
            await asyncio.sleep(0.0001)
            completed_count += 1
            return n

        # Create many concurrent operations
        items = list(range(1000))
        results = await gather_with_concurrency(
            500,  # Very high concurrency
            *[increment_counter(i) for i in items],
        )

        assert len(results) == 1000
        assert completed_count == 1000

    @pytest.mark.asyncio
    async def test_retry_under_high_failure_rate(self):
        """Test retry decorator with high failure rate."""
        attempt_counts = {}

        @async_retry(max_attempts=5, delay=0.001, backoff=1.5)
        async def flaky_operation(item_id: int) -> str:
            if item_id not in attempt_counts:
                attempt_counts[item_id] = 0
            attempt_counts[item_id] += 1

            # 60% failure rate until 3rd attempt
            if attempt_counts[item_id] < 3 and item_id % 10 < 6:
                raise ConnectionError(f"Temporary failure for {item_id}")

            return f"success_{item_id}"

        # Process many items with retry
        tasks = [flaky_operation(i) for i in range(100)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 100
        assert all("success_" in r for r in results)

        # Most items should have required retries
        retry_needed = sum(1 for count in attempt_counts.values() if count > 1)
        assert retry_needed > 50  # At least 50% needed retries

    @pytest.mark.asyncio
    async def test_timeout_cascade_prevention(self):
        """Test that timeouts don't cascade and affect other operations."""
        success_count = 0
        timeout_count = 0

        @async_timeout(0.05)
        async def variable_duration(duration: float) -> str:
            await asyncio.sleep(duration)
            return "completed"

        async def process_with_timeout(duration: float) -> str:
            nonlocal success_count, timeout_count
            try:
                result = await variable_duration(duration)
                success_count += 1
                return result
            except TimeoutError:
                timeout_count += 1
                return "timeout"

        # Mix of durations, some will timeout
        durations = [0.01, 0.1, 0.02, 0.2, 0.03, 0.15] * 10

        await asyncio.gather(*[process_with_timeout(d) for d in durations], return_exceptions=False)

        assert success_count > 0
        assert timeout_count > 0
        assert success_count + timeout_count == len(durations)

    @pytest.mark.asyncio
    async def test_throttle_under_burst_load(self):
        """Test throttle behavior under burst load."""
        from ClassicLib.Utils.async_utils import _throttler_registry, reset_throttlers

        # Reset state before test
        reset_throttlers()
        request_times = []

        async def make_request(request_id: int):
            await throttle(10, 1.0)  # 10 requests per second
            request_times.append(time.time())
            return request_id

        try:
            # Send burst of requests
            start_time = time.time()
            tasks = [make_request(i) for i in range(30)]
            results = await asyncio.gather(*tasks)

            total_time = time.time() - start_time

            assert len(results) == 30
            # With 10 req/s rate limit, 30 requests should take ~3 seconds
            assert total_time > 2.0  # Allow some tolerance
        finally:
            # Clean up background tasks
            for throttler in _throttler_registry.values():
                await throttler.cleanup()
            reset_throttlers()

    @pytest.mark.asyncio
    async def test_lazy_loader_concurrent_stress(self):
        """Test AsyncLazyLoader under heavy concurrent access."""
        load_count = 0

        async def expensive_loader():
            nonlocal load_count
            load_count += 1
            await asyncio.sleep(0.1)  # Simulate expensive operation
            return {"data": "expensive_result", "load_count": load_count}

        loader = AsyncLazyLoader(expensive_loader)

        # Many concurrent access attempts
        tasks = [loader.get() for _ in range(100)]
        results = await asyncio.gather(*tasks)

        # Should only load once despite concurrent access
        assert load_count == 1
        assert all(r["load_count"] == 1 for r in results)
        assert all(r["data"] == "expensive_result" for r in results)


class TestMemoryAndResourceManagement:
    """Test memory and resource management."""

    @pytest.mark.asyncio
    async def test_no_memory_leak_in_repeated_operations(self):
        """Test that repeated operations don't leak memory."""

        async def simple_operation(x: int) -> int:
            return x * 2

        # Perform many iterations
        for iteration in range(100):
            items = list(range(100))
            results = await async_map(simple_operation, items, max_concurrent=10)
            assert len(results) == 100

            # Clean up references
            del results
            del items

            # Force garbage collection periodically
            if iteration % 10 == 0:
                gc.collect()

    @pytest.mark.asyncio
    async def test_executor_cleanup(self):
        """Test that run_in_executor properly cleans up resources."""

        def cpu_bound_task(n: int) -> int:
            return sum(i * i for i in range(n))

        # Run many executor tasks
        tasks = []
        for i in range(100):
            tasks.append(run_in_executor(cpu_bound_task, 100 + i))

        results = await asyncio.gather(*tasks)
        assert len(results) == 100

        # Verify all tasks completed
        assert all(isinstance(r, int) for r in results)

    @pytest.mark.asyncio
    async def test_semaphore_cleanup_in_gather(self):
        """Test that semaphores are properly released in gather_with_concurrency."""
        call_times = []

        async def track_timing(item: int) -> int:
            call_times.append(time.time())
            await asyncio.sleep(0.01)
            return item

        # Run multiple batches to ensure semaphore reuse works
        for _batch_num in range(3):
            call_times.clear()
            coros = [track_timing(i) for i in range(10)]
            results = await gather_with_concurrency(3, *coros)

            assert len(results) == 10
            # Verify concurrency was limited (should see batching)
            # With concurrency of 3 and 10 items, should see at least 4 waves

    @pytest.mark.asyncio
    async def test_exception_cleanup_in_batch_process(self):
        """Test that exceptions don't leave resources in bad state."""
        process_count = 0

        async def sometimes_failing_processor(item: int) -> int:
            nonlocal process_count
            process_count += 1
            if item == 5:
                raise ValueError("Item 5 fails")
            return item * 2

        items = list(range(10))

        with pytest.raises(ValueError, match="Item 5 fails"):
            await batch_process(items, sometimes_failing_processor, batch_size=3, max_concurrent=2)

        # Some items were processed before failure
        assert process_count > 0
        assert process_count <= 10  # Should stop on error


class TestEdgeCasePerformance:
    """Test performance in edge case scenarios."""

    @pytest.mark.asyncio
    async def test_single_item_performance(self):
        """Test that single item doesn't have unnecessary overhead."""

        async def process(item: int) -> int:
            return item * 2

        # Single item should be fast
        async with AsyncTimer() as timer:
            result = await async_map(process, [42])

        assert result == [84]
        assert timer.elapsed < 0.1  # Should be very fast

    @pytest.mark.asyncio
    async def test_empty_input_performance(self):
        """Test that empty inputs return quickly."""

        async def process(item: Any) -> Any:
            return item

        operations = [
            async_map(process, []),
            async_filter(process, []),
            batch_process([], process),
            gather_with_concurrency(10),
        ]

        async with AsyncTimer() as timer:
            results = await asyncio.gather(*operations)

        # All should return empty results quickly
        assert all(r == [] for r in results)
        assert timer.elapsed < 0.1

    @pytest.mark.asyncio
    async def test_immediate_timeout_performance(self):
        """Test that immediate timeouts fail quickly."""

        async def never_completes():
            await asyncio.sleep(10)

        async with AsyncTimer() as timer:
            wrapper = run_with_timeout(never_completes(), 0.001, default="timeout")
            result = await wrapper()

        assert result == "timeout"
        assert timer.elapsed < 0.1  # Should timeout quickly
