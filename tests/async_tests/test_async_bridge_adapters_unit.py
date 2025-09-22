"""
Unit tests for async/sync bridging using AsyncBridge - basic adapter patterns.

This module contains unit tests for basic AsyncBridge adapter functionality,
including method calls, exception handling, and sync/async bridging patterns.

IMPORTANT: This module avoids using the name 'AsyncCore' to prevent confusion
with the deprecated AsyncCore module. All async components are clearly named
to indicate their purpose.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import asyncio
from unittest.mock import MagicMock

import pytest

from ClassicLib.AsyncBridge import AsyncBridge

pytestmark = pytest.mark.unit


class TestAsyncBridgeAdapter:
    """Test AsyncBridge adapter patterns.

    These tests demonstrate correct patterns for creating sync adapters
    that wrap async components using AsyncBridge.
    """

    def test_async_bridge_basic(self):
        """Test basic AsyncBridge functionality with async methods.

        Demonstrates direct use of AsyncBridge to call async methods
        from synchronous context.
        """

        class AsyncComponent:
            """Example component with async methods."""
            async def async_method(self, value):
                await asyncio.sleep(0.001)
                return value * 2

            async def async_property(self):
                return "async_value"

        async_obj = AsyncComponent()
        bridge = AsyncBridge.get_instance()

        # Test method call through bridge
        result = bridge.run_async(async_obj.async_method(5))
        assert result == 10

        # Test property access through bridge
        prop_value = bridge.run_async(async_obj.async_property())
        assert prop_value == "async_value"

    def test_async_bridge_with_exceptions(self):
        """Test AsyncBridge exception handling.

        Verifies that exceptions raised in async code are properly
        propagated through the bridge to sync code.
        """

        class AsyncComponent:
            """Component with failing async method."""
            async def failing_method(self):
                raise ValueError("Async error")

        async_obj = AsyncComponent()
        bridge = AsyncBridge.get_instance()

        # Exceptions should propagate through the bridge
        with pytest.raises(ValueError, match="Async error"):
            bridge.run_async(async_obj.failing_method())

    def test_async_bridge_with_args_kwargs(self):
        """Test AsyncBridge with various argument patterns.

        Ensures that positional and keyword arguments are correctly
        passed through the bridge to async methods.
        """

        class AsyncComponent:
            """Component with parameterized async method."""
            async def method_with_args(self, a, b, c=10):
                return a + b + c

        async_obj = AsyncComponent()
        bridge = AsyncBridge.get_instance()

        # Test with all arguments specified
        result = bridge.run_async(async_obj.method_with_args(1, 2, c=3))
        assert result == 6

        # Test with default argument
        result = bridge.run_async(async_obj.method_with_args(5, 10))
        assert result == 25

    def test_sync_adapter_pattern_with_bridge(self):
        """Test creating sync adapters using AsyncBridge.

        This demonstrates the CORRECT pattern for wrapping async components
        with sync interfaces. Note: We use 'AsyncBusinessLogic' instead of
        'AsyncCore' to avoid confusion with the deprecated AsyncCore module.
        """

        class AsyncBusinessLogic:
            """Example async business logic component.

            This represents the async core implementation that needs
            to be wrapped for synchronous use.
            """
            async def process(self, data):
                """Async processing method."""
                await asyncio.sleep(0.001)
                return data.upper()

            async def calculate(self, x, y):
                """Async calculation method."""
                return x + y

        class SyncAdapter:
            """Synchronous adapter for async business logic.

            This adapter provides a sync interface to async functionality
            using AsyncBridge. This is the recommended pattern for exposing
            async code to sync callers.
            """
            def __init__(self):
                # Initialize the async component
                self.async_logic = AsyncBusinessLogic()
                # Get bridge instance for sync/async conversion
                self.bridge = AsyncBridge.get_instance()

            def process(self, data):
                """Sync wrapper for async process method."""
                return self.bridge.run_async(self.async_logic.process(data))

            def calculate(self, x, y):
                """Sync wrapper for async calculate method."""
                return self.bridge.run_async(self.async_logic.calculate(x, y))

        # Test the adapter pattern
        adapter = SyncAdapter()
        assert adapter.process("hello") == "HELLO"
        assert adapter.calculate(3, 4) == 7

    def test_mixed_sync_async_component(self):
        """Test component with both sync and async methods.

        Shows how to handle components that have a mix of synchronous
        and asynchronous methods.
        """

        class MixedComponent:
            """Component with both sync and async methods."""
            def sync_method(self):
                """Regular synchronous method."""
                return "sync"

            async def async_method(self):
                """Asynchronous method."""
                await asyncio.sleep(0.001)
                return "async"

        component = MixedComponent()
        bridge = AsyncBridge.get_instance()

        # Sync method works normally without bridge
        assert component.sync_method() == "sync"

        # Async method needs bridge when called from sync context
        assert bridge.run_async(component.async_method()) == "async"


class TestHybridPattern:
    """Test hybrid sync/async patterns.

    These tests demonstrate patterns for components that need to support
    both synchronous and asynchronous usage.
    """

    def test_hybrid_pattern_sync_call(self):
        """Test hybrid pattern called from sync context.

        Shows how to create a service that can be used synchronously
        but leverages async operations internally.
        """

        class HybridService:
            """Service with both sync and async interfaces."""
            def __init__(self):
                self.bridge = AsyncBridge.get_instance()

            async def _async_process(self, data):
                """Internal async implementation."""
                await asyncio.sleep(0.001)
                return data * 2

            def process(self, data):
                """Public sync API that uses async internally.

                This method provides a synchronous interface but uses
                the async implementation through AsyncBridge.
                """
                return self.bridge.run_async(self._async_process(data))

        service = HybridService()
        result = service.process(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_hybrid_pattern_async_call(self):
        """Test hybrid pattern called from async context.

        When in an async context, we can call async methods directly
        without needing the bridge.
        """

        class HybridService:
            """Service with async methods."""
            async def async_process(self, data):
                """Async processing method."""
                await asyncio.sleep(0.001)
                return data * 2

        service = HybridService()
        # In async context, call directly without bridge
        result = await service.async_process(5)
        assert result == 10

    def test_hybrid_pattern_with_class_state(self):
        """Test hybrid pattern with stateful class.

        Demonstrates that AsyncBridge correctly handles stateful
        operations across multiple calls.
        """

        class StatefulHybrid:
            """Hybrid service with internal state."""
            def __init__(self):
                self.bridge = AsyncBridge.get_instance()
                self.counter = 0

            async def _async_increment(self):
                """Async method that modifies state."""
                await asyncio.sleep(0.001)
                self.counter += 1
                return self.counter

            def increment(self):
                """Sync wrapper for stateful async operation."""
                return self.bridge.run_async(self._async_increment())

        hybrid = StatefulHybrid()
        # State is maintained across bridge calls
        assert hybrid.increment() == 1
        assert hybrid.increment() == 2
        assert hybrid.counter == 2

    def test_hybrid_pattern_exception_handling(self):
        """Test exception handling in hybrid pattern.

        Verifies that exceptions are properly propagated through
        the hybrid sync/async interface.
        """

        class HybridWithErrors:
            """Hybrid service that can raise exceptions."""
            def __init__(self):
                self.bridge = AsyncBridge.get_instance()

            async def _async_may_fail(self, should_fail):
                """Async method that may raise an exception."""
                if should_fail:
                    raise RuntimeError("Async failure")
                return "success"

            def may_fail(self, should_fail):
                """Sync wrapper that propagates exceptions."""
                return self.bridge.run_async(self._async_may_fail(should_fail))

        hybrid = HybridWithErrors()
        # Success case
        assert hybrid.may_fail(False) == "success"

        # Exception propagation
        with pytest.raises(RuntimeError, match="Async failure"):
            hybrid.may_fail(True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
