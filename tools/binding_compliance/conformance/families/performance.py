"""Exact performance metrics facts without granting wall-clock timer coverage."""

import math
from collections.abc import Mapping
from functools import partial
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _single(milliseconds: int) -> dict[str, int]:
    """One-sample millisecond statistics, where every aggregate equals the sample."""
    return {
        "count": 1,
        "totalMs": milliseconds,
        "averageMs": milliseconds,
        "minMs": milliseconds,
        "maxMs": milliseconds,
    }


# Authored independently of any adapter: invalid samples are rejected with the
# stable core token and leave earlier samples intact; 1/1024 s and 3/1024 s are
# exact nanosecond ties that round to the even neighbour.
_EXPECTED = {
    "empty": {"snapshots": [{}, {}], "rejections": []},
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
        ],
        "rejections": [],
    },
    "invalid-rejected-unchanged": {
        "snapshots": [{"scan": _single(125)}],
        "rejections": [
            "timing_sample_negative",
            "timing_sample_out_of_range",
            "timing_sample_negative",
        ],
    },
    "counter-limit": {
        "snapshots": [{"full": _single(18_000_000_000_000)}],
        "rejections": ["timing_counter_overflow"],
    },
    "nanosecond-precision": {
        "snapshots": [
            {
                "tie": {"count": 1, "averageNs": 976_562},
                "odd": {"count": 1, "averageNs": 2_929_688},
                "zero": {"count": 1, "averageNs": 0},
            }
        ],
        "rejections": [],
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
    ) and all(type(token) is str for token in observation["rejections"])


# Public operations exercised by every scenario that records explicit samples.
_RECORD_OPERATIONS = (
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
                ("record_timing", "record_timing_millis", "get_summary", "clear_metrics", "MetricsSummary"),
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
            (
                "invalid-rejected-unchanged",
                "errors",
                ("record_timing", "record_timing_millis", "get_summary", "clear_metrics"),
                _RECORD_OPERATIONS,
            ),
            (
                "counter-limit",
                "errors",
                ("record_timing", "record_timing_millis", "get_summary", "clear_metrics"),
                _RECORD_OPERATIONS,
            ),
            (
                "nanosecond-precision",
                "values",
                ("record_timing", "record_timing_millis", "get_summary", "clear_metrics", "MetricsSummary"),
                _RECORD_OPERATIONS,
            ),
        )
    ),
)


def _validate_dual_unit_sample(operation):
    """Require one exact sample spelled identically in seconds and milliseconds.

    Seconds-based adapters (Rust, CXX, Python) and millisecond adapters (Node)
    each read their native unit, so neither performs a lossy unit conversion
    before the core's single nanosecond rounding.
    """
    if set(operation) != {"op", "label", "seconds", "milliseconds"} or not isinstance(
        operation["label"], str
    ):
        raise ValueError("invalid dual-unit performance sample")
    seconds, milliseconds = operation["seconds"], operation["milliseconds"]
    if (
        type(seconds) not in (int, float)
        or type(milliseconds) not in (int, float)
        or not math.isfinite(seconds)
        or not math.isfinite(milliseconds)
        or seconds * 1000 != milliseconds
        or math.copysign(1.0, seconds) != math.copysign(1.0, milliseconds)
    ):
        raise ValueError("dual-unit sample must state one exact duration")


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
            if operation.get("op") in {"clear", "summary", "summaryNs"} and set(
                operation
            ) == {"op"}:
                continue
            if operation.get("op") in {"sample", "reject"}:
                _validate_dual_unit_sample(operation)
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
