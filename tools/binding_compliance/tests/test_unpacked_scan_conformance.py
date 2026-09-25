"""Unpacked scans distinguish DDS inventory from actual issue classifications."""

from copy import deepcopy
from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.packs import load_and_validate_pack


def test_unpacked_results_keep_all_categories_and_readonly_effects() -> None:
    """Missing vectors or unrequested filesystem changes cannot earn scan facts."""
    from conformance.families.unpacked_scan import UNPACKED_SCAN_COVERAGE_POLICY

    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/unpacked_scan/v1.json")
    ).document()
    for scenario in pack["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            pack, scenario, expected, UNPACKED_SCAN_COVERAGE_POLICY
        )
        for key in expected:
            changed = deepcopy(expected)
            del changed[key]
            assert not derive_observed_fact_ids(
                pack, scenario, changed, UNPACKED_SCAN_COVERAGE_POLICY
            )
        changed = deepcopy(expected)
        changed["directories"].append("new-unrequested-directory")
        assert not derive_observed_fact_ids(
            pack, scenario, changed, UNPACKED_SCAN_COVERAGE_POLICY
        )
