"""Papyrus coverage requires real full, tail, idle and reset observations."""

from copy import deepcopy
from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.packs import load_and_validate_pack


def test_papyrus_predicates_reject_stale_tail_and_missing_fields() -> None:
    """No omitted stage or idle-counter drift can earn a monitor receipt."""
    from conformance.families.papyrus_monitor import PAPYRUS_MONITOR_COVERAGE_POLICY

    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/papyrus_monitor/v1.json")
    ).document()
    for scenario in pack["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            pack, scenario, expected, PAPYRUS_MONITOR_COVERAGE_POLICY
        )
        for key in expected:
            changed = deepcopy(expected)
            del changed[key]
            assert not derive_observed_fact_ids(
                pack, scenario, changed, PAPYRUS_MONITOR_COVERAGE_POLICY
            )
        if expected.get("exists"):
            changed = deepcopy(expected)
            changed["idle"]["errors"] += 1
            assert not derive_observed_fact_ids(
                pack, scenario, changed, PAPYRUS_MONITOR_COVERAGE_POLICY
            )
