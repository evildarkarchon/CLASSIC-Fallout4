"""Version decisions must keep errors distinct from ordinary no-update outcomes."""

from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.families.update_decisions import UPDATE_DECISIONS_COVERAGE_POLICY
from conformance.packs import load_and_validate_pack

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("tests/conformance/packs/update_decisions/v1.json")


def test_update_decisions_reject_wrong_boolean_and_swallowed_errors():
    """Exact authored decisions cannot be replaced by success-shaped error defaults."""
    document = load_and_validate_pack(ROOT, PACK).document()
    for scenario in document["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            document, scenario, expected, UPDATE_DECISIONS_COVERAGE_POLICY
        )
        changed = {"hasUpdate": not expected["hasUpdate"], "error": None}
        assert not set(
            derive_observed_fact_ids(
                document, scenario, expected, UPDATE_DECISIONS_COVERAGE_POLICY
            )
        ) & set(
            derive_observed_fact_ids(
                document, scenario, changed, UPDATE_DECISIONS_COVERAGE_POLICY
            )
        )
    for predicate in UPDATE_DECISIONS_COVERAGE_POLICY.predicates:
        for method in (
                "get_latest_release",
                "getLatestRelease",
                "download_asset",
                "set_token",
                "future_method",
        ):
            assert not predicate.covers_runtime_operation(method)


def test_update_decision_receipts_reject_changed_decision_and_replay(tmp_path):
    """A true-to-false adapter regression and a reused receipt both fail centrally."""
    import copy
    import json

    from conformance.packs import materialize_run_plan
    from conformance.receipts import validate_prepared_run
    from receipt_test_support import prepare_receipt_case

    for participant in ("cxx", "node", "python"):
        pack, run, receipt = prepare_receipt_case(
            ROOT,
            tmp_path / participant,
            PACK,
            participant,
            runner_id="update-decision-boundary-test",
        )
        report = validate_prepared_run(
            pack, run, coverage_policy=UPDATE_DECISIONS_COVERAGE_POLICY
        )
        assert not report.failures
        assert all(item.result == "pass" for item in report.scenarios)
        changed = copy.deepcopy(receipt)
        changed["scenarios"][0]["observation"] = {"hasUpdate": False, "error": None}
        run.receipt_path.write_text(json.dumps(changed))
        rejected = validate_prepared_run(
            pack, run, coverage_policy=UPDATE_DECISIONS_COVERAGE_POLICY
        )
        assert rejected.scenarios[0].result == "fail"
        other = materialize_run_plan(
            pack,
            participant_id=participant,
            participant_role="semantic-adapter",
            execution_instance_id=participant,
            source_paths=(PACK,),
        )
        other.receipt_path.write_text(json.dumps(receipt))
        assert validate_prepared_run(
            pack, other, coverage_policy=UPDATE_DECISIONS_COVERAGE_POLICY
        ).failures


def test_update_decision_validator_rejects_network_input(tmp_path):
    """Fixture transport cannot expand comparison into network orchestration."""
    import json

    import pytest
    from conformance.families.update_decisions import validate_update_decisions_pack

    document = load_and_validate_pack(ROOT, PACK).document()
    document["scenarios"] = [document["scenarios"][0]]
    path = tmp_path / document["fixtureRoot"] / document["fixtures"]["newer"]
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {"current": "8.0.0", "latest": "8.1.0", "url": "https://example.invalid"}
        )
    )
    with pytest.raises(ValueError):
        validate_update_decisions_pack(document, tmp_path)
