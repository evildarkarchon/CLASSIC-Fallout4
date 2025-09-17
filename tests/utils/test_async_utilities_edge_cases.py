"""Edge case and error handling tests for AsyncUtilities module.

Tests edge cases, error conditions, and boundary scenarios that might not be
covered in the main unit and integration tests.
"""

import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.AsyncUtilities import (
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


class TestGatherWithConcurrencyEdgeCases:
    """Edge case tests for gather_with_concurrency."""

    @pytest.mark.asyncio
    async def test_with_zero_concurrency(self):
        """Should handle zero concurrency (though not recommended)."""
        # Zero concurrency would create a Semaphore(0) which blocks everything
        # This is an edge case that causes deadlock
        async def simple_coro(x):
            return x

        # This would deadlock, so we set a timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                gather_with_concurrency(0, simple_coro(1)),
                timeout=0.1
            )

    @pytest.mark.asyncio
    async def test_with_negative_concurrency(self):
        """Should handle negative concurrency gracefully."""
        async def simple_coro(x):
            return x

        # Negative values create invalid semaphore
        with pytest.raises(ValueError):
            await gather_with_concurrency(-1, simple_coro(1))

    @pytest.mark.asyncio
    async def test_with_single_coroutine(self):
        """Should handle a single coroutine."""
        async def single_coro():
            return "single"

        results = await gather_with_concurrency(1, single_coro())
        assert results == ["single"]

    @pytest.mark.asyncio
    async def test_with_exception_in_coroutine(self):
        """Should propagate exceptions from coroutines."""
        async def failing_coro():
            raise RuntimeError("Test error")

        async def success_coro():
            return "success"

        with pytest.raises(RuntimeError, match="Test error"):
            await gather_with_concurrency(2, failing_coro(), success_coro())

    @pytest.mark.asyncio
    async def test_with_cancelled_coroutine(self):
        """Should handle cancelled coroutines."""
        async def long_running():
            await asyncio.sleep(10)
            return "completed"

        task = asyncio.create_task(
            gather_with_concurrency(1, long_running())
        )

        # Cancel after a short delay
        await asyncio.sleep(0.01)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task


class TestBatchProcessEdgeCases:
    """Edge case tests for batch_process."""

    @pytest.mark.asyncio
    async def test_with_empty_items(self):
        """Should handle empty item list."""
        async def processor(item):
            return item * 2

        results = await batch_process([], processor, batch_size=10)
        assert results == []

    @pytest.mark.asyncio
    async def test_with_none_processor(self):
        """Should handle None processor gracefully."""
        items = [1, 2, 3]

        with pytest.raises((TypeError, AttributeError)):
            await batch_process(items, None, batch_size=2)

    @pytest.mark.asyncio
    async def test_with_zero_batch_size(self):
        """Should handle zero batch size."""
        async def processor(item):
            return item

        items = [1, 2, 3]

        # Zero batch size causes ValueError in range()
        with pytest.raises(ValueError, match="arg 3 must not be zero"):
            await batch_process(items, processor, batch_size=0)

    @pytest.mark.asyncio
    async def test_with_negative_batch_size(self):
        """Should handle negative batch size."""
        async def processor(item):
            return item

        items = [1, 2, 3]

        # Negative batch size would result in no processing
        # range(0, n, -1) produces empty sequence
        results = await batch_process(items, processor, batch_size=-1)
        assert results == []  # No items processed

    @pytest.mark.asyncio
    async def test_processor_raises_exception(self):
        """Should propagate exceptions from processor."""
        def failing_processor(item):
            if item == 2:
                raise ValueError(f"Cannot process {item}")
            return item

        items = [1, 2, 3]

        with pytest.raises(ValueError, match="Cannot process 2"):
            await batch_process(items, failing_processor, batch_size=5)

    @pytest.mark.asyncio
    async def test_with_generator_items(self):
        """Should handle generator as items input."""
        async def processor(item):
            return item * 2

        def item_generator():
            for i in range(5):
                yield i

        # Generators need to be converted to list
        results = await batch_process(
            list(item_generator()), processor, batch_size=2
        )
        assert results == [0, 2, 4, 6, 8]


