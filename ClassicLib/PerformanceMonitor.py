"""
Performance monitoring utilities for tracking optimization improvements.

This module provides decorators and utilities for measuring and logging
performance metrics throughout the application, particularly for YAML
operations and async improvements.
"""

import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

from ClassicLib.Logger import logger

# Type variables for generic decorators
F = TypeVar("F", bound=Callable[..., Any])


def timed_operation(name: str | None = None, log_level: str = "info") -> Callable[[F], F]:
    """
    Decorator to time synchronous operations and log results.

    Args:
        name: Optional operation name (defaults to function name)
        log_level: Logging level ("debug", "info", "warning")

    Returns:
        Decorated function that logs execution time
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            operation_name = name or func.__name__
            start = time.perf_counter()

            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start

                # Log based on level
                log_msg = f"{operation_name} completed in {elapsed:.3f}s"
                if log_level == "debug":
                    logger.debug(log_msg)
                elif log_level == "warning":
                    logger.warning(log_msg)
                else:
                    logger.info(log_msg)

                # Store metrics for later analysis
                _store_metric(operation_name, elapsed)

                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(f"{operation_name} failed after {elapsed:.3f}s: {e}")
                raise

        return wrapper  # type: ignore

    return decorator


def async_timed_operation(name: str | None = None, log_level: str = "info") -> Callable[[F], F]:
    """
    Decorator to time async operations and log results.

    Args:
        name: Optional operation name (defaults to function name)
        log_level: Logging level ("debug", "info", "warning")

    Returns:
        Decorated async function that logs execution time
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            operation_name = name or func.__name__
            start = time.perf_counter()

            try:
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start

                # Log based on level
                log_msg = f"{operation_name} completed in {elapsed:.3f}s"
                if log_level == "debug":
                    logger.debug(log_msg)
                elif log_level == "warning":
                    logger.warning(log_msg)
                else:
                    logger.info(log_msg)

                # Store metrics for later analysis
                _store_metric(operation_name, elapsed)

                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(f"{operation_name} failed after {elapsed:.3f}s: {e}")
                raise

        return wrapper  # type: ignore

    return decorator


def batch_operation_monitor(operation_name: str) -> Callable[[F], F]:
    """
    Special decorator for monitoring batch operations.

    Logs both total time and average time per item for batch operations.

    Args:
        operation_name: Name of the batch operation

    Returns:
        Decorated function that logs batch performance metrics
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()

            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start

            # Try to determine batch size from result
            batch_size = 1
            if isinstance(result, (list, tuple)):
                batch_size = len(result)

            avg_time = elapsed / batch_size if batch_size > 0 else 0

            logger.info(f"{operation_name}: {batch_size} items in {elapsed:.3f}s (avg: {avg_time * 1000:.1f}ms per item)")

            _store_metric(operation_name, elapsed)
            _store_metric(f"{operation_name}_per_item", avg_time)

            return result

        return wrapper  # type: ignore

    return decorator


# Global metrics storage
_performance_metrics: dict[str, list[float]] = {}


def _store_metric(name: str, duration: float) -> None:
    """Store a performance metric for later analysis."""
    if name not in _performance_metrics:
        _performance_metrics[name] = []
    _performance_metrics[name].append(duration)


def get_performance_summary() -> dict[str, dict[str, float]]:
    """
    Get a summary of all collected performance metrics.

    Returns:
        Dictionary with operation names as keys and statistics as values
    """
    summary = {}

    for operation, times in _performance_metrics.items():
        if times:
            summary[operation] = {
                "count": len(times),
                "total": sum(times),
                "average": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
            }

    return summary


def log_performance_summary() -> None:
    """Log a formatted summary of all performance metrics."""
    summary = get_performance_summary()

    if not summary:
        logger.info("No performance metrics collected")
        return

    logger.info("=" * 60)
    logger.info("Performance Summary")
    logger.info("=" * 60)

    for operation, stats in sorted(summary.items()):
        logger.info(f"{operation:30} | Count: {stats['count']:4d} | Avg: {stats['average'] * 1000:7.2f}ms | Total: {stats['total']:.3f}s")

    logger.info("=" * 60)


def reset_metrics() -> None:
    """
    Resets the global performance metrics.

    This function clears the global `_performance_metrics` variable and logs the
    action. It is used to reset performance metrics, ensuring a clean state for
    new metric collection.

    Raises:
        None
    """
    global _performance_metrics
    _performance_metrics.clear()
    logger.debug("Performance metrics reset")


# Context manager for timing code blocks
class TimedBlock:
    """
    Context manager for measuring and logging execution time.

    TimedBlock is a context manager that helps measure the duration of code
    execution within a block. It logs the elapsed time upon completion or failure
    based on the provided log level. This utility is particularly useful for
    performance monitoring and debugging.

    Attributes:
        name (str): The name of the operation being timed.
        log_level (str): The logging level to use for reporting the results.
        start_time (float): The start time of the operation, initialized during
            context entry.
    """

    def __init__(self, name: str, log_level: str = "info"):
        """
        Represents an initialization for a logging system, setting basic properties
        such as the logger name and the log level. This class handles essential
        configuration that helps in monitoring and debugging the system.

        Args:
            name: The name identifier for the logger.
            log_level: The log level to be used, defaulting to "info". Common
                log levels include "debug", "info", "warn", "error", etc.

        Attributes:
            name: The name identifier of the logger instance.
            log_level: The configured logging level for the logger.
            start_time: A timestamp representing the starting point for logging
                activities, initialized to 0 and expected to update elsewhere.
        """
        self.name = name
        self.log_level = log_level
        self.start_time: float = 0

    def __enter__(self) -> "TimedBlock":
        """
        Acts as a context manager for measuring the execution time of a block of code.

        This method is invoked when entering the context of the `TimedBlock` instance using the `with` statement.
        It initializes the start time of the block for time measurement.

        Returns:
            TimedBlock: The context manager instance itself which can be used within the scope of the `with` statement.
        """
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Context manager exit method that handles logging and performance metrics based
        on the elapsed time. Logs the elapsed time of the operation and stores the
        metric upon successful execution, or an error message if an exception is
        raised.

        Args:
            exc_type (Any): Exception type that caused the context manager to exit.
            exc_val (Any): Exception value provided during the context manager's exit.
            exc_tb (Any): Traceback object related to the exception.

        """
        elapsed = time.perf_counter() - self.start_time

        if exc_type is None:
            log_msg = f"{self.name} completed in {elapsed:.3f}s"
            if self.log_level == "debug":
                logger.debug(log_msg)
            elif self.log_level == "warning":
                logger.warning(log_msg)
            else:
                logger.info(log_msg)
            _store_metric(self.name, elapsed)
        else:
            logger.error(f"{self.name} failed after {elapsed:.3f}s")
