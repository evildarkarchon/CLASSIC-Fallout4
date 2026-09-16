"""Value methods require explicit source rows and real range/compatibility observations."""

from pathlib import Path

from conformance.applicability import derive_applicability
from conformance.coverage import (
    derive_row_coverage,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
)
from conformance.families.version_registry_values import (
    VERSION_REGISTRY_VALUES_COVERAGE_POLICY as POLICY,
)
from conformance.receipts import validate_prepared_run

from receipt_test_support import prepare_receipt_case

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("tests/conformance/packs/version_registry_values/v1.json")


def test_value_methods_have_exact_python_applicability(tmp_path: Path) -> None:
    """Range enrollment cannot silently enroll CXX/Node or grant unknown method credit."""
    pack, run, _receipt = prepare_receipt_case(
        ROOT, tmp_path, PACK, "python", runner_id="registry-values-test"
    )
    rows = load_source_parity_rows(ROOT)
    assert {
               item.id for item in derive_applicability(pack.document(), rows).participants
           } == {"rust", "python"}
    report = validate_prepared_run(pack, run, coverage_policy=POLICY)
    assert not report.failures
    coverage = derive_row_coverage(
        pack.document(),
        rows,
        POLICY,
        (report,),
        scope_participant_id="python",
        retained_analyzers=load_retained_analyzer_kinds(ROOT),
    )
    assert not coverage.failures
    assert {
               "parity:python:version_registry.models.VersionInfo.__eq__",
               "parity:python:version_registry.models.VersionInfo.__hash__",
           } <= {row.obligation_id for row in coverage.rows}
    assert all(
        not predicate.covers_runtime_operation("future_value_method")
        for predicate in POLICY.predicates
    )
