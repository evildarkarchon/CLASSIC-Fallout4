"""Auxiliary receipt facts cover selected source rows and reject future aliases."""

from dataclasses import replace
from pathlib import Path

import pytest
from conformance.coverage import (
    derive_row_coverage,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
)
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
@pytest.mark.parametrize("participant", ("cxx", "node", "python"))
def test_owner_receipts_cover_selected_rows_and_reject_future_alias(
    tmp_path, family, policy, participant
):
    """Full source selection must not silently award new methods existing receipts."""
    path = Path(f"tests/conformance/packs/{family}/v1.json")
    pack, run, _receipt = prepare_receipt_case(
        ROOT, tmp_path, path, participant, runner_id="aux-source-boundary"
    )
    report = validate_prepared_run(pack, run, coverage_policy=policy)
    rows = load_source_parity_rows(ROOT)
    coverage = derive_row_coverage(
        pack.document(),
        rows,
        policy,
        (report,),
        scope_participant_id=participant,
        retained_analyzers=load_retained_analyzer_kinds(ROOT),
    )
    assert coverage.rows
    assert not coverage.failures, [
        (failure.obligation_id, failure.message) for failure in coverage.failures
    ]
    prototype = next(
        row
        for row in rows
        if row.participant_id == participant
        and row.rust_crate == pack.document()["domainOwner"]["rustCrate"]
        and row.rust_symbol in pack.document()["capabilities"][0]["rustSymbols"]
        and row.mapping_origin == "canonical_rust"
    )
    future = replace(
        prototype,
        obligation_id="parity:future-owner-alias",
        runtime_operation="future_unexecuted_operation",
        required_evidence_kind="runtime",
    )
    expanded = derive_row_coverage(
        pack.document(),
        (*rows, future),
        policy,
        (report,),
        scope_participant_id=participant,
        retained_analyzers=load_retained_analyzer_kinds(ROOT),
    )
    assert [failure.obligation_id for failure in expanded.failures] == [
        future.obligation_id
    ]
