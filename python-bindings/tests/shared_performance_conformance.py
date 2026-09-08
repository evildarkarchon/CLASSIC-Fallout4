"""Observe the native foundation monitor with an isolated global metric namespace."""

import math


def observe_shared_performance(fixture):
    """Record controlled durations plus one real timer, clearing on every exit."""
    from classic_shared import RustPerformanceMonitor

    monitor = RustPerformanceMonitor()
    monitor.clear_metrics()
    try:
        missing = monitor.get_operation_stats("samples") is None
        for record in fixture["records"]:
            monitor.record_metric("samples", record["milliseconds"], record["bytes"])
        raw = monitor.get_operation_stats("samples")
        samples = {
            key: raw[key]
            for key in (
                "count",
                "total_ms",
                "avg_ms",
                "min_ms",
                "max_ms",
                "bytes_processed",
            )
        }
        samples["throughput"] = format(raw["throughput_bytes_per_sec"], ".3f")
        timer = monitor.start_timer("timer")
        if (
            timer["operation"] != "timer"
            or not math.isfinite(timer["start_time"])
            or timer["start_time"] < 0
        ):
            raise ValueError("native timer returned invalid start state")
        monitor.stop_timer(timer, fixture["timerBytes"])
        timing = monitor.get_operation_stats("timer")
        all_stats = monitor.get_all_stats()
        if all_stats.get("samples") != raw or all_stats.get("timer") != timing:
            raise ValueError("full metric inventory disagrees with individual lookups")
        observation = {
            "missingBefore": missing,
            "samples": samples,
            "operations": sorted(all_stats),
            "timer": {
                "count": timing["count"],
                "bytes": timing["bytes_processed"],
                "durationValid": 0
                <= timing["min_ms"]
                <= timing["avg_ms"]
                <= timing["max_ms"]
                <= timing["total_ms"],
            },
        }
    finally:
        monitor.clear_metrics()
    observation["emptyAfter"] = (
        monitor.get_all_stats() == {} and monitor.get_operation_stats("samples") is None
    )
    return observation
