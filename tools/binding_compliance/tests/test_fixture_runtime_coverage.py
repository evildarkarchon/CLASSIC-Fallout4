"""Migrated fixture claims cannot stand in for executed conformance receipts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("binding", ("node", "python"))
def test_fixture_summaries_require_receipts_despite_legacy_claims(
    binding: str, tmp_path: Path
) -> None:
    """The public report rejects optimistic claims while retaining unmigrated rows."""
    registry_path = (
        "node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json"
        if binding == "node"
        else "python-bindings/tests/fixtures/runtime_coverage_registry.json"
    )
    registry = json.loads((ROOT / registry_path).read_text(encoding="utf-8"))
    repository_entries = list(registry["entries"])
    contract = json.loads(
        (
            ROOT
            / f"docs/implementation/{binding}_api_parity/baseline/parity_contract.json"
        ).read_text(encoding="utf-8")
    )
    # Simulate an old checkout's blanket positive claim, including identifier-only
    # aliases. Neither path may restore runtime credit to a migrated surface.
    registry["entries"].append(
        {
            "coverageId": "optimistic-fixture-claim",
            "classification": "runtime_verified",
            "contractIds": [row["id"] for row in contract["tier1Mappings"]],
            "bindingIdentifiers": [
                row["nodeExport"]
                for row in contract["tier1Mappings"]
                if row.get("nodeExport")
            ]
            if binding == "node"
            else [
                row["pythonModule"] + "." + row["pythonExportPath"]
                for row in contract["tier1Mappings"]
            ],
            "testSuite": "claimed-suite",
            "testCaseId": "claimed-pass",
            "fixtureRefs": ["claimed-fixture"],
            "notes": "Unexecuted claim",
        }
    )
    registry_file = tmp_path / "registry.json"
    registry_file.write_text(json.dumps(registry), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / f"tools/{binding}_api_parity/generate_baseline.py"),
            "--repo-root",
            str(ROOT),
            "--runtime-registry",
            str(registry_file),
            "--output-dir",
            str(tmp_path / "report"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads((tmp_path / "report/runtime_coverage_summary.json").read_text())
    migrated = [row for row in report["trackedSurface"] if row.get("conformanceFamily")]
    assert {
        "crash-suspect",
        "crashgen-settings",
        "mod-guidance",
        "formid-lookup",
        "named-record",
        "plugin-evidence",
        "installed-yaml-data",
        "config-vocabulary",
        "scan-run-vocabulary",
        "config-operations",
        "file-operations",
        "path-operations",
        "path-normalization",
        "message-operations",
        "database-operations",
        "version-registry",
        "scan-game",
    } <= {row["conformanceFamily"] for row in migrated}
    assert all(
        row["classification"] in {"receipt_required", "structural_analyzer"}
        for row in migrated
    )
    assert all(
        not {"coverageId", "testSuite", "testCaseId", "fixtureRefs", "notes"}
        & row.keys()
        for row in migrated
    )
    identifiers = {row["bindingIdentifier"] for row in migrated}
    assert not any(
        row["trackedType"] == "registry_only"
        and row.get("bindingIdentifier") in identifiers
        for row in report["trackedSurface"]
    )
    # The distinct finding analyzer has no replacement in the lookup pack.
    finding = [
        row
        for row in report["trackedSurface"]
        if row.get("rustSymbol") == "FormIDFindingAnalyzer"
    ]
    assert finding and all(
        row["classification"] == "runtime_verified" for row in finding
    )
    fixture_rows = [
        row for row in migrated if row["conformanceFamily"] != "user-settings"
    ]
    fixture_ids = {row["contractId"] for row in fixture_rows}
    fixture_identifiers = {row["bindingIdentifier"] for row in fixture_rows}
    for entry in repository_entries:
        # A mixed owner keeps exact unmigrated rows, never a blanket selector
        # that would silently recreate retired claims as the owner grows.
        selector = entry.get("contractSelector")
        selected = (
            {
                row["id"]
                for row in contract["tier1Mappings"]
                if all(row.get(key) == value for key, value in selector.items())
            }
            if selector
            else set(entry.get("contractIds", []))
        )
        assert not selected & fixture_ids, entry["coverageId"]
        assert not set(entry.get("bindingIdentifiers", [])) & fixture_identifiers, (
            entry["coverageId"]
        )
