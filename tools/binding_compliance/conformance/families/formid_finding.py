"""Executable FormID Finding facts preserve resolution, counts and strict failures."""

import re
from collections.abc import Mapping
from functools import partial
from typing import Any

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def _observed(mode: str, observation: Mapping[str, Any]) -> bool:
    """Require a complete typed result/error sum for the actually selected lookup mode."""
    if set(observation) != {"mode", "findings", "error"} or observation["mode"] != mode:
        return False
    if observation["error"] is not None:
        error = observation["error"]
        return (
            observation["findings"] is None
            and isinstance(error, Mapping)
            and set(error) == {"code", "message"}
            and error["code"]
            in {"invalid_configuration", "malformed_result", "operational_failure"}
            and isinstance(error["message"], str)
            and bool(error["message"])
        )
    findings = observation["findings"]
    if not isinstance(findings, list):
        return False
    identifiers = []
    for finding in findings:
        if not isinstance(finding, Mapping) or set(finding) != {
            "identifier",
            "occurrences",
            "plugin",
            "status",
            "value",
        }:
            return False
        identifier = finding["identifier"]
        if (
            not isinstance(identifier, str)
            or not re.fullmatch(r"[0-9A-F]{8}", identifier)
            or type(finding["occurrences"]) is not int
            or finding["occurrences"] <= 0
        ):
            return False
        identifiers.append(identifier)
        status = finding["status"]
        if status not in {"not_applicable", "disabled", "missing", "found"}:
            return False
        if (finding["plugin"] is None) != (status == "not_applicable"):
            return False
        if finding["plugin"] is not None and (
            not isinstance(finding["plugin"], str) or not finding["plugin"]
        ):
            return False
        if (finding["value"] is not None) != (status == "found"):
            return False
        if status == "found" and (
            not isinstance(finding["value"], str) or not finding["value"].strip()
        ):
            return False
    return identifiers == sorted(set(identifiers))


def _input_carriers(observation: Mapping[str, Any]) -> bool:
    """Resolved findings require real plugin and request carriers on the input path."""
    return (
        (_observed("disabled", observation) or _observed("in-memory", observation))
        and isinstance(observation["findings"], list)
        and any(finding["plugin"] is not None for finding in observation["findings"])
    )


def _lookup_entry(observation: Mapping[str, Any]) -> bool:
    """A found in-memory value proves the explicitly constructed lookup entry was consumed."""
    return (
        _observed("in-memory", observation)
        and isinstance(observation["findings"], list)
        and any(finding["status"] == "found" for finding in observation["findings"])
    )


FORMID_FINDING_COVERAGE_POLICY = FamilyCoveragePolicy(
    "formid-finding",
    (
        CoveragePredicate(
            "disabled-analysis",
            "formid-finding.analyze",
            "formid-finding.analyze",
            "formid-findings",
            ("FormIDFindingAnalyzer",),
            partial(_observed, "disabled"),
            runtime_operations=(
                None,
                "__init__",
                "analyze",
                "formid_finding_analyzer_disabled_new",
                "formid_finding_analyzer_construction_result",
                "formid_finding_analyze",
            ),
        ),
        CoveragePredicate(
            "memory-analysis",
            "formid-finding.analyze",
            "formid-finding.analyze",
            "formid-findings",
            ("FormIDFindingAnalyzer",),
            partial(_observed, "in-memory"),
            runtime_operations=(
                None,
                "in_memory",
                "analyze",
                "formid_finding_analyzer_in_memory_new",
                "formid_finding_analyzer_construction_result",
                "formid_finding_analyze",
            ),
        ),
        CoveragePredicate(
            "input-carriers",
            "formid-finding.analyze",
            "formid-finding.analyze",
            "formid-findings",
            ("FormIDFindingAnalysisInput", "FormIDPlugin"),
            _input_carriers,
            runtime_operations=(None, "__init__"),
        ),
        CoveragePredicate(
            "sqlite-constructor",
            "formid-finding.sqlite",
            "formid-finding.sqlite",
            "formid-findings",
            ("FormIDFindingAnalyzer",),
            partial(_observed, "sqlite-missing"),
            runtime_operations=("sqlite", "formid_finding_analyzer_sqlite_new"),
        ),
        CoveragePredicate(
            "lookup-entry",
            "formid-finding.lookup-entry",
            "formid-finding.analyze",
            "formid-findings",
            ("FormIdValueLookupEntry", "FormIdValueLookupInMemoryReply"),
            _lookup_entry,
            binding_obligation_ids=(
                "parity:python:scanlog.formid_finding_analyzer.FormIDFindingLookupEntry",
                "parity:python:scanlog.formid_finding_analyzer.FormIDFindingLookupEntry.__init__",
                "parity:python:scanlog.formid_finding_analyzer.FormIDFindingLookupReplyKind",
            ),
            runtime_operations=(None, "FormIDFindingLookupEntry.__init__"),
        ),
    ),
)
