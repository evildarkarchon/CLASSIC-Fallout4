"""Public conformance lifecycle and fact checks for Installed YAML Data."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from conformance.command import FAMILY_COVERAGE_POLICIES
from conformance.coverage import (
    derive_observed_fact_ids,
    derive_row_coverage,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
)
from conformance.enforcement import enforcement_for_family
from conformance.packs import load_and_validate_pack, materialize_run_plan
from conformance.receipts import validate_prepared_run

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("tests/conformance/packs/installed_yaml_data/v1.json")


def test_recovery_plan_credit_requires_observed_metadata() -> None:
    """Actual recovery metadata covers getters while unrelated successful loads cannot."""
    document = load_and_validate_pack(ROOT, PACK).document()
    policy = FAMILY_COVERAGE_POLICIES[document["familyId"]]
    scenario = next(
        item
        for item in document["scenarios"]
        if item["id"] == "recovery-plan-without-defaults"
    )
    facts = derive_observed_fact_ids(document, scenario, scenario["expected"], policy)
    assert any(
        predicate.id in facts
        and "LocalIgnoreRecoveryPlan" in predicate.rust_symbols
        and predicate.covers_runtime_operation("local_ignore_recovery_plan_diagnostics")
        for predicate in policy.predicates
    )


def test_installed_yaml_pack_has_input_only_fixtures_and_observation_facts() -> None:
    """Each required case proves public behavior without exposing the oracle."""
    pack = load_and_validate_pack(ROOT, PACK)
    document = pack.document()
    policy = FAMILY_COVERAGE_POLICIES[document["familyId"]]
    assert enforcement_for_family(document["familyId"]) == "blocking"
    for scenario in document["scenarios"]:
        fixture = json.loads(
            (
                    pack.fixture_root
                    / document["fixtures"][scenario["input"]["fixtureRef"]]
            ).read_text()
        )
        assert set(fixture) <= {
            "operation",
            "game",
            "selectedGameVersion",
            "files",
            "mutations",
            "recoveryAction",
        }
        assert set(fixture) >= {"operation", "game", "selectedGameVersion", "files"}
        expected = scenario["expected"]
        assert derive_observed_fact_ids(document, scenario, expected, policy)
        for field in expected:
            mutated = copy.deepcopy(expected)
            del mutated[field]
            assert not derive_observed_fact_ids(document, scenario, mutated, policy)
        assert not derive_observed_fact_ids(
            document, {**scenario, "action": "unrelated"}, expected, policy
        )


def test_named_forbidden_effect_facts_reject_contradictory_files() -> None:
    """Recovery selection cannot promote a canonical file or write rejected defaults."""
    document = load_and_validate_pack(ROOT, PACK).document()
    policy = FAMILY_COVERAGE_POLICIES[document["familyId"]]
    scenarios = {item["id"]: item for item in document["scenarios"]}
    for name, path in (
            ("previous-selected-read-only", "cache/CLASSIC/yaml-cache/CLASSIC Main.yaml"),
            (
                    "missing-ignore-invalid-defaults",
                    "installation/CLASSIC Data/CLASSIC Ignore.yaml",
            ),
    ):
        scenario = scenarios[name]
        observation = copy.deepcopy(scenario["expected"])
        observation["files"].append({"path": path, "sha256": "0" * 64, "byteLength": 1})
        observation["files"].sort(key=lambda item: item["path"])
        assert not derive_observed_fact_ids(document, scenario, observation, policy)


@pytest.mark.parametrize("participant", ("cxx", "node", "python"))
def test_installed_yaml_receipts_fail_closed_and_cover_only_executed_operations(
        tmp_path: Path, participant: str
) -> None:
    """Real receipt validation rejects semantic drift, omissions, replay, and new APIs."""
    fixtures = Path("tests/fixtures/installed_yaml_data_conformance")
    (tmp_path / PACK).parent.mkdir(parents=True)
    shutil.copyfile(ROOT / PACK, tmp_path / PACK)
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
    policy = FAMILY_COVERAGE_POLICIES[document["familyId"]]
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
        "id": "installed-yaml-boundary-test",
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
    report = validate_prepared_run(pack, run, coverage_policy=policy)
    assert not report.failures
    assert all(scenario.result == "pass" for scenario in report.scenarios)
    rows = load_source_parity_rows(ROOT)
    coverage = derive_row_coverage(
        document,
        rows,
        policy,
        (report,),
        scope_participant_id=participant,
        retained_analyzers=load_retained_analyzer_kinds(ROOT),
    )
    assert coverage.rows
    assert not coverage.failures
    prototype = next(
        row
        for row in rows
        if row.participant_id == participant
        and row.rust_symbol == "inspect_installed_yaml_data"
    )
    added = replace(
        prototype,
        obligation_id="parity:test:future-inspection",
        runtime_operation="future_inspection",
    )
    expanded = derive_row_coverage(
        document,
        (*rows, added),
        policy,
        (report,),
        scope_participant_id=participant,
        retained_analyzers=load_retained_analyzer_kinds(ROOT),
    )
    assert [failure.obligation_id for failure in expanded.failures] == [
        added.obligation_id
    ]
    for field, replacement in (
            ("main", None),
            ("diagnostics", []),
            ("files", []),
            ("snapshot", None),
    ):
        changed = copy.deepcopy(receipt)
        scenario_index = {"main": 0, "diagnostics": 2, "files": 1, "snapshot": 10}[
            field
        ]
        changed["scenarios"][scenario_index]["observation"][field] = replacement
        run.receipt_path.write_text(json.dumps(changed))
        rejected = validate_prepared_run(pack, run, coverage_policy=policy)
        assert rejected.scenarios[scenario_index].result == "fail"
    changed = copy.deepcopy(receipt)
    changed["scenarios"].pop()
    run.receipt_path.write_text(json.dumps(changed))
    rejected = validate_prepared_run(pack, run, coverage_policy=policy)
    assert rejected.failures or any(
        item.result != "pass" for item in rejected.scenarios
    )
    other_run = materialize_run_plan(
        pack,
        participant_id=participant,
        participant_role="semantic-adapter",
        execution_instance_id=participant,
        source_paths=(PACK,),
    )
    other_run.receipt_path.write_text(json.dumps(receipt))
    assert validate_prepared_run(pack, other_run, coverage_policy=policy).failures
