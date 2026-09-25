"""Tests for same-run retained-gate evidence used by full compliance."""

from __future__ import annotations

import json
import sys
import tempfile
from collections.abc import Iterator
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import pytest
from check_compliance import main as check_compliance_main  # type: ignore
from catalog import CommandSpec, ComplianceRequirement, requirements_for_profile  # type: ignore
from gate_evidence import (  # type: ignore
    GateEvidenceError,
    current_source_revision,
    load_gate_evidence,
    write_gate_evidence,
)
from run_retained_gate import run_one_requirement  # type: ignore
from suite import RequirementResult  # type: ignore


REPO_ROOT = Path(__file__).resolve().parents[3]
REVISION = "a" * 40
OWNED_IDS = {
    "cxx-ci": (
        "cxx-opaque-map-reachability",
        "node-package-metadata",
        "user-settings-exclusive-ownership",
        "scan-run-contract-variants",
        "scan-run-workflow-policy",
        "cxx-parity-gate",
    ),
    "node-ci": ("node-parity-gate", "node-dts-freshness"),
    "python-ci": (
        "python-parity-gate",
        "python-stub-validation",
        "python-tooling-sync",
        "python-schema-version-drift",
    ),
}
SINGLE_IDS = (
    "node-bun-runtime-tests",
    "node-node-runtime-tests",
    "python-bindings-rebuild",
    "python-runtime-smoke-tests",
)


@pytest.fixture
def repo_artifact_root() -> Iterator[Path]:
    """Place downloaded evidence inside the checkout as the full CI job does."""
    parent = (REPO_ROOT / "tools/binding_compliance/artifacts").resolve()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gate-evidence-", dir=parent) as directory:
        root = Path(directory).resolve()
        if not root.is_relative_to(parent):
            raise AssertionError("gate evidence test path escaped its artifact root")
        yield root


def _command_document(command: CommandSpec) -> dict[str, object]:
    """Build test evidence from catalog fields without calling the loader's encoder."""
    return {
        "argv": list(command.argv),
        "cwd": command.cwd,
        "env": dict(command.env),
        "timeoutSeconds": command.timeout_seconds,
    }


def _complete_evidence(tmp_path: Path, revision: str = REVISION) -> Path:
    """Write seven independent artifacts containing the current full denominator."""
    root = tmp_path / "downloaded"
    requirements = {
        requirement.id: requirement
        for requirement in requirements_for_profile("full")
        if requirement.command is not None
    }
    owners = [
        (profile, ids)
        for profile, ids in OWNED_IDS.items()
    ] + [("single-gate", (gate_id,)) for gate_id in SINGLE_IDS]
    for index, (profile, ids) in enumerate(owners):
        artifact = root / f"artifact-{index}" / "gate_evidence.json"
        artifact.parent.mkdir(parents=True)
        artifact.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "profile": profile,
                    "result": "pass",
                    "sourceRevision": revision,
                    "runId": "173",
                    "runAttempt": 1,
                    "results": [
                        {
                            "id": gate_id,
                            "status": "passed",
                            "command": _command_document(requirements[gate_id].command),
                        }
                        for gate_id in ids
                    ],
                }
            ),
            encoding="utf-8",
        )
    return root


def _load(root: Path) -> dict[str, object]:
    """Load a controlled artifact tree as full compliance would."""
    return load_gate_evidence(
        root.parent,
        root,
        requirements_for_profile("full"),
        source_revision=REVISION,
        run_id="173",
        run_attempt=2,
    )


def test_full_accepts_earlier_successful_attempt_in_same_run(tmp_path: Path) -> None:
    """A failed-only retry can reuse a prior successful job at the same revision."""
    results = _load(_complete_evidence(tmp_path))

    assert set(results) == set((*OWNED_IDS["cxx-ci"], *OWNED_IDS["node-ci"], *OWNED_IDS["python-ci"], *SINGLE_IDS))
    assert all(result.status == "passed" for result in results.values())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sourceRevision", "b" * 40),
        ("runId", "174"),
        ("runAttempt", 3),
        ("runAttempt", 0),
        ("runAttempt", "one"),
        ("result", "fail"),
    ],
)
def test_full_rejects_wrong_or_failed_producer_identity(
        tmp_path: Path, field: str, value: object
) -> None:
    """An artifact from another source, run, future attempt, or failed job is invalid."""
    root = _complete_evidence(tmp_path)
    artifact = root / "artifact-0" / "gate_evidence.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload[field] = value
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(GateEvidenceError):
        _load(root)


