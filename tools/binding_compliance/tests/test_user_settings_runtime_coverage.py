"""Public coverage-report checks for migrated User Settings parity rows."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("binding", ("node", "python"))
@pytest.mark.parametrize(
    "legacy_classification", ("runtime_verified", "contract_mapped")
)
def test_registry_cannot_grant_migrated_settings_runtime_coverage(
    binding: str, legacy_classification: str, tmp_path: Path
) -> None:
    """Promoted rows name their receipt obligation without claiming execution."""

    registry_path = (
        "node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json"
        if binding == "node"
        else "python-bindings/tests/fixtures/runtime_coverage_registry.json"
    )
    registry = json.loads((REPO_ROOT / registry_path).read_text(encoding="utf-8"))
    for entry in registry["entries"]:
        if entry.get("ownerModule") == "user_settings":
            entry["classification"] = legacy_classification
    # Even an explicit optimistic claim must lose to the migrated obligation.
    registry["entries"].append(
        {
            "coverageId": "hostile-settings-claim",
            "classification": "runtime_verified",
            "contractIds": [
                "user-settings-open",
                "user_settings.open",
            ],
            "bindingIdentifiers": [
                "openUserSettings"
                if binding == "node"
                else "classic_user_settings.open_user_settings"
            ],
            "testSuite": "claimed-test.py",
            "testCaseId": "claimed-pass",
            "fixtureRefs": ["claimed-fixture"],
            "notes": "Human-authored runtime verification claim.",
        }
    )
    hostile_registry = tmp_path / "registry.json"
    hostile_registry.write_text(json.dumps(registry), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / f"tools/{binding}_api_parity/generate_baseline.py"),
            "--repo-root",
            str(REPO_ROOT),
            "--runtime-registry",
            str(hostile_registry),
            "--output-dir",
            str(tmp_path / "generated"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    summary = json.loads(
        (tmp_path / "generated/runtime_coverage_summary.json").read_text(
            encoding="utf-8"
        )
    )
    migrated = [
        row
        for row in summary["trackedSurface"]
        if row.get("conformanceFamily") == "user-settings"
    ]
    assert migrated
    assert all(
        row["classification"] in {"receipt_required", "structural_analyzer"}
        for row in migrated
    )
    assert any(row["classification"] == "receipt_required" for row in migrated)
    assert all(
        not {"coverageId", "testSuite", "testCaseId", "fixtureRefs", "notes"}
        & row.keys()
        for row in migrated
    )
    migrated_identifiers = {row["bindingIdentifier"] for row in migrated}
    assert not any(
        row["trackedType"] == "registry_only"
        and row.get("bindingIdentifier") in migrated_identifiers
        for row in summary["trackedSurface"]
    )
    if legacy_classification == "runtime_verified":
        assert summary["summary"]["tier1_missing_runtime_total"] == 0
    else:
        assert summary["summary"]["tier1_missing_runtime_total"] > 0
    assert summary["summary"]["receipt_required_total"] > 0
    required_id = "user-settings-open" if binding == "node" else "user_settings.open"
    assert (
        next(row for row in migrated if row["contractId"] == required_id)[
            "classification"
        ]
        == "receipt_required"
    )
    # Consumer geometry transitions cannot claim semantic adapter coverage.
    legacy_id = (
        "user-settings-commit-frontend-geometry-transition"
        if binding == "node"
        else "user_settings.commit_frontend_geometry_transition"
    )
    assert (
        next(
            row
            for row in summary["trackedSurface"]
            if row.get("contractId") == legacy_id
        )["classification"]
        == legacy_classification
    )
