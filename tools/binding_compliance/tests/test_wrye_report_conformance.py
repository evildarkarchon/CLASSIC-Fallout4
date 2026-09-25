"""Wrye parsing preserves empty sections, warning metadata and exact report prose."""

from copy import deepcopy
from pathlib import Path

from conformance.coverage import (
    derive_observed_fact_ids,
    derive_row_coverage,
    load_source_parity_rows,
)
from conformance.packs import load_and_validate_pack


def test_wrye_predicates_require_complete_issues_and_formatter_output() -> None:
    """Missing issue metadata or a lost formatter result fails semantic evidence."""
    from conformance.families.wrye_report import WRYE_REPORT_COVERAGE_POLICY

    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/wrye_report/v1.json")
    ).document()
    for scenario in pack["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            pack, scenario, expected, WRYE_REPORT_COVERAGE_POLICY
        )
        for key in expected:
            changed = deepcopy(expected)
            del changed[key]
            assert not derive_observed_fact_ids(
                pack, scenario, changed, WRYE_REPORT_COVERAGE_POLICY
            )


def test_python_wrye_report_row_requires_a_runtime_receipt() -> None:
    """Keep the public report facade in the Wrye formatter's source denominator."""
    from conformance.families.wrye_report import WRYE_REPORT_COVERAGE_POLICY

    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/wrye_report/v1.json")
    ).document()
    row_id = "parity:python:scangame.wrye.parse_wrye_report"
    rows = tuple(row for row in load_source_parity_rows(root) if row.obligation_id == row_id)
    assert len(rows) == 1

    coverage = derive_row_coverage(pack, rows, WRYE_REPORT_COVERAGE_POLICY, ())
    assert [failure.obligation_id for failure in coverage.failures] == [row_id]
