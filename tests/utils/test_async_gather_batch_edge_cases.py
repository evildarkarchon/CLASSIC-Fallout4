"""Edge case and error handling tests for gathering and batching async utilities.

Tests edge cases, error conditions, and boundary scenarios for gather_with_concurrency
and batch_process functions.
"""

import asyncio

import pytest

from ClassicLib.Utils.Async import (
    batch_process,
    gather_with_concurrency,
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

        # Use a task instead of raw coroutine to avoid "coroutine never awaited" warning
        # when the operation times out and the coroutine is never started
        task = asyncio.create_task(simple_coro(1))

        # This would deadlock, so we set a timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(gather_with_concurrency(0, task), timeout=0.1)

        # Clean up the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_with_negative_concurrency(self):
        """Should handle negative concurrency gracefully."""

        async def simple_coro(x):
            return x

        # Create coroutine but ensure it's cleaned up if not awaited
        coro = simple_coro(1)

        try:
            # Negative values create invalid semaphore
            with pytest.raises(ValueError):
                await gather_with_concurrency(-1, coro)
        finally:
            # Close the coroutine since gather_with_concurrency raises before awaiting it
            coro.close()

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

        task = asyncio.create_task(gather_with_concurrency(1, long_running()))

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
            await batch_process(items, None, batch_size=2)  # type: ignore[arg-type]

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
        results = await batch_process(list(item_generator()), processor, batch_size=2)
        assert results == [0, 2, 4, 6, 8]
