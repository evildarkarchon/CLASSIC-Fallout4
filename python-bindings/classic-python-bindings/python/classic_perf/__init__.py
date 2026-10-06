"""Python module for performance monitoring.

This module provides high-precision timing, metrics collection, and
performance analysis tools. The core functionality is implemented in
Rust for maximum performance.

Core Functions:
    record_timing(name, duration_secs): Record a timing measurement
    get_summary(): Get statistics for all metrics
    clear_metrics(): Clear all recorded metrics
    start_timer(name): Create a new RAII timer

Classes:
    Timer: RAII timer for automatic timing
    MetricsSummary: Statistics summary for a metric

Example:
    >>> import classic_perf
    >>> classic_perf.record_timing("my_operation", 0.123)
    >>> summary = classic_perf.get_summary()
    >>> summary["my_operation"].average
    0.123
"""

# Direct-import facade over the one CLASSIC native extension. Every name is
# the canonical native object, so values and exceptions created through any
# facade are the same Python types everywhere. Keep the import list and the
# literal ``__all__`` in step with ``__init__.pyi``: validate_stubs.py and the
# Python parity resolver read both.

from _classic_native._native.classic_perf import (
    MetricsSummary,
    Timer,
    __version__,
    clear_metrics,
    get_summary,
    record_timing,
    reset_metrics,
    start_timer,
)

__all__ = [
    "MetricsSummary",
    "Timer",
    "__version__",
    "clear_metrics",
    "get_summary",
    "record_timing",
    "reset_metrics",
    "start_timer",
]
