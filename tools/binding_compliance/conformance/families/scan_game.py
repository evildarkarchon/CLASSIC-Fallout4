"""Narrow Scan Game INI and ENB coverage from native results and disk inventories."""

from __future__ import annotations

from collections.abc import Mapping
from functools import partial
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy
from .file_operations import _files


def _directories(value: object) -> bool:
    """Require a sorted, unique inventory of contained directory paths."""
    return isinstance(value, list) and _files(
        [{"path": path, "content": ""} for path in value]
    )


def _observed(operation: str, outcome: str, observation: Mapping[str, Any]) -> bool:
    """Recognize typed findings only when the full owned filesystem stays unchanged."""
    if (
        set(observation)
        != {
            "operation",
            "game",
            "result",
            "beforeFiles",
            "files",
            "beforeDirectories",
            "directories",
        }
        or observation["operation"] != operation
        or observation["game"] not in {"Fallout4", "Fallout4VR"}
        or not _files(observation["files"])
        or not _directories(observation["directories"])
        or observation["beforeFiles"] != observation["files"]
        or observation["beforeDirectories"] != observation["directories"]
    ):
        return False
    result = observation["result"]
    if not isinstance(result, Mapping):
        return False
    if operation == "validate-enb":
        return (
            set(result) == {"binaries", "config"}
            and result["binaries"] in {"Present", "Partial", "NotInstalled"}
            and result["config"] in {"Valid", "NotFound", "Unreadable"}
            and f"{result['binaries']}-{result['config']}" == outcome
        )
    if (
        set(result) != {"report", "issues"}
        or not isinstance(result["report"], str)
        or not isinstance(result["issues"], list)
    ):
        return False
    for issue in result["issues"]:
        if (
            not isinstance(issue, Mapping)
            or set(issue)
            != {
                "filePath",
                "section",
                "setting",
                "currentValue",
                "recommendedValue",
                "description",
                "severity",
            }
            or not all(isinstance(value, str) for value in issue.values())
            or not _files([{"path": issue["filePath"], "content": ""}])
            or issue["severity"] not in {"Error", "Warning", "Info"}
        ):
            return False
    if outcome == "findings":
        return bool(result["issues"]) and all(
            issue["currentValue"] != issue["recommendedValue"]
            for issue in result["issues"]
        )
    if outcome == "game-notice":
        return (
            observation["game"] == "Fallout4"
            and "sStartingConsoleCommand" in result["report"]
            and not result["issues"]
        )
    if outcome == "other-game":
        return (
            observation["game"] == "Fallout4VR"
            and not result["report"]
            and not result["issues"]
        )
    return not result["report"] and not result["issues"]


_VALIDATOR_POLICY = FamilyCoveragePolicy(
    "scan-game",
    tuple(
        CoveragePredicate(
            id=f"{operation}-{outcome.lower()}",
            capability_id=f"scan-game.{operation}",
            action=f"scan-game.{operation}",
            observation_family="game-check-results",
            rust_symbols=(
                "IniValidator",
                "validate_inis",
                "detect_all_issues",
                "ConfigIssue",
                "IssueSeverity",
            )
            if operation == "validate-ini"
            else (
                "EnbChecker",
                "validate",
                "EnbValidationResult",
                "EnbResult",
                "EnbConfigResult",
            ),
            matches=partial(_observed, operation, outcome),
            runtime_operations=(
                None,
                "__init__",
                "validate_inis",
                "detect_all_issues",
                "ini_validator_validate_inis",
                "ini_validator_detect_all_issues_for_root",
            )
            if operation == "validate-ini"
            else (
                None,
                "__init__",
                "check_binaries",
                "check_config",
                "validate",
                "checkEnb",
                "enb_checker_validate",
                "check_enb",
                "format_message",
                "is_present",
                "is_fully_configured",
            ),
        )
        for operation, outcomes in (
            ("validate-ini", ("empty", "findings", "game-notice", "other-game")),
            (
                "validate-enb",
                (
                    "NotInstalled-NotFound",
                    "Partial-NotFound",
                    "Present-Valid",
                    "Present-Unreadable",
                ),
            ),
        )
        for outcome in outcomes
    ),
)


def _logs_observed(value):
    """Require exact report data alongside unchanged complete file inventories."""
    return (
        set(value)
        == {"report", "beforeFiles", "files", "beforeDirectories", "directories"}
        and isinstance(value["report"], str)
        and _files(value["files"])
        and _directories(value["directories"])
        and value["beforeFiles"] == value["files"]
        and value["beforeDirectories"] == value["directories"]
    )


def _reports_observed(value):
    """Require full texts, native message templates, and exact combined concatenation."""
    return (
        set(value)
        == {"unpacked", "archived", "combined", "unpackedMessages", "archivedMessages"}
        and all(
            isinstance(value[key], str) for key in ("unpacked", "archived", "combined")
        )
        and value["combined"] == value["unpacked"] + value["archived"]
        and all(
            isinstance(value[key], dict)
            and value[key]
            and all(
                isinstance(lines, list) and all(isinstance(line, str) for line in lines)
                for lines in value[key].values()
            )
            for key in ("unpackedMessages", "archivedMessages")
        )
    )


SCAN_GAME_COVERAGE_POLICY = FamilyCoveragePolicy(
    "scan-game",
    _VALIDATOR_POLICY.predicates
    + (
        CoveragePredicate(
            "log-processing",
            "scan-game.process-logs",
            "scan-game.process-logs",
            "game-log-report",
            ("LogProcessor", "process_logs"),
            _logs_observed,
            runtime_operations=(
                None,
                "__init__",
                "process_logs",
                "processGameLogs",
                "__repr__",
            ),
        ),
        CoveragePredicate(
            "report-assembly",
            "scan-game.assemble-reports",
            "scan-game.assemble-reports",
            "game-scan-report",
            (
                "build_archived_report",
                "build_unpacked_report",
                "build_combined_report",
                "get_issue_messages",
            ),
            _reports_observed,
            runtime_operations=(
                "build_archived_report",
                "build_unpacked_report",
                "build_combined_scan_report",
                "get_scan_issue_messages",
            ),
        ),
    ),
)
