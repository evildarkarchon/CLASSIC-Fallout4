"""Retired metadata cannot re-enter a source gate or claim runtime execution."""

import subprocess
import sys
from pathlib import Path

import pytest

from tools.binding_compliance.catalog import REQUIREMENTS

ROOT = Path(__file__).resolve().parents[3]


def test_legacy_metadata_loaders_and_artifacts_are_absent():
    """Keep the completed migration free of duplicate authority and inventories."""
    for relative in (
        "tools/binding_parity_runtime_coverage.py",
        "tools/binding_compliance/migration_ledger.py",
        "node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json",
        "python-bindings/tests/fixtures/runtime_coverage_registry.json",
        "python-bindings/tests/test_binding_coverage_tooling.py",
        "python-bindings/parity-artifacts/runtime_coverage_summary.json",
        "python-bindings/parity-artifacts/runtime_coverage_summary.md",
        "docs/implementation/binding_compliance/evidence_migration_ledger.json",
        "docs/implementation/binding_compliance/evidence_migration_ledger.md",
        *(
            f"docs/implementation/{binding}_api_parity/baseline/runtime_coverage_summary.{extension}"
            for binding in ("node", "python")
            for extension in ("json", "md")
        ),
    ):
        assert not (ROOT / relative).exists(), relative
    ids = {requirement.id for requirement in REQUIREMENTS}
    assert (
        not {"evidence-migration-ledger", "runtime-coverage-registries-present"} & ids
    )
    assert {
        "node-parity-gate",
        "python-parity-gate",
        "python-stub-validation",
        "repository-receipt-coverage",
    } <= ids


def test_node_smoke_registration_has_no_registry_activation():
    """Every maintained Node smoke group registers even without metadata files."""
    source = (
        ROOT / "node-bindings/classic-node/__test__/runtime.node.test.mjs"
    ).read_text()
    assert "activeTier1Owners" not in source
    assert "runtimeCoverageRegistry" not in source
    assert "runtime_coverage_registry.json" not in source


@pytest.mark.parametrize("binding", ("node", "python"))
@pytest.mark.parametrize("entrypoint", ("generate_baseline.py", "check_parity_gate.py"))
def test_source_entrypoints_reject_legacy_registry_arguments(
    binding, entrypoint, tmp_path
):
    """Even supplied optimistic metadata has no loader or accepted CLI channel."""
    registry = tmp_path / "optimistic.json"
    registry.write_text('{"classification":"runtime_verified"}')
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / f"tools/{binding}_api_parity/{entrypoint}"),
            "--repo-root",
            str(ROOT),
            "--runtime-registry",
            str(registry),
            "--output-dir",
            str(tmp_path / "output"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
    assert "unrecognized arguments: --runtime-registry" in completed.stderr
