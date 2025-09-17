"""
Stress tests for AsyncBridge to ensure robustness under heavy load.

This module contains comprehensive stress tests for AsyncBridge including
concurrent access, error propagation, and resource management.
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.AsyncBridge import AsyncBridge


@pytest.mark.unit
@pytest.mark.slow
class TestAsyncBridgeStress:
    """Stress tests for AsyncBridge under heavy load conditions."""

    @pytest.fixture(autouse=True)
    def cleanup_bridge(self):
        """Ensure bridge is cleaned up after each test."""
        yield
        # Clean up singleton after test
        AsyncBridge._instance = None
        AsyncBridge._lock = threading.Lock()

    def test_concurrent_bridge_initialization(self):
        """Test that concurrent initialization of AsyncBridge is thread-safe."""
        bridges = []
        errors = []

        def get_bridge():
            """Get bridge instance and store it."""
            try:
                bridge = AsyncBridge.get_instance()
                bridges.append(bridge)
            except Exception as e:
                errors.append(e)

        # Try to initialize bridge from multiple threads simultaneously
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_bridge) for _ in range(50)]
            for future in as_completed(futures):
                future.result()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors during initialization: {errors}"

        # Verify all threads got the same singleton instance
        assert len(set(id(b) for b in bridges)) == 1, "Multiple bridge instances created!"
        assert len(bridges) == 50

    def test_heavy_concurrent_async_operations(self):
        """Test AsyncBridge with many concurrent async operations."""
        bridge = AsyncBridge.get_instance()
        num_operations = 100
        results = []

        async def async_operation(task_id):
            """Simulate async work with variable duration."""
            await asyncio.sleep(0.001 * (task_id % 10))  # Variable delays
            return f"Task {task_id} done"

        def run_task(task_id):
            """Run async task through bridge."""
            return bridge.run_async(async_operation(task_id))

        # Run many concurrent operations
        start_time = time.perf_counter()
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(run_task, i) for i in range(num_operations)]
            results = [f.result() for f in as_completed(futures)]
        elapsed = time.perf_counter() - start_time

        # Verify all operations completed successfully
        assert len(results) == num_operations
        for i in range(num_operations):
            assert f"Task {i} done" in results

        # Performance check - should handle concurrent ops efficiently
        assert elapsed < 5.0, f"Operations took too long: {elapsed:.2f}s"

    def test_error_propagation_under_stress(self):
        """Test that errors are properly propagated even under heavy load."""
        bridge = AsyncBridge.get_instance()
        errors_caught = []
        successes = []

        async def maybe_failing_task(task_id):
            """Task that sometimes fails."""
            await asyncio.sleep(0.001)
            if task_id % 5 == 0:  # Every 5th task fails
                raise ValueError(f"Task {task_id} failed intentionally")
            return f"Task {task_id} success"

        def run_task_with_error_handling(task_id):
            """Run task and handle errors."""
            try:
                result = bridge.run_async(maybe_failing_task(task_id))
                successes.append(result)
            except ValueError as e:
                errors_caught.append(str(e))

        # Run tasks with mixed success/failure
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(run_task_with_error_handling, i) for i in range(50)]
            for future in as_completed(futures):
                future.result()

        # Verify correct number of errors and successes
        expected_errors = 10  # task_id 0, 5, 10, 15, 20, 25, 30, 35, 40, 45
        expected_successes = 40

        assert len(errors_caught) == expected_errors
        assert len(successes) == expected_successes

        # Verify error messages are correct
        for i in range(0, 50, 5):
            assert f"Task {i} failed intentionally" in errors_caught

    def test_nested_async_operations(self):
        """Test AsyncBridge with nested async operations."""
        bridge = AsyncBridge.get_instance()

        async def inner_task(value):
            """Inner async task."""
            await asyncio.sleep(0.001)
            return value * 2

        async def outer_task(task_id):
            """Outer task that calls inner tasks."""
            results = []
            for i in range(5):
                # Nested async operations
                result = await inner_task(task_id * 10 + i)
                results.append(result)
            return results

        # Run nested operations from multiple threads
        def run_nested(task_id):
            return bridge.run_async(outer_task(task_id))

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_nested, i) for i in range(10)]
            results = [f.result() for f in futures]

        # Verify nested operations completed correctly
        assert len(results) == 10
        for task_id in range(10):
            expected = [(task_id * 10 + i) * 2 for i in range(5)]
            assert expected in results

    def test_memory_leak_prevention(self):
        """Test that AsyncBridge doesn't leak memory under stress."""
        bridge = AsyncBridge.get_instance()
        import gc
        import sys

        async def memory_intensive_task(size_mb):
            """Create and discard large data."""
            data = bytearray(size_mb * 1024 * 1024)  # Allocate MB of memory
            await asyncio.sleep(0.001)
            return len(data)

        # Get initial memory baseline
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Run many memory-intensive tasks
        for _ in range(20):
            bridge.run_async(memory_intensive_task(10))  # 10MB each

        # Force garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())

        # Check that we don't have excessive object growth
        # Some growth is expected, but it should be reasonable
        object_growth = final_objects - initial_objects
        assert object_growth < 1000, f"Excessive object growth: {object_growth}"

    def test_event_loop_resilience(self):
        """Test that AsyncBridge event loop remains functional after errors."""
        bridge = AsyncBridge.get_instance()

        async def crashing_task():
            """Task that crashes hard."""
            await asyncio.sleep(0.001)
            raise RuntimeError("Catastrophic failure!")

        async def normal_task():
            """Normal task that should work."""
            await asyncio.sleep(0.001)
            return "Success!"

        # First, cause an error
        with pytest.raises(RuntimeError, match="Catastrophic failure"):
            bridge.run_async(crashing_task())

        # Event loop should still be functional
        result = bridge.run_async(normal_task())
        assert result == "Success!"

        # Run more tasks to ensure stability
        for i in range(10):
            result = bridge.run_async(normal_task())
            assert result == "Success!"

    def test_timeout_handling(self):
        """Test AsyncBridge behavior with tasks that timeout."""
        bridge = AsyncBridge.get_instance()

        async def slow_task():
            """Task that takes too long."""
            await asyncio.sleep(10)  # Very slow
            return "Finally done"

        async def timeout_wrapper():
            """Wrap slow task with timeout."""
            try:
                return await asyncio.wait_for(slow_task(), timeout=0.1)
            except asyncio.TimeoutError:
                return "Timed out"

        result = bridge.run_async(timeout_wrapper())
        assert result == "Timed out"

        # Bridge should still be functional after timeout
        async def quick_task():
            return "Quick!"

        result = bridge.run_async(quick_task())
        assert result == "Quick!"

    def test_cancellation_handling(self):
        """Test handling of cancelled async tasks."""
        bridge = AsyncBridge.get_instance()
        cancellation_handled = False

        async def cancellable_task():
            """Task that can be cancelled."""
            nonlocal cancellation_handled
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                cancellation_handled = True
                raise
            return "Not cancelled"

        async def cancel_wrapper():
            """Create and cancel a task."""
            task = asyncio.create_task(cancellable_task())
            await asyncio.sleep(0.01)  # Let it start
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                return "Cancelled successfully"
            return "Failed to cancel"

        result = bridge.run_async(cancel_wrapper())
        assert result == "Cancelled successfully"
        assert cancellation_handled

    def test_recursive_bridge_calls(self):
        """Test recursive calls through AsyncBridge."""
        bridge = AsyncBridge.get_instance()

        async def recursive_async(depth):
            """Recursive async function."""
            if depth <= 0:
                return "Done"
            await asyncio.sleep(0.001)
            # Note: Can't call bridge.run_async from within async context
            # This would deadlock, so we test indirect recursion
            return f"Level {depth}"

        def recursive_sync(depth):
            """Recursive sync function using bridge."""
            if depth <= 0:
                return "Done"

            async def task():
                await asyncio.sleep(0.001)
                return f"Level {depth}"

            result = bridge.run_async(task())
            if depth > 1:
                # Recursive call through sync
                next_result = recursive_sync(depth - 1)
                return f"{result} -> {next_result}"
            return result

        # Test recursive calls
        result = recursive_sync(5)
        assert "Level 5" in result
        assert "Level 4" in result
        assert "Level 3" in result

    def test_exception_types_preservation(self):
        """Test that different exception types are properly preserved."""
        bridge = AsyncBridge.get_instance()

        exceptions_to_test = [
            (ValueError, "Value error test"),
            (KeyError, "key_error"),
            (AttributeError, "Attribute error test"),
            (TypeError, "Type error test"),
            (RuntimeError, "Runtime error test"),
            (IOError, "IO error test"),
            (ZeroDivisionError, "Division by zero"),
        ]

        for exc_type, exc_msg in exceptions_to_test:
            async def failing_task():
                await asyncio.sleep(0.001)
                if exc_type == KeyError:
                    raise exc_type(exc_msg)
                else:
                    raise exc_type(exc_msg)

            # Verify correct exception type is raised
            with pytest.raises(exc_type) as exc_info:
                bridge.run_async(failing_task())

            # Verify message is preserved
            if exc_type == KeyError:
                assert exc_msg in str(exc_info.value)
            else:
                assert exc_msg == str(exc_info.value)