class TestAsyncRetryEdgeCases:
    """Edge case tests for async_retry decorator."""

    @pytest.mark.asyncio
    async def test_with_zero_attempts(self):
        """Should handle zero max_attempts."""
        call_count = 0

        @async_retry(max_attempts=0, delay=0.01)
        async def never_runs():
            nonlocal call_count
            call_count += 1
            return "should not run"

        # With 0 attempts, the last_error is None initially
        # The loop won't run, so it raises the last_error which is None
        # This will cause an error when trying to raise None
        with pytest.raises((TypeError, AttributeError)):
            await never_runs()

        assert call_count == 0  # Function never called

    @pytest.mark.asyncio
    async def test_with_negative_delay(self):
        """Should handle negative delay values."""
        call_count = 0

        @async_retry(max_attempts=3, delay=-1.0)
        async def negative_delay_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry me")
            return "success"

        # Negative delay should be treated as 0
        result = await negative_delay_func()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_with_zero_backoff(self):
        """Should handle zero backoff (no increase in delay)."""
        delays = []
        start_time = asyncio.get_event_loop().time()

        @async_retry(max_attempts=3, delay=0.01, backoff=0.0)
        async def zero_backoff_func():
            current_time = asyncio.get_event_loop().time()
            delays.append(current_time - start_time)
            if len(delays) < 3:
                raise ValueError("Retry")
            return "done"

        result = await zero_backoff_func()
        assert result == "done"
        # With 0 backoff, delay stays constant
        assert len(delays) == 3

    @pytest.mark.asyncio
    async def test_with_custom_exception_not_in_tuple(self):
        """Should not retry exceptions not in the exceptions tuple."""
        @async_retry(max_attempts=3, exceptions=(ValueError,))
        async def specific_exception():
            raise TypeError("Wrong type")

        # TypeError is not in exceptions tuple, so no retry
        with pytest.raises(TypeError, match="Wrong type"):
            await specific_exception()

    @pytest.mark.asyncio
    async def test_with_asyncio_cancelled_error(self):
        """Should not retry CancelledError."""
        attempt_count = 0

        @async_retry(max_attempts=3, delay=0.01)
        async def cancellable_func():
            nonlocal attempt_count
            attempt_count += 1
            raise asyncio.CancelledError()

        with pytest.raises(asyncio.CancelledError):
            await cancellable_func()

        # Should not retry on CancelledError
        assert attempt_count == 1


class TestAsyncTimeoutEdgeCases:
    """Edge case tests for async_timeout decorator."""

    @pytest.mark.asyncio
    async def test_with_zero_timeout(self):
        """Should handle zero timeout."""
        @async_timeout(0.0)
        async def instant_timeout():
            return "instant"

        # Zero timeout should fail immediately for any async operation
        with pytest.raises(TimeoutError):
            await instant_timeout()

    @pytest.mark.asyncio
    async def test_with_negative_timeout(self):
        """Should handle negative timeout."""
        @async_timeout(-1.0)
        async def negative_timeout():
            return "negative"

        # Negative timeout should raise immediately
        with pytest.raises((ValueError, TimeoutError)):
            await negative_timeout()

    @pytest.mark.asyncio
    async def test_with_infinite_timeout(self):
        """Should handle very large timeout values."""
        @async_timeout(float('inf'))
        async def infinite_timeout():
            await asyncio.sleep(0.01)
            return "completed"

        # Should complete normally with infinite timeout
        result = await infinite_timeout()
        assert result == "completed"

    @pytest.mark.asyncio
    async def test_timeout_with_exception(self):
        """Should propagate exceptions even with timeout."""
        @async_timeout(1.0)
        async def raises_error():
            raise ValueError("Function error")

        with pytest.raises(ValueError, match="Function error"):
            await raises_error()