def test_full_rejects_missing_gate_file(tmp_path: Path) -> None:
    """A missing runtime test cannot inherit success from its workflow result."""
    root = _complete_evidence(tmp_path)
    (root / "artifact-3" / "gate_evidence.json").unlink()

    with pytest.raises(GateEvidenceError):
        _load(root)


def test_full_rejects_duplicate_gate_file(tmp_path: Path) -> None:
    """Two artifacts for one retained gate must not be silently coalesced."""
    root = _complete_evidence(tmp_path)
    duplicate = root / "duplicate" / "gate_evidence.json"
    duplicate.parent.mkdir()
    duplicate.write_bytes((root / "artifact-3" / "gate_evidence.json").read_bytes())

    with pytest.raises(GateEvidenceError):
        _load(root)


def test_full_rejects_failed_or_changed_command(tmp_path: Path) -> None:
    """A matching gate ID is insufficient when execution failed or argv changed."""
    root = _complete_evidence(tmp_path)
    artifact = root / "artifact-3" / "gate_evidence.json"
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    payload["results"][0]["command"]["argv"] = ["echo", "pretend pass"]
    artifact.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(GateEvidenceError):
        _load(root)

    payload["results"][0]["command"] = _command_document(
        next(req.command for req in requirements_for_profile("full") if req.id == SINGLE_IDS[0])
    )
    payload["results"][0]["status"] = "failed"
    artifact.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(GateEvidenceError):
        _load(root)


def test_producer_writes_only_owned_passed_commands(tmp_path: Path) -> None:
    """Shared guards have one evidence owner even though other profiles rerun them."""
    requirements = requirements_for_profile("node-ci")
    report = {
        "profile": "node-ci",
        "summary": {"result": "pass"},
        "requirements": [
            {"id": requirement.id, "status": "passed"}
            for requirement in requirements
        ],
    }
    output = tmp_path / "gate_evidence.json"
    write_gate_evidence(
        REPO_ROOT,
        output,
        report,
        requirements,
        source_revision=REVISION,
        environment={"GITHUB_RUN_ID": "173", "GITHUB_RUN_ATTEMPT": "2"},
    )
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["profile"] == "node-ci"
    assert payload["runId"] == "173"
    assert payload["runAttempt"] == 2
    assert [entry["id"] for entry in payload["results"]] == list(OWNED_IDS["node-ci"])
    assert payload["results"][0]["command"] == {
        "argv": ["python", "tools/node_api_parity/check_parity_gate.py", "--repo-root", "."],
        "cwd": None,
        "env": {},
        "timeoutSeconds": None,
    }


def test_producer_requires_github_run_identity(tmp_path: Path) -> None:
    """Local reports without a workflow identity cannot become imported CI proof."""
    requirements = requirements_for_profile("node-ci")
    report = {
        "profile": "node-ci",
        "summary": {"result": "pass"},
        "requirements": [
            {"id": requirement.id, "status": "passed"}
            for requirement in requirements
        ],
    }

    with pytest.raises(GateEvidenceError):
        write_gate_evidence(
            REPO_ROOT,
            tmp_path / "gate_evidence.json",
            report,
            requirements,
            source_revision=REVISION,
            environment={},
        )


