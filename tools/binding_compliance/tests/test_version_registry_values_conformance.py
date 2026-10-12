"""Value methods are Rust-only and require real range/compatibility observations."""

from pathlib import Path

from conformance.applicability import derive_applicability
from conformance.families.version_registry_values import (
    VERSION_REGISTRY_VALUES_COVERAGE_POLICY as POLICY,
)
from conformance.participants import load_participants
from conformance.receipts import validate_prepared_run

from receipt_test_support import prepare_receipt_case

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("tests/conformance/packs/version_registry_values/v1.json")


def test_value_methods_enroll_no_bridge_and_grant_no_unknown_credit(tmp_path: Path) -> None:
    """The pack cannot silently enroll CXX, and value facts grant no unknown method credit.

    The Python value methods that once enrolled a binding retired with it, so
    only the Rust owner runs this pack.
    """
    pack, run, _receipt = prepare_receipt_case(
        ROOT, tmp_path, PACK, "rust", runner_id="registry-values-test"
    )
    assert {
               item.id
               for item in derive_applicability(
            pack.document(), load_participants(ROOT)
        ).participants
           } == {"rust"}
    report = validate_prepared_run(pack, run, coverage_policy=POLICY)
    assert not report.failures
    assert all(scenario.observed_fact_ids for scenario in report.scenarios)
    assert all(
        not predicate.covers_runtime_operation("future_value_method")
        for predicate in POLICY.predicates
    )
