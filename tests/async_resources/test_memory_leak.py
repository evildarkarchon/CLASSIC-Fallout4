"""Tests for detecting memory leaks in async operations."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001

import asyncio
import gc
import weakref

import pytest


@pytest.mark.asyncio
class TestMemoryLeakDetection:
    """Tests for detecting memory leaks in async operations."""

    async def test_no_memory_leak_in_repeated_operations(self):
        """Test that repeated async operations don't leak memory."""
        # Track object counts
        initial_objects = len(gc.get_objects())

        # Perform repeated operations
        for _ in range(10):

            async def dummy_operation():
                data = ["test"] * 100
                await asyncio.sleep(0)
                return data

            result = await dummy_operation()
            del result

        # Force garbage collection
        gc.collect()
        await asyncio.sleep(0)

        # Check object count didn't grow significantly
        final_objects = len(gc.get_objects())
        growth = final_objects - initial_objects

        # Allow some growth for test infrastructure, but not excessive
        assert growth < 100, f"Possible memory leak: {growth} objects not freed"

    async def test_weakref_cleanup_in_async_context(self):
        """Test that weakrefs are properly cleaned up in async contexts."""
        cleaned_up = False

        class TrackedObject:
            pass

        def cleanup_callback(ref):
            nonlocal cleaned_up
            cleaned_up = True

        # Create and track object
        obj = TrackedObject()
        weak_ref = weakref.ref(obj, cleanup_callback)

        # Object should exist
        assert weak_ref() is not None
        assert not cleaned_up

        # Delete object
        del obj
        gc.collect()
        await asyncio.sleep(0)  # Allow callbacks to run

        # Object should be gone
        assert weak_ref() is None
        assert cleaned_up

    async def test_task_cleanup_after_cancellation(self):
        """Test that cancelled tasks are properly cleaned up."""
        # Track initial tasks
        initial_tasks = asyncio.all_tasks()

        # Create a long-running task
        async def long_task():
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                # Cleanup on cancellation
                pass
            finally:
                # Always cleanup
                pass

        # Start tasks
        tasks = [asyncio.create_task(long_task()) for _ in range(5)]

        # Give tasks time to start
        await asyncio.sleep(0)

        # Cancel all tasks
        for task in tasks:
            task.cancel()

        # Wait for cancellation to complete
        await asyncio.gather(*tasks, return_exceptions=True)

        # Check all tasks are done
        assert all(t.done() for t in tasks)

        # Check no leaked tasks
        current_tasks = asyncio.all_tasks()
        leaked = current_tasks - initial_tasks
        assert len(leaked) == 0, f"Leaked tasks: {leaked}"

    async def test_async_generator_cleanup(self):
        """Test that async generators are properly cleaned up."""
        cleanup_called = False

        async def test_generator():
            nonlocal cleanup_called
            try:
                for i in range(10):
                    yield i
                    await asyncio.sleep(0)
            finally:
                cleanup_called = True

        # Use generator partially
        gen = test_generator()
        async for i in gen:
            if i >= 5:
                break

        # Close generator explicitly
        await gen.aclose()

        # Verify cleanup was called
        assert cleanup_called

    async def test_circular_reference_cleanup(self):
        """Test cleanup of circular references in async contexts."""

        class Node:
            def __init__(self, value: int) -> None:
                self.value = value
                self.next: "Node | None" = None
                self.task: asyncio.Task | None = None

            async def process(self) -> int:
                await asyncio.sleep(0)
                return self.value

        # Create circular reference
        node1 = Node(1)
        node2 = Node(2)
        node1.next = node2
        node2.next = node1

        # Track with weakref
        weak_node1 = weakref.ref(node1)
        weak_node2 = weakref.ref(node2)

        # Use nodes
        node1.task = asyncio.create_task(node1.process())
        node2.task = asyncio.create_task(node2.process())

        assert node1.task is not None
        await node1.task
        assert node2.task is not None
        await node2.task

        # Remove local references (circular reference remains between nodes)
        del node1
        del node2

        # Force cleanup
        gc.collect()
        await asyncio.sleep(0)

        # Check objects are gone
        assert weak_node1() is None
        assert weak_node2() is None
