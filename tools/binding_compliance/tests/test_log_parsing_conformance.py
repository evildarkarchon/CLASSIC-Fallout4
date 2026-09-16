"""Parsing conformance validates full native extraction and cache observations."""

from copy import deepcopy
from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.packs import load_and_validate_pack


def test_log_parsing_facts_require_complete_observations() -> None:
    """Neither an absent result nor a changed cache transition earns a fact."""
    from conformance.families.log_parsing import LOG_PARSING_COVERAGE_POLICY

    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/log_parsing/v1.json")
    ).document()
    assert {
               "log-parsing.formids",
               "log-parsing.plugins",
               "log-parsing.records",
               "log-parsing.gpu",
               "log-parsing.node-parser",
               "log-parsing.crashgen-version",
           } <= {capability["id"] for capability in pack["capabilities"]}
    for scenario in pack["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            pack, scenario, expected, LOG_PARSING_COVERAGE_POLICY
        )
        for key in expected:
            changed = deepcopy(expected)
            del changed[key]
            assert not derive_observed_fact_ids(
                pack, scenario, changed, LOG_PARSING_COVERAGE_POLICY
            )
        if "afterClear" in expected:
            changed = deepcopy(expected)
            changed["afterClear"] = [100, 100]
            assert not derive_observed_fact_ids(
                pack, scenario, changed, LOG_PARSING_COVERAGE_POLICY
            )
