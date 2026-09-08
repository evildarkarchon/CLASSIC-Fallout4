"""Wrye report facts preserve grouping, warning metadata and authored report text."""

from collections.abc import Mapping
from functools import partial
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _observed(formatted: bool, observation: Mapping[str, Any]) -> bool:
    """Require all issue fields and the corresponding formatted section headings."""
    if set(observation) != ({"issues", "report"} if formatted else {"issues"}):
        return False
    issues = observation["issues"]
    if not isinstance(issues, list):
        return False
    for issue in issues:
        if not isinstance(issue, Mapping) or set(issue) != {
            "section",
            "plugins",
            "warning",
            "severity",
        }:
            return False
        if (
            not isinstance(issue["section"], str)
            or issue["section"] == "Active Plugins:"
            or not isinstance(issue["plugins"], list)
            or not all(isinstance(plugin, str) for plugin in issue["plugins"])
        ):
            return False
        if issue["warning"] is not None and not isinstance(issue["warning"], str):
            return False
        if issue["severity"] not in {"Info", "Warning", "Error"}:
            return False
    return not formatted or (
        isinstance(observation["report"], str)
        and all(issue["section"] in observation["report"] for issue in issues)
        and (bool(observation["report"]) if issues else observation["report"] == "")
    )


WRYE_REPORT_COVERAGE_POLICY = FamilyCoveragePolicy(
    "wrye-report",
    (
        CoveragePredicate(
            "parsed-rows",
            "wrye-report.parse",
            "wrye-report.parse",
            "wrye-issues",
            ("parse",),
            partial(_observed, False),
            runtime_operations=("wrye_parse_html_rows",),
        ),
        CoveragePredicate(
            "formatted-issues",
            "wrye-report.format",
            "wrye-report.format",
            "wrye-format",
            ("WryeBashParser", "WryeIssue", "WryeSeverity"),
            partial(_observed, True),
            runtime_operations=(
                None,
                "__init__",
                "parse",
                "format_report",
                "parse_wrye_report",
            ),
        ),
    ),
)