class TestRunWithTimeoutEdgeCases:
    """Edge case tests for run_with_timeout."""

    @pytest.mark.asyncio
    async def test_with_none_coroutine(self):
        """Should handle None as coroutine."""
        with pytest.raises((TypeError, AttributeError)):
            await run_with_timeout(None, timeout=1.0)

    @pytest.mark.asyncio
    async def test_with_sync_function(self):
        """Should handle sync function (not coroutine)."""
        def sync_func():
            return "sync_result"

        # Should raise or handle gracefully
        with pytest.raises((TypeError, RuntimeError)):
            await run_with_timeout(sync_func, timeout=1.0)

    @pytest.mark.asyncio
    async def test_with_already_completed_coroutine(self):
        """Should handle already awaited coroutine."""
        async def coro():
            return "result"

        coro_instance = coro()
        # First await works
        result1 = await run_with_timeout(coro_instance, timeout=1.0)
        assert result1 == "result"

        # Second await on same instance should fail
        with pytest.raises(RuntimeError):
            await run_with_timeout(coro_instance, timeout=1.0)

    @pytest.mark.asyncio
    async def test_default_value_types(self):
        """Test various default value types."""
        async def slow():
            await asyncio.sleep(1.0)

        # Test different default types
        assert await run_with_timeout(slow(), 0.01, default=None) is None
        assert await run_with_timeout(slow(), 0.01, default=42) == 42
        assert await run_with_timeout(slow(), 0.01, default="timeout") == "timeout"
        assert await run_with_timeout(slow(), 0.01, default=[]) == []
        assert await run_with_timeout(slow(), 0.01, default={}) == {}


class TestAsyncMapEdgeCases:
    """Edge case tests for async_map."""

    @pytest.mark.asyncio
    async def test_with_empty_items(self):
        """Should handle empty items list."""
        async def func(x):
            return x * 2

        results = await async_map(func, [])
        assert results == []

    @pytest.mark.asyncio
    async def test_with_none_function(self):
        """Should handle None as function."""
        with pytest.raises((TypeError, AttributeError)):
            await async_map(None, [1, 2, 3])

    @pytest.mark.asyncio
    async def test_with_generator_items(self):
        """Should handle generator as items."""
        async def double(x):
            return x * 2

        gen = (i for i in range(5))
        results = await async_map(double, gen)
        assert results == [0, 2, 4, 6, 8]

    @pytest.mark.asyncio
    async def test_function_raises_exception(self):
        """Should propagate exceptions from mapped function."""
        async def failing_func(x):
            if x == 2:
                raise ValueError(f"Cannot process {x}")
            return x

        with pytest.raises(ValueError, match="Cannot process 2"):
            await async_map(failing_func, [1, 2, 3])

    @pytest.mark.asyncio
    async def test_with_mixed_types(self):
        """Should handle items of mixed types."""
        async def stringify(x):
            return str(x)

        items = [1, "two", 3.0, None, True, [4, 5]]
        results = await async_map(stringify, items)
        assert results == ["1", "two", "3.0", "None", "True", "[4, 5]"]


class TestAsyncFilterEdgeCases:
    """Edge case tests for async_filter."""

    @pytest.mark.asyncio
    async def test_with_empty_items(self):
        """Should handle empty items list."""
        async def predicate(x):
            return True

        results = await async_filter(predicate, [])
        assert results == []

    @pytest.mark.asyncio
    async def test_with_none_predicate(self):
        """Should handle None as predicate."""
        with pytest.raises((TypeError, AttributeError)):
            await async_filter(None, [1, 2, 3])

    @pytest.mark.asyncio
    async def test_predicate_returns_non_boolean(self):
        """Should handle non-boolean return values from predicate."""
        async def truthy_predicate(x):
            # Return truthy/falsy values instead of bool
            return x if x % 2 == 0 else 0

        results = await async_filter(truthy_predicate, [1, 2, 3, 4, 5])
        # 2 and 4 return truthy values
        assert results == [2, 4]

    @pytest.mark.asyncio
    async def test_predicate_raises_exception(self):
        """Should propagate exceptions from predicate."""
        async def failing_predicate(x):
            if x == 3:
                raise ValueError(f"Cannot check {x}")
            return x % 2 == 0

        with pytest.raises(ValueError, match="Cannot check 3"):
            await async_filter(failing_predicate, [1, 2, 3, 4])

    @pytest.mark.asyncio
    async def test_with_set_input(self):
        """Should handle set as input."""
        async def is_even(x):
            return x % 2 == 0

        items_set = {1, 2, 3, 4, 5}
        results = await async_filter(is_even, items_set)
        assert set(results) == {2, 4}


