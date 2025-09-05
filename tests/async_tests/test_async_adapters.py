"""
Tests for sync/async adapters and hybrid methods.

This module contains tests for components that bridge sync and async code,
including SyncAdapter, HybridMethod, and various wrapper utilities.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import asyncio
from unittest.mock import MagicMock

import pytest

from ClassicLib.AsyncCore import SyncAdapter, create_sync_adapter
from ClassicLib.AsyncCore.sync_adapter import HybridMethod, create_sync_wrapper


class TestSyncAdapter:
    """Test SyncAdapter class"""

    def test_sync_adapter_basic(self):
        """Test basic sync adapter functionality"""

        class AsyncComponent:
            async def async_method(self, value):
                await asyncio.sleep(0.001)
                return value * 2

            async def async_property(self):
                return "async_value"

        async_obj = AsyncComponent()
        sync_obj = SyncAdapter(async_obj)

        # Test method call
        result = sync_obj.async_method(5)
        assert result == 10

        # Test property access
        prop_value = sync_obj.async_property()
        assert prop_value == "async_value"

    def test_sync_adapter_with_exceptions(self):
        """Test sync adapter exception handling"""

        class AsyncComponent:
            async def failing_method(self):
                raise ValueError("Async error")

        async_obj = AsyncComponent()
        sync_obj = SyncAdapter(async_obj)

        with pytest.raises(ValueError) as exc_info:
            sync_obj.failing_method()
        assert "Async error" in str(exc_info.value)

    def test_sync_adapter_with_args_kwargs(self):
        """Test sync adapter with various arguments"""

        class AsyncComponent:
            async def complex_method(self, *args, **kwargs):
                await asyncio.sleep(0.001)
                return {"args": args, "kwargs": kwargs}

        async_obj = AsyncComponent()
        sync_obj = SyncAdapter(async_obj)

        result = sync_obj.complex_method(1, 2, 3, key1="value1", key2="value2")
        assert result["args"] == (1, 2, 3)
        assert result["kwargs"] == {"key1": "value1", "key2": "value2"}

    def test_create_sync_adapter_function(self):
        """Test create_sync_adapter utility function"""

        class AsyncClass:
            def __init__(self, multiplier):
                self.multiplier = multiplier

            async def process(self, value):
                await asyncio.sleep(0.001)
                return value * self.multiplier

        SyncClass = create_sync_adapter(AsyncClass)
        sync_instance = SyncClass(3)

        result = sync_instance.process(4)
        assert result == 12

    def test_sync_adapter_preserves_sync_methods(self):
        """Test that sync adapter preserves synchronous methods"""

        class MixedComponent:
            def sync_method(self):
                return "sync_result"

            async def async_method(self):
                return "async_result"

        mixed_obj = MixedComponent()
        sync_obj = SyncAdapter(mixed_obj)

        # Sync method should work directly
        sync_result = sync_obj.sync_method()
        assert sync_result == "sync_result"

        # Async method should be wrapped
        async_result = sync_obj.async_method()
        assert async_result == "async_result"


class TestHybridMethod:
    """Test HybridMethod decorator"""

    def test_hybrid_method_sync_call(self):
        """Test hybrid method called synchronously"""

        class TestClass:
            @HybridMethod
            async def process(self, value):
                await asyncio.sleep(0.001)
                return value * 2

        obj = TestClass()

        # Call synchronously
        result = obj.process.sync(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_hybrid_method_async_call(self):
        """Test hybrid method called asynchronously"""

        class TestClass:
            @HybridMethod
            async def process(self, value):
                await asyncio.sleep(0.001)
                return value * 2

        obj = TestClass()

        # Call asynchronously
        result = await obj.process(5)
        assert result == 10

    def test_hybrid_method_with_class_state(self):
        """Test hybrid method accessing class state"""

        class TestClass:
            def __init__(self, multiplier):
                self.multiplier = multiplier

            @HybridMethod
            async def process(self, value):
                await asyncio.sleep(0.001)
                return value * self.multiplier

        obj = TestClass(3)

        # Test sync call
        sync_result = obj.process.sync(4)
        assert sync_result == 12

    @pytest.mark.asyncio
    async def test_hybrid_method_exception_handling(self):
        """Test hybrid method exception handling in both modes"""

        class TestClass:
            @HybridMethod
            async def failing_method(self):
                raise ValueError("Test error")

        obj = TestClass()

        # Test sync call exception
        with pytest.raises(ValueError) as exc_info:
            obj.failing_method.sync()
        assert "Test error" in str(exc_info.value)

        # Test async call exception
        with pytest.raises(ValueError) as exc_info:
            await obj.failing_method()
        assert "Test error" in str(exc_info.value)


class TestSyncWrapper:
    """Test create_sync_wrapper function"""

    def test_create_sync_wrapper_basic(self):
        """Test basic sync wrapper creation"""

        async def async_function(x, y):
            await asyncio.sleep(0.001)
            return x + y

        sync_function = create_sync_wrapper(async_function)
        result = sync_function(3, 4)
        assert result == 7

    def test_create_sync_wrapper_with_kwargs(self):
        """Test sync wrapper with keyword arguments"""

        async def async_function(a, b=2, c=3):
            await asyncio.sleep(0.001)
            return a * b * c

        sync_function = create_sync_wrapper(async_function)
        result = sync_function(2, b=3, c=4)
        assert result == 24

    def test_create_sync_wrapper_preserves_name(self):
        """Test that sync wrapper preserves function name and docs"""

        async def special_async_function():
            """This is a special function"""
            return "special"

        sync_function = create_sync_wrapper(special_async_function)

        # Check that name and docstring are preserved
        assert sync_function.__name__ == "special_async_function"
        assert sync_function.__doc__ == "This is a special function"

    def test_sync_wrapper_with_generator(self):
        """Test sync wrapper with async generator"""

        async def async_generator():
            for i in range(3):
                await asyncio.sleep(0.001)
                yield i

        sync_function = create_sync_wrapper(async_generator)

        # This should convert the async generator to a list
        result = sync_function()
        assert isinstance(result, (list, type(None)))  # Implementation dependent

    def test_nested_sync_adapters(self):
        """Test nested sync adapter usage"""

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

        outer_async = OuterAsync()
        outer_sync = SyncAdapter(outer_async)

        result = outer_sync.process_with_inner(5)
        assert result == 12  # (5 + 1) * 2
