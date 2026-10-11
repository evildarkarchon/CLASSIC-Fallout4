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
                "future_metric_operation",
        ):
            assert not predicate.covers_runtime_operation(operation)


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


def test_performance_rejections_require_exact_stable_tokens():
    """Error scenarios fail when a rejection is missing, extra or renamed."""
    document = load_and_validate_pack(ROOT, PACK).document()
    scenarios = {item["id"]: item for item in document["scenarios"]}
    assert {
        "invalid-rejected-unchanged",
        "counter-limit",
        "nanosecond-precision",
    } <= set(scenarios)
    for scenario_id in ("invalid-rejected-unchanged", "counter-limit"):
        scenario = scenarios[scenario_id]
        expected = scenario["expected"]
        assert expected["rejections"]
        for changed_rejections in (
                expected["rejections"][1:],
                [*expected["rejections"], "timing_sample_negative"],
                ["InvalidArg", *expected["rejections"][1:]],
        ):
            changed = copy.deepcopy(expected)
            changed["rejections"] = changed_rejections
            assert not derive_observed_fact_ids(
                document, scenario, changed, PERFORMANCE_COVERAGE_POLICY
            )
        # A rejected sample that leaked into the summary is a mutation failure.
        mutated = copy.deepcopy(expected)
        label = next(iter(mutated["snapshots"][0]))
        mutated["snapshots"][0][label]["count"] = 2
        assert not derive_observed_fact_ids(
            document, scenario, mutated, PERFORMANCE_COVERAGE_POLICY
        )
    precision = scenarios["nanosecond-precision"]
    for label, truncated in (("tie", 976_563), ("odd", 2_929_687)):
        changed = copy.deepcopy(precision["expected"])
        changed["snapshots"][0][label]["averageNs"] = truncated
        assert not derive_observed_fact_ids(
            document, precision, changed, PERFORMANCE_COVERAGE_POLICY
        )


def test_performance_validator_rejects_inconsistent_dual_unit_samples(tmp_path):
    """Dual-unit samples must state one finite duration with one sign."""
    import json

    import pytest
    from conformance.families.performance import validate_performance_pack

    document = load_and_validate_pack(ROOT, PACK).document()
    document["scenarios"] = [document["scenarios"][0]]
    path = tmp_path / document["fixtureRoot"] / document["fixtures"]["empty"]
    path.parent.mkdir(parents=True)
    for operation in (
            {"op": "sample", "label": "a", "seconds": 0.5, "milliseconds": 499},
            {"op": "reject", "label": "a", "seconds": True, "milliseconds": 1000},
            {"op": "sample", "label": "a", "seconds": -0.0, "milliseconds": 0.0},
            {"op": "reject", "label": "a", "seconds": 1, "milliseconds": 1000, "x": 1},
            {"op": "summaryNs", "label": "a"},
    ):
        path.write_text(json.dumps({"operations": [operation]}))
        with pytest.raises(ValueError):
            validate_performance_pack(document, tmp_path)
    path.write_text(
        json.dumps(
            {"operations": [{"op": "reject", "label": "a", "seconds": -1, "milliseconds": -1000}]}
        )
    )
    assert validate_performance_pack(document, tmp_path)
