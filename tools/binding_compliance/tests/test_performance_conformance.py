"""Performance facts require actual deterministic metric state transitions."""

import copy
from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.families.performance import PERFORMANCE_COVERAGE_POLICY
from conformance.packs import load_and_validate_pack

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("tests/conformance/packs/performance/v1.json")


def test_performance_facts_reject_changed_statistics_and_missing_clear_effects():
    """A receipt must preserve every authored sample statistic and clear snapshot."""
    document = load_and_validate_pack(ROOT, PACK).document()
    for scenario in document["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            document, scenario, expected, PERFORMANCE_COVERAGE_POLICY
        )
        for index, snapshot in enumerate(expected["snapshots"]):
            changed = copy.deepcopy(expected)
            changed["snapshots"].pop(index)
            assert not derive_observed_fact_ids(
                document, scenario, changed, PERFORMANCE_COVERAGE_POLICY
            )
            for label, stats in snapshot.items():
                for field in stats:
                    changed = copy.deepcopy(expected)
                    changed["snapshots"][index][label][field] = "incorrect"
                    assert not derive_observed_fact_ids(
                        document, scenario, changed, PERFORMANCE_COVERAGE_POLICY
                    )
    for predicate in PERFORMANCE_COVERAGE_POLICY.predicates:
        for operation in (
            "start_timer",
            "elapsed",
            "finish",
            "reset_metrics",
            "future_metric_operation",
        ):
            assert not predicate.covers_runtime_operation(operation)


def test_performance_receipts_reject_drift_replay_and_future_operations(tmp_path):
    """Real receipt validation rejects missing effects, replay and new API credit."""
    import json
    from dataclasses import replace

    from conformance.coverage import derive_row_coverage, load_source_parity_rows
    from conformance.packs import materialize_run_plan
    from conformance.receipts import validate_prepared_run
    from receipt_test_support import prepare_receipt_case

    for participant in ("node", "python"):
        pack, run, receipt = prepare_receipt_case(
            ROOT,
            tmp_path / participant,
            PACK,
            participant,
            runner_id="performance-boundary-test",
        )
        assert all("expected" not in item for item in run.document()["scenarios"])
        report = validate_prepared_run(
            pack, run, coverage_policy=PERFORMANCE_COVERAGE_POLICY
        )
        assert not report.failures
        assert all(item.result == "pass" for item in report.scenarios)
        rows = load_source_parity_rows(ROOT)
        prototype = next(
            row
            for row in rows
            if row.participant_id == "python"
            and row.rust_crate == "classic-perf-core"
            and row.rust_symbol == "record_timing"
        )
        future = replace(
            prototype,
            participant_id=participant,
            obligation_id="parity:future-perf",
            runtime_operation="future_metric_operation",
        )
        coverage = derive_row_coverage(
            pack.document(),
            (future,),
            PERFORMANCE_COVERAGE_POLICY,
            (report,),
            scope_participant_id=participant,
        )
        assert [failure.obligation_id for failure in coverage.failures] == [
            future.obligation_id
        ]
        changed = copy.deepcopy(receipt)
        changed["scenarios"][1]["observation"]["snapshots"][2] = {"stale": {"count": 1}}
        run.receipt_path.write_text(json.dumps(changed))
        assert (
            validate_prepared_run(
                pack, run, coverage_policy=PERFORMANCE_COVERAGE_POLICY
            )
            .scenarios[1]
            .result
            == "fail"
        )
        other = materialize_run_plan(
            pack,
            participant_id=participant,
            participant_role="semantic-adapter",
            execution_instance_id=participant,
            source_paths=(PACK,),
        )
        other.receipt_path.write_text(json.dumps(receipt))
        assert validate_prepared_run(
            pack, other, coverage_policy=PERFORMANCE_COVERAGE_POLICY
        ).failures


def test_performance_validator_rejects_non_integer_durations(tmp_path):
    """A boolean or timer operation cannot enter a deterministic run plan."""
    import json

    import pytest
    from conformance.families.performance import validate_performance_pack

    document = load_and_validate_pack(ROOT, PACK).document()
    document["scenarios"] = [document["scenarios"][0]]
    path = tmp_path / document["fixtureRoot"] / document["fixtures"]["empty"]
    path.parent.mkdir(parents=True)
    for operation in (
        {"op": "record", "label": "scan", "durationMs": True},
        {"op": "timer"},
    ):
        path.write_text(json.dumps({"operations": [operation]}))
        with pytest.raises(ValueError):
            validate_performance_pack(document, tmp_path)
