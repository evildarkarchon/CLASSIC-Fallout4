"""Integration tests for AsyncUtilities module.

Tests async utilities working together and with real I/O operations.
"""

import asyncio
from pathlib import Path
from typing import Any

import pytest

from ClassicLib.Utils.Async import (
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
)


class TestAsyncUtilitiesIntegration:
    """Integration tests for async utilities working together."""

    @pytest.mark.asyncio
    async def test_batch_process_with_retry(self, tmp_path: Path):
        """Test batch processing with retry logic for file operations."""
        test_files = []
        for i in range(5):
            file_path = tmp_path / f"test_{i}.txt"
            file_path.write_text(f"content_{i}")
            test_files.append(file_path)

        failure_count = {}

        @async_retry(max_attempts=3, delay=0.01)
        async def process_file_with_retry(file_path: Path) -> str:
            # Simulate flaky file reading
            if file_path not in failure_count:
                failure_count[file_path] = 0

            failure_count[file_path] += 1
            if failure_count[file_path] < 2:
                raise OSError(f"Temporary read error for {file_path.name}")

            content = file_path.read_text()
            return f"processed_{content}"

        results = await batch_process(test_files, process_file_with_retry, batch_size=2, max_concurrent=2)

        assert len(results) == 5
        assert all("processed_content_" in r for r in results)
        # Each file should have been attempted at least twice
        assert all(count >= 2 for count in failure_count.values())

    @pytest.mark.asyncio
    async def test_async_map_with_timeout(self):
        """Test async_map with timeout wrapper."""

        @async_timeout(0.1)
        async def process_with_timeout(value: int) -> int:
            if value > 3:
                await asyncio.sleep(0.2)  # This will timeout
            return value * 2

        items = [1, 2, 3, 4, 5]

        # Some items will timeout
        with pytest.raises(TimeoutError):
            await async_map(process_with_timeout, items, max_concurrent=2)

    @pytest.mark.asyncio
    async def test_filter_and_map_pipeline(self):
        """Test chaining async_filter and async_map."""

        async def is_valid(item: int) -> bool:
            await asyncio.sleep(0.001)
            return item % 2 == 0

        async def transform(item: int) -> str:
            await asyncio.sleep(0.001)
            return f"item_{item}"

        items = list(range(10))

        # Filter even numbers then transform
        filtered = await async_filter(is_valid, items, max_concurrent=3)
        transformed = await async_map(transform, filtered, max_concurrent=3)

        assert transformed == ["item_0", "item_2", "item_4", "item_6", "item_8"]

    @pytest.mark.asyncio
    async def test_lazy_loader_with_timeout(self):
        """Test AsyncLazyLoader with timeout constraints."""

        async def slow_loader():
            await asyncio.sleep(0.1)
            return "slow_data"

        loader = AsyncLazyLoader(slow_loader)

        # First load with timeout should fail
        wrapper1 = run_with_timeout(loader.get(), 0.05, default="timeout")
        result = await wrapper1()
        assert result == "timeout"

        # Second attempt with longer timeout should succeed
        wrapper2 = run_with_timeout(loader.get(), 0.2, default="timeout")
        result = await wrapper2()
        assert result == "slow_data"

        # Subsequent access should be instant (cached)
        wrapper3 = run_with_timeout(loader.get(), 0.01, default="timeout")
        result = await wrapper3()
        assert result == "slow_data"

    @pytest.mark.asyncio
    async def test_concurrent_operations_with_timer(self):
        """Test timing concurrent operations."""
        async with AsyncTimer() as timer:
            # Run multiple operations concurrently

            async def operation(n: int) -> int:
                await asyncio.sleep(0.05)
                return n * 2

            results = await gather_with_concurrency(3, *[operation(i) for i in range(6)])

            # With concurrency of 3, 6 operations should take ~0.1s
            assert results == [0, 2, 4, 6, 8, 10]

        # Should take around 0.1 seconds (2 batches of 0.05s each)
        assert 0.08 < timer.elapsed < 0.15

    @pytest.mark.asyncio
    async def test_run_in_executor_with_file_operations(self, tmp_path: Path):
        """Test running sync file operations in executor."""

        def sync_file_operation(path: Path, content: str) -> int:
            # Synchronous file write
            path.write_text(content)
            # Return length of content written
            return len(content)

        test_file = tmp_path / "executor_test.txt"
        content = "Test content for executor"

        # Run sync operation in executor
        length = await run_in_executor(sync_file_operation, test_file, content)

        assert length == len(content)
        assert test_file.read_text() == content

    @pytest.mark.asyncio
    async def test_batch_process_mixed_sync_async(self):
        """Test batch processing with mixed sync/async processors."""
        items = list(range(10))

        # First pass: async processor
        async def async_double(x: int) -> int:
            await asyncio.sleep(0.001)
            return x * 2

        doubled = await batch_process(items, async_double, batch_size=3)

        # Second pass: sync processor
        def sync_add_ten(x: int) -> int:
            return x + 10

        final = await batch_process(doubled, sync_add_ten, batch_size=4)

        expected = [(i * 2) + 10 for i in range(10)]
        assert final == expected

    @pytest.mark.asyncio
    async def test_complex_error_handling_pipeline(self):
        """Test complex pipeline with multiple error handling strategies."""
        processed_items = []

        @async_retry(max_attempts=2, delay=0.01)
        @async_timeout(0.1)
        async def process_item(item: int) -> dict[str, Any]:
            # Simulate different behaviors based on item value
            if item == 3:
                # Will always fail after retries
                raise ValueError(f"Item {item} is invalid")
            if item == 5:
                # Will succeed on retry
                if item not in processed_items:
                    processed_items.append(item)
                    raise ConnectionError("Temporary network error")

            await asyncio.sleep(0.01)
            return {"item": item, "result": item * 2}

        items = [1, 2, 3, 4, 5, 6]
        results = []
        errors = []

        for item in items:
            try:
                result = await process_item(item)
                results.append(result)
            except Exception as e:
                errors.append({"item": item, "error": str(e)})

        # Should have processed all except item 3
        assert len(results) == 5
        assert len(errors) == 1
        assert errors[0]["item"] == 3

        # Item 5 should have been retried
        assert 5 in processed_items

    @pytest.mark.asyncio
    async def test_gather_with_concurrency_error_propagation(self):
        """Test that gather_with_concurrency properly propagates errors."""

        async def failing_coro(n: int):
            if n == 3:
                raise ValueError(f"Error at {n}")
            await asyncio.sleep(0.01)
            return n

        coros = [failing_coro(i) for i in range(5)]

        with pytest.raises(ValueError, match="Error at 3"):
            await gather_with_concurrency(2, *coros)

    @pytest.mark.asyncio
    async def test_performance_comparison(self):
        """Compare performance of different concurrency strategies."""
        items = list(range(20))

        async def slow_operation(n: int) -> int:
            await asyncio.sleep(0.01)
            return n * 2

        # Test 1: No concurrency limit
        async with AsyncTimer() as timer_unlimited:
            results_unlimited = await async_map(slow_operation, items)

        # Test 2: Limited concurrency
        async with AsyncTimer() as timer_limited:
            results_limited = await async_map(slow_operation, items, max_concurrent=5)

        # Test 3: Batch processing
        async with AsyncTimer() as timer_batch:
            results_batch = await batch_process(items, slow_operation, batch_size=5, max_concurrent=5)

        # All should produce same results
        assert results_unlimited == results_limited == results_batch

        # Unlimited should be fastest (all concurrent)
        assert timer_unlimited.elapsed < timer_limited.elapsed

        # Batch should be similar to limited concurrency
        assert abs(timer_batch.elapsed - timer_limited.elapsed) < 0.1
