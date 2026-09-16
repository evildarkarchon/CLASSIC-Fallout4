"""Public launcher checks for mandatory User Settings execution evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import run_scan_run_conformance as shared_launcher
import run_user_settings_conformance as settings_launcher
from check_compliance import main as compliance_main
from conformance.packs import load_and_validate_pack, materialize_run_plan

from test_user_settings_conformance import _receipt


def test_missing_adapter_reports_blocking_settings_failure(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed launch retains diagnostics without claiming semantic success."""

    def fail_to_spawn(*_args: object, **_kwargs: object) -> tuple[None, None, OSError]:
        """Represent an unavailable native executable at the process boundary."""

        return None, None, FileNotFoundError("settings adapter is unavailable")

    monkeypatch.setattr(shared_launcher, "_run_adapter_command", fail_to_spawn)
    artifact_root = (
            settings_launcher.REPO_ROOT
            / "tools/binding_compliance/artifacts"
            / tmp_path.name
    )
    result, artifact_dir = settings_launcher.run_participant(
        "rust", artifact_root=artifact_root
    )
    report = json.loads(
        (artifact_dir / "conformance_report.json").read_text(encoding="utf-8")
    )
    plan = json.loads((artifact_dir / "run_plan.json").read_text(encoding="utf-8"))

    assert result == 1
    assert report["enforcement"] == "blocking"
    assert report["result"] == "fail"
    assert plan["familyId"] == "user-settings"
    assert not (artifact_dir / "receipt.json").exists()
    assert "settings adapter is unavailable" in (
            artifact_dir / "attempt.json"
    ).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "state", ("valid", "missing", "stale", "malformed", "skipped", "mismatching")
)
def test_settings_compliance_requires_current_executed_facts(
        tmp_path: Path, state: str
) -> None:
    """Registry-backed parity cannot replace a current, matching Node receipt."""

    root = settings_launcher.REPO_ROOT
    pack = load_and_validate_pack(root, settings_launcher.PACK_PATH)
    run = materialize_run_plan(
        pack,
        participant_id="node",
        participant_role="semantic-adapter",
        execution_instance_id="node",
        source_paths=settings_launcher.PARTICIPANT_COMMANDS["node"].source_paths,
        artifact_root=root / "tools/binding_compliance/artifacts" / tmp_path.name,
    )
    receipt = _receipt(pack, run)
    if state == "stale":
        identity = receipt["invocation"]["sourceIdentity"]
        receipt["invocation"]["sourceIdentity"] = identity[:-1] + (
            "0" if identity[-1] != "0" else "1"
        )
    elif state == "skipped":
        receipt["scenarios"][0]["executionStatus"] = "skipped"
    elif state == "mismatching":
        receipt["scenarios"][0]["observation"]["view"]["update_check"] = False
    if state != "missing":
        run.receipt_path.write_text(
            "{" if state == "malformed" else json.dumps(receipt), encoding="utf-8"
        )

    result = compliance_main(
        [
            "--repo-root",
            str(root),
            "--profile",
            "conformance",
            "--participant",
            "node",
            "--receipt",
            str(run.receipt_path),
            "--output-dir",
            str(run.artifact_dir),
        ]
    )
    report = json.loads(
        (run.artifact_dir / "binding_compliance_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["conformance"]["enforcement"] == "blocking"
    assert result == (0 if state == "valid" else 1)
    coverage = report["conformance"]["coverage"]
    if state == "valid":
        assert any(row["evidenceKind"] == "executable" for row in coverage["rows"])
    else:
        assert coverage["failures"]
