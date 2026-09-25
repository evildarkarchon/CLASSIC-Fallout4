"""Observe deterministic metrics through the actual Python extension."""

from collections.abc import Mapping
from typing import Any


def _milliseconds(seconds: float) -> int:
    """Convert exact authored durations without rounding away native differences."""
    value = seconds * 1000
    if not value.is_integer():
        raise ValueError("metric duration is not an exact integer millisecond")
    return int(value)


def observe_performance(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Execute explicit samples serially and clear process-global metrics on exit."""
    import classic_perf

    if set(fixture) != {"operations"} or not isinstance(fixture["operations"], list):
        raise ValueError("unsupported performance fixture")
    snapshots = []
    classic_perf.clear_metrics()
    try:
        for operation in fixture["operations"]:
            op = operation.get("op")
            if op == "clear" and set(operation) == {"op"}:
                classic_perf.reset_metrics()
            elif op == "summary" and set(operation) == {"op"}:
                snapshots.append(
                    {
                        label: {
                            "count": stats.count,
                            "totalMs": _milliseconds(stats.total),
                            "averageMs": _milliseconds(stats.average),
                            "minMs": _milliseconds(stats.min),
                            "maxMs": _milliseconds(stats.max),
                        }
                        for label, stats in classic_perf.get_summary().items()
                    }
                )
            elif (
                    op == "record"
                    and set(operation) == {"op", "label", "durationMs"}
                    and isinstance(operation["label"], str)
                    and type(operation["durationMs"]) is int
                    and 0 <= operation["durationMs"] <= 1000000
            ):
                classic_perf.record_timing(
                    operation["label"], operation["durationMs"] / 1000
                )
            else:
                raise ValueError("unsupported performance operation")
        return {"snapshots": snapshots}
    finally:
        # Process-global samples must not leak into the next fixture after failure.
        classic_perf.clear_metrics()


def observe_timers(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Measure both native timer constructors and verify exactly-once sample recording.

    A bounded sleep tests clock progress without asserting a platform-specific
    duration. Global metrics are cleared even when a native operation fails.
    """
    import math
    import time

    import classic_perf

    if fixture != {"constructors": ["direct", "factory"]}:
        raise ValueError("unsupported timer fixture")
    classic_perf.clear_metrics()
    timers = []
    try:
        for constructor in fixture["constructors"]:
            timer = (
                classic_perf.Timer(constructor)
                if constructor == "direct"
                else classic_perf.start_timer(constructor)
            )
            first = timer.elapsed()
            time.sleep(0.002)
            later = timer.elapsed()
            timer.finish()
            del timer
            summary = classic_perf.get_summary()[constructor]
            timers.append(
                {
                    "constructor": constructor,
                    "advanced": math.isfinite(first)
                                and math.isfinite(later)
                                and 0 <= first < later,
                    "positive": summary.total >= later > 0,
                    "singleSample": summary.count == 1,
                    "summaryConsistent": summary.total
                                         == summary.average
                                         == summary.min
                                         == summary.max,
                }
            )
        classic_perf.clear_metrics()
        return {"timers": timers, "cleared": not classic_perf.get_summary()}
    finally:
        # Timer fixtures share process-global metrics with the deterministic suite.
        classic_perf.clear_metrics()
