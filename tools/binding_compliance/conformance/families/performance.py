"""Exact performance metrics facts without granting wall-clock timer coverage."""

from collections.abc import Mapping
from functools import partial
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy

_EXPECTED = {
    "empty": {"snapshots": [{}, {}]},
    "record-clear-reuse": {
        "snapshots": [
            {},
            {
                "scan": {
                    "count": 2,
                    "totalMs": 500,
                    "averageMs": 250,
                    "minMs": 125,
                    "maxMs": 375,
                },
                "zero": {
                    "count": 1,
                    "totalMs": 0,
                    "averageMs": 0,
                    "minMs": 0,
                    "maxMs": 0,
                },
            },
            {},
            {
                "scan": {
                    "count": 1,
                    "totalMs": 1000,
                    "averageMs": 1000,
                    "minMs": 1000,
                    "maxMs": 1000,
                }
            },
        ]
    },
}


def _matches(kind: str, observation: Mapping[str, Any]) -> bool:
    """Match independent worked examples and reject booleans masquerading as counts."""
    if observation != _EXPECTED[kind]:
        return False
    return all(
        type(value) is int
        for snapshot in observation["snapshots"]
        for stats in snapshot.values()
        for value in stats.values()
    )


PERFORMANCE_COVERAGE_POLICY = FamilyCoveragePolicy(
    "performance",
    tuple(
        CoveragePredicate(
            id=f"performance.{kind}",
            capability_id="performance.metrics",
            action="performance.metrics",
            observation_family=family,
            rust_symbols=symbols,
            matches=partial(_matches, kind),
            runtime_operations=operations,
        )
        for kind, family, symbols, operations in (
            (
                "empty",
                "durable-effects",
                ("get_summary", "clear_metrics"),
                (
                    None,
                    "get_summary",
                    "clear_metrics",
                    "reset_metrics",
                    "getMetricsSummary",
                    "clearAllMetrics",
                    "perf_clear_metrics",
                    "perf_get_summary",
                    "perf_get_operation_average",
                    "perf_get_operation_count",
                ),
            ),
            (
                "record-clear-reuse",
                "values",
                ("record_timing", "get_summary", "clear_metrics", "MetricsSummary"),
                (
                    None,
                    "record_timing",
                    "reset_metrics",
                    "get_summary",
                    "clear_metrics",
                    "recordTimingMetric",
                    "perf_record_timing",
                    "getMetricsSummary",
                    "clearAllMetrics",
                    "perf_clear_metrics",
                    "perf_get_summary",
                    "perf_get_operation_average",
                    "perf_get_operation_count",
                ),
            ),
        )
    ),
)


def validate_performance_pack(document, root):
    """Reject unknown operations, duration types and undeclared fixture transport."""
    import json

    paths = []
    for case in document["scenarios"]:
        reference = case["input"].get("fixtureRef")
        if (
            case["action"] != "performance.metrics"
            or case["input"] != {"fixtureRef": reference}
            or case["fixtureRefs"] != [reference]
        ):
            raise ValueError("performance scenario requires its sole operation fixture")
        path = (
            root / document["fixtureRoot"] / document["fixtures"][reference]
        ).resolve()
        if not path.is_relative_to((root / document["fixtureRoot"]).resolve()):
            raise ValueError("performance fixture escapes root")
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if (
            set(fixture) != {"operations"}
            or not isinstance(fixture["operations"], list)
            or not fixture["operations"]
        ):
            raise ValueError("invalid performance operations")
        for operation in fixture["operations"]:
            if not isinstance(operation, dict):
                raise TypeError("performance operation must be an object")
            if operation.get("op") in {"clear", "summary"} and set(operation) == {"op"}:
                continue
            if (
                set(operation) != {"op", "label", "durationMs"}
                or operation["op"] != "record"
                or not isinstance(operation["label"], str)
                or type(operation["durationMs"]) is not int
                or not 0 <= operation["durationMs"] <= 1000000
            ):
                raise ValueError("invalid explicit performance sample")
        paths.append(path)
    return tuple(paths)
