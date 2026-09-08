"""Generated-file receipts preserve existing files and inspect complete effects."""

from copy import deepcopy
from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.packs import load_and_validate_pack


def test_file_generation_predicates_require_nonreplacement_and_exact_inventory() -> (
    None
):
    """An existing-file overwrite or omitted observation cannot donate coverage."""
    from conformance.families.file_generation import FILE_GENERATION_COVERAGE_POLICY

    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/file_generation/v1.json")
    ).document()
    for scenario in pack["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            pack, scenario, expected, FILE_GENERATION_COVERAGE_POLICY
        )
        for key in expected:
            changed = deepcopy(expected)
            del changed[key]
            assert not derive_observed_fact_ids(
                pack, scenario, changed, FILE_GENERATION_COVERAGE_POLICY
            )
        changed = deepcopy(expected)
        changed["standalone"] = [True, True]
        assert not derive_observed_fact_ids(
            pack, scenario, changed, FILE_GENERATION_COVERAGE_POLICY
        )
