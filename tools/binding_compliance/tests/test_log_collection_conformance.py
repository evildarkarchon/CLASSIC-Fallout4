"""Log collection receipts preserve source copies and account for moved files."""

from copy import deepcopy
from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.packs import load_and_validate_pack


def test_log_collection_requires_paths_and_durable_effects() -> None:
    """An omitted inventory or a discovered nonexistent log cannot earn coverage."""
    from conformance.families.log_collection import LOG_COLLECTION_COVERAGE_POLICY

    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/log_collection/v1.json")
    ).document()
    for scenario in pack["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            pack, scenario, expected, LOG_COLLECTION_COVERAGE_POLICY
        )
        for key in expected:
            changed = deepcopy(expected)
            del changed[key]
            assert not derive_observed_fact_ids(
                pack, scenario, changed, LOG_COLLECTION_COVERAGE_POLICY
            )
        changed = deepcopy(expected)
        changed["second"].append("base/Crash Logs/crash-invented.log")
        assert not derive_observed_fact_ids(
            pack, scenario, changed, LOG_COLLECTION_COVERAGE_POLICY
        )
