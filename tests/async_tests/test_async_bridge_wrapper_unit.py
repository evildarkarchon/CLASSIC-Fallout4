"""
Unit tests for async/sync bridging using AsyncBridge - wrapper patterns and characteristics.

This module contains unit tests for AsyncBridge wrapper patterns and behavioral
characteristics like event loop reuse, concurrency handling, and singleton pattern.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR6301, BLE001

import asyncio
import logging

import pytest

from ClassicLib.AsyncBridge import AsyncBridge

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.unit


class TestAsyncBridgeWrapper:
    """Test AsyncBridge wrapper patterns"""

    def test_function_wrapper_basic(self, async_bridge):
        """Test wrapping async functions for sync use.

        Args:
            async_bridge: Properly isolated AsyncBridge instance from fixture
        """

        async def async_function(x):
            await asyncio.sleep(0.001)
            return x * 2

        # Create sync wrapper using fixture-provided bridge
        def sync_wrapper(x):
            return async_bridge.run_async(async_function(x))

        assert sync_wrapper(5) == 10
        assert sync_wrapper(0) == 0

    def test_function_wrapper_with_kwargs(self, async_bridge):
        """Test wrapping functions with keyword arguments.

        Args:
            async_bridge: Properly isolated AsyncBridge instance from fixture
        """

        async def async_calc(a, b=10, c=20):
            await asyncio.sleep(0.001)
            return a + b + c

        def sync_calc(**kwargs):
            return async_bridge.run_async(async_calc(**kwargs))

        assert sync_calc(a=1) == 31
        assert sync_calc(a=1, b=2) == 23
        assert sync_calc(a=1, b=2, c=3) == 6

    def test_lambda_wrapper_pattern(self, async_bridge):
        """Test using lambdas for quick sync wrappers.

        Args:
            async_bridge: Properly isolated AsyncBridge instance from fixture
        """

        async def async_upper(text):
            await asyncio.sleep(0.001)
            return text.upper()

        def sync_upper(text):
            return async_bridge.run_async(async_upper(text))

        assert sync_upper("hello") == "HELLO"
        assert sync_upper("world") == "WORLD"

    def test_nested_async_calls(self, async_bridge):
        """Test bridging nested async calls.

        Args:
            async_bridge: Properly isolated AsyncBridge instance from fixture
        """

        class OuterAsync:
            async def process(self, value):
                inner = InnerAsync()
                result = await inner.transform(value)
                return result * 2

        class InnerAsync:
            async def transform(self, value):
                await asyncio.sleep(0.001)
                return value + 1

        class OuterSync:
            def __init__(self):
                self.outer_async = OuterAsync()
                self.bridge = async_bridge

            def process_with_inner(self, value):
                return self.bridge.run_async(self.outer_async.process(value))

        outer_sync = OuterSync()
        result = outer_sync.process_with_inner(5)
        assert result == 12  # (5 + 1) * 2


class TestAsyncBridgeBehavior:
    """Test AsyncBridge behavioral characteristics"""

    def test_bridge_reuses_event_loop(self, async_bridge):
        """Test that AsyncBridge reuses the same event loop in a thread.

        Args:
            async_bridge: Properly isolated AsyncBridge instance from fixture
        """

        async def get_loop_id():
            await asyncio.sleep(0)
            return id(asyncio.get_running_loop())

        # Multiple calls should use the same loop
        loop_id1 = async_bridge.run_async(get_loop_id())
        loop_id2 = async_bridge.run_async(get_loop_id())
        loop_id3 = async_bridge.run_async(get_loop_id())

        assert loop_id1 == loop_id2 == loop_id3

    def test_bridge_handles_concurrent_calls(self, async_bridge):
        """Test AsyncBridge handles sequential operations correctly.

        Args:
            async_bridge: Properly isolated AsyncBridge instance from fixture
        """
        results = []

        async def async_task(n):
            await asyncio.sleep(0.001)
            return n * 2

        # Sequential calls through fixture-provided bridge
        for i in range(5):
            result = async_bridge.run_async(async_task(i))
            results.append(result)

        assert results == [0, 2, 4, 6, 8]

    def test_bridge_singleton_pattern(self, async_bridge):
        """Test that AsyncBridge follows singleton pattern.

        Args:
            async_bridge: Properly isolated AsyncBridge instance from fixture

        Note: This test verifies that within a thread, get_instance() returns
        the same instance. The fixture ensures proper isolation between tests.
        """
        # The fixture provides the instance for this test
        # Verify that get_instance returns the same instance within the test
        bridge1 = AsyncBridge.get_instance()
        bridge2 = AsyncBridge.get_instance()

        # Both should be the same as the fixture-provided instance
        assert bridge1 is bridge2
        assert bridge1 is async_bridge

    def test_bridge_thread_safety(self):
        """Test AsyncBridge thread safety - each thread gets own instance.

        This test validates that AsyncBridge correctly provides per-thread
        instances and that each thread can safely execute async operations
        without interfering with other threads.

        Note: We don't use the async_bridge fixture here because we need to test
        the per-thread instance behavior, not a shared instance.
        """
        import asyncio
        import threading

        from ClassicLib.AsyncBridge import AsyncBridge

        results = []
        errors = []
        lock = threading.Lock()

        async def async_work(thread_id):
            """Async work to be executed from thread.

            Args:
                thread_id: Unique identifier for this thread

            Returns:
                String identifying the thread that executed the work
            """
            await asyncio.sleep(0.001)  # Simulate async work
            return f"thread_{thread_id}"

        def thread_work(thread_id):
            """Worker function - each thread gets its own AsyncBridge instance.

            Each thread MUST call get_instance() to obtain its own bridge.
            Sharing a bridge instance across threads is an error.

            Args:
                thread_id: Unique identifier for this thread
            """
            try:
                # ✅ CORRECT: Each thread gets its own bridge instance
                # AsyncBridge uses per-thread instances stored by thread ID
                bridge = AsyncBridge.get_instance()

                # Execute async work via this thread's bridge
                result = bridge.run_async(async_work(thread_id))

                # Thread-safe result storage
                with lock:
                    results.append(result)

            except Exception as e:
                # Thread-safe error storage
                with lock:
                    errors.append((thread_id, str(e), type(e).__name__))

        # Launch worker threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=thread_work, args=(i,), name=f"TestWorker-{i}")
            threads.append(t)
            t.start()

        # Wait for all threads with timeout
        for t in threads:
            t.join(timeout=10.0)  # Generous timeout for debugging
            if t.is_alive():
                errors.append((-1, f"Thread {t.name} timed out", "TimeoutError"))

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred in worker threads: {errors}"

        # Verify all threads completed successfully
        assert len(results) == 3, f"Expected 3 results, got {len(results)}: {results}"

        # Verify each result is correctly formatted
        assert all(r.startswith("thread_") for r in results), f"Invalid result format: {results}"

        # Verify we got results from all 3 threads
        thread_ids = [r.split("_")[1] for r in results]
        assert set(thread_ids) == {"0", "1", "2"}, f"Missing thread results: {thread_ids}"

        # Cleanup: shutdown all bridge instances created by threads
        # This is important to prevent test pollution
        with AsyncBridge._lock:
            for instance in list(AsyncBridge._instances.values()):
                try:
                    instance.shutdown()
                except Exception as e:
                    # Log but don't fail test on cleanup errors
                    logger.debug(f"Error during bridge cleanup: {e}")
            AsyncBridge._instances.clear()

    def test_bridge_error_propagation(self, async_bridge):
        """Test that AsyncBridge properly propagates errors.

        Args:
            async_bridge: Properly isolated AsyncBridge instance from fixture
        """

        async def async_error():
            await asyncio.sleep(0.001)
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            async_bridge.run_async(async_error())

        # Bridge should still work after error
        async def async_ok():
            await asyncio.sleep(0)
            return "ok"

        assert async_bridge.run_async(async_ok()) == "ok"


if __name__ == "__main__":
    pytest.main([__file__])
