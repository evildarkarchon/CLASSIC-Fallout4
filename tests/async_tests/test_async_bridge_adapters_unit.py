"""
Unit tests for async/sync bridging using AsyncBridge - basic adapter patterns.

This module contains unit tests for basic AsyncBridge adapter functionality,
including method calls, exception handling, and sync/async bridging patterns.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import asyncio
from unittest.mock import MagicMock

import pytest

from ClassicLib.AsyncBridge import AsyncBridge

pytestmark = pytest.mark.unit


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

        with pytest.raises(ValueError, match="Async error"):
            bridge.run_async(async_obj.failing_method())

    def test_async_bridge_with_args_kwargs(self):
        """Test AsyncBridge with various argument patterns"""

        class AsyncComponent:
            async def method_with_args(self, a, b, c=10):
                return a + b + c

        async_obj = AsyncComponent()
        bridge = AsyncBridge.get_instance()

        result = bridge.run_async(async_obj.method_with_args(1, 2, c=3))
        assert result == 6

        result = bridge.run_async(async_obj.method_with_args(5, 10))
        assert result == 25

    def test_sync_adapter_pattern_with_bridge(self):
        """Test creating sync adapters using AsyncBridge"""

        class AsyncCore:
            async def process(self, data):
                await asyncio.sleep(0.001)
                return data.upper()

            async def calculate(self, x, y):
                return x + y

        class SyncAdapter:
            def __init__(self):
                self.core = AsyncCore()
                self.bridge = AsyncBridge.get_instance()

            def process(self, data):
                return self.bridge.run_async(self.core.process(data))

            def calculate(self, x, y):
                return self.bridge.run_async(self.core.calculate(x, y))

        adapter = SyncAdapter()
        assert adapter.process("hello") == "HELLO"
        assert adapter.calculate(3, 4) == 7

    def test_mixed_sync_async_component(self):
        """Test component with both sync and async methods"""

        class MixedComponent:
            def sync_method(self):
                return "sync"

            async def async_method(self):
                await asyncio.sleep(0.001)
                return "async"

        component = MixedComponent()
        bridge = AsyncBridge.get_instance()

        # Sync method works normally
        assert component.sync_method() == "sync"

        # Async method needs bridge
        assert bridge.run_async(component.async_method()) == "async"


class TestHybridPattern:
    """Test hybrid sync/async patterns"""

    def test_hybrid_pattern_sync_call(self):
        """Test hybrid pattern called from sync context"""

        class HybridService:
            def __init__(self):
                self.bridge = AsyncBridge.get_instance()

            async def _async_process(self, data):
                await asyncio.sleep(0.001)
                return data * 2

            def process(self, data):
                """Public sync API that uses async internally"""
                return self.bridge.run_async(self._async_process(data))

        service = HybridService()
        result = service.process(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_hybrid_pattern_async_call(self):
        """Test hybrid pattern called from async context"""

        class HybridService:
            async def async_process(self, data):
                await asyncio.sleep(0.001)
                return data * 2

        service = HybridService()
        result = await service.async_process(5)
        assert result == 10

    def test_hybrid_pattern_with_class_state(self):
        """Test hybrid pattern with stateful class"""

        class StatefulHybrid:
            def __init__(self):
                self.bridge = AsyncBridge.get_instance()
                self.counter = 0

            async def _async_increment(self):
                await asyncio.sleep(0.001)
                self.counter += 1
                return self.counter

            def increment(self):
                return self.bridge.run_async(self._async_increment())

        hybrid = StatefulHybrid()
        assert hybrid.increment() == 1
        assert hybrid.increment() == 2
        assert hybrid.counter == 2

    def test_hybrid_pattern_exception_handling(self):
        """Test exception handling in hybrid pattern"""

        class HybridWithErrors:
            def __init__(self):
                self.bridge = AsyncBridge.get_instance()

            async def _async_may_fail(self, should_fail):
                if should_fail:
                    raise RuntimeError("Async failure")
                return "success"

            def may_fail(self, should_fail):
                return self.bridge.run_async(self._async_may_fail(should_fail))

        hybrid = HybridWithErrors()
        assert hybrid.may_fail(False) == "success"

        with pytest.raises(RuntimeError, match="Async failure"):
            hybrid.may_fail(True)


if __name__ == "__main__":
    pytest.main([__file__])
