"""Public launcher checks for the shadow User Settings execution slice."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import run_scan_run_conformance as shared_launcher
import run_user_settings_conformance as settings_launcher


def test_missing_adapter_still_reports_settings_shadow_failure(
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
    assert report["enforcement"] == "shadow"
    assert report["result"] == "fail"
    assert plan["familyId"] == "user-settings"
    assert not (artifact_dir / "receipt.json").exists()
    assert "settings adapter is unavailable" in (
        artifact_dir / "attempt.json"
    ).read_text(encoding="utf-8")
