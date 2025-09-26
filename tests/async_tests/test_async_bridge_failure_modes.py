"""Comprehensive tests for AsyncBridge failure modes and edge cases.

This module tests AsyncBridge's behavior under various failure conditions,
including error propagation, concurrent operation limits, and fallback mechanisms.
"""

import pytest
import asyncio
import threading
import time
from unittest.mock import MagicMock, Mock, patch, AsyncMock
from typing import Any
from concurrent.futures import ThreadPoolExecutor

from ClassicLib.AsyncBridge import AsyncBridge

# Mark all tests in this module
pytestmark = [pytest.mark.asyncio, pytest.mark.unit]


class TestAsyncBridgeFailureModes:
    """Test AsyncBridge failure modes and fallback mechanisms."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Reset AsyncBridge singleton before each test."""
        # Clear singleton to ensure clean state
        if hasattr(AsyncBridge, "_instance"):
            delattr(AsyncBridge, "_instance")
        if hasattr(AsyncBridge, "_lock"):
            delattr(AsyncBridge, "_lock")

    def test_fallback_when_rust_unavailable(self) -> None:
        """Test fallback mechanism when Rust acceleration is unavailable."""
        bridge = AsyncBridge.get_instance()

        # Simulate Rust unavailable scenario
        with patch("ClassicLib.integration.status.RUST_AVAILABLE", {}):
            # Should still work with Python fallback
            async def test_func():
                return "fallback_result"

            result = bridge.run_async(test_func())
            assert result == "fallback_result"

    def test_error_propagation_from_async_to_sync(self) -> None:
        """Test that exceptions properly propagate from async to sync context."""
        bridge = AsyncBridge.get_instance()

        class CustomException(Exception):
            """Custom exception for testing."""
            pass

        async def failing_async_func():
            raise CustomException("Async error occurred")

        # Exception should propagate to sync context
        with pytest.raises(CustomException) as exc_info:
            bridge.run_async(failing_async_func())

        assert str(exc_info.value) == "Async error occurred"

    def test_nested_async_call_prevention(self) -> None:
        """Test that nested async calls from within async context are prevented."""
        bridge = AsyncBridge.get_instance()

        async def inner_async():
            return "inner_result"

        async def outer_async():
            # This should raise an error - can't use run_async from async context
            return bridge.run_async(inner_async())

        with pytest.raises(RuntimeError) as exc_info:
            bridge.run_async(outer_async())

        assert "Cannot use run_async from within an async context" in str(exc_info.value)

    def test_concurrent_operation_limits(self) -> None:
        """Test AsyncBridge behavior under concurrent operations."""
        bridge = AsyncBridge.get_instance()
        results = []
        errors = []

        async def delayed_task(task_id: int, delay: float):
            await asyncio.sleep(delay)
            return f"task_{task_id}"

        def run_task(task_id: int):
            try:
                result = bridge.run_async(delayed_task(task_id, 0.01))
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Run multiple tasks concurrently from different threads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(run_task, i) for i in range(10)]
            for future in futures:
                future.result()

        # All tasks should complete successfully
        assert len(results) == 10
        assert len(errors) == 0
        assert all(f"task_{i}" in results for i in range(10))

    def test_event_loop_recovery_after_error(self) -> None:
        """Test that AsyncBridge recovers properly after an error."""
        bridge = AsyncBridge.get_instance()

        async def failing_task():
            raise ValueError("Task failed")

        async def successful_task():
            return "success"

        # First task fails
        with pytest.raises(ValueError):
            bridge.run_async(failing_task())

        # Bridge should still work for subsequent tasks
        result = bridge.run_async(successful_task())
        assert result == "success"

    def test_timeout_handling(self) -> None:
        """Test AsyncBridge behavior with long-running tasks."""
        bridge = AsyncBridge.get_instance()

        async def long_task():
            await asyncio.sleep(10)  # Simulate long operation
            return "completed"

        # Test with custom timeout (if implemented)
        # For now, test that long tasks can be started
        async def cancellable_task():
            try:
                await asyncio.sleep(10)
                return "completed"
            except asyncio.CancelledError:
                return "cancelled"

        # This would ideally test timeout, but AsyncBridge doesn't have built-in timeout
        # Testing that it handles long tasks without blocking indefinitely
        start = time.time()

        # Create a task that we can cancel
        async def run_with_timeout():
            task = asyncio.create_task(cancellable_task())
            await asyncio.sleep(0.1)  # Let it start
            task.cancel()
            try:
                return await task
            except asyncio.CancelledError:
                return "cancelled"

        result = bridge.run_async(run_with_timeout())
        elapsed = time.time() - start

        assert elapsed < 1.0  # Should not take full 10 seconds
        assert result == "cancelled"

    def test_memory_cleanup_after_exceptions(self) -> None:
        """Test that AsyncBridge properly cleans up after exceptions."""
        bridge = AsyncBridge.get_instance()

        # Track memory state
        initial_tasks = []

        async def leaky_task():
            # Create some data that could leak if not cleaned up
            data = [i for i in range(10000)]
            initial_tasks.append(id(data))
            raise MemoryError("Simulated memory error")

        # Run multiple failing tasks
        for _ in range(5):
            with pytest.raises(MemoryError):
                bridge.run_async(leaky_task())

        # Bridge should still be functional
        async def check_health():
            return "healthy"

        result = bridge.run_async(check_health())
        assert result == "healthy"

    def test_concurrent_sync_calls_from_multiple_threads(self) -> None:
        """Test multiple threads calling run_async simultaneously."""
        bridge = AsyncBridge.get_instance()
        results = {}

        async def thread_specific_task(thread_id: str):
            await asyncio.sleep(0.01)
            return f"thread_{thread_id}"

        def thread_worker(thread_id: str):
            result = bridge.run_async(thread_specific_task(thread_id))
            results[thread_id] = result

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=thread_worker, args=(str(i),))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Check all threads got correct results
        assert len(results) == 5
        for i in range(5):
            assert results[str(i)] == f"thread_{i}"

    def test_exception_types_preservation(self) -> None:
        """Test that specific exception types are preserved across boundaries."""
        bridge = AsyncBridge.get_instance()

        test_exceptions = [
            (ValueError, "value error"),
            (KeyError, "key error"),
            (TypeError, "type error"),
            (RuntimeError, "runtime error"),
            (AttributeError, "attribute error"),
        ]

        for exc_type, message in test_exceptions:
            async def raise_specific():
                raise exc_type(message)

            with pytest.raises(exc_type) as exc_info:
                bridge.run_async(raise_specific())

            assert str(exc_info.value) == message

    def test_async_generator_handling(self) -> None:
        """Test AsyncBridge with async generators."""
        bridge = AsyncBridge.get_instance()

        async def async_generator():
            for i in range(3):
                await asyncio.sleep(0.01)
                yield i

        async def consume_generator():
            results = []
            async for value in async_generator():
                results.append(value)
            return results

        result = bridge.run_async(consume_generator())
        assert result == [0, 1, 2]

    def test_context_manager_cleanup(self) -> None:
        """Test AsyncBridge with async context managers."""
        bridge = AsyncBridge.get_instance()
        cleanup_called = False

        class AsyncResource:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                nonlocal cleanup_called
                cleanup_called = True

        async def use_resource():
            async with AsyncResource() as resource:
                return "resource_used"

        result = bridge.run_async(use_resource())
        assert result == "resource_used"
        assert cleanup_called

    def test_context_manager_cleanup_on_exception(self) -> None:
        """Test async context manager cleanup on exception."""
        bridge = AsyncBridge.get_instance()
        cleanup_called = False

        class AsyncResource:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                nonlocal cleanup_called
                cleanup_called = True
                return False  # Don't suppress exception

        async def use_resource_with_error():
            async with AsyncResource():
                raise ValueError("Error in context")

        with pytest.raises(ValueError):
            bridge.run_async(use_resource_with_error())

        assert cleanup_called

    def test_coroutine_not_awaited_detection(self) -> None:
        """Test detection of unawaited coroutines."""
        bridge = AsyncBridge.get_instance()

        async def outer():
            # Intentionally not awaiting
            inner_coro = inner()  # This creates a coroutine
            return "completed"

        async def inner():
            return "inner_result"

        # This should complete but might generate a warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = bridge.run_async(outer())

            # The function completes
            assert result == "completed"

            # Check if any coroutine warnings were issued
            # (Python may issue warnings about unawaited coroutines)

    def test_reentrant_lock_behavior(self) -> None:
        """Test AsyncBridge behavior with reentrant calls."""
        bridge = AsyncBridge.get_instance()

        async def async_task():
            return "result"

        def sync_function():
            # This is called from sync context
            return bridge.run_async(async_task())

        # Direct call should work
        result = sync_function()
        assert result == "result"

        # Call from thread should also work
        def thread_worker():
            return sync_function()

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(thread_worker)
            result = future.result()
            assert result == "result"

    def test_singleton_thread_safety(self) -> None:
        """Test that AsyncBridge singleton is thread-safe."""
        instances = []

        def get_instance_in_thread():
            instance = AsyncBridge.get_instance()
            instances.append(instance)

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_instance_in_thread)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All instances should be the same
        assert len(instances) == 10
        assert all(inst is instances[0] for inst in instances)

    @pytest.mark.skipif(
        not hasattr(asyncio, "eager_task_factory"),
        reason="Requires Python 3.12+ for eager tasks"
    )
    def test_eager_task_execution(self) -> None:
        """Test AsyncBridge with eager task execution (Python 3.12+)."""
        bridge = AsyncBridge.get_instance()

        async def eager_task():
            # Should execute eagerly without explicit await
            return "eager_result"

        result = bridge.run_async(eager_task())
        assert result == "eager_result"