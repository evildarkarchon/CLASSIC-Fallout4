"""Crashgen checker and orchestration require actual native results over owned files."""

from collections.abc import Mapping
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _observed(observation: Mapping[str, Any]) -> bool:
    """Require every issue column and metadata while preserving all input bytes."""
    if set(observation) != {
        "message",
        "issues",
        "name",
        "config",
        "plugins",
        "beforeFiles",
        "files",
    }:
        return False
    if not isinstance(observation["message"], str) or observation["name"] != "Buffout4":
        return False
    if observation["config"] is not None and not isinstance(observation["config"], str):
        return False
    if not isinstance(observation["plugins"], list) or not all(
        isinstance(value, str) for value in observation["plugins"]
    ):
        return False
    issues = observation["issues"]
    if not isinstance(issues, list) or not all(
        isinstance(issue, Mapping)
        and set(issue)
        == {
            "path",
            "section",
            "setting",
            "current",
            "recommended",
            "description",
            "severity",
        }
        and all(isinstance(value, str) for value in issue.values())
        and issue["severity"] in {"Info", "Warning", "Error"}
        for issue in issues
    ):
        return False
    return (
        isinstance(observation["files"], list)
        and all(
            isinstance(item, Mapping)
            and set(item) == {"path", "content"}
            and all(isinstance(value, str) for value in item.values())
            for item in observation["files"]
        )
        and observation["files"] == observation["beforeFiles"]
    )


CRASHGEN_CHECK_COVERAGE_POLICY = FamilyCoveragePolicy(
    "crashgen-check",
    (
        CoveragePredicate(
            "checker-and-orchestrator",
            "crashgen-check.check",
            "crashgen-check.check",
            "configuration-report",
            (
                "CrashgenChecker",
                "CrashgenCheckOrchestrator",
                "CrashgenReport",
                "TomlIssueSeverity",
                "check",
                # Python's check_crashgen_settings maps to this core operation.
                "check_with_rules",
            ),
            _observed,
            runtime_operations=(
                None,
                "__init__",
                "check",
                "detect_plugins",
                "resolve_config_path",
                "check_crashgen_config",
                "check_crashgen_settings",
                "checkCrashgenConfig",
                "checkCrashgenFull",
                "checkCrashgenConfigWithRules",
                "checkCrashgenFullWithRules",
                "crashgen_checker_check",
                "crashgen_checker_get_issues",
                "crashgen_orchestrator_check_summary",
                "crashgen_orchestrator_get_issues",
                "crashgen_orchestrator_get_installed_plugins",
            ),
        ),
    ),
)
