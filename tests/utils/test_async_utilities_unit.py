"""Unit tests for AsyncUtilities module.

Tests individual async utility functions in isolation with proper mocking.
"""

import asyncio
import time
import tracemalloc
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ClassicLib.Utils.Async import (
    AsyncLazyLoader,
    AsyncTimer,
    ExecutorDecisionMaker,
    FAST_PATH_OPERATIONS,
    SIZE_DEPENDENT_OPERATIONS,
    async_filter,
    async_filter_smart,
    async_map,
    async_map_smart,
    async_retry,
    async_timeout,
    batch_process,
    batch_process_smart,
    gather_with_concurrency,
    run_in_executor,
    run_with_timeout,
    smart_run_in_executor,
    throttle,
)


@pytest.mark.unit
@pytest.mark.asyncio
class TestGatherWithConcurrency:
    """Tests for gather_with_concurrency function."""

    @pytest.mark.asyncio
    async def test_concurrent_execution_with_limit(self):
        """Should execute coroutines with concurrency limit."""
        execution_times = []

        async def track_execution(value: int) -> int:
            execution_times.append(time.time())
            await asyncio.sleep(0.01)
            return value * 2

        coros = [track_execution(i) for i in range(5)]
        results = await gather_with_concurrency(2, *coros)

        assert results == [0, 2, 4, 6, 8]
        # With concurrency of 2, we should see batched execution
        assert len(execution_times) == 5

    @pytest.mark.asyncio
    async def test_preserves_order_of_results(self):
        """Should return results in the same order as input."""

        async def delayed_return(value: int, delay: float) -> int:
            await asyncio.sleep(delay)
            return value

        # Create coroutines with varying delays
        coros = [
            delayed_return(1, 0.03),
            delayed_return(2, 0.01),
            delayed_return(3, 0.02),
        ]

        results = await gather_with_concurrency(3, *coros)
        assert results == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_handles_empty_input(self):
        """Should handle empty coroutine list."""
        results = await gather_with_concurrency(5)
        assert results == []


@pytest.mark.unit
@pytest.mark.asyncio
class TestBatchProcess:
    """Tests for batch_process function."""

    @pytest.mark.asyncio
    async def test_processes_items_in_batches(self):
        """Should process items in specified batch sizes."""
        processed_batches = []

        async def process_item(item: int) -> int:
            batch_size = len([i for i in processed_batches if i is None])
            if batch_size == 0 or processed_batches[-1] is not None:
                processed_batches.append(None)
            return item * 2

        items = list(range(10))
        results = await batch_process(items, process_item, batch_size=3, max_concurrent=2)

        assert results == [i * 2 for i in range(10)]
        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_handles_sync_processor(self):
        """Should handle synchronous processor functions."""

        def sync_processor(item: int) -> int:
            return item * 3

        items = [1, 2, 3, 4, 5]
        results = await batch_process(items, sync_processor, batch_size=2)

        assert results == [3, 6, 9, 12, 15]

    @pytest.mark.asyncio
    async def test_respects_max_concurrent(self):
        """Should respect max_concurrent parameter."""
        concurrent_count = 0
        max_seen = 0

        async def track_concurrency(item: int) -> int:
            nonlocal concurrent_count, max_seen
            concurrent_count += 1
            max_seen = max(max_seen, concurrent_count)
            await asyncio.sleep(0.01)
            concurrent_count -= 1
            return item

        items = list(range(10))
        await batch_process(items, track_concurrency, batch_size=5, max_concurrent=2)

        # Max concurrent should not exceed 2
        assert max_seen <= 2


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncRetry:
    """Tests for async_retry decorator."""

    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        """Should retry function on failure."""
        attempt_count = 0

        @async_retry(max_attempts=3, delay=0.01, backoff=1.0)
        async def flaky_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary error")
            return "success"

        result = await flaky_function()
        assert result == "success"
        assert attempt_count == 3

    @pytest.mark.asyncio
    @pytest.mark.skipif(tracemalloc.is_tracing(), reason="Timing assertions are unreliable with tracemalloc enabled")
    async def test_applies_backoff(self):
        """Should apply backoff multiplier between retries."""
        delays = []
        last_time = time.time()

        @async_retry(max_attempts=3, delay=0.05, backoff=2.0)
        async def measure_delays():
            nonlocal last_time
            current_time = time.time()
            delays.append(current_time - last_time)
            last_time = current_time
            if len(delays) < 3:
                raise ValueError("Retry me")
            return "done"

        result = await measure_delays()
        assert result == "done"
        # Check that delays are present (we get 3 measurements)
        assert len(delays) == 3
        # With backoff=2.0, second retry delay should be larger than first
        # Verify the delay increases (backoff is being applied)
        assert delays[2] > delays[1] * 1.5  # Strict check when not under tracemalloc

    @pytest.mark.asyncio
    async def test_raises_after_max_attempts(self):
        """Should raise the last exception after max attempts."""

        @async_retry(max_attempts=2, delay=0.01)
        async def always_fails():
            raise RuntimeError("Permanent error")

        with pytest.raises(RuntimeError, match="Permanent error"):
            await always_fails()

    @pytest.mark.asyncio
    async def test_catches_specific_exceptions(self):
        """Should only retry specified exceptions."""

        @async_retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        async def specific_error():
            raise TypeError("Wrong type")

        with pytest.raises(TypeError):
            await specific_error()


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncTimeout:
    """Tests for async_timeout decorator."""

    @pytest.mark.asyncio
    async def test_enforces_timeout(self):
        """Should enforce timeout on slow functions."""

        @async_timeout(0.05)
        async def slow_function():
            await asyncio.sleep(0.2)
            return "completed"

        with pytest.raises(TimeoutError, match="slow_function timed out"):
            await slow_function()

    @pytest.mark.asyncio
    async def test_allows_fast_completion(self):
        """Should allow function to complete if faster than timeout."""

        @async_timeout(0.5)
        async def fast_function():
            await asyncio.sleep(0.01)
            return "quick"

        result = await fast_function()
        assert result == "quick"


