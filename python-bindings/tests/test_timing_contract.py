"""Direct timing-contract tests for inputs JSON conformance fixtures cannot carry.

The ``performance`` conformance pack covers negative, out-of-range, overflow,
negative-zero, and rounding behaviour with JSON fixtures. NaN and infinity are
not valid JSON, so they are exercised here against the real extensions, along
with the no-mutation guarantee, the at-most-once timer, and the
``RustPerformanceMonitor`` timer-stop and millisecond paths.
"""

from __future__ import annotations

import math

import classic_perf
import classic_shared
import pytest


@pytest.fixture(autouse=True)
def _clean_metrics():
    """Each extension's default store is process-global; isolate every test."""
    classic_perf.clear_metrics()
    classic_shared.RustPerformanceMonitor().clear_metrics()
    yield
    classic_perf.clear_metrics()
    classic_shared.RustPerformanceMonitor().clear_metrics()


def _snapshot() -> dict[str, tuple[int, float, float, float, float]]:
    """Comparable copy of the classic_perf seconds view."""
    return {
        name: (stats.count, stats.total, stats.average, stats.min, stats.max)
        for name, stats in classic_perf.get_summary().items()
    }


@pytest.mark.parametrize(
    ("value", "token"),
    [
        (math.nan, "timing_sample_not_finite"),
        (math.inf, "timing_sample_not_finite"),
        (-math.inf, "timing_sample_not_finite"),
        (-1e-9, "timing_sample_negative"),
        (1e300, "timing_sample_out_of_range"),
    ],
)
def test_record_timing_rejects_invalid_samples_without_mutation(value, token):
    classic_perf.record_timing("kept", 0.25)
    before = _snapshot()

    with pytest.raises(ValueError, match=f"^{token}: "):
        classic_perf.record_timing("kept", value)
    with pytest.raises(ValueError, match=f"^{token}: "):
        classic_perf.record_timing("never_created", value)

    assert _snapshot() == before


def test_record_timing_rejects_accumulated_overflow_without_mutation():
    classic_perf.record_timing("full", 18e9)
    before = _snapshot()

    with pytest.raises(ValueError, match="^timing_counter_overflow: "):
        classic_perf.record_timing("full", 1e9)

    assert _snapshot() == before


def test_negative_zero_and_single_nanosecond_rounding():
    classic_perf.record_timing("zero", -0.0)
    # 1/1024 s is exactly 976_562.5 ns; the tie rounds to the even neighbour.
    classic_perf.record_timing("tie", 1 / 1024)

    summary = classic_perf.get_summary()
    assert summary["zero"].count == 1
    assert summary["zero"].total == 0.0
    assert round(summary["tie"].total * 1e9) == 976_562


def test_timer_records_at_most_once():
    timer = classic_perf.Timer("once")
    timer.finish()
    timer.finish()
    del timer

    assert classic_perf.get_summary()["once"].count == 1


def test_monitor_stop_timer_rejects_forged_start_without_mutation():
    monitor = classic_shared.RustPerformanceMonitor()
    for start_time in (math.nan, math.inf, 1e300):
        # A start in the future (or nonfinite) gives an invalid elapsed time.
        with pytest.raises(ValueError, match="^timing_sample_"):
            monitor.stop_timer({"operation": "forged", "start_time": start_time}, 8)

    assert monitor.get_operation_stats("forged") is None
    assert monitor.get_all_stats() == {}


def test_monitor_record_metric_rejects_invalid_milliseconds():
    monitor = classic_shared.RustPerformanceMonitor()
    monitor.record_metric("kept", 5, 64)
    before = monitor.get_all_stats()

    with pytest.raises(ValueError, match="^timing_sample_negative: "):
        monitor.record_metric("kept", -1, 64)
    with pytest.raises(ValueError, match="^timing_sample_out_of_range: "):
        monitor.record_metric("kept", 2**64, 64)
    # Ints beyond i128 still reach core validation instead of OverflowError.
    with pytest.raises(ValueError, match="^timing_sample_out_of_range: "):
        monitor.record_metric("kept", 2**200, 64)
    with pytest.raises(ValueError, match="^timing_sample_negative: "):
        monitor.record_metric("kept", -(2**200), 64)
    with pytest.raises(TypeError):
        monitor.record_metric("kept", "5", 64)
    with pytest.raises(ValueError, match="^timing_counter_overflow: "):
        monitor.record_metric("kept", 1, 2**64 - 1)

    assert monitor.get_all_stats() == before


def test_monitor_instances_share_the_extension_default_store():
    first = classic_shared.RustPerformanceMonitor()
    second = classic_shared.RustPerformanceMonitor()
    first.record_metric("shared", 3, 10)

    assert second.get_operation_stats("shared")["count"] == 1

    second.clear_metrics()
    assert first.get_all_stats() == {}
