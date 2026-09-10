"""Tests for binding compliance suite execution and reports."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from catalog import (  # type: ignore
    CommandSpec,
    ComplianceRequirement,
    TextExpectation,
    requirements_for_profile,  # type: ignore
)
from suite import ComplianceSuite, RequirementResult, build_summary  # type: ignore


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (b"\xe2\x9c\x8d diagnostics", "\u270d diagnostics"),
        (b"native \x8d diagnostics", "native \ufffd diagnostics"),
    ],
)
def test_command_evidence_survives_windows_locale(
    tmp_path: Path, payload: bytes, expected: str
) -> None:
    """Retain both output streams even when native bytes cannot decode as cp1252."""
    requirement = ComplianceRequirement(
        id="output-check",
        title="Output check",
        surface="policy",
        classification="existing_gate",
        profiles=("ci",),
        blocking=True,
        summary="Capture native tool diagnostics.",
        command=CommandSpec(
            argv=(
                sys.executable,
                "-c",
                f"import os; os.write(1, {payload!r}); os.write(2, {payload!r})",
            ),
        ),
    )
    # Model Windows' legacy locale even on UTF-8 developer machines; the child
    # still writes real bytes through the production subprocess capture path.
    with patch("subprocess._text_encoding", return_value="cp1252"):
        report = ComplianceSuite(
            repo_root=tmp_path, profile="ci", requirements=(requirement,)
        ).run()

    result = report["requirements"][0]
    assert result["status"] == "passed"
    assert result["stdout"] == expected
    assert result["stderr"] == expected


def test_full_profile_requires_repository_receipts(tmp_path: Path) -> None:
    """Passing source checks alone cannot establish repository conformance."""
    report = ComplianceSuite(repo_root=tmp_path, profile="full", requirements=()).run()
    assert report["summary"]["result"] == "fail"
    assert report["summary"]["repository_complete"] is False


def test_full_profile_cannot_skip_retained_commands(tmp_path: Path) -> None:
    """Receipt success cannot compensate for an unexecuted retained gate."""
    requirement = ComplianceRequirement(
        id="retained",
        title="Retained",
        surface="policy",
        classification="existing_gate",
        profiles=("full",),
        blocking=True,
        summary="Retained analyzer",
        command=CommandSpec(argv=("python", "check.py")),
    )
    report = ComplianceSuite(
        repo_root=tmp_path,
        profile="full",
        requirements=(requirement,),
        skip_commands=True,
        conformance_report={
            "enforcement": "blocking",
            "result": "pass",
            "repositoryComplete": True,
        },
    ).run()
    assert report["summary"]["result"] == "fail"
    assert report["summary"]["repository_complete"] is False


def test_build_summary_keeps_gap_reporting_non_blocking_by_default() -> None:
    results = [
        RequirementResult(
            id="passing-check",
            surface="node",
            classification="new_check",
            status="passed",
            blocking=True,
            summary="Node declaration artifact exists.",
        ),
        RequirementResult(
            id="known-gap",
            surface="runtime_coverage",
            classification="coverage_gap",
            status="gap",
            blocking=False,
            summary="C++ runtime coverage registry is not available yet.",
            gaps=["No C++ runtime coverage registry is documented."],
        ),
    ]

    summary = build_summary(results)

    assert summary["result"] == "pass"
    assert summary["passed"] == 1
    assert summary["coverage_gaps"] == 1
    assert summary["failed"] == 0


def test_static_requirement_checks_paths_and_expected_text(tmp_path: Path) -> None:
    (tmp_path / "docs/api").mkdir(parents=True)
    doc_path = tmp_path / "docs/api/binding-compliance-suite.md"
    doc_path.write_text(
        "Run python tools/binding_compliance/check_compliance.py --repo-root .\n",
        encoding="utf-8",
    )

    requirement = ComplianceRequirement(
        id="docs-canonical-command",
        title="Canonical binding compliance docs",
        surface="docs",
        classification="new_check",
        profiles=("static",),
        blocking=True,
        summary="Contributor docs name the canonical command.",
        paths=("docs/api/binding-compliance-suite.md",),
        text_expectations=(
            TextExpectation(
                path="docs/api/binding-compliance-suite.md",
                contains=("tools/binding_compliance/check_compliance.py",),
            ),
        ),
    )

    suite = ComplianceSuite(
        repo_root=tmp_path,
        profile="static",
        requirements=(requirement,),
        skip_commands=True,
    )
    report = suite.run()

    assert report["summary"]["result"] == "pass"
    assert report["requirements"][0]["status"] == "passed"


def test_skip_commands_marks_command_requirements_as_skipped(tmp_path: Path) -> None:
    requirement = ComplianceRequirement(
        id="command-check",
        title="Command check",
        surface="cxx",
        classification="existing_gate",
        profiles=("ci",),
        blocking=True,
        summary="Runs an existing gate.",
        command=CommandSpec(argv=("python", "tool.py")),
    )

    suite = ComplianceSuite(
        repo_root=tmp_path,
        profile="ci",
        requirements=(requirement,),
        skip_commands=True,
    )
    report = suite.run()

    assert report["summary"]["result"] == "pass"
    assert report["summary"]["skipped"] == 1
    assert report["requirements"][0]["status"] == "skipped"


def test_timeout_preserves_stdout_and_stderr_separately(tmp_path: Path) -> None:
    requirement = ComplianceRequirement(
        id="timeout-check",
        title="Timeout check",
        surface="cxx",
        classification="existing_gate",
        profiles=("ci",),
        blocking=True,
        summary="Runs a command that times out.",
        command=CommandSpec(argv=("python", "tool.py"), timeout_seconds=1),
    )

    def raise_timeout(*_args: object, **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired(
            cmd=["python", "tool.py"],
            timeout=1,
            output="captured stdout",
            stderr="captured stderr",
        )

    suite = ComplianceSuite(
        repo_root=tmp_path,
        profile="ci",
        requirements=(requirement,),
    )

    with patch("suite.subprocess.run", side_effect=raise_timeout):
        report = suite.run()

    result = report["requirements"][0]
    assert result["status"] == "failed"
    assert result["stdout"] == "captured stdout"
    assert result["stderr"] == "captured stderr"


def test_blocking_conformance_failure_fails_alongside_legacy_results(
    tmp_path: Path,
) -> None:
    """A promoted receipt failure is conjunctive with retained legacy gates."""

    requirement = ComplianceRequirement(
        id="existing-gate",
        title="Existing gate",
        surface="node",
        classification="existing_gate",
        profiles=("ci",),
        blocking=True,
        summary="The current parity gate remains authoritative.",
    )
    shadow = {
        "schemaVersion": 1,
        "enforcement": "blocking",
        "result": "fail",
        "failures": [{"kind": "coverage_mapping_gap"}],
    }

    report = ComplianceSuite(
        repo_root=tmp_path,
        profile="ci",
        requirements=(requirement,),
        conformance_report=shadow,
    ).run()

    assert report["summary"]["result"] == "fail"
    assert report["conformance"] == shadow


def test_shadow_success_cannot_turn_a_blocking_failure_green(tmp_path: Path) -> None:
    """A passing shadow section never overrides a failed current requirement."""

    requirement = ComplianceRequirement(
        id="missing-existing-gate",
        title="Missing existing gate",
        surface="python",
        classification="existing_gate",
        profiles=("ci",),
        blocking=True,
        summary="The current parity artifact is still required.",
        paths=("missing.json",),
    )

    report = ComplianceSuite(
        repo_root=tmp_path,
        profile="ci",
        requirements=(requirement,),
        conformance_report={
            "schemaVersion": 1,
            "enforcement": "shadow",
            "result": "pass",
            "failures": [],
        },
    ).run()

    assert report["summary"]["result"] == "fail"
    assert report["conformance"]["result"] == "pass"


def test_future_shadow_family_cannot_block_a_passing_retained_gate(
    tmp_path: Path,
) -> None:
    """Coverage diagnostics remain nonblocking until their family is promoted."""

    requirement = ComplianceRequirement(
        id="existing-gate",
        title="Existing gate",
        surface="cxx",
        classification="existing_gate",
        profiles=("ci",),
        blocking=True,
        summary="The current source parity check remains green.",
    )
    shadow = {
        "schemaVersion": 1,
        "enforcement": "shadow",
        "result": "fail",
        "failures": [],
        "coverage": {
            "failures": [
                {
                    "kind": "coverage_mapping_gap",
                    "obligationId": "parity:cxx:new-row",
                    "blocking": True,
                }
            ]
        },
    }

    report = ComplianceSuite(
        repo_root=tmp_path,
        profile="ci",
        requirements=(requirement,),
        conformance_report=shadow,
    ).run()

    assert report["summary"]["result"] == "pass"
    assert report["summary"]["blocking_conformance_coverage_gaps"] == 1


def test_conformance_profile_uses_its_scoped_report_as_process_result(
    tmp_path: Path,
) -> None:
    """A receipt-only native job fails when its exact scope is incomplete."""

    shadow = {
        "schemaVersion": 1,
        "enforcement": "shadow",
        "result": "fail",
        "failures": [{"kind": "missing_receipt"}],
    }

    report = ComplianceSuite(
        repo_root=tmp_path,
        profile="conformance",
        requirements=requirements_for_profile("conformance"),
        conformance_report=shadow,
    ).run()

    assert report["requirements"] == []
    assert report["summary"]["result"] == "fail"