class TestAsyncTimerEdgeCases:
    """Edge case tests for AsyncTimer."""

    @pytest.mark.asyncio
    async def test_timer_without_exit(self):
        """Test timer behavior when not properly exited."""
        timer = AsyncTimer()
        await timer.__aenter__()

        # Access elapsed before exit
        elapsed_during = timer.elapsed
        assert elapsed_during >= 0

        await asyncio.sleep(0.01)
        await timer.__aexit__(None, None, None)

        # Elapsed should be set after exit
        assert timer.elapsed > elapsed_during

    @pytest.mark.asyncio
    async def test_timer_reuse(self):
        """Test reusing the same timer instance."""
        timer = AsyncTimer()

        # First use
        async with timer:
            await asyncio.sleep(0.01)
        first_elapsed = timer.elapsed

        # Second use (reuse same instance)
        async with timer:
            await asyncio.sleep(0.02)
        second_elapsed = timer.elapsed

        # Second timing should be independent
        assert second_elapsed > first_elapsed

    @pytest.mark.asyncio
    async def test_timer_with_exception(self):
        """Test timer behavior when exception occurs in context."""
        timer = AsyncTimer()

        with pytest.raises(ValueError):
            async with timer:
                await asyncio.sleep(0.01)
                raise ValueError("Test error")

        # Timer should still have elapsed time
        assert timer.elapsed > 0


class TestThrottleEdgeCases:
    """Edge case tests for throttle function."""

    @pytest.fixture(autouse=True)
    async def cleanup_throttlers(self):
        """Clean up throttlers before and after each test."""
        from ClassicLib.AsyncUtilities import reset_throttlers, _throttler_registry
        reset_throttlers()
        yield
        # Clean up any background tasks
        for throttler in _throttler_registry.values():
            await throttler.cleanup()
        reset_throttlers()

    @pytest.mark.asyncio
    async def test_with_zero_rate_limit(self):
        """Should handle zero rate limit."""
        # Zero rate limit would create Semaphore(0) which blocks
        # This will timeout/block indefinitely
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(throttle(0, 1.0), timeout=0.1)

    @pytest.mark.asyncio
    async def test_with_negative_rate_limit(self):
        """Should handle negative rate limit."""
        # Negative values create invalid semaphore
        with pytest.raises(ValueError):
            await throttle(-1, 1.0)

    @pytest.mark.asyncio
    async def test_with_zero_time_window(self):
        """Should handle zero time window."""
        # Zero time window means immediate release
        operations = []

        for i in range(3):
            await throttle(2, 0.0)
            operations.append(i)

        assert operations == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_throttle_state_persistence(self):
        """Test that throttle maintains state between calls."""
        from ClassicLib.AsyncUtilities import _throttler_registry

        # First set of operations
        for i in range(2):
            await throttle(2, 0.1)

        # Should have created a throttler in the registry
        assert (2, 0.1) in _throttler_registry
        throttler = _throttler_registry[(2, 0.1)]

        # Subsequent calls should reuse the same throttler
        await throttle(2, 0.1)
        assert _throttler_registry[(2, 0.1)] is throttler


