"""
Tests for AsyncBridge Phase 2: Context-Aware Wrappers.

Tests the context-aware functionality that automatically uses AsyncBridge
only in GUI mode, and allows native async in CLI/TUI modes.
"""

import asyncio
from unittest.mock import patch

import pytest

from ClassicLib.core.async_bridge import (
    context_aware_sync,
    smart_await,
)
from ClassicLib.core.registry import GlobalRegistry

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def cleanup_registry():
    """Clear GlobalRegistry before each test."""
    # Store original value if it exists
    original_gui_mode = GlobalRegistry.get(GlobalRegistry.Keys.IS_GUI_MODE)

    yield

    # Restore original value
    if original_gui_mode is not None:
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, original_gui_mode)
    elif GlobalRegistry.is_registered(GlobalRegistry.Keys.IS_GUI_MODE):
        # Remove the key if it wasn't there originally
        GlobalRegistry.unregister(GlobalRegistry.Keys.IS_GUI_MODE)


@pytest.mark.unit
class TestContextAwareSyncDecorator:
    """Test context_aware_sync decorator."""

    async def test_returns_async_function_in_cli_mode(self):
        """Test decorator returns original async function in CLI mode."""
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, False)

        @context_aware_sync
        async def async_function():
            return "result"

        # Function should still be async
        result = async_function()
        assert asyncio.iscoroutine(result)

        # Should be awaitable
        actual_result = await result
        assert actual_result == "result"

    def test_returns_sync_wrapper_in_gui_mode(self):
        """Test decorator returns sync wrapper in GUI mode."""
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, True)

        @context_aware_sync
        async def async_function():
            await asyncio.sleep(0.01)
            return "result"

        # Function should be sync
        result = async_function()
        assert not asyncio.iscoroutine(result)
        assert result == "result"

    async def test_preserves_function_metadata(self):
        """Test decorator preserves function name and docstring."""
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, False)

        @context_aware_sync
        async def my_function():
            """My docstring."""
            return "result"

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."

    async def test_handles_function_arguments(self):
        """Test decorator works with function arguments."""
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, False)

        @context_aware_sync
        async def async_function(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"

        result = await async_function("a", "b", kwarg1="c")  # type: ignore[misc]
        assert result == "a-b-c"

    def test_sync_wrapper_handles_arguments_in_gui_mode(self):
        """Test sync wrapper handles arguments correctly."""
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, True)

        @context_aware_sync
        async def async_function(arg1, arg2, kwarg1=None):
            await asyncio.sleep(0.01)
            return f"{arg1}-{arg2}-{kwarg1}"

        result = async_function("a", "b", kwarg1="c")
        assert result == "a-b-c"


@pytest.mark.unit
class TestSmartAwait:
    """Test smart_await function."""

    def test_smart_await_works_in_gui_mode(self):
        """Test smart_await uses AsyncBridge in GUI mode."""
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, True)

        async def async_function():
            await asyncio.sleep(0.01)
            return "result"

        result = smart_await(async_function())
        assert result == "result"

    def test_smart_await_errors_in_cli_mode(self):
        """Test smart_await raises error in CLI mode."""
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, False)

        async def async_function():
            return "result"

        coro = async_function()
        with pytest.raises(RuntimeError, match="Cannot use smart_await.*CLI/TUI mode"):
            smart_await(coro)
        coro.close()

    def test_smart_await_error_message_suggests_await(self):
        """Test error message suggests using native 'await'."""
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, False)

        async def async_function():
            return "result"

        coro = async_function()
        with pytest.raises(RuntimeError, match="Use native 'await' instead"):
            smart_await(coro)
        coro.close()


@pytest.mark.integration
class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_migration_pattern_before_after(self):
        """Test migration from Phase 1 to Phase 2 pattern."""

        # BEFORE: Always uses AsyncBridge (Phase 1)
        class OldImplementation:
            async def _async_method(self):
                await asyncio.sleep(0.01)
                return "result"

            def method(self):
                """Always uses AsyncBridge."""
                from ClassicLib.core.async_bridge import run_async

                return run_async(self._async_method())

        # AFTER: Context-aware (Phase 2)
        class NewImplementation:
            @context_aware_sync
            async def method(self):
                """Context-aware."""
                await asyncio.sleep(0.01)
                return "result"

        # Test old implementation (works in both modes, but always uses bridge)
        old = OldImplementation()
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, True)
        assert old.method() == "result"

        # Test new implementation in GUI mode
        new = NewImplementation()
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, True)
        assert new.method() == "result"

        # Test new implementation in CLI mode (returns coroutine, need to run it)
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, False)
        result = asyncio.run(new.method())  # type: ignore[arg-type]
        assert result == "result"

    def test_context_detection_in_method(self):
        """Test using context detection inside methods."""

        class SmartClass:
            async def _async_implementation(self, data):
                await asyncio.sleep(0.01)
                return f"async: {data}"

            def smart_method(self, data):
                """Adapts based on context."""
                if GlobalRegistry.is_gui_mode():
                    # GUI mode - use bridge
                    from ClassicLib.core.async_bridge import run_async

                    return run_async(self._async_implementation(data))

                # CLI/TUI mode - error, should use async version
                msg = "Use async version in CLI/TUI mode"
                raise RuntimeError(msg)

        obj = SmartClass()

        # GUI mode - sync wrapper works
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, True)
        result = obj.smart_method("test")
        assert result == "async: test"

        # CLI mode - errors appropriately
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, False)
        with pytest.raises(RuntimeError, match="async version"):
            obj.smart_method("test")


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in Phase 2 functionality."""

    async def test_context_aware_sync_propagates_exceptions_in_cli_mode(self):
        """Test decorator propagates exceptions in CLI mode."""
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, False)

        @context_aware_sync
        async def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await failing_function()

    def test_context_aware_sync_propagates_exceptions_in_gui_mode(self):
        """Test decorator propagates exceptions in GUI mode."""
        GlobalRegistry.register(GlobalRegistry.Keys.IS_GUI_MODE, True)

        @context_aware_sync
        async def failing_function():
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_function()  # type: ignore