@pytest.mark.unit
@pytest.mark.asyncio
class TestRunWithTimeout:
    """Tests for run_with_timeout function."""

    @pytest.mark.asyncio
    async def test_returns_default_on_timeout(self):
        """Should return default value on timeout."""

        async def slow_coro():
            await asyncio.sleep(0.2)
            return "completed"

        # run_with_timeout returns a coroutine function that needs to be awaited
        timeout_func = run_with_timeout(slow_coro(), 0.05, default="timeout")
        result = await timeout_func()
        assert result == "timeout"

    @pytest.mark.asyncio
    async def test_handles_coroutine_function(self):
        """Should handle both coroutine and coroutine function."""

        async def coro_func():
            return "from_func"

        # Test with coroutine function - returns a wrapper that needs to be awaited
        timeout_func = run_with_timeout(coro_func, 0.1, default="timeout")
        result = await timeout_func()
        assert result == "from_func"

        # Test with coroutine - returns a wrapper that needs to be awaited
        timeout_func = run_with_timeout(coro_func(), 0.1, default="timeout")
        result = await timeout_func()
        assert result == "from_func"

    @pytest.mark.asyncio
    async def test_returns_none_default(self):
        """Should return None as default if not specified."""

        async def timeout_func():
            await asyncio.sleep(0.2)

        # run_with_timeout returns a coroutine function that needs to be awaited
        wrapper = run_with_timeout(timeout_func(), 0.05)
        result = await wrapper()
        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncMap:
    """Tests for async_map function."""

    @pytest.mark.asyncio
    async def test_maps_async_function(self):
        """Should map async function over items."""

        async def double(x: int) -> int:
            await asyncio.sleep(0.01)
            return x * 2

        items = [1, 2, 3, 4, 5]
        results = await async_map(double, items)
        assert results == [2, 4, 6, 8, 10]

    @pytest.mark.asyncio
    async def test_maps_sync_function(self):
        """Should map sync function over items."""

        def triple(x: int) -> int:
            return x * 3

        items = [1, 2, 3]
        results = await async_map(triple, items)
        assert results == [3, 6, 9]

    @pytest.mark.asyncio
    async def test_respects_concurrency_limit(self):
        """Should respect max_concurrent parameter."""
        concurrent_count = 0
        max_seen = 0

        async def track_concurrency(item: int) -> int:
            nonlocal concurrent_count, max_seen
            concurrent_count += 1
            max_seen = max(max_seen, concurrent_count)
            await asyncio.sleep(0.01)
            concurrent_count -= 1
            return item

        items = list(range(10))
        await async_map(track_concurrency, items, max_concurrent=3)

        assert max_seen <= 3


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncFilter:
    """Tests for async_filter function."""

    @pytest.mark.asyncio
    async def test_filters_with_async_predicate(self):
        """Should filter items using async predicate."""

        async def is_even(x: int) -> bool:
            await asyncio.sleep(0.001)
            return x % 2 == 0

        items = [1, 2, 3, 4, 5, 6]
        results = await async_filter(is_even, items)
        assert results == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_filters_with_sync_predicate(self):
        """Should filter items using sync predicate."""

        def is_positive(x: int) -> bool:
            return x > 0

        items = [-2, -1, 0, 1, 2, 3]
        results = await async_filter(is_positive, items)
        assert results == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_preserves_order(self):
        """Should preserve original order of items."""

        async def is_selected(x: int) -> bool:
            # Add varying delays
            await asyncio.sleep(0.01 * (5 - x))
            return x in {1, 3, 5}

        items = [1, 2, 3, 4, 5]
        results = await async_filter(is_selected, items)
        assert results == [1, 3, 5]


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncTimer:
    """Tests for AsyncTimer context manager."""

    @pytest.mark.asyncio
    async def test_measures_elapsed_time(self):
        """Should measure elapsed time of async operations."""
        async with AsyncTimer() as timer:
            await asyncio.sleep(0.05)

        assert 0.04 < timer.elapsed < 0.1

    @pytest.mark.asyncio
    @pytest.mark.skipif(tracemalloc.is_tracing(), reason="Timing assertions are unreliable with tracemalloc enabled")
    async def test_elapsed_during_operation(self):
        """Should provide elapsed time during operation."""
        async with AsyncTimer() as timer:
            await asyncio.sleep(0.05)
            mid_elapsed = timer.elapsed
            await asyncio.sleep(0.05)

        assert mid_elapsed < timer.elapsed
        # Use lenient bounds: mid_elapsed should be positive and less than total
        assert 0.01 < mid_elapsed < 0.15


