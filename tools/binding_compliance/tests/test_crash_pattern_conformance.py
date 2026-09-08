"""Crash-pattern receipts distinguish shared tokens from legacy full error text."""

from copy import deepcopy
from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.packs import load_and_validate_pack


def test_classifier_facts_require_explicit_results_and_known_tokens() -> None:
    """No missing result or invented token can earn classification evidence."""
    from conformance.families.crash_pattern import CRASH_PATTERN_COVERAGE_POLICY

    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/crash_pattern/v1.json")
    ).document()
    for scenario in pack["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            pack, scenario, expected, CRASH_PATTERN_COVERAGE_POLICY
        )
        assert not derive_observed_fact_ids(
            pack, scenario, {}, CRASH_PATTERN_COVERAGE_POLICY
        )
        if "token" in expected:
            changed = deepcopy(expected)
            changed["token"] = "UNKNOWN_NEW_TOKEN"
            assert not derive_observed_fact_ids(
                pack, scenario, changed, CRASH_PATTERN_COVERAGE_POLICY
            )