class TestRunInExecutorEdgeCases:
    """Edge case tests for run_in_executor."""

    @pytest.mark.asyncio
    async def test_with_none_function(self):
        """Should handle None as function."""
        with pytest.raises((TypeError, AttributeError)):
            await run_in_executor(None, 1, 2)

    @pytest.mark.asyncio
    async def test_with_exception_in_function(self):
        """Should propagate exceptions from executed function."""
        def failing_func(x):
            raise RuntimeError(f"Error with {x}")

        with pytest.raises(RuntimeError, match="Error with 42"):
            await run_in_executor(failing_func, 42)

    @pytest.mark.asyncio
    async def test_with_custom_executor(self):
        """Should work with custom executor."""
        def cpu_bound(n):
            # Simulate CPU-bound work
            result = sum(i * i for i in range(n))
            return result

        with ThreadPoolExecutor(max_workers=2) as executor:
            result = await run_in_executor(cpu_bound, 100, executor=executor)
            assert result == sum(i * i for i in range(100))

    @pytest.mark.asyncio
    async def test_with_no_args(self):
        """Should handle function with no arguments."""
        def no_args_func():
            return "no args"

        result = await run_in_executor(no_args_func)
        assert result == "no args"

    @pytest.mark.asyncio
    async def test_with_mixed_args_kwargs(self):
        """Should handle mix of args and kwargs."""
        def mixed_func(a, b, c=10, d=20):
            return a + b + c + d

        result = await run_in_executor(mixed_func, 1, 2, c=3, d=4)
        assert result == 10


class TestAsyncLazyLoaderEdgeCases:
    """Edge case tests for AsyncLazyLoader."""

    @pytest.mark.asyncio
    async def test_with_none_loader(self):
        """Should handle None as loader function."""
        loader = AsyncLazyLoader(None)

        with pytest.raises((TypeError, AttributeError)):
            await loader.get()

    @pytest.mark.asyncio
    async def test_loader_raises_exception(self):
        """Should propagate exceptions from loader."""
        async def failing_loader():
            raise IOError("Cannot load data")

        loader = AsyncLazyLoader(failing_loader)

        with pytest.raises(IOError, match="Cannot load data"):
            await loader.get()

        # Should not be marked as loaded on failure
        assert not loader._loaded

    @pytest.mark.asyncio
    async def test_reset_during_loading(self):
        """Test reset called while loading is in progress."""
        loading_started = asyncio.Event()
        loading_complete = asyncio.Event()

        async def slow_loader():
            loading_started.set()
            await loading_complete.wait()
            return "data"

        loader = AsyncLazyLoader(slow_loader)

        # Start loading
        load_task = asyncio.create_task(loader.get())

        # Wait for loading to start
        await loading_started.wait()

        # Reset while loading (this resets the flags but loading continues)
        loader.reset()

        # Complete the loading
        loading_complete.set()

        result = await load_task
        assert result == "data"

        # The reset during loading doesn't prevent the current load from completing
        # and marking _loaded as True. The behavior depends on implementation.
        # After the first load completes, it will be marked as loaded
        assert loader._loaded

        # But if we reset again and load, it should load anew
        loader.reset()
        assert not loader._loaded

    @pytest.mark.asyncio
    async def test_multiple_concurrent_resets(self):
        """Test multiple resets during concurrent access."""
        call_count = 0

        async def counting_loader():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return f"load_{call_count}"

        loader = AsyncLazyLoader(counting_loader)

        async def reset_task():
            await asyncio.sleep(0.005)
            loader.reset()

        # Start multiple operations
        tasks = [
            asyncio.create_task(loader.get()),
            asyncio.create_task(reset_task()),
            asyncio.create_task(loader.get()),
        ]

        results = await asyncio.gather(*tasks[::2])  # Get results from get() calls

        # Should have loaded at least once
        assert call_count >= 1

    @pytest.mark.asyncio
    async def test_loader_returns_none(self):
        """Should handle loader returning None."""
        async def none_loader():
            return None

        loader = AsyncLazyLoader(none_loader)

        result = await loader.get()
        assert result is None
        assert loader._loaded

    @pytest.mark.asyncio
    async def test_sync_loader_raises_exception(self):
        """Should handle exceptions from sync loader."""
        def failing_sync_loader():
            raise ValueError("Sync loader error")

        loader = AsyncLazyLoader(failing_sync_loader)

        with pytest.raises(ValueError, match="Sync loader error"):
            await loader.get()