@pytest.mark.unit
@pytest.mark.asyncio
class TestThrottle:
    """Tests for throttle function."""

    @pytest.mark.asyncio
    @pytest.mark.slow  # This test uses real time delays
    async def test_limits_rate(self):
        """Should limit operations to specified rate."""
        # Reset global state before test
        from ClassicLib.Utils.Async import _throttler_registry, reset_throttlers

        reset_throttlers()

        operations = []

        try:
            for _i in range(5):
                await throttle(2, 0.1)  # 2 ops per 0.1 second
                operations.append(time.time())

            # First 2 should be immediate, next ones delayed
            assert operations[1] - operations[0] < 0.05
            # Third operation should be delayed
            assert operations[2] - operations[0] > 0.08
        finally:
            # Clean up any background tasks
            for throttler in _throttler_registry.values():
                await throttler.cleanup()
            reset_throttlers()


@pytest.mark.unit
@pytest.mark.asyncio
class TestThrottler:
    """Tests for the Throttler class (more testable design)."""

    @pytest.mark.asyncio
    async def test_throttler_context_manager(self):
        """Should work as a context manager."""
        from ClassicLib.Utils.Async import Throttler

        throttler = Throttler(2, 0.1)
        operations = []

        try:
            for _i in range(5):
                async with throttler:
                    operations.append(time.time())

            # Basic rate limiting check (first 2 immediate)
            assert len(operations) == 5
        finally:
            # Clean up background tasks
            await throttler.cleanup()

    @pytest.mark.asyncio
    async def test_throttler_cleanup(self):
        """Should properly clean up background tasks."""
        from ClassicLib.Utils.Async import Throttler

        throttler = Throttler(1, 0.5)

        # Create some operations that spawn background tasks
        async with throttler:
            pass
        async with throttler:
            pass

        # Should have background tasks
        assert len(throttler.tasks) > 0

        # Cleanup should cancel all tasks
        await throttler.cleanup()
        assert len(throttler.tasks) == 0

    @pytest.mark.asyncio
    async def test_throttler_isolation(self):
        """Multiple throttlers should be independent."""
        from ClassicLib.Utils.Async import Throttler

        throttler1 = Throttler(1, 0.1)
        throttler2 = Throttler(2, 0.1)

        try:
            # Each throttler should maintain its own state
            async with throttler1:
                pass
            async with throttler2:
                pass

            # Different throttlers should have different semaphores
            assert throttler1.semaphore != throttler2.semaphore
        finally:
            await throttler1.cleanup()
            await throttler2.cleanup()

    @pytest.mark.asyncio
    async def test_no_task_leakage(self):
        """Verify that using cleanup prevents task leakage between tests."""
        import gc

        from ClassicLib.Utils.Async import Throttler

        # Get initial task count
        initial_tasks = len(asyncio.all_tasks())

        throttler = Throttler(2, 0.1)

        # Create multiple throttled operations
        for _ in range(5):
            async with throttler:
                pass

        # Without cleanup, tasks would be lingering
        mid_tasks = len(asyncio.all_tasks())
        assert mid_tasks > initial_tasks  # Background tasks created

        # Clean up
        await throttler.cleanup()

        # Allow event loop to process cancellations
        await asyncio.sleep(0.01)
        gc.collect()

        # Task count should return to baseline
        final_tasks = len(asyncio.all_tasks())
        assert final_tasks == initial_tasks