class TestAsyncBridgeEdgeCases:
    """Test edge cases and boundary conditions for AsyncBridge."""

    @pytest.fixture(autouse=True)
    def cleanup_bridge(self):
        """Ensure bridge is cleaned up after each test."""
        yield
        AsyncBridge._instance = None
        AsyncBridge._lock = threading.Lock()

    def test_empty_coroutine(self):
        """Test handling of empty/minimal coroutines."""
        bridge = AsyncBridge.get_instance()

        async def empty():
            """Empty async function."""
            pass

        result = bridge.run_async(empty())
        assert result is None

    def test_immediate_return(self):
        """Test coroutines that return immediately without await."""
        bridge = AsyncBridge.get_instance()

        async def immediate():
            """Return immediately without any await."""
            return 42

        result = bridge.run_async(immediate())
        assert result == 42

    def test_large_return_values(self):
        """Test handling of large return values."""
        bridge = AsyncBridge.get_instance()

        async def large_data():
            """Return large amount of data."""
            # Create a large list
            return list(range(1000000))

        result = bridge.run_async(large_data())
        assert len(result) == 1000000
        assert result[0] == 0
        assert result[-1] == 999999

    def test_complex_object_returns(self):
        """Test returning complex objects through the bridge."""
        bridge = AsyncBridge.get_instance()

        class ComplexObject:
            def __init__(self):
                self.data = {"nested": {"value": 42}}
                self.list = [1, 2, 3]
                self.callback = lambda x: x * 2

        async def complex_return():
            """Return complex object."""
            await asyncio.sleep(0.001)
            return ComplexObject()

        result = bridge.run_async(complex_return())
        assert isinstance(result, ComplexObject)
        assert result.data["nested"]["value"] == 42
        assert result.list == [1, 2, 3]
        assert result.callback(5) == 10

    def test_generator_async_iteration(self):
        """Test async generators through the bridge."""
        bridge = AsyncBridge.get_instance()

        async def async_generator():
            """Async generator function."""
            for i in range(5):
                await asyncio.sleep(0.001)
                yield i

        async def consume_generator():
            """Consume async generator."""
            results = []
            async for value in async_generator():
                results.append(value)
            return results

        result = bridge.run_async(consume_generator())
        assert result == [0, 1, 2, 3, 4]
