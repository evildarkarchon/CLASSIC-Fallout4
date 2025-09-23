"""Tests for async resource tracker and leak detection."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001

import asyncio

import pytest

from tests.async_tests.test_async_utils import (
    AsyncResourceTracker,
    async_test_context,
    ensure_event_loop_cleanup,
    safe_async_cleanup,
    track_async_resources,
)


@pytest.mark.asyncio
class TestAsyncResourceTracker:
    """Tests for async resource tracking and cleanup verification."""

    @track_async_resources
    async def test_resource_tracker_detects_leaks(self):
        """Test that the resource tracker can detect leaked resources."""
        tracker = AsyncResourceTracker()

        # Create a mock resource that won't be cleaned up
        class LeakyResource:
            def __init__(self, name):
                self.name = name
                self.closed = False

            async def close(self):
                self.closed = True

        # Create and track resources
        resource1 = LeakyResource("resource1")
        resource2 = LeakyResource("resource2")

        # Register resources with tracker
        tracker.register(resource1, "resource1")
        tracker.register(resource2, "resource2")

        # Clean up only one resource
        await resource1.close()
        del resource1  # Allow it to be garbage collected

        # Force garbage collection
        import gc
        gc.collect()

        # Check that tracker detects the leak
        leaks = tracker.check_leaks()
        assert len(leaks) == 1

        # Clean up for test
        await resource2.close()

    @ensure_event_loop_cleanup
    async def test_event_loop_cleanup_decorator(self) -> None:
        """Test that ensure_event_loop_cleanup properly cleans up tasks."""
        # Track tasks created in this test
        initial_tasks = asyncio.all_tasks()

        # Create some async tasks
        async def dummy_task():
            await asyncio.sleep(0.01)
            return "completed"

        tasks = [asyncio.create_task(dummy_task()) for _ in range(3)]

        # Wait for tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        assert len(results) == 3
        assert all(r == "completed" for r in results)

        # Check no new tasks remain
        current_tasks = asyncio.all_tasks()
        new_tasks = current_tasks - initial_tasks
        assert len(new_tasks) == 0 or all(t.done() for t in new_tasks)

    async def test_safe_async_cleanup_handles_various_resources(self) -> None:
        """Test safe_async_cleanup with different resource types."""
        cleaned = []

        # Mock resources with different behaviors
        class GoodResource:
            async def close(self):
                cleaned.append("good")

        class BadResource:
            async def close(self):
                cleaned.append("bad")
                raise RuntimeError("Close failed")

        class SlowResource:
            async def close(self):
                await asyncio.sleep(0.01)
                cleaned.append("slow")

        # Create resources
        resources = [GoodResource(), BadResource(), SlowResource()]

        # Clean up all resources (should not raise)
        await safe_async_cleanup(*resources)

        # Check all were attempted
        assert "good" in cleaned
        assert "bad" in cleaned
        assert "slow" in cleaned

    async def test_async_test_context_manager(self):
        """Test the async_test_context context manager."""
        test_value = None

        # async_test_context doesn't take arguments, it's a simple context manager
        async with async_test_context():
            # Simulate some async work
            await asyncio.sleep(0.01)
            test_value = "completed"

        assert test_value == "completed"

    async def test_async_cleanup_fixture(self):
        """Test async cleanup in fixtures."""
        cleanup_called = False

        class TestResource:
            async def initialize(self):
                # Simulate async initialization
                await asyncio.sleep(0.01)
                return self

            async def cleanup(self):
                nonlocal cleanup_called
                cleanup_called = True
                await asyncio.sleep(0.01)

        # Create and use resource
        resource = TestResource()
        await resource.initialize()

        # Cleanup
        await resource.cleanup()
        assert cleanup_called

    async def test_clean_event_loop_pattern(self):
        """Test pattern for ensuring clean event loop between tests."""
        # Get initial state
        loop = asyncio.get_event_loop()
        initial_tasks = asyncio.all_tasks(loop)

        # Create some test tasks
        async def worker(n):
            await asyncio.sleep(0.01)
            return n * 2

        # Run tasks
        tasks = [asyncio.create_task(worker(i)) for i in range(5)]
        results = await asyncio.gather(*tasks)
        assert results == [0, 2, 4, 6, 8]

        # Ensure cleanup
        current_tasks = asyncio.all_tasks(loop)
        new_tasks = current_tasks - initial_tasks
        for task in new_tasks:
            if not task.done():
                task.cancel()

        # Wait for cancellations
        if new_tasks:
            await asyncio.gather(*new_tasks, return_exceptions=True)

        # Verify cleanup
        final_tasks = asyncio.all_tasks(loop)
        remaining = final_tasks - initial_tasks
        assert len(remaining) == 0
