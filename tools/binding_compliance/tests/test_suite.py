"""Tests for binding compliance suite execution and reports."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from catalog import ComplianceRequirement, CommandSpec, TextExpectation # type: ignore
from suite import ComplianceSuite, RequirementResult, build_summary # type: ignore


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