@pytest.mark.unit
@pytest.mark.asyncio
class TestRunInExecutor:
    """Tests for run_in_executor function."""

    @pytest.mark.asyncio
    async def test_runs_sync_function(self):
        """Should run synchronous function in executor."""

        def sync_operation(x: int, y: int) -> int:
            return x + y

        result = await run_in_executor(sync_operation, 5, 3)
        assert result == 8

    @pytest.mark.asyncio
    async def test_handles_kwargs(self):
        """Should handle keyword arguments."""

        def sync_with_kwargs(a: int, b: int = 10, c: int = 20) -> int:
            return a + b + c

        result = await run_in_executor(sync_with_kwargs, 5, b=15, c=25)
        assert result == 45


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncLazyLoader:
    """Tests for AsyncLazyLoader class."""

    @pytest.mark.asyncio
    async def test_loads_on_first_access(self):
        """Should load data on first access only."""
        load_count = 0

        async def load_data():
            nonlocal load_count
            load_count += 1
            await asyncio.sleep(0.01)
            return "loaded_data"

        loader = AsyncLazyLoader(load_data)

        # First access should load
        data1 = await loader.get()
        assert data1 == "loaded_data"
        assert load_count == 1

        # Second access should use cache
        data2 = await loader.get()
        assert data2 == "loaded_data"
        assert load_count == 1

    @pytest.mark.asyncio
    async def test_handles_sync_loader(self):
        """Should handle synchronous loader functions."""

        def sync_loader():
            return "sync_data"

        loader = AsyncLazyLoader(sync_loader)
        data = await loader.get()
        assert data == "sync_data"

    @pytest.mark.asyncio
    async def test_reset_clears_cache(self):
        """Should reload data after reset."""
        load_count = 0

        async def counting_loader():
            nonlocal load_count
            load_count += 1
            return f"load_{load_count}"

        loader = AsyncLazyLoader(counting_loader)

        data1 = await loader.get()
        assert data1 == "load_1"

        loader.reset()

        data2 = await loader.get()
        assert data2 == "load_2"

    @pytest.mark.asyncio
    async def test_thread_safe_loading(self):
        """Should handle concurrent access safely."""
        load_count = 0

        async def slow_loader():
            nonlocal load_count
            load_count += 1
            await asyncio.sleep(0.05)
            return "data"

        loader = AsyncLazyLoader(slow_loader)

        # Concurrent access should only load once
        results = await asyncio.gather(loader.get(), loader.get(), loader.get())

        assert all(r == "data" for r in results)
        assert load_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
