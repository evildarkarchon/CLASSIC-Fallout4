"""
Tests for async error handling components.

This module contains tests for error handling, retry logic, and circuit breaker
patterns used in the async pipeline.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from ClassicLib.AsyncCore import (
    AsyncErrorHandler,
    AsyncExecutionError,
    ErrorSeverity,
)
from ClassicLib.AsyncCore.error_handler import AsyncCircuitBreaker, retry_async


class TestAsyncErrorHandler:
    """Test AsyncErrorHandler class"""

    @pytest.mark.asyncio
    async def test_error_logging(self):
        """Test error logging functionality"""
        handler = AsyncErrorHandler()
        error = ValueError("Test error")

        await handler.handle_error(error, context={"context": "test_context"})
        assert len(handler.get_error_history()) == 1

        error_record = handler.get_error_history()[0]
        assert error_record.original_error == error
        assert error_record.context == {"context": "test_context"}
        assert error_record.severity == ErrorSeverity.ERROR

    @pytest.mark.asyncio
    async def test_error_severity_levels(self):
        """Test different error severity levels"""
        handler = AsyncErrorHandler()

        await handler.handle_error(
            ValueError("Warning"), context={"test": "context"}, severity=ErrorSeverity.WARNING
        )
        await handler.handle_error(
            RuntimeError("Error"), context={"test": "context"}, severity=ErrorSeverity.ERROR
        )
        await handler.handle_error(
            Exception("Critical"), context={"test": "context"}, severity=ErrorSeverity.CRITICAL
        )

        errors = handler.get_error_history()
        assert len(errors) == 3
        assert errors[0].severity == ErrorSeverity.WARNING
        assert errors[1].severity == ErrorSeverity.ERROR
        assert errors[2].severity == ErrorSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_error_callback(self):
        """Test error callback functionality"""
        callback_called = False
        callback_error = None

        async def error_callback(exec_error):
            nonlocal callback_called, callback_error
            callback_called = True
            callback_error = exec_error

        handler = AsyncErrorHandler()
        handler.register_callback(error_callback)

        test_error = ValueError("Test")
        await handler.handle_error(test_error, context={"test": "context"})

        assert callback_called
        assert callback_error.original_error == test_error

    @pytest.mark.asyncio
    async def test_clear_errors(self):
        """Test clearing error history"""
        handler = AsyncErrorHandler()

        await handler.handle_error(ValueError("Error 1"))
        await handler.handle_error(ValueError("Error 2"))
        assert len(handler.get_error_history()) == 2

        handler.clear_history()
        assert len(handler.get_error_history()) == 0

    @pytest.mark.asyncio
    async def test_get_errors_by_severity(self):
        """Test filtering errors by severity"""
        handler = AsyncErrorHandler()

        await handler.handle_error(ValueError("W1"), severity=ErrorSeverity.WARNING)
        await handler.handle_error(ValueError("E1"), severity=ErrorSeverity.ERROR)
        await handler.handle_error(ValueError("W2"), severity=ErrorSeverity.WARNING)
        await handler.handle_error(ValueError("C1"), severity=ErrorSeverity.CRITICAL)

        # Get filtered errors using get_error_history with severity filter
        warnings = handler.get_error_history(severity=ErrorSeverity.WARNING)
        assert len(warnings) == 2

        critical = handler.get_error_history(severity=ErrorSeverity.CRITICAL)
        assert len(critical) == 1


class TestAsyncRetry:
    """Test async retry functionality"""

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry logic on failure"""
        attempt_count = 0

        async def flaky_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary failure")
            return "Success"

        # retry_async is a function, not a decorator
        result = await retry_async(flaky_function, max_attempts=3, delay=0.01)
        assert result == "Success"
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_retry_max_attempts_exceeded(self):
        """Test retry when max attempts exceeded"""

        async def always_fails():
            raise ValueError("Always fails")

        # Import AsyncRetryError for the correct exception type
        from ClassicLib.AsyncCore.error_handler import AsyncRetryError

        with pytest.raises(AsyncRetryError) as exc_info:
            await retry_async(always_fails, max_attempts=2, delay=0.01)

        assert "retry attempts failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self):
        """Test retry with exponential backoff"""
        attempt_times = []

        async def track_timing():
            nonlocal attempt_times
            attempt_times.append(asyncio.get_event_loop().time())
            if len(attempt_times) < 3:
                raise ValueError("Retry needed")
            return "Success"

        # Use backoff parameter for exponential backoff (not exponential_backoff)
        result = await retry_async(track_timing, max_attempts=3, delay=0.01, backoff=2.0)
        assert result == "Success"
        assert len(attempt_times) == 3

        # Check that delays increase exponentially
        if len(attempt_times) >= 3:
            delay1 = attempt_times[1] - attempt_times[0]
            delay2 = attempt_times[2] - attempt_times[1]
            # Second delay should be roughly twice the first (with backoff=2.0)
            assert delay2 > delay1 * 1.5

    @pytest.mark.asyncio
    async def test_retry_specific_exceptions(self):
        """Test retry only on specific exception types"""

        async def selective_retry():
            raise TypeError("Should not retry")

        # Use exceptions parameter (not retry_on)
        with pytest.raises(TypeError):
            await retry_async(selective_retry, max_attempts=3, delay=0.01, exceptions=(ValueError,))


