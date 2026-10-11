"""Papyrus counters require full read, tail-from-end, idle and reset semantics."""

from collections.abc import Mapping
from functools import partial
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _stats(value: object) -> bool:
    """Require complete nonnegative counters and the native ratio relationship."""
    if not isinstance(value, Mapping) or set(value) != {
        "dumps",
        "stacks",
        "warnings",
        "errors",
        "lines",
        "ratio",
    }:
        return False
    if not all(
        type(value[key]) is int and value[key] >= 0
        for key in ("dumps", "stacks", "warnings", "errors", "lines")
    ):
        return False
    ratio = (
        value["dumps"] / value["stacks"] if value["dumps"] and value["stacks"] else 0.0
    )
    return value["ratio"] == f"{ratio:.3f}"


def _observed(exists: bool, observation: Mapping[str, Any]) -> bool:
    """Reject missing stages, replayed idle data and failure disguised as an empty log."""
    if (
        set(observation)
        != {
            "exists",
            "error",
            "initial",
            "tailStart",
            "updated",
            "idle",
            "afterReset",
            "finalContent",
        }
        or observation["exists"] is not exists
    ):
        return False
    stages = ("initial", "tailStart", "updated", "idle", "afterReset")
    if not exists:
        return (
            observation["error"] == "missing"
            and observation["finalContent"] is None
            and all(observation[key] is None for key in stages)
        )
    if (
        observation["error"] is not None
        or not all(_stats(observation[key]) for key in stages)
        or not isinstance(observation["finalContent"], str)
    ):
        return False
    return (
        all(
            observation["tailStart"][key] == 0
            for key in ("dumps", "stacks", "warnings", "errors", "lines")
        )
        and observation["idle"] == observation["updated"]
        and all(
            observation["afterReset"][key]
            == observation["initial"][key] + observation["updated"][key]
            for key in ("dumps", "stacks", "warnings", "errors", "lines")
        )
        and observation["afterReset"]["lines"]
        == len(observation["finalContent"].splitlines())
    )


PAPYRUS_MONITOR_COVERAGE_POLICY = FamilyCoveragePolicy(
    "papyrus-monitor",
    tuple(
        CoveragePredicate(
            "monitor-stages" if exists else "missing-log",
            "papyrus-monitor.observe",
            "papyrus-monitor.observe",
            "monitor-stages",
            ("PapyrusAnalyzer", "PapyrusStats") if exists else ("PapyrusAnalyzer",),
            partial(_observed, exists),
            runtime_operations=(
                None,
                "__init__",
                "analyze_full",
                "analyze_to_string",
                "log_exists",
                "log_path",
                "stats",
                "reset",
                "start_monitoring",
                "check_for_updates",
                "dumps_to_stacks_ratio",
                "papyrus_analyzer_new",
                "papyrus_analyze_full",
                "papyrus_log_exists",
                "papyrus_reset",
                "papyrus_start_monitoring",
                "papyrus_check_updates",
                "papyrus_logging",
            )
            if exists
            else (
                "analyze_full",
                "papyrus_analyze_full",
                "log_exists",
                "papyrus_log_exists",
            ),
        )
        for exists in (True, False)
    ),
)