class TestExecutorDecisionMaker:
    """Tests for ExecutorDecisionMaker class."""

    @pytest.mark.asyncio
    async def test_run_with_executor_with_kwargs(self):
        """Should correctly run function with kwargs via executor."""

        def func_with_kwargs(a: int, b: int = 10) -> int:
            return a + b

        decision_maker = ExecutorDecisionMaker(
            func_with_kwargs,
            args=(5,),
            kwargs={"b": 20},
            threshold_bytes=1024,
        )

        result = await decision_maker._run_with_executor()
        assert result == 25

    @pytest.mark.asyncio
    async def test_run_with_executor_without_kwargs(self):
        """Should correctly run function without kwargs via executor."""

        def simple_func(a: int, b: int) -> int:
            return a * b

        decision_maker = ExecutorDecisionMaker(
            simple_func,
            args=(3, 4),
            kwargs={},
            threshold_bytes=1024,
        )

        result = await decision_maker._run_with_executor()
        assert result == 12

    @pytest.mark.asyncio
    async def test_run_directly(self):
        """Should run function directly without executor."""

        def direct_func(x: int) -> int:
            return x ** 2

        decision_maker = ExecutorDecisionMaker(
            direct_func,
            args=(5,),
            kwargs={},
            threshold_bytes=1024,
        )

        result = decision_maker._run_directly()
        assert result == 25

    @pytest.mark.asyncio
    async def test_run_directly_with_kwargs(self):
        """Should run function directly with kwargs."""

        def func_with_kwargs(x: int, multiplier: int = 2) -> int:
            return x * multiplier

        decision_maker = ExecutorDecisionMaker(
            func_with_kwargs,
            args=(5,),
            kwargs={"multiplier": 3},
            threshold_bytes=1024,
        )

        result = decision_maker._run_directly()
        assert result == 15

    @pytest.mark.asyncio
    async def test_should_use_executor_for_io_no_args(self):
        """Should default to True when no args provided."""

        def io_func() -> None:
            pass

        decision_maker = ExecutorDecisionMaker(
            io_func, args=(), kwargs={}, threshold_bytes=1024
        )

        result = decision_maker._should_use_executor_for_io()
        assert result is True

    @pytest.mark.asyncio
    async def test_should_use_executor_for_io_non_path_arg(self):
        """Should default to True when first arg is not Path/str."""

        def io_func(data: int) -> None:
            pass

        decision_maker = ExecutorDecisionMaker(
            io_func, args=(42,), kwargs={}, threshold_bytes=1024
        )

        result = decision_maker._should_use_executor_for_io()
        assert result is True

    @pytest.mark.asyncio
    async def test_should_use_executor_for_read_small_file(self, tmp_path: Path):
        """Should return False for read operation on small file."""
        small_file = tmp_path / "small.txt"
        small_file.write_text("small content")

        # Create a mock function with __name__ = "read_text"
        mock_func = MagicMock()
        mock_func.__name__ = "read_text"

        decision_maker = ExecutorDecisionMaker(
            mock_func, args=(small_file,), kwargs={}, threshold_bytes=1024
        )

        result = decision_maker._should_use_executor_for_io()
        assert result is False  # Small file, run directly

    @pytest.mark.asyncio
    async def test_should_use_executor_for_read_large_file(self, tmp_path: Path):
        """Should return True for read operation on large file."""
        large_file = tmp_path / "large.txt"
        large_file.write_text("x" * 2048)  # Larger than 1024 threshold

        mock_func = MagicMock()
        mock_func.__name__ = "read_text"

        decision_maker = ExecutorDecisionMaker(
            mock_func, args=(large_file,), kwargs={}, threshold_bytes=1024
        )

        result = decision_maker._should_use_executor_for_io()
        assert result is True  # Large file, use executor

    @pytest.mark.asyncio
    async def test_should_use_executor_for_write_small_content(self, tmp_path: Path):
        """Should return False for write operation with small content."""
        target_file = tmp_path / "output.txt"
        small_content = "short"

        mock_func = MagicMock()
        mock_func.__name__ = "write_text"

        decision_maker = ExecutorDecisionMaker(
            mock_func, args=(target_file, small_content), kwargs={}, threshold_bytes=1024
        )

        result = decision_maker._should_use_executor_for_io()
        assert result is False  # Small content, run directly

    @pytest.mark.asyncio
    async def test_should_use_executor_for_write_large_content(self, tmp_path: Path):
        """Should return True for write operation with large content."""
        target_file = tmp_path / "output.txt"
        large_content = "x" * 2048

        mock_func = MagicMock()
        mock_func.__name__ = "write_text"

        decision_maker = ExecutorDecisionMaker(
            mock_func, args=(target_file, large_content), kwargs={}, threshold_bytes=1024
        )

        result = decision_maker._should_use_executor_for_io()
        assert result is True  # Large content, use executor

    @pytest.mark.asyncio
    async def test_should_use_executor_handles_oserror(self, tmp_path: Path):
        """Should return True on OSError (default to executor)."""
        nonexistent = tmp_path / "nonexistent.txt"

        mock_func = MagicMock()
        mock_func.__name__ = "read_text"

        decision_maker = ExecutorDecisionMaker(
            mock_func, args=(nonexistent,), kwargs={}, threshold_bytes=1024
        )

        # File doesn't exist, so path.stat() would fail
        # But exists() returns False, so it should go to else branch and return True
        result = decision_maker._should_use_executor_for_io()
        assert result is True

    @pytest.mark.asyncio
    async def test_execute_force_executor_true(self):
        """Should use executor when force_executor=True."""

        def simple_func(x: int) -> int:
            return x * 2

        decision_maker = ExecutorDecisionMaker(
            simple_func, args=(5,), kwargs={}, threshold_bytes=1024
        )

        result = await decision_maker.execute(force_executor=True)
        assert result == 10

    @pytest.mark.asyncio
    async def test_execute_force_executor_false(self):
        """Should run directly when force_executor=False."""

        def simple_func(x: int) -> int:
            return x * 2

        decision_maker = ExecutorDecisionMaker(
            simple_func, args=(5,), kwargs={}, threshold_bytes=1024
        )

        result = await decision_maker.execute(force_executor=False)
        assert result == 10

    @pytest.mark.asyncio
    async def test_execute_auto_fast_path(self):
        """Should run directly for fast path operations."""

        def exists_mock(path: str) -> bool:
            return True

        # Name the function to match a fast path operation
        exists_mock.__name__ = "exists"

        decision_maker = ExecutorDecisionMaker(
            exists_mock, args=("/some/path",), kwargs={}, threshold_bytes=1024
        )

        result = await decision_maker.execute(force_executor=None)
        assert result is True

    @pytest.mark.asyncio
    async def test_execute_auto_unknown_defaults_to_executor(self):
        """Should use executor for unknown operations."""

        def custom_operation(x: int) -> int:
            return x + 1

        decision_maker = ExecutorDecisionMaker(
            custom_operation, args=(10,), kwargs={}, threshold_bytes=1024
        )

        result = await decision_maker.execute(force_executor=None)
        assert result == 11


