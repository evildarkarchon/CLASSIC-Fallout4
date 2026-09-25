"""Version Registry facts require actual metadata, selection and error observations."""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest
from conformance.coverage import (
    derive_observed_fact_ids,
    derive_row_coverage,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
)
from conformance.families.version_registry import VERSION_REGISTRY_COVERAGE_POLICY
from conformance.packs import load_and_validate_pack, materialize_run_plan
from conformance.receipts import validate_prepared_run

from receipt_test_support import prepare_receipt_case

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("tests/conformance/packs/version_registry/v1.json")


def test_version_registry_observations_fail_closed() -> None:
    """Missing result fields or relabeled actions cannot prove registry behavior."""
    document = load_and_validate_pack(ROOT, PACK).document()
    policy = VERSION_REGISTRY_COVERAGE_POLICY
    for scenario in document["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(document, scenario, expected, policy)
        for field in expected:
            incomplete = copy.deepcopy(expected)
            del incomplete[field]
            assert not derive_observed_fact_ids(document, scenario, incomplete, policy)
        if isinstance(expected["result"], dict):
            for field in expected["result"]:
                incomplete = copy.deepcopy(expected)
                del incomplete["result"][field]
                assert not derive_observed_fact_ids(
                    document, scenario, incomplete, policy
                )
        assert not derive_observed_fact_ids(
            document, {**scenario, "action": "unrelated"}, expected, policy
        )


def test_version_registry_fixtures_seed_one_isolated_registry() -> None:
    """OnceLock scenarios share immutable input bytes and exact post-call inventory."""
    document = load_and_validate_pack(ROOT, PACK).document()
    sources = set()
    for scenario in document["scenarios"]:
        fixture = json.loads(
            (
                    ROOT / document["fixtureRoot"] / document["fixtures"][scenario["id"]]
            ).read_text()
        )
        sources.add(fixture["registryYaml"])
        assert scenario["expected"]["files"] == [
            {"path": "CLASSIC Main.yaml", "content": fixture["registryYaml"]}
        ]
    assert len(sources) == 1


def test_version_registry_credit_stays_at_executed_operations() -> None:
    """Lookup and matching cannot prove unrelated registry enumeration or mutation."""
    for predicate in VERSION_REGISTRY_COVERAGE_POLICY.predicates:
        if predicate.action != "version-registry.query":
            continue
        assert not predicate.covers_runtime_operation("get_all")
        assert not predicate.covers_runtime_operation("get_all_for_game")
        assert not predicate.covers_runtime_operation("get_crashgen_versions")
        assert not predicate.covers_runtime_operation("future_registry_operation")


def test_remaining_registry_queries_have_separate_executable_facts() -> None:
    """Enumeration and configuration lookups cannot borrow metadata lookup credit."""
    document = load_and_validate_pack(ROOT, PACK).document()
    actions = {scenario["action"] for scenario in document["scenarios"]}
    assert {
               "version-registry.enumerate",
               "version-registry.crashgen",
               "version-registry.xse",
           } <= actions
    for predicate in VERSION_REGISTRY_COVERAGE_POLICY.predicates:
        assert not predicate.covers_runtime_operation("future_registry_operation")


@pytest.mark.parametrize("participant", ("cxx", "node", "python"))
def test_version_registry_receipt_lifecycle_fails_closed(
        tmp_path: Path, participant: str
) -> None:
    """Validate genuine receipt transport while rejecting drift, replay, and new APIs."""
    pack, run, receipt = prepare_receipt_case(
        ROOT, tmp_path, PACK, participant, runner_id="version-registry-boundary-test"
    )
    document = pack.document()
    plan = run.document()
    assert all("expected" not in scenario for scenario in plan["scenarios"])
    policy = VERSION_REGISTRY_COVERAGE_POLICY
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
        and row.runtime_operation
        in {"version_registry_get_by_id", "getVersionById", "get_by_id"}
    )
    added = replace(
        prototype,
        obligation_id="parity:test:future-version-registry-operation",
        runtime_operation="future_registry_operation",
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
            (6, "error", None),
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