def test_single_gate_runner_executes_command_and_writes_evidence(tmp_path: Path) -> None:
    """The raw runtime gate gets a report from its actual process exit status."""
    requirement = ComplianceRequirement(
        id="node-bun-runtime-tests",
        title="Bun runtime tests",
        surface="node",
        classification="existing_gate",
        profiles=("full",),
        blocking=True,
        summary="Bun runtime tests",
        command=CommandSpec(argv=(sys.executable, "-c", "print('executed')")),
    )
    output = tmp_path / "gate_evidence.json"
    result = run_one_requirement(
        REPO_ROOT,
        requirement,
        output,
        environment={"GITHUB_RUN_ID": "173", "GITHUB_RUN_ATTEMPT": "2"},
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 0
    assert payload["result"] == "pass"
    assert payload["results"][0]["status"] == "passed"
    assert payload["results"][0]["command"]["argv"] == [sys.executable, "-c", "print('executed')"]


def test_single_gate_runner_records_failed_command(tmp_path: Path) -> None:
    """A failed process cannot be uploaded as a passing retained gate."""
    requirement = ComplianceRequirement(
        id="node-bun-runtime-tests",
        title="Bun runtime tests",
        surface="node",
        classification="existing_gate",
        profiles=("full",),
        blocking=True,
        summary="Bun runtime tests",
        command=CommandSpec(argv=(sys.executable, "-c", "raise SystemExit(7)")),
    )
    output = tmp_path / "gate_evidence.json"
    result = run_one_requirement(
        REPO_ROOT,
        requirement,
        output,
        environment={"GITHUB_RUN_ID": "173", "GITHUB_RUN_ATTEMPT": "2"},
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result == 1
    assert payload["result"] == "fail"
    assert payload["results"][0]["status"] == "failed"


def test_producer_cli_publishes_profile_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The profile CLI writes reusable proof beside its ordinary compliance report."""
    monkeypatch.setenv("GITHUB_RUN_ID", "173")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    requirements = requirements_for_profile("node-ci")
    report = {
        "profile": "node-ci",
        "summary": {"result": "pass", "total": len(requirements), "passed": len(requirements), "failed": 0,
                    "blocking_failed": 0, "coverage_gaps": 0, "skipped": 0},
        "gaps": [],
        "requirements": [
            asdict(RequirementResult(
                id=requirement.id,
                title=requirement.title,
                surface=requirement.surface,
                classification=requirement.classification,
                status="passed",
                blocking=requirement.blocking,
                summary=requirement.summary,
            ))
            for requirement in requirements
        ],
    }
    evidence_path = tmp_path / "node" / "gate_evidence.json"
    with patch("check_compliance.ComplianceSuite") as fake_suite:
        fake_suite.return_value.run.return_value = report
        result = check_compliance_main(
            ["--repo-root", str(REPO_ROOT), "--profile", "node-ci",
             "--output-dir", str(tmp_path / "report"),
             "--gate-evidence-out", str(evidence_path)]
        )

    assert result == 0
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert payload["sourceRevision"] == current_source_revision(REPO_ROOT)
    assert [entry["id"] for entry in payload["results"]] == list(OWNED_IDS["node-ci"])


def test_full_cli_imports_gate_evidence_without_running_commands(
        tmp_path: Path, repo_artifact_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The full entrypoint combines current receipts with authenticated producer gates."""
    monkeypatch.setenv("GITHUB_RUN_ID", "173")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    evidence_root = _complete_evidence(repo_artifact_root, current_source_revision(REPO_ROOT))
    full_commands = tuple(
        requirement for requirement in requirements_for_profile("full")
        if requirement.command is not None
    )
    conformance = {
        "enforcement": "blocking", "result": "pass", "repositoryComplete": True,
    }
    with (
        patch("check_compliance.requirements_for_profile", return_value=full_commands),
        patch("check_compliance.build_repository_report", return_value=conformance),
        patch("suite.ComplianceSuite._run_command_requirement", side_effect=AssertionError("reran gate")),
    ):
        result = check_compliance_main(
            ["--repo-root", str(REPO_ROOT), "--profile", "full",
             "--output-dir", str(tmp_path / "report"),
             "--gate-evidence-directory", str(evidence_root)]
        )

    report = json.loads((tmp_path / "report" / "binding_compliance_report.json").read_text(encoding="utf-8"))
    assert result == 0
    assert report["summary"]["repository_complete"] is True
    assert report["summary"]["passed"] == len(full_commands)


def test_full_cli_writes_failing_report_when_gate_evidence_is_missing(
        tmp_path: Path, repo_artifact_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing producer artifact remains visible in a structured red full report."""
    monkeypatch.setenv("GITHUB_RUN_ID", "173")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    evidence_root = _complete_evidence(repo_artifact_root, current_source_revision(REPO_ROOT))
    (evidence_root / "artifact-3" / "gate_evidence.json").unlink()
    full_commands = tuple(
        requirement for requirement in requirements_for_profile("full")
        if requirement.command is not None
    )
    conformance = {
        "enforcement": "blocking", "result": "pass", "repositoryComplete": True,
    }
    output_dir = tmp_path / "report"
    with (
        patch("check_compliance.requirements_for_profile", return_value=full_commands),
        patch("check_compliance.build_repository_report", return_value=conformance),
        patch("suite.ComplianceSuite._run_command_requirement", side_effect=AssertionError("reran gate")),
    ):
        result = check_compliance_main(
            ["--repo-root", str(REPO_ROOT), "--profile", "full",
             "--output-dir", str(output_dir),
             "--gate-evidence-directory", str(evidence_root)]
        )

    report = json.loads((output_dir / "binding_compliance_report.json").read_text(encoding="utf-8"))
    assert result == 1
    assert report["summary"]["result"] == "fail"
    assert report["summary"]["repository_complete"] is False
    assert "missing retained-gate results" in report["gateEvidenceError"]
    assert "missing retained-gate results" in (output_dir / "binding_compliance_report.md").read_text(encoding="utf-8")
