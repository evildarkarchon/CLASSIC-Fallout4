"""Independent byte-golden compilation and public Autoscan Report facts.

Only the central validator sees report templates. Runners return unmodified file
bytes; the three existing FCX path tokens are expanded on the expectation side.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from ..compare import NormalizationError
from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def compile_report_expectations(
    document: Mapping[str, Any], fixture_root: Path
) -> tuple[dict[str, Any], tuple[Path, ...]]:
    """Read contained, separately authored Markdown without exposing it as input."""
    pack = copy.deepcopy(dict(document))
    oracles = []
    inputs = {(fixture_root / p).resolve() for p in pack["fixtures"].values()}
    for scenario in pack["scenarios"]:
        for report in scenario["expected"]["durableEffects"]["reports"]:
            template = report.pop("template")
            relative = PurePosixPath(template)
            if relative.is_absolute() or ".." in relative.parts or "\\" in template:
                raise ValueError("report oracle must be a contained relative path")
            oracle = (fixture_root / template).resolve(strict=True)
            oracle.relative_to(fixture_root)
            if oracle in inputs:
                raise ValueError("report oracle cannot be an adapter input fixture")
            data = oracle.read_bytes()
            report.update(
                bytesHex=data.hex(),
                sha256=hashlib.sha256(data).hexdigest(),
                byteLength=len(data),
            )
            oracles.append(oracle)
    return pack, tuple(oracles)


def expand_report_expectation(
    expected: Mapping[str, Any], actual: Mapping[str, Any]
) -> dict[str, Any]:
    """Expand only authored FCX path tokens, preserving every other expected byte.

    The root is environment metadata, not report content supplied by an adapter.
    Reject malformed roots and retain exact comparison of all raw byte identities.
    """
    root = actual.get("executionRoot")
    if not isinstance(root, str) or not root or any(c in root for c in "\r\n\x00{}"):
        raise NormalizationError(
            "report execution root must be an absolute path", "$.executionRoot"
        )
    pure = (
        PureWindowsPath(root)
        if PureWindowsPath(root).is_absolute()
        else PurePosixPath(root)
    )
    if not pure.is_absolute() or ".." in pure.parts:
        raise NormalizationError(
            "report execution root must be an absolute path", "$.executionRoot"
        )
    result = copy.deepcopy(dict(expected))
    result["executionRoot"] = root
    for report in result["durableEffects"]["reports"]:
        data = bytes.fromhex(report["bytesHex"])
        if result["semanticInputs"]["fcxMode"]:
            for token, value in (
                ("{{FCX_GAME_ROOT}}", str(pure / "fcx-game")),
                ("{{FCX_DOCUMENTS_ROOT}}", str(pure / "fcx-documents")),
                (
                    "{{PATH_SEPARATOR}}",
                    "\\" if isinstance(pure, PureWindowsPath) else "/",
                ),
            ):
                data = data.replace(token.encode(), value.encode("utf-8"))
        report.update(
            bytesHex=data.hex(),
            sha256=hashlib.sha256(data).hexdigest(),
            byteLength=len(data),
        )
    return result


def _report_observed(observation: Mapping[str, Any]) -> bool:
    """Require persisted bytes to agree with identity, log outcome and side effects."""
    if set(observation) != {
        "executionRoot",
        "semanticInputs",
        "run",
        "logs",
        "displayContent",
        "durableEffects",
    }:
        return False
    try:
        effects = observation["durableEffects"]
        reports = effects["reports"]
        logs = observation["logs"]
        if len(reports) != 1 or len(logs) != 1:
            return False
        report, log = reports[0], logs[0]
        data = bytes.fromhex(report["bytesHex"])
        return (
            bool(data)
            and report["sha256"] == hashlib.sha256(data).hexdigest()
            and type(report["byteLength"]) is int
            and report["byteLength"] == len(data)
            and report["path"] == log["autoscanReport"]["path"]
            and log["disposition"] == "succeeded"
            and log["dispositionLabel"] == "succeeded"
            and not log["failures"]
            and all(
                type(log[key]) is int and log[key] >= 0
                for key in ("formidCount", "pluginCount", "suspectCount")
            )
            and observation["run"]["status"] == "completed"
            and observation["run"]["succeeded"] == 1
            and bool(observation["displayContent"])
            and not effects["unexpectedFiles"]
            and bool(effects["forbiddenPaths"])
            and all(item["exists"] is False for item in effects["forbiddenPaths"])
            and len(effects["inputFiles"]) >= 4
        )
    except (KeyError, TypeError, ValueError):
        return False


AUTOSCAN_REPORT_COVERAGE_POLICY = FamilyCoveragePolicy(
    "autoscan-report",
    (
        CoveragePredicate(
            id="autoscan-report.persisted-bytes",
            capability_id="autoscan-report.execute",
            action="autoscan-report.execute",
            observation_family="report-bytes",
            rust_symbols=("LogResult", "LogDisposition"),
            matches=_report_observed,
            runtime_operations=(None, "scan_run_log_disposition_label"),
        ),
    ),
)
