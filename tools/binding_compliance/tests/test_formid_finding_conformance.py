"""FormID findings retain counts, resolved plugins, lookup states and typed failures."""

from copy import deepcopy
from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.packs import load_and_validate_pack


def test_formid_finding_requires_complete_typed_observations() -> None:
    """Dropping values or inventing lookup states cannot earn analyzer evidence."""
    from conformance.families.formid_finding import FORMID_FINDING_COVERAGE_POLICY

    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/formid_finding/v1.json")
    ).document()
    for scenario in pack["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            pack, scenario, expected, FORMID_FINDING_COVERAGE_POLICY
        )
        for key in expected:
            changed = deepcopy(expected)
            del changed[key]
            assert not derive_observed_fact_ids(
                pack, scenario, changed, FORMID_FINDING_COVERAGE_POLICY
            )
        if expected["findings"]:
            changed = deepcopy(expected)
            changed["findings"][0]["status"] = "invented"
            assert not derive_observed_fact_ids(
                pack, scenario, changed, FORMID_FINDING_COVERAGE_POLICY
            )
