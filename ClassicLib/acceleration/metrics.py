"""Component performance metrics tracking.

This module provides the ComponentMetrics dataclass for tracking performance
metrics of individual components in the Rust acceleration system.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ComponentMetrics:
    """Represent metrics for a component, tracking performance and error data.

    This class is designed to aggregate and provide metrics related to calls made
    to a given component. It includes information about the number of calls,
    execution times, cache performance, and errors. It also provides calculated
    properties such as average execution time and cache hit rate.

    Attributes:
        name (str): The name of the component being tracked.
        calls (int): The total number of calls made to the component.
        total_time (float): The total execution time of all calls.
        min_time (float): The shortest execution time of any single call.
        max_time (float): The longest execution time of any single call.
        errors (int): The total number of errors recorded.
        cache_hits (int): The number of successful cache hits.
        cache_misses (int): The number of cache misses.
        last_error (str | None): The most recent error message, if any.

    """

    name: str
    calls: int = 0
    total_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    errors: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    last_error: str | None = None

    @property
    def avg_time(self) -> float:
        """Calculate and retrieves the average time per call.

        This property computes the average time taken for each call by dividing
        the total accumulated time by the number of recorded calls. If no calls
        have been recorded, the average time defaults to 0.0.

        Returns:
            float: The average time per call. Returns 0.0 if there are no calls.

        """
        return self.total_time / self.calls if self.calls > 0 else 0.0

    @property
    def cache_hit_rate(self) -> float:
        """Calculate and returns the cache hit rate as a percentage.

        The cache hit rate is the ratio of cache hits to the total cache
        accesses (hits + misses), expressed as a percentage. If there are
        no cache accesses, the hit rate is considered to be 0.0.

        Returns:
            float: The cache hit rate as a percentage, or 0.0 if there are no
            cache hits or misses.

        """
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0

    def record_call(self, duration: float, cache_hit: bool = False) -> None:
        """Record a single function call's duration and whether it was a cache hit or miss.
        Updates the statistics including total calls, total time, minimum time, maximum time,
        cache hits, and cache misses based on the provided data.

        Args:
            duration (float): The duration of the function call to be recorded.
            cache_hit (bool, optional): Specifies whether the call was a cache hit. Defaults to False.

        """
        self.calls += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)

        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    def record_error(self, error: str) -> None:
        """Record an error by incrementing the error count and storing the latest error.

        Args:
            error (str): The error message to be recorded.

        """
        self.errors += 1
        self.last_error = error


__all__ = ["ComponentMetrics"]
