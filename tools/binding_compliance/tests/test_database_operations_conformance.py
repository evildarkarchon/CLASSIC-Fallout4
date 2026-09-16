"""Database receipts require complete observable pool and durable-file evidence."""

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
from conformance.families.database_operations import DATABASE_OPERATIONS_COVERAGE_POLICY
from conformance.packs import load_and_validate_pack, materialize_run_plan
from conformance.receipts import validate_prepared_run

from receipt_test_support import prepare_receipt_case

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("tests/conformance/packs/database_operations/v1.json")


def test_database_constants_have_an_independent_shared_observation() -> None:
    """Cache defaults must be observed as values, not inferred from pool behavior."""
    document = load_and_validate_pack(ROOT, PACK).document()
    scenario = next(
        (case for case in document["scenarios"] if case["id"] == "cache-defaults"), None
    )
    assert scenario is not None
    expected = scenario["expected"]
    assert expected == {
        "defaultTtl": 300,
        "batchTtl": 1800,
        "maximumTtl": 3600,
        "capacity": 20000,
        "cleanupThreshold": 2048,
        "cleanupInterval": 30,
    }
    assert derive_observed_fact_ids(
        document, scenario, expected, DATABASE_OPERATIONS_COVERAGE_POLICY
    )


def test_database_control_methods_have_executable_fact_ownership() -> None:
    """Pool controls and cache inspection are exercised alongside lookup effects."""
    for operation in (
            "set_cache_capacity",
            "get_cache_capacity",
            "set_game_table",
            "get_stats",
            "optimize",
            "rebalance_connections",
            "recalculate_max_connections",
            "db_pool_cache_size",
    ):
        assert any(
            predicate.covers_runtime_operation(operation)
            for predicate in DATABASE_OPERATIONS_COVERAGE_POLICY.predicates
        )


def test_database_facts_require_complete_observations() -> None:
    """No incomplete envelope or relabeled operation may earn a pool fact."""
    document = load_and_validate_pack(ROOT, PACK).document()
    for scenario in document["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            document, scenario, expected, DATABASE_OPERATIONS_COVERAGE_POLICY
        )
        for field in expected:
            observation = copy.deepcopy(expected)
            del observation[field]
            assert not derive_observed_fact_ids(
                document, scenario, observation, DATABASE_OPERATIONS_COVERAGE_POLICY
            )
        assert not derive_observed_fact_ids(
            document,
            {**scenario, "action": "unrelated"},
            expected,
            DATABASE_OPERATIONS_COVERAGE_POLICY,
        )


def test_database_fact_does_not_credit_unobserved_pool_methods() -> None:
    """Exercising current pool controls must not credit unknown future methods."""
    for predicate in DATABASE_OPERATIONS_COVERAGE_POLICY.predicates:
        for operation in ("future_pool_method",):
            assert not predicate.covers_runtime_operation(operation)


def test_database_lookup_order_misses_and_close_are_material() -> None:
    """Changing a value, omitting a miss, or retaining an open pool loses the fact."""
    document = load_and_validate_pack(ROOT, PACK).document()
    scenario = next(item for item in document["scenarios"] if item["id"] == "populated")
    for field, value in (
            ("single", []),
            ("batch", []),
            ("closedAvailable", True),
            ("files", []),
    ):
        changed = copy.deepcopy(scenario["expected"])
        changed[field] = value
        assert not derive_observed_fact_ids(
            document, scenario, changed, DATABASE_OPERATIONS_COVERAGE_POLICY
        )


@pytest.mark.parametrize("participant", ("cxx", "node", "python"))
def test_database_receipt_lifecycle_fails_closed(
        tmp_path: Path, participant: str
) -> None:
    """Validate genuine receipt transport while rejecting drift, replay, and new APIs."""
    pack, run, receipt = prepare_receipt_case(
        ROOT, tmp_path, PACK, participant, runner_id="database-boundary-test"
    )
    document = pack.document()
    plan = run.document()
    assert all("expected" not in scenario for scenario in plan["scenarios"])
    policy = DATABASE_OPERATIONS_COVERAGE_POLICY
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
        if row.participant_id == participant and row.rust_symbol == "DatabasePool"
    )
    added = replace(
        prototype,
        obligation_id="parity:test:future-database-operation",
        runtime_operation="future_database_operation",
        required_evidence_kind="runtime",
        retained_analyzer_id=None,
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
            (0, "single", []),
            (1, "files", [{"path": "formids.db", "hex": "00"}]),
            (2, "error", None),
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
