"""File fingerprint evidence is derived from complete public results."""

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest
from conformance.coverage import (
    derive_row_coverage,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
)
from conformance.families.file_fingerprint import FILE_FINGERPRINT_COVERAGE_POLICY
from conformance.packs import load_and_validate_pack
from conformance.receipts import validate_prepared_run

from receipt_test_support import prepare_receipt_case

ROOT = Path(__file__).resolve().parents[3]


def test_fingerprints_use_independent_standard_sha256_vectors() -> None:
    """A known SHA-256 vector and a missing-file result remain explicit."""
    pack = load_and_validate_pack(
        ROOT, Path("tests/conformance/packs/file_fingerprint/v1.json")
    ).document()
    cases = {case["id"]: case["expected"] for case in pack["scenarios"]}
    assert cases["ascii"]["hash"] == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    assert cases["missing"]["hash"] is None
    assert cases["missing"]["error"] == "not_found"


@pytest.mark.parametrize("participant", ["node", "python"])
def test_fingerprint_receipts_reject_lost_effects_and_new_methods(
        tmp_path: Path, participant: str
) -> None:
    """Only complete current observations can credit the source-selected operations."""
    policy = FILE_FINGERPRINT_COVERAGE_POLICY
    pack, run, receipt = prepare_receipt_case(
        ROOT,
        tmp_path,
        Path("tests/conformance/packs/file_fingerprint/v1.json"),
        participant,
        runner_id="fingerprint-boundary",
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
    assert not coverage.failures
    prototype = next(
        row
        for row in rows
        if row.participant_id == participant and row.rust_symbol == "FileHasher"
    )
    future = replace(
        prototype,
        obligation_id="parity:future-hash-method",
        runtime_operation="future_method",
        required_evidence_kind="runtime",
        retained_analyzer_id=None,
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
    for mutation in ("hash", "cache", "reset", "cleared", "files", "encoding"):
        changed = copy.deepcopy(receipt)
        changed["scenarios"][0]["observation"].pop(mutation)
        run.receipt_path.write_text(json.dumps(changed), encoding="utf-8")
        assert validate_prepared_run(pack, run, coverage_policy=policy).failures
