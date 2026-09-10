"""Shared header classification facts with a separate legacy CXX text contract."""

from collections.abc import Mapping
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _token(observation: Mapping[str, Any]) -> bool:
    """Require an explicit optional result from the frozen shared token vocabulary."""
    if set(observation) != {"token"}:
        return False
    return (
        observation["token"] is None
        or isinstance(observation["token"], str)
        and observation["token"]
        in {
            "ACCESS_VIOLATION",
            "STACK_OVERFLOW",
            "INT_DIVIDE_BY_ZERO",
            "BREAKPOINT",
            "ILLEGAL_INSTRUCTION",
            "STACK_BUFFER_OVERRUN",
            "HEAP_CORRUPTION",
        }
    )


def _legacy(observation: Mapping[str, Any]) -> bool:
    """Keep legacy full header text distinct from token classification."""
    return (
        set(observation) == {"mainError"}
        and isinstance(observation["mainError"], str)
        and (
            observation["mainError"] == ""
            or observation["mainError"].startswith("Unhandled exception")
        )
    )


def _vr(observation: Mapping[str, Any]) -> bool:
    """Require an actual boolean from the shared VR marker detector."""
    return set(observation) == {"vr"} and type(observation["vr"]) is bool


CRASH_PATTERN_COVERAGE_POLICY = FamilyCoveragePolicy(
    "crash-pattern",
    (
        CoveragePredicate(
            "vr-markers",
            "crash-pattern.vr",
            "crash-pattern.vr",
            "vr-detection",
            ("detect_vr_log",),
            _vr,
            runtime_operations=(
                "detect_vr_log",
                "detectVrLog",
                "LogParser.detect_vr_log",
            ),
        ),
        CoveragePredicate(
            "classified-header",
            "crash-pattern.classify",
            "crash-pattern.classify",
            "classification",
            ("detect_crash_pattern",),
            _token,
            runtime_operations=(
                "detect_crash_pattern",
                "detectCrashPattern",
                "classify_crash_pattern",
            ),
        ),
        CoveragePredicate(
            "legacy-header-text",
            "crash-pattern.legacy",
            "crash-pattern.legacy",
            "main-error",
            ("LogParser",),
            _legacy,
            runtime_operations=("detect_crash_pattern",),
        ),
    ),
)
