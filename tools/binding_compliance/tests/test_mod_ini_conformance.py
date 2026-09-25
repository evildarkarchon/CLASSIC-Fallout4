"""INI cache and scan observations preserve actual typed values and file contents."""

from copy import deepcopy
from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.packs import load_and_validate_pack


def test_mod_ini_facts_reject_missing_data_and_durable_changes() -> None:
    """Read-only scanning cannot claim a fact after omitting or rewriting evidence."""
    from conformance.families.mod_ini import MOD_INI_COVERAGE_POLICY

    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/mod_ini/v1.json")
    ).document()
    assert any(
        capability["id"] == "mod-ini.duplicates" for capability in pack["capabilities"]
    )
    for scenario in pack["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            pack, scenario, expected, MOD_INI_COVERAGE_POLICY
        )
        for key in expected:
            changed = deepcopy(expected)
            del changed[key]
            assert not derive_observed_fact_ids(
                pack, scenario, changed, MOD_INI_COVERAGE_POLICY
            )
        changed = deepcopy(expected)
        changed["files"].append(
            {"path": "unexpected.txt", "content": "unrequested write"}
        )
        assert not derive_observed_fact_ids(
            pack, scenario, changed, MOD_INI_COVERAGE_POLICY
        )
