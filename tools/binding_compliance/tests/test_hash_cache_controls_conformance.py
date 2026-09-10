"""Empty CXX cache control observations are executable without claiming seeded state."""

from copy import deepcopy
from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.packs import load_and_validate_pack


def test_empty_cache_controls_require_complete_native_statistics() -> None:
    """Missing fields or nonzero post-reset values cannot satisfy empty-state evidence."""
    from conformance.families.hash_cache_controls import (
        HASH_CACHE_CONTROLS_COVERAGE_POLICY,
    )

    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/hash_cache_controls/v1.json")
    ).document()
    scenario = pack["scenarios"][0]
    expected = scenario["expected"]
    assert derive_observed_fact_ids(
        pack, scenario, expected, HASH_CACHE_CONTROLS_COVERAGE_POLICY
    )
    for key in expected:
        changed = deepcopy(expected)
        del changed[key]
        assert not derive_observed_fact_ids(
            pack, scenario, changed, HASH_CACHE_CONTROLS_COVERAGE_POLICY
        )
    changed = deepcopy(expected)
    changed["afterClear"]["size"] = 1
    assert not derive_observed_fact_ids(
        pack, scenario, changed, HASH_CACHE_CONTROLS_COVERAGE_POLICY
    )
