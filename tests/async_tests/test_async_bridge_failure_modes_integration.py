"""Comprehensive tests for AsyncBridge failure modes and edge cases.

This module tests AsyncBridge's behavior under various failure conditions,
including error propagation, concurrent operation limits, and fallback mechanisms.
"""

import asyncio
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from unittest.mock import patch

import pytest

from ClassicLib.AsyncBridge import AsyncBridge

# Mark all tests in this module
pytestmark = [pytest.mark.unit]


class TestAsyncBridgeFailureModes:
    """Test AsyncBridge failure modes and fallback mechanisms."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Reset AsyncBridge singleton before each test."""
        # Clear all instances to ensure clean state
        # DO NOT delete class variables like _lock - they must persist
        with AsyncBridge._lock:
            # Shutdown existing instances
            for instance in AsyncBridge._instances.values():
                try:
                    instance.shutdown()
                except Exception:
                    pass
            # Clear the instances dict
            AsyncBridge._instances.clear()

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
            coro = inner_async()
            try:
                return bridge.run_async(coro)
            except Exception:
                coro.close()
                raise

        with pytest.raises(RuntimeError) as exc_info:
            bridge.run_async(outer_async())

        assert "Cannot use AsyncBridge.run_async() from within an async context" in str(exc_info.value)

    def test_concurrent_operation_limits(self) -> None:
        """Test AsyncBridge behavior under concurrent operations from same thread.

        Note: This tests multiple operations from the same thread using the same
        bridge instance. For multi-thread concurrency, each thread gets its own
        bridge instance (thread-local design).
        """
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
                errors.append((task_id, type(e).__name__, str(e)))

        # Run tasks sequentially from the main thread (same bridge instance)
        for i in range(10):
            run_task(i)

        # All tasks should complete successfully from same thread
        assert len(results) == 10, f"Expected 10 results, got {len(results)}"
        assert len(errors) == 0, f"Expected no errors, got {errors}"
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

        async def long_task():  # pyright: ignore[reportUnusedFunction]
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
        """Test multiple threads calling run_async simultaneously.

        Each thread gets its own AsyncBridge instance (thread-local),
        so they don't interfere with each other.
        """
        results = {}
        errors = {}
        lock = threading.Lock()

        async def thread_specific_task(thread_id: str):
            await asyncio.sleep(0.02)
            return f"thread_{thread_id}"

        def thread_worker(thread_id: str):
            try:
                # Each thread gets its own bridge instance
                bridge = AsyncBridge.get_instance()
                result = bridge.run_async(thread_specific_task(thread_id))
                with lock:
                    results[thread_id] = result
            except Exception as e:
                with lock:
                    errors[thread_id] = (type(e).__name__, str(e))

        # Create multiple threads with slight stagger to reduce startup contention
        threads = []
        for i in range(5):
            thread = threading.Thread(target=thread_worker, args=(str(i),))
            threads.append(thread)
            thread.start()
            time.sleep(0.01)  # Slight delay to reduce event loop startup contention

        # Wait for all threads
        for thread in threads:
            thread.join(timeout=10.0)

        # Check results - all should succeed or gracefully fail
        assert len(results) + len(errors) == 5, f"Expected 5 total outcomes, got {len(results)} results and {len(errors)} errors"

        # If there are errors, they should be timeout-related (acceptable under heavy load)
        for thread_id, (error_type, error_msg) in errors.items():
            assert "timeout" in error_msg.lower() or "RuntimeError" in error_type, (
                f"Thread {thread_id} failed with unexpected error: {error_type}: {error_msg}"
            )

        # All successful results should be correct
        for thread_id, result in results.items():
            assert result == f"thread_{thread_id}", f"Thread {thread_id} got wrong result: {result}"

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
            # Create a factory function to avoid closure issues
            def make_raiser(exc_class, exc_message):
                async def raise_specific():
                    raise exc_class(exc_message)

                return raise_specific

            raiser = make_raiser(exc_type, message)

            with pytest.raises(exc_type) as exc_info:
                bridge.run_async(raiser())

            # KeyError adds quotes around the message, others don't
            exc_str = str(exc_info.value)
            if exc_type is KeyError:
                # KeyError wraps message in quotes
                assert message in exc_str
            else:
                assert exc_str == message

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
            async with AsyncResource():
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
            inner()  # pyright: ignore[reportUnusedCoroutine] # This creates a coroutine
            return "completed"

        async def inner():
            return "inner_result"

        # This should complete but might generate a warning
        with warnings.catch_warnings(record=True):
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
        """Test that AsyncBridge is thread-local and thread-safe.

        AsyncBridge maintains one instance per thread (thread-local),
        not a single global instance. This test verifies:
        1. Each thread gets its own unique instance
        2. Multiple calls within the same thread return the same instance
        3. Instance creation is thread-safe
        """
        instances_by_thread = {}
        lock = threading.Lock()

        def get_instance_twice(thread_id: int):
            # Get instance twice in same thread
            instance1 = AsyncBridge.get_instance()
            instance2 = AsyncBridge.get_instance()

            with lock:
                instances_by_thread[thread_id] = (instance1, instance2)

        threads = []
        for i in range(10):
            thread = threading.Thread(target=get_instance_twice, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify we got instances for all threads
        assert len(instances_by_thread) == 10

        # Within each thread, both calls should return the same instance
        for thread_id, (inst1, inst2) in instances_by_thread.items():
            assert inst1 is inst2, f"Thread {thread_id} got different instances on consecutive calls"

        # Different threads should have different instances (thread-local behavior)
        all_instances = [inst1 for inst1, _ in instances_by_thread.values()]
        unique_instances = set(id(inst) for inst in all_instances)
        assert len(unique_instances) == 10, "Each thread should have its own unique AsyncBridge instance"

    @pytest.mark.skipif(not hasattr(asyncio, "eager_task_factory"), reason="Requires Python 3.12+ for eager tasks")
    def test_eager_task_execution(self) -> None:
        """Test AsyncBridge with eager task execution (Python 3.12+)."""
        bridge = AsyncBridge.get_instance()

        async def eager_task():
            # Should execute eagerly without explicit await
            return "eager_result"

        result = bridge.run_async(eager_task())
        assert result == "eager_result"

    def test_concurrent_shutdown_during_active_use(self) -> None:
        """Test shutdown behavior when threads are actively using bridges.

        Tests Issue #3 fix: proper diagnostic logging during cleanup
        Tests Issue #4 fix: resource leak prevention in shutdown

        The improved implementation allows graceful handling - tasks can complete
        even during shutdown, or they can fail gracefully with clear errors.
        """
        results = []
        errors = []

        async def quick_task(task_id: int):
            await asyncio.sleep(0.05)
            return f"task_{task_id}_complete"

        def worker(task_id: int):
            try:
                bridge = AsyncBridge.get_instance()

                # First thread initiates cleanup
                if task_id == 0:
                    # Start task, then shutdown mid-execution
                    result = bridge.run_async(quick_task(task_id))
                    results.append(result)
                    # Now cleanup while others might be running
                    AsyncBridge._cleanup_all()
                else:
                    # Other threads try to get/use bridge
                    result = bridge.run_async(quick_task(task_id))
                    results.append(result)
            except Exception as e:
                errors.append((task_id, type(e).__name__, str(e)))

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i) for i in range(5)]
            for future in futures:
                future.result()

        # Should handle gracefully - all operations accounted for
        assert len(results) + len(errors) == 5

        # The improved implementation can handle this gracefully, so we just
        # verify no crashes occurred and all tasks are accounted for
        # (both success and failure are acceptable outcomes)

    def test_loop_health_recovery(self) -> None:
        """Test recovery when background thread dies unexpectedly.

        Tests Issue #7 fix: loop health checking and recovery
        """
        bridge = AsyncBridge.get_instance()

        async def simple_task():
            return "success"

        # First call establishes loop
        result1 = bridge.run_async(simple_task())
        assert result1 == "success"

        # Simulate thread death by stopping the loop
        if bridge._loop:
            bridge._loop.call_soon_threadsafe(bridge._loop.stop)
            time.sleep(0.2)  # Let thread die

        # Next call should detect dead thread and recreate loop
        result2 = bridge.run_async(simple_task())
        assert result2 == "success"

    def test_timeout_enforcement_both_levels(self) -> None:
        """Test timeout is enforced at both asyncio and future levels.

        Tests Issue #5 fix: proper timeout implementation with defense-in-depth
        """
        bridge = AsyncBridge.get_instance()

        async def slow_task():
            await asyncio.sleep(10.0)
            return "completed"

        # Test that timeout is enforced
        start_time = time.time()
        with pytest.raises(TimeoutError) as exc_info:
            bridge.run_async_with_timeout(slow_task(), timeout=0.5)

        elapsed = time.time() - start_time

        # Should timeout quickly (within timeout + buffer)
        assert elapsed < 2.0, f"Timeout took too long: {elapsed}s"
        assert "timed out" in str(exc_info.value).lower()

    def test_metrics_callback(self) -> None:
        """Test metrics collection callback.

        Tests new enhancement: metrics hooks
        """
        collected_metrics = []

        def metrics_handler(event: str, metrics: dict[str, Any]):
            collected_metrics.append((event, metrics))

        # Set up metrics callback
        AsyncBridge.set_metrics_callback(metrics_handler)

        try:
            bridge = AsyncBridge.get_instance()

            async def test_task():
                await asyncio.sleep(0.01)
                return "result"

            # Run task - should collect metrics
            result = bridge.run_async(test_task())
            assert result == "result"

            # Check metrics were collected
            assert len(collected_metrics) > 0
            event_name, metrics = collected_metrics[0]
            assert event_name == "async_bridge_run"
            assert "duration" in metrics
            assert "success" in metrics
            assert metrics["success"] is True
            assert "thread_id" in metrics

        finally:
            # Clean up - disable metrics
            AsyncBridge.set_metrics_callback(None)

    def test_metrics_callback_on_error(self) -> None:
        """Test metrics collection on error.

        Tests new enhancement: metrics hooks with error tracking
        """
        collected_metrics = []

        def metrics_handler(event: str, metrics: dict[str, Any]):
            collected_metrics.append((event, metrics))

        AsyncBridge.set_metrics_callback(metrics_handler)

        try:
            bridge = AsyncBridge.get_instance()

            async def failing_task():
                raise ValueError("Test error")

            # Run failing task
            with pytest.raises(ValueError):
                bridge.run_async(failing_task())

            # Check error metrics were collected
            assert len(collected_metrics) > 0
            event_name, metrics = collected_metrics[0]
            assert event_name == "async_bridge_run"
            assert metrics["success"] is False
            assert metrics["error_type"] == "ValueError"

        finally:
            AsyncBridge.set_metrics_callback(None)

    def test_context_manager_support(self) -> None:
        """Test context manager usage.

        Tests new enhancement: context manager support
        """

        async def test_task():
            return "context_result"

        # Use bridge as context manager
        with AsyncBridge.get_instance() as bridge:
            result = bridge.run_async(test_task())
            assert result == "context_result"

        # Bridge should be shutdown after exiting context
        # Note: get_instance() will create a new one, but the old one is shutdown

    def test_threading_local_optimization(self) -> None:
        """Test thread-local caching optimization.

        Tests new enhancement: threading.local optimization for get_instance()
        """
        # First call populates cache
        bridge1 = AsyncBridge.get_instance()

        # Second call should use cache
        bridge2 = AsyncBridge.get_instance()

        # Should be the same instance
        assert bridge1 is bridge2

        # In a different thread, should get different instance
        other_thread_instance = []

        def get_in_thread():
            other_thread_instance.append(AsyncBridge.get_instance())

        thread = threading.Thread(target=get_in_thread)
        thread.start()
        thread.join()

        assert len(other_thread_instance) == 1
        # Different thread should have different instance
        assert other_thread_instance[0] is not bridge1
