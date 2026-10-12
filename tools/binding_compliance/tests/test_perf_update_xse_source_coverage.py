"""Auxiliary receipts pass for CXX and their facts reject future aliases."""

from pathlib import Path

import pytest
from conformance.families.performance import PERFORMANCE_COVERAGE_POLICY
from conformance.families.update_decisions import UPDATE_DECISIONS_COVERAGE_POLICY
from conformance.families.xse_operations import XSE_OPERATIONS_COVERAGE_POLICY
from conformance.receipts import validate_prepared_run

from receipt_test_support import prepare_receipt_case

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    "family,policy",
    (
            ("performance", PERFORMANCE_COVERAGE_POLICY),
            ("update_decisions", UPDATE_DECISIONS_COVERAGE_POLICY),
            ("xse_operations", XSE_OPERATIONS_COVERAGE_POLICY),
    ),
)
@pytest.mark.parametrize("participant", ("rust", "cxx"))
def test_owner_receipts_pass_and_facts_reject_future_alias(
        tmp_path, family, policy, participant
):
    """Complete receipts pass, and no fact silently speaks for a new method."""
    from conformance.participants import load_participants

    # The consumer-driven bridge trim (#307-#309) leaves some of these families
    # Rust-only; Rust receives every pack, so it carries the checks there.
    if participant == "cxx" and family.replace("_", "-") not in load_participants(
        ROOT
    ).family_ids:
        pytest.skip("Rust-only family: CXX is not enrolled in participants.json")
    path = Path(f"tests/conformance/packs/{family}/v1.json")
    pack, run, _receipt = prepare_receipt_case(
        ROOT, tmp_path, path, participant, runner_id="aux-source-boundary"
    )
    report = validate_prepared_run(pack, run, coverage_policy=policy)
    assert not report.failures
    assert all(scenario.result == "pass" for scenario in report.scenarios)
    assert not any(
        predicate.covers_runtime_operation("future_unexecuted_operation")
        for predicate in policy.predicates
    )
