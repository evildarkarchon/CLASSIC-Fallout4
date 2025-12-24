"""Edge case and error handling tests for miscellaneous async utilities.

Tests edge cases, error conditions, and boundary scenarios for AsyncTimer,
throttle, run_in_executor, and AsyncLazyLoader.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest

from ClassicLib.Utils.Async import (
    AsyncLazyLoader,
    AsyncTimer,
    run_in_executor,
    throttle,
)


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
        from ClassicLib.Utils.Async import _throttler_registry, reset_throttlers

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
        from ClassicLib.Utils.Async import _throttler_registry

        # First set of operations
        for _i in range(2):
            await throttle(2, 0.1)

        # Should have created a throttler in the registry
        assert (2, 0.1) in _throttler_registry
        throttler = _throttler_registry[2, 0.1]

        # Subsequent calls should reuse the same throttler
        await throttle(2, 0.1)
        assert _throttler_registry[2, 0.1] is throttler


class TestRunInExecutorEdgeCases:
    """Edge case tests for run_in_executor."""

    @pytest.mark.asyncio
    async def test_with_none_function(self):
        """Should handle None as function."""
        with pytest.raises((TypeError, AttributeError)):
            await run_in_executor(None, 1, 2)  # type: ignore[arg-type]

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
        loader = AsyncLazyLoader(None)  # type: ignore[arg-type]

        with pytest.raises((TypeError, AttributeError)):
            await loader.get()

    @pytest.mark.asyncio
    async def test_loader_raises_exception(self):
        """Should propagate exceptions from loader."""

        async def failing_loader():
            raise OSError("Cannot load data")

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

        await asyncio.gather(*tasks[::2])  # Get results from get() calls

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
