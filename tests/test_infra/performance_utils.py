"""Performance testing utilities for CLASSIC test suite."""

import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any


@dataclass
class PerformanceResult:
    """Result of a performance measurement."""

    name: str
    duration: float
    iterations: int = 1

    @property
    def average_duration(self) -> float:
        """Average duration per iteration."""
        return self.duration / self.iterations if self.iterations > 0 else 0.0


class PerformanceTimer:
    """Timer for measuring performance of code blocks."""

    def __init__(self, name: str = "Operation", iterations: int = 1):
        """Initialize the timer.

        Args:
            name: Name of the operation being timed
            iterations: Number of iterations for averaging
        """
        self.name = name
        self.iterations = iterations
        self.start_time: float | None = None
        self.end_time: float | None = None

    def __enter__(self) -> "PerformanceTimer":
        """Start timing."""
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        """Stop timing."""
        self.end_time = time.perf_counter()

    @property
    def duration(self) -> float:
        """Get the measured duration in seconds."""
        if self.start_time is None or self.end_time is None:
            return 0.0
        return self.end_time - self.start_time

    @property
    def elapsed(self) -> float:
        """Alias for duration for backward compatibility."""
        return self.duration

    @property
    def result(self) -> PerformanceResult:
        """Get the performance result."""
        return PerformanceResult(name=self.name, duration=self.duration, iterations=self.iterations)


@contextmanager
def measure_performance(name: str = "Operation", callback: Callable[[PerformanceResult], None] | None = None):
    """Context manager for measuring performance.

    Args:
        name: Name of the operation being measured
        callback: Optional callback to process the result

    Yields:
        PerformanceTimer instance
    """
    timer = PerformanceTimer(name)
    timer.start_time = time.perf_counter()

    try:
        yield timer
    finally:
        timer.end_time = time.perf_counter()
        if callback:
            callback(timer.result)
