"""Foundation performance storage and wrapper timer lifecycle observations."""

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _observed(value):
    """Require metrics, namespace inventory, misses, timer mutation and cleanup."""
    return (
        set(value) == {"missingBefore", "samples", "operations", "timer", "emptyAfter"}
        and value["missingBefore"] is True
        and value["emptyAfter"] is True
        and value["operations"] == ["samples", "timer"]
        and set(value["samples"])
        == {
            "count",
            "total_ms",
            "avg_ms",
            "min_ms",
            "max_ms",
            "bytes_processed",
            "throughput",
        }
        and value["timer"] == {"count": 1, "bytes": 32, "durationValid": True}
    )


SHARED_PERFORMANCE_COVERAGE_POLICY = FamilyCoveragePolicy(
    "shared-performance",
    (
        CoveragePredicate(
            id="shared-performance.observed",
            capability_id="shared-performance.observe",
            action="shared-performance.observe",
            observation_family="metrics",
            rust_symbols=("PerformanceMetrics",),
            matches=_observed,
            runtime_operations=(
                None,
                *(
                    "RustPerformanceMonitor." + operation
                    for operation in (
                        "__init__",
                        "clear_metrics",
                        "get_all_stats",
                        "get_operation_stats",
                        "record_metric",
                        "start_timer",
                        "stop_timer",
                    )
                ),
            ),
        ),
    ),
)
