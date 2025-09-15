"""
Unit tests for async/sync bridging using AsyncBridge - wrapper patterns and characteristics.

This module contains unit tests for AsyncBridge wrapper patterns and behavioral
characteristics like event loop reuse, concurrency handling, and singleton pattern.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import asyncio
from unittest.mock import MagicMock

import pytest

from ClassicLib.AsyncBridge import AsyncBridge

pytestmark = pytest.mark.unit


class TestAsyncBridgeWrapper:
    """Test AsyncBridge wrapper patterns"""

    def test_function_wrapper_basic(self):
        """Test wrapping async functions for sync use"""

        async def async_function(x):
            await asyncio.sleep(0.001)
            return x * 2

        bridge = AsyncBridge.get_instance()

        # Create sync wrapper
        def sync_wrapper(x):
            return bridge.run_async(async_function(x))

        assert sync_wrapper(5) == 10
        assert sync_wrapper(0) == 0

    def test_function_wrapper_with_kwargs(self):
        """Test wrapping functions with keyword arguments"""

        async def async_calc(a, b=10, c=20):
            await asyncio.sleep(0.001)
            return a + b + c

        bridge = AsyncBridge.get_instance()

        def sync_calc(**kwargs):
            return bridge.run_async(async_calc(**kwargs))

        assert sync_calc(a=1) == 31
        assert sync_calc(a=1, b=2) == 23
        assert sync_calc(a=1, b=2, c=3) == 6

    def test_lambda_wrapper_pattern(self):
        """Test using lambdas for quick sync wrappers"""

        async def async_upper(text):
            await asyncio.sleep(0.001)
            return text.upper()

        bridge = AsyncBridge.get_instance()
        sync_upper = lambda text: bridge.run_async(async_upper(text))

        assert sync_upper("hello") == "HELLO"
        assert sync_upper("world") == "WORLD"

    def test_nested_async_calls(self):
        """Test bridging nested async calls"""

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
                self.bridge = AsyncBridge.get_instance()

            def process_with_inner(self, value):
                return self.bridge.run_async(self.outer_async.process(value))

        outer_sync = OuterSync()
        result = outer_sync.process_with_inner(5)
        assert result == 12  # (5 + 1) * 2


class TestAsyncBridgeBehavior:
    """Test AsyncBridge behavioral characteristics"""

    def test_bridge_reuses_event_loop(self):
        """Test that AsyncBridge reuses the same event loop in a thread"""
        bridge = AsyncBridge.get_instance()

        async def get_loop_id():
            return id(asyncio.get_running_loop())

        # Multiple calls should use the same loop
        loop_id1 = bridge.run_async(get_loop_id())
        loop_id2 = bridge.run_async(get_loop_id())
        loop_id3 = bridge.run_async(get_loop_id())

        assert loop_id1 == loop_id2 == loop_id3

    def test_bridge_handles_concurrent_calls(self):
        """Test AsyncBridge handles sequential operations correctly"""
        bridge = AsyncBridge.get_instance()
        results = []

        async def async_task(n):
            await asyncio.sleep(0.001)
            return n * 2

        # Sequential calls through bridge
        for i in range(5):
            result = bridge.run_async(async_task(i))
            results.append(result)

        assert results == [0, 2, 4, 6, 8]

    def test_bridge_singleton_pattern(self):
        """Test that AsyncBridge follows singleton pattern"""
        bridge1 = AsyncBridge.get_instance()
        bridge2 = AsyncBridge.get_instance()

        assert bridge1 is bridge2

    def test_bridge_thread_safety(self):
        """Test AsyncBridge thread safety characteristics"""
        import threading

        bridge = AsyncBridge.get_instance()
        results = []

        async def async_work(thread_id):
            await asyncio.sleep(0.001)
            return f"thread_{thread_id}"

        def thread_work(thread_id):
            result = bridge.run_async(async_work(thread_id))
            results.append(result)

        threads = []
        for i in range(3):
            t = threading.Thread(target=thread_work, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All threads should complete successfully
        assert len(results) == 3
        assert all(r.startswith("thread_") for r in results)

    def test_bridge_error_propagation(self):
        """Test that AsyncBridge properly propagates errors"""
        bridge = AsyncBridge.get_instance()

        async def async_error():
            await asyncio.sleep(0.001)
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            bridge.run_async(async_error())

        # Bridge should still work after error
        async def async_ok():
            return "ok"

        assert bridge.run_async(async_ok()) == "ok"


if __name__ == "__main__":
    pytest.main([__file__])
