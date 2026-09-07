"""Config operation facts must arise from complete public observations."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from conformance.coverage import (
    derive_observed_fact_ids,
    derive_row_coverage,
    load_source_parity_rows,
)
from conformance.families.config_operations import CONFIG_OPERATIONS_COVERAGE_POLICY
from conformance.packs import load_and_validate_pack, materialize_run_plan
from conformance.receipts import validate_prepared_run

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("tests/conformance/packs/config_operations/v1.json")


def test_config_operations_have_complete_observations() -> None:
    """Every case proves a fact, while missing fields and relabeled actions do not."""
    document = load_and_validate_pack(ROOT, PACK).document()
    policy = CONFIG_OPERATIONS_COVERAGE_POLICY
    for scenario in document["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(document, scenario, expected, policy)
        for field in expected:
            incomplete = copy.deepcopy(expected)
            del incomplete[field]
            assert not derive_observed_fact_ids(document, scenario, incomplete, policy)
        assert not derive_observed_fact_ids(
            document, {**scenario, "action": "unrelated"}, expected, policy
        )


def test_config_read_failure_cannot_claim_generated_ignore() -> None:
    """Missing explicit Ignore files remain absent; a fabricated repair earns no fact."""
    document = load_and_validate_pack(ROOT, PACK).document()
    scenario = next(
        item for item in document["scenarios"] if item["id"] == "missing-ignore"
    )
    observation = copy.deepcopy(scenario["expected"])
    observation["files"].append({"path": "ignore.yaml", "content": "generated"})
    observation["files"].sort(key=lambda item: item["path"])
    assert not derive_observed_fact_ids(
        document, scenario, observation, CONFIG_OPERATIONS_COVERAGE_POLICY
    )


def test_config_fact_limits_credit_to_observed_api() -> None:
    """An explicit load cannot cover unrelated loaders or configuration setters."""
    for predicate in CONFIG_OPERATIONS_COVERAGE_POLICY.predicates:
        assert predicate.covers_runtime_operation("load_explicit_yaml_data")
        assert not predicate.covers_runtime_operation("load_installed_yaml_data")
        assert not predicate.covers_runtime_operation("yaml_data_set_value")


@pytest.mark.parametrize("participant", ("cxx", "node", "python"))
def test_config_receipt_lifecycle_fails_closed(
    tmp_path: Path, participant: str
) -> None:
    """Validate genuine receipt transport while rejecting drift, replay, and new APIs."""
    (tmp_path / PACK).parent.mkdir(parents=True)
    shutil.copyfile(ROOT / PACK, tmp_path / PACK)
    fixtures = Path("tests/fixtures/config_operations")
    shutil.copytree(ROOT / fixtures, tmp_path / fixtures)
    for arguments in (
        ("init",),
        ("config", "user.email", "conformance@example.invalid"),
        ("config", "user.name", "Conformance Tests"),
        ("add", "."),
        ("commit", "-m", "fixture"),
    ):
        subprocess.run(
            ["git", "-C", str(tmp_path), *arguments], check=True, capture_output=True
        )
    pack = load_and_validate_pack(tmp_path, PACK)
    document = pack.document()
    run = materialize_run_plan(
        pack,
        participant_id=participant,
        participant_role="semantic-adapter",
        execution_instance_id=participant,
        source_paths=(PACK,),
    )
    plan = run.document()
    assert all("expected" not in scenario for scenario in plan["scenarios"])
    receipt = {
        key: plan[key]
        for key in (
            "schemaVersion",
            "familyId",
            "familyVersion",
            "expectationDigest",
            "invocation",
            "participant",
        )
    }
    receipt["runner"] = {
        "id": "config-boundary-test",
        "version": 1,
        "platform": "windows",
        "toolchain": participant,
    }
    receipt["scenarios"] = [
        {
            "id": scenario["id"],
            "executionStatus": "completed",
            "capabilityIds": scenario["capabilityIds"],
            "observation": scenario["expected"],
            "failure": None,
        }
        for scenario in document["scenarios"]
    ]
    run.receipt_path.write_text(json.dumps(receipt))
    policy = CONFIG_OPERATIONS_COVERAGE_POLICY
    report = validate_prepared_run(pack, run, coverage_policy=policy)
    assert not report.failures
    assert all(scenario.result == "pass" for scenario in report.scenarios)
    rows = load_source_parity_rows(ROOT)
    coverage = derive_row_coverage(
        document, rows, policy, (report,), scope_participant_id=participant
    )
    assert coverage.rows
    assert not coverage.failures
    prototype = next(
        row
        for row in rows
        if row.participant_id == participant
        and row.rust_symbol == "load_explicit_yaml_data"
    )
    added = replace(
        prototype,
        obligation_id="parity:test:future-config-operation",
        runtime_operation="future_config_operation",
    )
    expanded = derive_row_coverage(
        document, (*rows, added), policy, (report,), scope_participant_id=participant
    )
    assert [failure.obligation_id for failure in expanded.failures] == [
        added.obligation_id
    ]
    for index, field, replacement in (
        (0, "result", None),
        (1, "error", None),
        (2, "files", []),
    ):
        changed = copy.deepcopy(receipt)
        changed["scenarios"][index]["observation"][field] = replacement
        run.receipt_path.write_text(json.dumps(changed))
        rejected = validate_prepared_run(pack, run, coverage_policy=policy)
        assert rejected.scenarios[index].result == "fail"
    changed = copy.deepcopy(receipt)
    changed["scenarios"].pop()
    run.receipt_path.write_text(json.dumps(changed))
    rejected = validate_prepared_run(pack, run, coverage_policy=policy)
    assert rejected.failures or any(
        item.result != "pass" for item in rejected.scenarios
    )
    other = materialize_run_plan(
        pack,
        participant_id=participant,
        participant_role="semantic-adapter",
        execution_instance_id=participant,
        source_paths=(PACK,),
    )
    other.receipt_path.write_text(json.dumps(receipt))
    assert validate_prepared_run(pack, other, coverage_policy=policy).failures


@pytest.mark.parametrize("binding", ("node", "python"))
def test_legacy_registry_cannot_grant_config_runtime_coverage(
    tmp_path: Path, binding: str
) -> None:
    """Legacy green suite labels never substitute for explicit-loader receipts."""
    registry_path = (
        "node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json"
        if binding == "node"
        else "python-bindings/tests/fixtures/runtime_coverage_registry.json"
    )
    registry = json.loads((ROOT / registry_path).read_text())
    for entry in registry["entries"]:
        if entry.get("ownerModule") == "config":
            entry.update(
                classification="runtime_verified",
                testSuite="claimed-suite",
                testCaseId="claimed-pass",
                notes="Optimistic registry claim",
            )
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(registry))
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / f"tools/{binding}_api_parity/generate_baseline.py"),
            "--repo-root",
            str(ROOT),
            "--runtime-registry",
            str(path),
            "--output-dir",
            str(tmp_path / "generated"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    summary = json.loads(
        (tmp_path / "generated/runtime_coverage_summary.json").read_text()
    )
    migrated = [
        row
        for row in summary["trackedSurface"]
        if row.get("conformanceFamily") == "config-operations"
    ]
    assert migrated
    assert all(row["classification"] == "receipt_required" for row in migrated)
    assert all(
        not {"coverageId", "testSuite", "testCaseId", "fixtureRefs", "notes"}
        & row.keys()
        for row in migrated
    )
    assert {row["rustSymbol"] for row in migrated} == {"load_explicit_yaml_data"}
