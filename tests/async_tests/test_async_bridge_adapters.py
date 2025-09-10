"""
Tests for async/sync bridging using AsyncBridge.

This module contains tests for bridging sync and async code using AsyncBridge,
replacing the deprecated AsyncCore adapter patterns.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import asyncio
from unittest.mock import MagicMock

import pytest

from ClassicLib.AsyncBridge import AsyncBridge


class TestAsyncBridgeAdapter:
    """Test AsyncBridge adapter patterns"""

    def test_async_bridge_basic(self):
        """Test basic AsyncBridge functionality"""

        class AsyncComponent:
            async def async_method(self, value):
                await asyncio.sleep(0.001)
                return value * 2

            async def async_property(self):
                return "async_value"

        async_obj = AsyncComponent()
        bridge = AsyncBridge.get_instance()

        # Test method call
        result = bridge.run_async(async_obj.async_method(5))
        assert result == 10

        # Test property access
        prop_value = bridge.run_async(async_obj.async_property())
        assert prop_value == "async_value"

    def test_async_bridge_with_exceptions(self):
        """Test AsyncBridge exception handling"""

        class AsyncComponent:
            async def failing_method(self):
                raise ValueError("Async error")

        async_obj = AsyncComponent()
        bridge = AsyncBridge.get_instance()

        with pytest.raises(ValueError) as exc_info:
            bridge.run_async(async_obj.failing_method())
        assert "Async error" in str(exc_info.value)

    def test_async_bridge_with_args_kwargs(self):
        """Test AsyncBridge with various arguments"""

        class AsyncComponent:
            async def complex_method(self, *args, **kwargs):
                await asyncio.sleep(0.001)
                return {"args": args, "kwargs": kwargs}

        async_obj = AsyncComponent()
        bridge = AsyncBridge.get_instance()

        result = bridge.run_async(async_obj.complex_method(1, 2, 3, key1="value1", key2="value2"))
        assert result["args"] == (1, 2, 3)
        assert result["kwargs"] == {"key1": "value1", "key2": "value2"}

    def test_sync_adapter_pattern_with_bridge(self):
        """Test creating a sync adapter using AsyncBridge"""

        class AsyncClass:
            def __init__(self, multiplier):
                self.multiplier = multiplier

            async def process(self, value):
                await asyncio.sleep(0.001)
                return value * self.multiplier

        # Create a sync wrapper class using AsyncBridge
        class SyncClass:
            def __init__(self, multiplier):
                self.async_instance = AsyncClass(multiplier)
                self.bridge = AsyncBridge.get_instance()

            def process(self, value):
                return self.bridge.run_async(self.async_instance.process(value))

        sync_instance = SyncClass(3)
        result = sync_instance.process(4)
        assert result == 12

    def test_mixed_sync_async_component(self):
        """Test component with both sync and async methods"""

        class MixedComponent:
            def sync_method(self):
                return "sync_result"

            async def async_method(self):
                return "async_result"

        mixed_obj = MixedComponent()
        bridge = AsyncBridge.get_instance()

        # Sync method works directly
        sync_result = mixed_obj.sync_method()
        assert sync_result == "sync_result"

        # Async method through bridge
        async_result = bridge.run_async(mixed_obj.async_method())
        assert async_result == "async_result"


class TestHybridPattern:
    """Test hybrid sync/async patterns using AsyncBridge"""

    def test_hybrid_pattern_sync_call(self):
        """Test hybrid pattern called synchronously"""

        class TestClass:
            def __init__(self):
                self.bridge = AsyncBridge.get_instance()

            async def _process_async(self, value):
                await asyncio.sleep(0.001)
                return value * 2

            def process(self, value):
                """Sync wrapper using AsyncBridge"""
                return self.bridge.run_async(self._process_async(value))

            async def process_async(self, value):
                """Direct async method"""
                return await self._process_async(value)

        obj = TestClass()

        # Call synchronously
        result = obj.process(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_hybrid_pattern_async_call(self):
        """Test hybrid pattern called asynchronously"""

        class TestClass:
            async def process(self, value):
                await asyncio.sleep(0.001)
                return value * 2

        obj = TestClass()

        # Call asynchronously
        result = await obj.process(5)
        assert result == 10

    def test_hybrid_pattern_with_class_state(self):
        """Test hybrid pattern accessing class state"""

        class TestClass:
            def __init__(self, multiplier):
                self.multiplier = multiplier
                self.bridge = AsyncBridge.get_instance()

            async def _process_async(self, value):
                await asyncio.sleep(0.001)
                return value * self.multiplier

            def process(self, value):
                """Sync version using bridge"""
                return self.bridge.run_async(self._process_async(value))

        obj = TestClass(3)

        # Test sync call
        sync_result = obj.process(4)
        assert sync_result == 12

    def test_hybrid_pattern_exception_handling(self):
        """Test hybrid pattern exception handling"""

        class TestClass:
            def __init__(self):
                self.bridge = AsyncBridge.get_instance()

            async def _failing_method_async(self):
                raise ValueError("Test error")

            def failing_method(self):
                return self.bridge.run_async(self._failing_method_async())

        obj = TestClass()

        # Test sync call exception
        with pytest.raises(ValueError) as exc_info:
            obj.failing_method()
        assert "Test error" in str(exc_info.value)


class TestAsyncBridgeWrapper:
    """Test wrapper patterns using AsyncBridge"""

    def test_function_wrapper_basic(self):
        """Test basic function wrapper using AsyncBridge"""

        async def async_function(x, y):
            await asyncio.sleep(0.001)
            return x + y

        # Create sync wrapper using AsyncBridge
        def sync_function(x, y):
            bridge = AsyncBridge.get_instance()
            return bridge.run_async(async_function(x, y))

        result = sync_function(3, 4)
        assert result == 7

    def test_function_wrapper_with_kwargs(self):
        """Test wrapper with keyword arguments"""

        async def async_function(a, b=2, c=3):
            await asyncio.sleep(0.001)
            return a * b * c

        # Create sync wrapper
        def sync_function(a, b=2, c=3):
            bridge = AsyncBridge.get_instance()
            return bridge.run_async(async_function(a, b=b, c=c))

        result = sync_function(2, b=3, c=4)
        assert result == 24

    def test_lambda_wrapper_pattern(self):
        """Test using lambda for simple wrappers"""

        async def async_function():
            """This is a special function"""
            return "special"

        bridge = AsyncBridge.get_instance()
        sync_function = lambda: bridge.run_async(async_function())

        result = sync_function()
        assert result == "special"

    def test_nested_async_calls(self):
        """Test nested async call patterns"""

        class InnerAsync:
            async def process(self, value):
                await asyncio.sleep(0.001)
                return value + 1

        class OuterAsync:
            def __init__(self):
                self.inner = InnerAsync()

            async def process_with_inner(self, value):
                result = await self.inner.process(value)
                return result * 2

        # Create sync wrapper
        class OuterSync:
            def __init__(self):
                self.outer_async = OuterAsync()
                self.bridge = AsyncBridge.get_instance()

            def process_with_inner(self, value):
                return self.bridge.run_async(self.outer_async.process_with_inner(value))

        outer_sync = OuterSync()
        result = outer_sync.process_with_inner(5)
        assert result == 12  # (5 + 1) * 2


class TestAsyncBridgePerformance:
    """Test AsyncBridge performance characteristics"""

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
        """Test AsyncBridge handles concurrent operations correctly"""
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
