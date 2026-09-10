"""BA2 conformance includes positive data for every issue-vector getter."""

from copy import deepcopy
from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.packs import load_and_validate_pack


def test_ba2_scenarios_prove_every_issue_column_and_preserve_bytes() -> None:
    """A fail-soft empty bridge cannot replace real parsed issue vectors."""
    from conformance.families.ba2_scan import BA2_SCAN_COVERAGE_POLICY

    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/ba2_scan/v1.json")
    ).document()
    columns = set()
    for scenario in pack["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            pack, scenario, expected, BA2_SCAN_COVERAGE_POLICY
        )
        columns.update(key for key, value in expected["issues"].items() if value)
        for key in expected:
            changed = deepcopy(expected)
            del changed[key]
            assert not derive_observed_fact_ids(
                pack, scenario, changed, BA2_SCAN_COVERAGE_POLICY
            )
    assert columns == {"dimensions", "formats", "sounds", "scripts"}
