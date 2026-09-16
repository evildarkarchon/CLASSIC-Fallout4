"""Extended registry queries require complete native facts and exact applicability."""

import copy
from pathlib import Path

import pytest
from conformance.applicability import derive_applicability
from conformance.coverage import (
    derive_observed_fact_ids,
    derive_row_coverage,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
)
from conformance.families.version_registry_details import (
    VERSION_REGISTRY_DETAILS_COVERAGE_POLICY as POLICY,
)
from conformance.packs import load_and_validate_pack
from conformance.receipts import validate_prepared_run

from receipt_test_support import prepare_receipt_case

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("tests/conformance/packs/version_registry_details/v1.json")


def test_details_require_every_field_and_exclude_cxx() -> None:
    """CXX has no extended query surface; partial observations never grant facts."""
    document = load_and_validate_pack(ROOT, PACK).document()
    applicability = derive_applicability(document, load_source_parity_rows(ROOT))
    assert {participant.id for participant in applicability.participants} == {
        "rust",
        "node",
        "python",
    }
    for scenario in document["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(document, scenario, expected, POLICY)
        for field in expected:
            changed = copy.deepcopy(expected)
            del changed[field]
            assert not derive_observed_fact_ids(document, scenario, changed, POLICY)
        if isinstance(expected["result"], dict):
            for field in expected["result"]:
                changed = copy.deepcopy(expected)
                del changed["result"][field]
                assert not derive_observed_fact_ids(document, scenario, changed, POLICY)
    assert all(
        not predicate.covers_runtime_operation("future_registry_method")
        for predicate in POLICY.predicates
    )


@pytest.mark.parametrize("participant", ("node", "python"))
def test_details_receipts_cover_only_executed_operations(
        tmp_path: Path, participant: str
) -> None:
    """Prepared receipt facts retain structural owners and cannot hide missing queries."""
    pack, run, _receipt = prepare_receipt_case(
        ROOT, tmp_path, PACK, participant, runner_id="registry-details-test"
    )
    report = validate_prepared_run(pack, run, coverage_policy=POLICY)
    assert not report.failures
    coverage = derive_row_coverage(
        pack.document(),
        load_source_parity_rows(ROOT),
        POLICY,
        (report,),
        scope_participant_id=participant,
        retained_analyzers=load_retained_analyzer_kinds(ROOT),
    )
    assert coverage.rows
    assert not coverage.failures
