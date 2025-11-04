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
    A decorator to measure the execution time of a function, log the duration,
    and optionally store execution metrics. The decorator allows customization
    of the operation name and logging level.

    Args:
        name (str | None): The name of the operation for logging and metric purposes.
            If None, the decorated function's name will be used.
        log_level (str): The logging level to use for recording the operation's duration.
            Supported levels are "info", "debug", or "warning". Defaults to "info".

    Returns:
        Callable[[F], F]: A decorator that wraps the provided function to measure and log
        its execution time.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            operation_name = name or func.__name__
            start = time.perf_counter()

            try:
                result = func(*args, **kwargs)
            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(f"{operation_name} failed after {elapsed:.3f}s: {e}")
                raise
            else:
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

        return wrapper  # type: ignore

    return decorator


def async_timed_operation(name: str | None = None, log_level: str = "info") -> Callable[[F], F]:
    """
    Decorator function to measure and log the duration of asynchronous operations. This decorator
    can be applied to any coroutine. The operation name for logging can be explicitly specified or
    defaulted to the function name. Additionally, logs are created based on the specified log level,
    and execution time is stored as a metric for analysis.

    Args:
        name (str | None): Optional custom name for the operation. Defaults to None, which uses the
            function name as the operation name.
        log_level (str): Logging level to use for the operation's status. Defaults to "info".

    Returns:
        Callable[[F], F]: A decorator that wraps the target coroutine, timing its execution
            and logging the result.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            operation_name = name or func.__name__
            start = time.perf_counter()

            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(f"{operation_name} failed after {elapsed:.3f}s: {e}")
                raise
            else:
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

        return wrapper  # type: ignore

    return decorator


def batch_operation_monitor(operation_name: str) -> Callable[[F], F]:
    """
    A decorator function used for monitoring the performance of batch operations. It measures
    the elapsed time for the execution of the decorated function and attempts to calculate the
    average time per item in a batch if applicable. The function logs relevant performance
    metrics and stores them using appropriate metric handlers.

    Args:
        operation_name (str): The name of the operation being monitored. This name will be
            used for log messages and metric storage.

    Returns:
        Callable[[F], F]: A decorator function that can wrap another function for monitoring.
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
    """
    Stores a performance metric by associating a metric name with a duration value.
    If the metric name does not already exist within the performance metrics storage,
    a new entry is added to initialize tracking for this metric. Each duration value
    is appended to the list associated with the key, facilitating performance tracking
    over time.

    Args:
        name (str): The name of the performance metric to store. Used as a key
            for tracking the metric durations.
        duration (float): The duration value associated with the metric. Represents
            the specific performance measurement to record.

    Returns:
        None
    """
    if name not in _performance_metrics:
        _performance_metrics[name] = []
    _performance_metrics[name].append(duration)


def get_performance_summary() -> dict[str, dict[str, float]]:
    """
    Calculates and summarizes performance metrics for various operations.

    This function aggregates performance metrics for different operations and
    returns a summary containing statistics such as count, total time, average,
    minimum time, and maximum time for each operation.

    Returns:
        dict[str, dict[str, float]]: A dictionary where each key is the name of
        an operation and the value is another dictionary containing statistical
        metrics ("count", "total", "average", "min", "max") for that operation.
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
    """
    Logs a summary of performance metrics collected during the execution.

    The function retrieves a performance summary and logs it in a
    structured format. If no metrics are available, it logs an
    appropriate message. Otherwise, it logs each operation's performance
    statistics, including count, average time per operation, and
    total time spent.

    Raises:
        KeyError: If the structure of the performance summary contains missing
            or unexpected keys for operations.
    """
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

    This function clears all data in the global performance metrics storage. It is
    typically used to reset metrics tracking during or after execution.

    Raises:
        KeyError: If the global performance metrics storage does not exist.
    """
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
        Initializes the instance of the class with the provided name and log level.
        The class is responsible for managing logging behavior based on the specified
        log level and tracking operational start time for additional functionality.

        Args:
            name (str): The name identifier for the instance.
            log_level (str, optional): The logging level for the instance, defaults to "info".
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
