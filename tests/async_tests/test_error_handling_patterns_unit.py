"""
Unit tests for error_handling_patterns - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

# IMPORTANT: Async Test Pattern Documentation
# ============================================
# This test file follows correct AsyncBridge patterns:
# 1. For sync wrappers using AsyncBridge: Mock bridge.run_async(), not the async function
# 2. For pure async tests: Use @pytest.mark.asyncio and real async/await
# 3. Never use AsyncMock for methods called through AsyncBridge
# 4. See docs/async_test_patterns_guide.md for comprehensive patterns

import asyncio
import logging
from contextlib import asynccontextmanager

import pytest

pytestmark = pytest.mark.unit


class TestStandardErrorHandling:
    """Test standard Python error handling patterns"""

    @pytest.mark.asyncio
    async def test_basic_error_handling(self):
        """Test basic try/except error handling"""

        async def risky_operation():
            raise ValueError("Something went wrong")

        async def safe_operation():
            try:
                return await risky_operation()
            except ValueError as e:
                logging.error(f"Operation failed: {e}")
                return None

        result = await safe_operation()
        assert result is None

    @pytest.mark.asyncio
    async def test_error_callback_pattern(self):
        """Test error callback pattern"""

        class ErrorHandler:
            def __init__(self):
                self.callbacks = []

            def register_callback(self, callback):
                self.callbacks.append(callback)

            async def handle_error(self, error: Exception, context: dict | None = None):
                for callback in self.callbacks:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(error, context)
                    else:
                        callback(error, context)

        handler = ErrorHandler()
        callback_called = False
        received_error = None

        async def error_callback(error, context):
            nonlocal callback_called, received_error
            callback_called = True
            received_error = error

        handler.register_callback(error_callback)
        test_error = ValueError("Test error")
        await handler.handle_error(test_error, {"test": "context"})
        assert callback_called
        assert received_error == test_error


class TestRetryPatterns:
    """Test retry patterns without AsyncCore"""

    @pytest.mark.asyncio
    async def test_simple_retry_pattern(self):
        """Test simple retry implementation"""

        async def retry_async(func, max_attempts=3, delay=0.1, backoff=2.0):
            """Simple retry implementation"""
            last_error = None
            current_delay = delay
            for attempt in range(max_attempts):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func()
                    return await func
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        raise
            raise last_error  # pyright: ignore[reportGeneralTypeIssues]

        attempt_count = 0

        async def flaky_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary failure")
            return "Success"

        result = await retry_async(flaky_function, max_attempts=3, delay=0.01)
        assert result == "Success"
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_decorator_retry_pattern(self):
        """Test retry as a decorator"""

        def async_retry(max_attempts=3, delay=0.1):

            def decorator(func):

                async def wrapper(*args, **kwargs):
                    last_error = None
                    for attempt in range(max_attempts):
                        try:
                            return await func(*args, **kwargs)
                        except Exception as e:
                            last_error = e
                            if attempt < max_attempts - 1:
                                await asyncio.sleep(delay)
                    raise last_error  # pyright: ignore[reportGeneralTypeIssues]

                return wrapper

            return decorator

        attempt_count = 0

        @async_retry(max_attempts=3, delay=0.01)
        async def flaky_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Temporary error")
            return "Success"

        result = await flaky_operation()
        assert result == "Success"
        assert attempt_count == 2


class TestAsyncContextManagers:
    """Test async context managers for error handling"""

    @pytest.mark.asyncio
    async def test_error_handling_context_manager(self):
        """Test context manager for error handling"""

        @asynccontextmanager
        async def error_handler(default_value=None, log_errors=True):
            try:
                yield
            except Exception as e:
                if log_errors:
                    logging.error(f"Error in context: {e}")
                if default_value is not None:
                    pass
                else:
                    raise

        async with error_handler():
            result = 1 + 1
            assert result == 2
        with pytest.raises(ValueError):
            async with error_handler():
                raise ValueError("Test error")

    @pytest.mark.asyncio
    async def test_resource_cleanup_on_error(self):
        """Test resource cleanup on error"""
        cleanup_called = False

        @asynccontextmanager
        async def managed_resource():
            resource = {"active": True}
            try:
                yield resource
            except Exception as e:
                logging.error(f"Error with resource: {e}")
                raise
            finally:
                nonlocal cleanup_called
                cleanup_called = True
                resource["active"] = False

        with pytest.raises(ValueError):
            async with managed_resource() as resource:
                assert resource["active"]
                raise ValueError("Error during operation")
        assert cleanup_called