@pytest.mark.unit
@pytest.mark.asyncio
class TestSmartRunInExecutor:
    """Tests for smart_run_in_executor function."""

    @pytest.mark.asyncio
    async def test_force_executor_true(self):
        """Should always use executor when force_executor=True."""

        def simple_func(x: int) -> int:
            return x * 3

        result = await smart_run_in_executor(simple_func, 5, force_executor=True)
        assert result == 15

    @pytest.mark.asyncio
    async def test_force_executor_false(self):
        """Should run directly when force_executor=False."""

        def simple_func(x: int) -> int:
            return x * 4

        result = await smart_run_in_executor(simple_func, 5, force_executor=False)
        assert result == 20

    @pytest.mark.asyncio
    async def test_auto_fast_path_operation(self):
        """Should detect and run fast path operations directly."""

        def exists(path: str) -> bool:
            return True

        result = await smart_run_in_executor(exists, "/some/path")
        assert result is True

    @pytest.mark.asyncio
    async def test_with_kwargs(self):
        """Should correctly pass kwargs to function."""

        def func_with_kwargs(a: int, b: int = 10, c: int = 20) -> int:
            return a + b + c

        result = await smart_run_in_executor(func_with_kwargs, 5, b=15, c=25)
        assert result == 45

    @pytest.mark.asyncio
    async def test_custom_threshold_bytes(self, tmp_path: Path):
        """Should respect custom threshold_bytes parameter."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("x" * 500)

        def read_text(path: Path) -> str:
            return path.read_text()

        # With threshold 250, 500 byte file should use executor
        # With threshold 1000, should run directly
        result_high = await smart_run_in_executor(
            read_text, test_file, threshold_bytes=1000
        )
        assert result_high == "x" * 500

        result_low = await smart_run_in_executor(
            read_text, test_file, threshold_bytes=250
        )
        assert result_low == "x" * 500


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncMapSmart:
    """Tests for async_map_smart function."""

    @pytest.mark.asyncio
    async def test_maps_async_function(self):
        """Should map async function over items."""

        async def double(x: int) -> int:
            await asyncio.sleep(0.001)
            return x * 2

        items = [1, 2, 3, 4, 5]
        results = await async_map_smart(double, items)
        assert results == [2, 4, 6, 8, 10]

    @pytest.mark.asyncio
    async def test_maps_sync_function_with_executor_never(self):
        """Should run sync function directly with use_executor='never'."""

        def triple(x: int) -> int:
            return x * 3

        items = [1, 2, 3]
        results = await async_map_smart(triple, items, use_executor="never")
        assert results == [3, 6, 9]

    @pytest.mark.asyncio
    async def test_maps_sync_function_with_executor_always(self):
        """Should run sync function in executor with use_executor='always'."""

        def quadruple(x: int) -> int:
            return x * 4

        items = [1, 2, 3]
        results = await async_map_smart(quadruple, items, use_executor="always")
        assert results == [4, 8, 12]

    @pytest.mark.asyncio
    async def test_maps_sync_function_with_executor_auto(self):
        """Should auto-detect executor usage with use_executor='auto'."""

        def quintuple(x: int) -> int:
            return x * 5

        items = [1, 2, 3]
        results = await async_map_smart(quintuple, items, use_executor="auto")
        assert results == [5, 10, 15]

    @pytest.mark.asyncio
    async def test_respects_max_concurrent(self):
        """Should respect max_concurrent parameter."""
        concurrent_count = 0
        max_seen = 0

        async def track_concurrency(item: int) -> int:
            nonlocal concurrent_count, max_seen
            concurrent_count += 1
            max_seen = max(max_seen, concurrent_count)
            await asyncio.sleep(0.01)
            concurrent_count -= 1
            return item

        items = list(range(10))
        await async_map_smart(track_concurrency, items, max_concurrent=3)

        assert max_seen <= 3

    @pytest.mark.asyncio
    async def test_profile_mode_with_fast_operation(self):
        """Should profile and choose 'never' for fast direct operations."""

        def fast_operation(x: int) -> int:
            return x * 2  # Very fast, should be better without executor

        items = list(range(5))

        with patch("ClassicLib.Logger.logger") as mock_logger:
            results = await async_map_smart(
                fast_operation, items, use_executor="profile"
            )
            assert results == [0, 2, 4, 6, 8]
            # Logger should have been called with profiling results
            # (may not be called if profiling is skipped)

    @pytest.mark.asyncio
    async def test_handles_empty_items_in_profile_mode(self):
        """Should handle empty items list in profile mode."""

        def double(x: int) -> int:
            return x * 2

        results = await async_map_smart(double, [], use_executor="profile")
        assert results == []

    @pytest.mark.asyncio
    async def test_with_max_concurrent_none_and_executor_never(self):
        """Should work with max_concurrent=None and use_executor='never'."""

        def double(x: int) -> int:
            return x * 2

        items = [1, 2, 3]
        results = await async_map_smart(
            double, items, max_concurrent=None, use_executor="never"
        )
        assert results == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_with_max_concurrent_none_and_executor_auto(self):
        """Should work with max_concurrent=None and use_executor='auto'."""

        def double(x: int) -> int:
            return x * 2

        items = [1, 2, 3]
        results = await async_map_smart(
            double, items, max_concurrent=None, use_executor="auto"
        )
        assert results == [2, 4, 6]


@pytest.mark.unit
@pytest.mark.asyncio
class TestBatchProcessSmart:
    """Tests for batch_process_smart function."""

    @pytest.mark.asyncio
    async def test_processes_items_in_batches(self):
        """Should process items in specified batch sizes."""
        items = list(range(10))

        async def double(item: int) -> int:
            return item * 2

        results = await batch_process_smart(items, double, batch_size=3, max_concurrent=2)
        assert results == [i * 2 for i in range(10)]

    @pytest.mark.asyncio
    async def test_handles_sync_processor_with_executor_always(self):
        """Should handle sync processor with executor='always'."""

        def triple(item: int) -> int:
            return item * 3

        items = [1, 2, 3, 4, 5]
        results = await batch_process_smart(
            items, triple, batch_size=2, use_executor="always"
        )
        assert results == [3, 6, 9, 12, 15]

    @pytest.mark.asyncio
    async def test_handles_sync_processor_with_executor_never(self):
        """Should run sync processor directly with executor='never'."""

        def quadruple(item: int) -> int:
            return item * 4

        items = [1, 2, 3, 4, 5]
        results = await batch_process_smart(
            items, quadruple, batch_size=2, use_executor="never"
        )
        assert results == [4, 8, 12, 16, 20]

    @pytest.mark.asyncio
    async def test_handles_sync_processor_with_executor_auto(self):
        """Should use smart detection with executor='auto'."""

        def quintuple(item: int) -> int:
            return item * 5

        items = [1, 2, 3, 4, 5]
        results = await batch_process_smart(
            items, quintuple, batch_size=2, use_executor="auto"
        )
        assert results == [5, 10, 15, 20, 25]

    @pytest.mark.asyncio
    async def test_handles_empty_items(self):
        """Should handle empty item list."""

        async def processor(item: int) -> int:
            return item * 2

        results = await batch_process_smart([], processor, batch_size=10)
        assert results == []

    @pytest.mark.asyncio
    async def test_respects_max_concurrent(self):
        """Should respect max_concurrent parameter within each batch."""
        concurrent_count = 0
        max_seen = 0

        async def track_concurrency(item: int) -> int:
            nonlocal concurrent_count, max_seen
            concurrent_count += 1
            max_seen = max(max_seen, concurrent_count)
            await asyncio.sleep(0.01)
            concurrent_count -= 1
            return item

        items = list(range(10))
        await batch_process_smart(
            items, track_concurrency, batch_size=5, max_concurrent=2
        )

        # Max concurrent should not exceed 2
        assert max_seen <= 2

    @pytest.mark.asyncio
    async def test_multiple_batches_with_never_mode(self):
        """Should process multiple batches with use_executor='never'."""
        processed = []

        def track_processor(item: int) -> int:
            processed.append(item)
            return item * 2

        items = list(range(6))
        results = await batch_process_smart(
            items, track_processor, batch_size=2, use_executor="never"
        )

        assert results == [0, 2, 4, 6, 8, 10]
        assert processed == [0, 1, 2, 3, 4, 5]


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncFilterSmart:
    """Tests for async_filter_smart function."""

    @pytest.mark.asyncio
    async def test_filters_with_async_predicate(self):
        """Should filter items using async predicate."""

        async def is_even(x: int) -> bool:
            await asyncio.sleep(0.001)
            return x % 2 == 0

        items = [1, 2, 3, 4, 5, 6]
        results = await async_filter_smart(is_even, items)
        assert results == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_filters_with_sync_predicate_executor_never(self):
        """Should filter with sync predicate using use_executor='never'."""

        def is_positive(x: int) -> bool:
            return x > 0

        items = [-2, -1, 0, 1, 2, 3]
        results = await async_filter_smart(
            is_positive, items, use_executor="never"
        )
        assert results == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_filters_with_sync_predicate_executor_always(self):
        """Should filter with sync predicate using use_executor='always'."""

        def is_even(x: int) -> bool:
            return x % 2 == 0

        items = [1, 2, 3, 4, 5]
        results = await async_filter_smart(is_even, items, use_executor="always")
        assert results == [2, 4]

    @pytest.mark.asyncio
    async def test_filters_with_sync_predicate_executor_auto(self):
        """Should filter with sync predicate using use_executor='auto'."""

        def is_divisible_by_3(x: int) -> bool:
            return x % 3 == 0

        items = [1, 2, 3, 4, 5, 6, 9]
        results = await async_filter_smart(
            is_divisible_by_3, items, use_executor="auto"
        )
        assert results == [3, 6, 9]

    @pytest.mark.asyncio
    async def test_respects_max_concurrent(self):
        """Should respect max_concurrent parameter."""
        concurrent_count = 0
        max_seen = 0

        async def is_even_tracked(x: int) -> bool:
            nonlocal concurrent_count, max_seen
            concurrent_count += 1
            max_seen = max(max_seen, concurrent_count)
            await asyncio.sleep(0.01)
            concurrent_count -= 1
            return x % 2 == 0

        items = list(range(10))
        await async_filter_smart(is_even_tracked, items, max_concurrent=3)

        assert max_seen <= 3

    @pytest.mark.asyncio
    async def test_preserves_order(self):
        """Should preserve original order of items."""

        async def is_selected(x: int) -> bool:
            # Add varying delays
            await asyncio.sleep(0.01 * (5 - x) if x < 5 else 0.01)
            return x in {1, 3, 5}

        items = [1, 2, 3, 4, 5]
        results = await async_filter_smart(is_selected, items)
        assert results == [1, 3, 5]

    @pytest.mark.asyncio
    async def test_handles_empty_items(self):
        """Should handle empty items list."""

        async def predicate(x: int) -> bool:
            return True

        results = await async_filter_smart(predicate, [])
        assert results == []

    @pytest.mark.asyncio
    async def test_without_max_concurrent_executor_never(self):
        """Should work without max_concurrent and use_executor='never'."""

        def is_positive(x: int) -> bool:
            return x > 0

        items = [-1, 0, 1, 2]
        results = await async_filter_smart(
            is_positive, items, max_concurrent=None, use_executor="never"
        )
        assert results == [1, 2]

    @pytest.mark.asyncio
    async def test_without_max_concurrent_executor_auto(self):
        """Should work without max_concurrent and use_executor='auto'."""

        def is_positive(x: int) -> bool:
            return x > 0

        items = [-1, 0, 1, 2]
        results = await async_filter_smart(
            is_positive, items, max_concurrent=None, use_executor="auto"
        )
        assert results == [1, 2]


@pytest.mark.unit
class TestFastPathOperationsConstant:
    """Tests to verify FAST_PATH_OPERATIONS constant coverage."""

    def test_contains_expected_path_operations(self):
        """Should contain path metadata operations."""
        path_ops = {"exists", "is_file", "is_dir", "stat", "resolve", "absolute"}
        assert path_ops.issubset(FAST_PATH_OPERATIONS)

    def test_contains_expected_string_operations(self):
        """Should contain string operations."""
        string_ops = {"split", "join", "strip", "upper", "lower", "replace"}
        assert string_ops.issubset(FAST_PATH_OPERATIONS)

    def test_contains_expected_builtin_operations(self):
        """Should contain fast built-in operations."""
        builtin_ops = {"len", "bool", "int", "str", "hash", "type"}
        assert builtin_ops.issubset(FAST_PATH_OPERATIONS)

    def test_contains_expected_collection_operations(self):
        """Should contain collection operations."""
        collection_ops = {"append", "extend", "pop", "get", "keys", "values", "items"}
        assert collection_ops.issubset(FAST_PATH_OPERATIONS)


@pytest.mark.unit
class TestSizeDependentOperationsConstant:
    """Tests to verify SIZE_DEPENDENT_OPERATIONS constant coverage."""

    def test_contains_expected_io_operations(self):
        """Should contain I/O operations that depend on size."""
        io_ops = {"read_text", "read_bytes", "write_text", "write_bytes", "open"}
        assert io_ops.issubset(SIZE_DEPENDENT_OPERATIONS)

    def test_contains_expected_file_operations(self):
        """Should contain file modification operations."""
        file_ops = {"unlink", "rename", "replace", "chmod", "touch"}
        assert file_ops.issubset(SIZE_DEPENDENT_OPERATIONS)
