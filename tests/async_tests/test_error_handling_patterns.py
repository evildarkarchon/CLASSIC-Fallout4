"""
Tests for error handling patterns without AsyncCore.

This module demonstrates how to implement error handling, retry logic,
and circuit breaker patterns without relying on deprecated AsyncCore components.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from unittest.mock import AsyncMock

import pytest


class ErrorSeverity(Enum):
    """Error severity levels"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorRecord:
    """Record of an error occurrence"""

    message: str
    error: Exception
    severity: ErrorSeverity
    context: dict
    timestamp: datetime


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
    async def test_error_logging_pattern(self):
        """Test error logging with context"""

        class ErrorLogger:
            def __init__(self):
                self.errors = []

            def log_error(self, error: Exception, context: dict, severity: ErrorSeverity):
                record = ErrorRecord(
                    message=str(error),
                    error=error,
                    severity=severity,
                    context=context,
                    timestamp=datetime.now(),
                )
                self.errors.append(record)

                # Log to Python logger
                logger = logging.getLogger(__name__)
                log_method = getattr(logger, severity.value, logger.error)
                log_method(f"{record.message} - Context: {context}")

            def get_errors_by_severity(self, severity: ErrorSeverity):
                return [e for e in self.errors if e.severity == severity]

        logger = ErrorLogger()

        # Log different severity errors
        logger.log_error(ValueError("Warning"), {"component": "test"}, ErrorSeverity.WARNING)
        logger.log_error(RuntimeError("Error"), {"component": "test"}, ErrorSeverity.ERROR)
        logger.log_error(Exception("Critical"), {"component": "test"}, ErrorSeverity.CRITICAL)

        assert len(logger.errors) == 3
        assert len(logger.get_errors_by_severity(ErrorSeverity.WARNING)) == 1
        assert len(logger.get_errors_by_severity(ErrorSeverity.ERROR)) == 1
        assert len(logger.get_errors_by_severity(ErrorSeverity.CRITICAL)) == 1

    @pytest.mark.asyncio
    async def test_error_callback_pattern(self):
        """Test error callback pattern"""

        class ErrorHandler:
            def __init__(self):
                self.callbacks = []

            def register_callback(self, callback):
                self.callbacks.append(callback)

            async def handle_error(self, error: Exception, context: dict = None):
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

            raise last_error

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
                    raise last_error

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

    @pytest.mark.asyncio
    async def test_retry_with_specific_exceptions(self):
        """Test retry only on specific exceptions"""

        async def selective_retry(func, exceptions=(ValueError,), max_attempts=3, delay=0.01):
            for attempt in range(max_attempts):
                try:
                    return await func()
                except exceptions as e:
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay)
                    else:
                        raise
                except Exception:
                    # Don't retry other exceptions
                    raise

        async def function_with_different_errors():
            # This would not be retried
            raise RuntimeError("Different error")

        with pytest.raises(RuntimeError):
            await selective_retry(function_with_different_errors)


class TestCircuitBreakerPattern:
    """Test circuit breaker pattern implementation"""

    @pytest.mark.asyncio
    async def test_simple_circuit_breaker(self):
        """Test simple circuit breaker implementation"""

        class CircuitBreaker:
            def __init__(self, failure_threshold=3, timeout=1.0):
                self.failure_threshold = failure_threshold
                self.timeout = timeout
                self.failure_count = 0
                self.last_failure_time = None
                self.state = "closed"  # closed, open, half-open

            async def call(self, func, *args, **kwargs):
                if self.state == "open":
                    if self.last_failure_time:
                        elapsed = asyncio.get_event_loop().time() - self.last_failure_time
                        if elapsed > self.timeout:
                            self.state = "half-open"
                        else:
                            raise RuntimeError("Circuit breaker is open")

                try:
                    result = await func(*args, **kwargs)
                    if self.state == "half-open":
                        self.state = "closed"
                        self.failure_count = 0
                    return result
                except Exception as e:
                    self.failure_count += 1
                    self.last_failure_time = asyncio.get_event_loop().time()

                    if self.failure_count >= self.failure_threshold:
                        self.state = "open"
                    raise e

        breaker = CircuitBreaker(failure_threshold=2, timeout=0.1)
        call_count = 0

        async def unreliable_service():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError("Service error")
            return "Success"

        # First two calls fail
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(unreliable_service)

        # Circuit should be open now
        assert breaker.state == "open"

        # Next call should fail immediately
        with pytest.raises(RuntimeError) as exc_info:
            await breaker.call(unreliable_service)
        assert "Circuit breaker is open" in str(exc_info.value)

        # Wait for timeout
        await asyncio.sleep(0.11)

        # Circuit should allow retry (half-open)
        result = await breaker.call(unreliable_service)
        assert result == "Success"
        assert breaker.state == "closed"


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
                    # Can't return value from context manager
                    # This pattern is for logging/cleanup only
                    pass
                else:
                    raise

        # Success case
        async with error_handler():
            result = 1 + 1
            assert result == 2

        # Error case with re-raise
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

        # Error case - cleanup should still happen
        with pytest.raises(ValueError):
            async with managed_resource() as resource:
                assert resource["active"]
                raise ValueError("Error during operation")

        assert cleanup_called
