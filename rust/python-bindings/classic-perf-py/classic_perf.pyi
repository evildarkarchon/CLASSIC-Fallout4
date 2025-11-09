"""Type stubs for classic_perf.

Python bindings for classic-perf-core, providing high-precision timing, metrics collection,
and performance analysis tools. The core functionality is implemented in Rust for maximum
performance.

Architecture:
    - classic-perf-core: Business logic (timing, metrics storage, statistics)
    - classic-perf-py: Python bindings (this module - PyO3 adapters)

Features:
    - High-precision timing using Rust's Instant
    - Thread-safe metrics collection with DashMap
    - Automatic statistics calculation (count, total, average, min, max)
    - RAII timer pattern for automatic measurements
    - Zero overhead when not collecting metrics

Usage:
    import classic_perf

    # Record individual timings
    classic_perf.record_timing("my_operation", 0.123)

    # Use RAII timer for automatic timing
    timer = classic_perf.start_timer("database_query")
    # ... perform operation ...
    timer.finish()  # Records timing automatically

    # Get summary statistics
    summary = classic_perf.get_summary()
    for name, stats in summary.items():
        print(f"{name}: {stats.average:.3f}s avg over {stats.count} samples")

    # Clear metrics
    classic_perf.clear_metrics()
"""

from __future__ import annotations

__version__: str

class MetricsSummary:
    """Summary statistics for a performance metric.

    This class contains aggregated statistics for a single metric,
    including count, total time, average, minimum, and maximum.

    Attributes:
        count: Number of samples recorded.
        total: Total time in seconds.
        average: Average time per sample in seconds.
        min: Minimum time in seconds.
        max: Maximum time in seconds.

    Example:
        >>> import classic_perf
        >>> classic_perf.record_timing("op1", 0.1)
        >>> classic_perf.record_timing("op1", 0.2)
        >>> summary = classic_perf.get_summary()
        >>> stats = summary["op1"]
        >>> print(f"Average: {stats.average}s")
        Average: 0.15s
    """

    count: int
    total: float
    average: float
    min: float
    max: float

    def __repr__(self) -> str:
        """Gets a string representation of the metrics summary.

        Returns:
            Formatted string showing all statistics.

        Example:
            >>> stats = MetricsSummary(...)
            >>> print(repr(stats))
            MetricsSummary(count=2, total=0.300s, average=0.150s, min=0.100s, max=0.200s)
        """

class Timer:
    """RAII timer that automatically records timing on drop.

    This timer starts when created and automatically records its elapsed
    time when it goes out of scope or when `finish()` is called.

    Note:
        Timer does NOT support context manager protocol (no 'with' statement).
        Use manual finish() or let Python garbage collect to record timing.

    Example:
        >>> timer = Timer("my_operation")
        >>> # ... do work ...
        >>> print(f"Elapsed: {timer.elapsed()}s")
        >>> timer.finish()  # Records timing

    Note:
        If finish() is not called explicitly, the timer will automatically
        record when it goes out of scope (when Python garbage collects it).
    """

    def __init__(self, name: str) -> None:
        """Create a new timer with the given operation name.

        Args:
            name: Operation name for metrics tracking.

        Example:
            >>> timer = Timer("database_query")
            >>> # ... do work ...
            >>> timer.finish()
        """

    def finish(self) -> None:
        """Finish timing and record the measurement.

        This consumes the timer and records the elapsed time.
        If the timer is dropped without calling `finish()`, it will
        automatically record on drop.

        Example:
            >>> timer = Timer("operation")
            >>> # ... do work ...
            >>> timer.finish()
        """

    def elapsed(self) -> float:
        """Get the current elapsed time without finishing the timer.

        Returns:
            Elapsed time in seconds.

        Example:
            >>> timer = Timer("operation")
            >>> # ... do some work ...
            >>> print(f"So far: {timer.elapsed()}s")
            >>> # ... do more work ...
            >>> timer.finish()
        """

    def __repr__(self) -> str:
        """Return the debug representation of this Timer.

        Returns:
            A string representation suitable for debugging.
        """

def record_timing(name: str, duration_secs: float) -> None:
    """Record a timing measurement.

    This function stores a single timing sample for the given operation name.
    Multiple samples can be recorded for the same operation, and statistics
    will be computed across all samples.

    Args:
        name: The operation name.
        duration_secs: The duration in seconds.

    Example:
        >>> import classic_perf
        >>> classic_perf.record_timing("my_operation", 0.123)
        >>> classic_perf.record_timing("my_operation", 0.156)
        >>> summary = classic_perf.get_summary()
        >>> print(summary["my_operation"].count)
        2
    """

def get_summary() -> dict[str, MetricsSummary]:
    """Get summary statistics for all recorded metrics.

    Returns a dictionary mapping operation names to MetricsSummary objects
    containing count, total, average, min, and max statistics.

    Returns:
        Dictionary mapping operation names to their statistics.

    Example:
        >>> import classic_perf
        >>> classic_perf.record_timing("op1", 0.1)
        >>> classic_perf.record_timing("op1", 0.2)
        >>> summary = classic_perf.get_summary()
        >>> stats = summary["op1"]
        >>> print(f"Average: {stats.average}s")
        Average: 0.15s
        >>> print(f"Count: {stats.count}")
        Count: 2
    """

def clear_metrics() -> None:
    """Clear all recorded metrics.

    This removes all timing data from the metrics storage. Useful for
    resetting between test runs or measurement sessions.

    Example:
        >>> import classic_perf
        >>> classic_perf.record_timing("op1", 0.1)
        >>> classic_perf.clear_metrics()
        >>> summary = classic_perf.get_summary()
        >>> print(len(summary))
        0
    """

def reset_metrics() -> None:
    """Alias for clear_metrics() for API compatibility.

    This is an alias for `clear_metrics()` to match the Python API.

    Example:
        >>> import classic_perf
        >>> classic_perf.record_timing("op1", 0.1)
        >>> classic_perf.reset_metrics()
        >>> summary = classic_perf.get_summary()
        >>> print(len(summary))
        0
    """

def start_timer(name: str) -> Timer:
    """Start a new timer.

    Convenience function that creates and starts a Timer.

    Args:
        name: Operation name for metrics tracking.

    Returns:
        A running timer instance.

    Example:
        >>> import classic_perf
        >>> timer = classic_perf.start_timer("my_operation")
        >>> # ... do work ...
        >>> timer.finish()
    """
