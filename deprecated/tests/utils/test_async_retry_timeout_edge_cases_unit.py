"""Edge case and error handling tests for retry and timeout async utilities.

Tests edge cases, error conditions, and boundary scenarios for async_retry,
async_timeout, and run_with_timeout functions.
"""

import asyncio

import pytest

from ClassicLib.Utils.async_utils import (
    async_retry,
    async_timeout,
    run_with_timeout,
)


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

        # With 0 attempts, the decorator raises a RuntimeError with a message
        with pytest.raises(RuntimeError, match="failed after 0 attempts with no captured exception"):
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

        @async_timeout(float("inf"))
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
            # run_with_timeout doesn't take 'timeout' kwarg, it's positional
            wrapper = run_with_timeout(None, 1.0)  # type: ignore[arg-type]
            await wrapper()

    @pytest.mark.asyncio
    async def test_with_sync_function(self):
        """Should handle sync function (not coroutine)."""

        def sync_func():
            return "sync_result"

        # Should raise or handle gracefully
        with pytest.raises((TypeError, RuntimeError)):
            wrapper = run_with_timeout(sync_func, 1.0)  # type: ignore[arg-type]
            await wrapper()

    @pytest.mark.asyncio
    async def test_with_already_completed_coroutine(self):
        """Should handle already awaited coroutine."""

        async def coro():
            return "result"

        coro_instance = coro()
        # First await works
        wrapper1 = run_with_timeout(coro_instance, 1.0)
        result1 = await wrapper1()
        assert result1 == "result"

        # Second await on same instance should fail
        with pytest.raises(RuntimeError):
            wrapper2 = run_with_timeout(coro_instance, 1.0)
            await wrapper2()

    @pytest.mark.asyncio
    async def test_default_value_types(self):
        """Test various default value types."""

        async def slow():
            await asyncio.sleep(1.0)

        # Test different default types - run_with_timeout returns a wrapper
        wrapper1 = run_with_timeout(slow(), 0.01, default=None)
        assert await wrapper1() is None

        wrapper2 = run_with_timeout(slow(), 0.01, default=42)
        assert await wrapper2() == 42

        wrapper3 = run_with_timeout(slow(), 0.01, default="timeout")
        assert await wrapper3() == "timeout"

        wrapper4 = run_with_timeout(slow(), 0.01, default=[])
        assert await wrapper4() == []

        wrapper5 = run_with_timeout(slow(), 0.01, default={})
        assert await wrapper5() == {}
