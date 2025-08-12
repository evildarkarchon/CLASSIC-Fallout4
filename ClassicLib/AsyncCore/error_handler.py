"""Async error handling framework for CLASSIC"""

import asyncio
import logging
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorSeverity(Enum):
    """Error severity levels"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AsyncExecutionError(Exception):
    """Custom exception for async execution errors"""

    message: str
    original_error: Exception | None = None
    context: dict | None = None
    severity: ErrorSeverity = ErrorSeverity.ERROR
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        super().__init__(self.message)

    def __str__(self):
        msg = f"[{self.severity.value.upper()}] {self.message}"
        if self.original_error:
            msg += f"\nOriginal error: {self.original_error}"
        if self.context:
            msg += f"\nContext: {self.context}"
        return msg


class AsyncErrorHandler:
    """Centralized error handling for async operations"""

    def __init__(self):
        self._error_callbacks = []
        self._error_history = []
        self._max_history = 100

    def register_callback(self, callback: Callable[[AsyncExecutionError], None]):
        """Register a callback to be called on errors"""
        self._error_callbacks.append(callback)

    async def handle_error(self, error: Exception, context: dict | None = None, severity: ErrorSeverity = ErrorSeverity.ERROR) -> None:
        """Handle an error with logging and callbacks"""
        # Create structured error
        exec_error = AsyncExecutionError(message=str(error), original_error=error, context=context, severity=severity)

        # Add to history
        self._error_history.append(exec_error)
        if len(self._error_history) > self._max_history:
            self._error_history.pop(0)

        # Log based on severity
        log_func = getattr(logger, severity.value, logger.error)
        log_func(str(exec_error))

        if severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            logger.debug(traceback.format_exc())

        # Call registered callbacks
        for callback in self._error_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(exec_error)
                else:
                    callback(exec_error)
            except Exception as cb_error:
                logger.error(f"Error in error callback: {cb_error}")

    async def safe_execute(self, coro: Callable, default: Any = None, context: dict | None = None, reraise: bool = False) -> Any:
        """Execute a coroutine safely with error handling

        Args:
            coro: Coroutine to execute
            default: Default value to return on error
            context: Additional context for error reporting
            reraise: Whether to re-raise the exception after handling

        Returns:
            Result of coroutine or default value on error
        """
        try:
            if asyncio.iscoroutinefunction(coro):
                return await coro()
            return await coro
        except Exception as e:
            await self.handle_error(e, context=context)
            if reraise:
                raise
            return default

    def safe_task(self, coro: Callable, name: str | None = None, context: dict | None = None) -> asyncio.Task:
        """Create a task with built-in error handling

        Args:
            coro: Coroutine to run as task
            name: Optional name for the task
            context: Additional context for error reporting

        Returns:
            Created task
        """

        async def wrapped():
            try:
                if asyncio.iscoroutinefunction(coro):
                    return await coro()
                return await coro
            except Exception as e:
                await self.handle_error(e, context=context)
                raise

        task = asyncio.create_task(wrapped())
        if name:
            task.set_name(name)
        return task

    def get_error_history(self, severity: ErrorSeverity | None = None) -> list[AsyncExecutionError]:
        """Get error history, optionally filtered by severity"""
        if severity:
            return [e for e in self._error_history if e.severity == severity]
        return self._error_history.copy()

    def clear_history(self):
        """Clear error history"""
        self._error_history.clear()


def async_error_handler(default: Any = None, severity: ErrorSeverity = ErrorSeverity.ERROR, reraise: bool = False):
    """Decorator for async functions with error handling

    Args:
        default: Default value to return on error
        severity: Error severity level
        reraise: Whether to re-raise the exception after handling

    Example:
        @async_error_handler(default=[], severity=ErrorSeverity.WARNING)
        async def get_files():
            # This will return [] on error and log as warning
            ...
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error = AsyncExecutionError(
                    message=f"Error in {func.__name__}: {e!s}",
                    original_error=e,
                    context={"args": args, "kwargs": kwargs},
                    severity=severity,
                )

                log_func = getattr(logger, severity.value, logger.error)
                log_func(str(error))

                if severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
                    logger.debug(traceback.format_exc())

                if reraise:
                    raise
                return default

        return wrapper

    return decorator


class AsyncRetryError(AsyncExecutionError):
    """Error raised when retry attempts are exhausted"""


async def retry_async(
    func: Callable, max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions: tuple = (Exception,)
) -> Any:
    """Retry an async function with exponential backoff

    Args:
        func: Async function to retry
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts in seconds
        backoff: Backoff multiplier for delay
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Result of successful function call

    Raises:
        AsyncRetryError: When all retry attempts are exhausted
    """
    last_error = None
    current_delay = delay

    for attempt in range(max_attempts):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func()
            return await func
        except exceptions as e:
            last_error = e
            if attempt < max_attempts - 1:
                logger.debug(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
                await asyncio.sleep(current_delay)
                current_delay *= backoff
            else:
                break

    raise AsyncRetryError(
        message=f"All {max_attempts} retry attempts failed",
        original_error=last_error,
        context={"function": func.__name__ if hasattr(func, "__name__") else str(func), "max_attempts": max_attempts},
    )


class AsyncCircuitBreaker:
    """Circuit breaker pattern for async operations

    Prevents repeated calls to failing services.
    """

    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0, half_open_attempts: int = 1):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_attempts = half_open_attempts

        self._failure_count = 0
        self._last_failure_time = None
        self._state = "closed"  # closed, open, half-open
        self._half_open_count = 0

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function through circuit breaker

        Raises:
            AsyncExecutionError: When circuit is open
        """
        if self._state == "open":
            if self._last_failure_time:
                time_since_failure = asyncio.get_event_loop().time() - self._last_failure_time
                if time_since_failure > self.timeout:
                    self._state = "half-open"
                    self._half_open_count = 0
                else:
                    raise AsyncExecutionError(
                        message="Circuit breaker is open",
                        severity=ErrorSeverity.WARNING,
                        context={"time_until_retry": self.timeout - time_since_failure},
                    )

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = await func

            # Success - reset on successful call
            if self._state == "half-open":
                self._half_open_count += 1
                if self._half_open_count >= self.half_open_attempts:
                    self._state = "closed"
                    self._failure_count = 0
                    logger.info("Circuit breaker closed after successful calls")
            elif self._state == "closed":
                self._failure_count = 0

            return result

        except Exception:
            self._failure_count += 1
            self._last_failure_time = asyncio.get_event_loop().time()

            if self._state == "half-open":
                self._state = "open"
                logger.warning("Circuit breaker reopened after failure in half-open state")
            elif self._failure_count >= self.failure_threshold:
                self._state = "open"
                logger.warning(f"Circuit breaker opened after {self._failure_count} failures")

            raise

    @property
    def is_open(self) -> bool:
        """Check if circuit breaker is open"""
        return self._state == "open"

    @property
    def state(self) -> str:
        """Get current state of circuit breaker"""
        return self._state

    def reset(self):
        """Manually reset circuit breaker"""
        self._state = "closed"
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_count = 0