class TestAsyncCircuitBreaker:
    """Test AsyncCircuitBreaker class"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens(self):
        """Test circuit breaker opens after failures"""
        breaker = AsyncCircuitBreaker(failure_threshold=2, timeout=0.1)

        async def failing_func():
            raise ValueError("Failure")

        # First two failures should work
        for _ in range(2):
            with pytest.raises(ValueError):
                await breaker.call(failing_func)

        # Circuit should now be open
        with pytest.raises(AsyncExecutionError) as exc_info:
            await breaker.call(failing_func)
        assert "Circuit breaker is open" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout"""
        breaker = AsyncCircuitBreaker(failure_threshold=1, timeout=0.05)

        async def failing_then_success():
            if breaker._failure_count == 0:
                raise ValueError("First failure")
            return "Success"

        # Trigger circuit open
        with pytest.raises(ValueError):
            await breaker.call(failing_then_success)

        # Circuit should be open
        with pytest.raises(AsyncExecutionError):
            await breaker.call(failing_then_success)

        # Wait for recovery timeout
        await asyncio.sleep(0.06)

        # Circuit should be half-open, next call should succeed
        result = await breaker.call(failing_then_success)
        assert result == "Success"

    @pytest.mark.asyncio
    async def test_circuit_breaker_success_resets(self):
        """Test that successful calls reset the failure count"""
        breaker = AsyncCircuitBreaker(failure_threshold=3)
        call_count = 0

        async def sometimes_fails():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Failure")
            return f"Success {call_count}"

        # First call fails
        with pytest.raises(ValueError):
            await breaker.call(sometimes_fails)

        # Second call succeeds and should reset failure count
        result = await breaker.call(sometimes_fails)
        assert "Success" in result
        assert breaker._failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_state(self):
        """Test circuit breaker half-open state behavior"""
        breaker = AsyncCircuitBreaker(failure_threshold=1, timeout=0.05)

        async def test_func():
            return "Success"

        # Open the circuit
        async def fail_func():
            raise ValueError("Fail")

        with pytest.raises(ValueError):
            await breaker.call(fail_func)

        # Circuit is now open (use property, not _is_open)
        assert breaker.is_open

        # Wait for recovery
        await asyncio.sleep(0.06)

        # Circuit should be half-open, successful call should close it
        result = await breaker.call(test_func)
        assert result == "Success"
        assert not breaker.is_open
        assert breaker._failure_count == 0
