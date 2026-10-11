"""Scan-run input coverage must be anchored to actual executed public operations."""

import json
from pathlib import Path

from conformance.coverage import load_source_parity_rows
from conformance.families.crash_log_scan_run import CRASH_LOG_SCAN_RUN_COVERAGE_POLICY
from selector_test_support import candidate_predicates


def test_executed_request_inputs_and_cancellation_have_receipt_predicates():
    """Existing successful and cancelled runs prove their input constructors."""
    root = Path(__file__).resolve().parents[3]
    document = json.loads(
        (root / "tests/conformance/packs/crash_log_scan_run/v1.json").read_text()
    )
    # The surviving CXX bridge operations; the Python and Node constructor rows
    # retired with those bindings.
    operations = {
        "scan_run_contract_execute",
        "scan_run_unsolved_logs_leave_in_place",
        "scan_run_unsolved_logs_move_to_custom",
    }
    rows = [
        row
        for row in load_source_parity_rows(root)
        if row.runtime_operation in operations
    ]
    assert {row.runtime_operation for row in rows} == operations
    for row in rows:
        assert candidate_predicates(
            row, document, CRASH_LOG_SCAN_RUN_COVERAGE_POLICY
        ), row
