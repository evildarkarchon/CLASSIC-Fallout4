"""Config operation facts must arise from complete public observations."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from conformance.coverage import (
    derive_observed_fact_ids,
    derive_row_coverage,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
)
from conformance.families.config_operations import CONFIG_OPERATIONS_COVERAGE_POLICY
from conformance.packs import load_and_validate_pack, materialize_run_plan
from conformance.receipts import validate_prepared_run

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("tests/conformance/packs/config_operations/v1.json")


def test_game_local_update_preserves_omitted_docs_and_unrelated_settings() -> None:
    """Path persistence must observe the preserved docs field and unrelated raw settings bytes."""
    document = load_and_validate_pack(ROOT, PACK).document()
    scenario = next(
        (s for s in document["scenarios"] if s["id"] == "persist-local-preserve"), None
    )
    assert scenario is not None
    files = {file["path"]: file["content"] for file in scenario["expected"]["files"]}
    assert 'Root_Folder_Docs: "C:/Docs/Existing"' in files["local.yaml"]
    assert files["CLASSIC Settings.yaml"] == "{malformed settings sentinel"


def test_yaml_accessors_require_complete_public_projection() -> None:
    """Each raw-field/accessor observation must be present before a YAML view earns credit."""
    document = load_and_validate_pack(ROOT, PACK).document()
    scenario = document["scenarios"][0]
    observation = copy.deepcopy(scenario["expected"])
    assert "yamlValues" in observation["result"]
    fact = "config-operations.yaml-values"
    assert fact in derive_observed_fact_ids(
        document, scenario, observation, CONFIG_OPERATIONS_COVERAGE_POLICY
    )
    del observation["result"]["yamlValues"]["classic_version_date"]
    assert fact not in derive_observed_fact_ids(
        document, scenario, observation, CONFIG_OPERATIONS_COVERAGE_POLICY
    )


def test_main_version_fact_requires_real_nonempty_version_result() -> None:
    """A bundled version observation earns credit only with its complete durable envelope."""
    document = load_and_validate_pack(ROOT, PACK).document()
    scenario = {
        "action": "config-operations.main-version",
        "capabilityIds": ["config-operations.main-version"],
    }
    observation = {
        "result": {"version": "9.1.0"},
        "error": None,
        "files": [
            {
                "path": "CLASSIC Main.yaml",
                "content": 'schema_version: "2.0"\nCLASSIC_Info:\n  version: "9.1.0"\n',
            }
        ],
    }
    document["capabilities"].append(
        {
            "id": "config-operations.main-version",
            "rustSymbols": ["load_main_yaml_version_with_bundled_dir"],
            "observationFamilies": ["values"],
        }
    )
    fact = "config-operations.main-version"
    assert fact in derive_observed_fact_ids(
        document, scenario, observation, CONFIG_OPERATIONS_COVERAGE_POLICY
    )
    observation["result"]["version"] = ""
    assert fact not in derive_observed_fact_ids(
        document, scenario, observation, CONFIG_OPERATIONS_COVERAGE_POLICY
    )


def test_snapshot_content_identity_cannot_claim_changed_bytes() -> None:
    """A content identity fact must authenticate every retained YAML byte sequence."""
    document = load_and_validate_pack(ROOT, PACK).document()
    scenario = document["scenarios"][0]
    observation = copy.deepcopy(scenario["expected"])
    observation["result"]["gameRole"] = "Fallout4"
    observation["result"]["identities"] = {
        item["path"]: {
            "sha256": hashlib.sha256(item["content"].encode()).hexdigest(),
            "byteLen": len(item["content"].encode()),
        }
        for item in observation["files"]
    }
    fact = "config-operations.snapshot-identities"
    assert fact in derive_observed_fact_ids(
        document, scenario, observation, CONFIG_OPERATIONS_COVERAGE_POLICY
    )
    observation["result"]["identities"]["main.yaml"]["sha256"] = "0" * 64
    assert fact not in derive_observed_fact_ids(
        document, scenario, observation, CONFIG_OPERATIONS_COVERAGE_POLICY
    )


def test_snapshot_game_requires_observed_game_identity() -> None:
    """Reject missing or wrong snapshot identity before crediting its CXX accessor."""
    document = load_and_validate_pack(ROOT, PACK).document()
    scenario = document["scenarios"][0]
    observation = copy.deepcopy(scenario["expected"])
    observation["result"]["game"] = "Fallout4"
    policy = CONFIG_OPERATIONS_COVERAGE_POLICY
    fact = "config-operations.snapshot-game"
    assert fact in derive_observed_fact_ids(document, scenario, observation, policy)
    for game in (None, "Skyrim", ""):
        observation["result"]["game"] = game
        assert fact not in derive_observed_fact_ids(
            document, scenario, observation, policy
        )
    del observation["result"]["game"]
    assert fact not in derive_observed_fact_ids(document, scenario, observation, policy)


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
        assert any(
            predicate.covers_runtime_operation(operation)
            for operation in (
                "load_explicit_yaml_data",
                "explicit_yaml_data_snapshot_game",
                "explicit_yaml_data_snapshot_main_identity",
                "load_main_yaml_version",
                "yaml_data_classic_version",
                "persist_game_local_paths",
                "clear_yaml_cache",
            )
        )
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
    from receipt_test_support import copy_source_inventory

    copy_source_inventory(ROOT, tmp_path)
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
        if scenario["id"] in {item["id"] for item in plan["scenarios"]}
    ]
    run.receipt_path.write_text(json.dumps(receipt))
    policy = CONFIG_OPERATIONS_COVERAGE_POLICY
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
        and row.rust_symbol == "load_explicit_yaml_data"
    )
    added = replace(
        prototype,
        obligation_id="parity:test:future-config-operation",
        runtime_operation="future_config_operation",
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
