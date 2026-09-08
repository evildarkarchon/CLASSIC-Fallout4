"""Wrye parsing preserves empty sections, warning metadata and exact report prose."""

from copy import deepcopy
from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
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
