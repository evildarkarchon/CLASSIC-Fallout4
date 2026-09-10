"""Crashgen receipts require native issue details, report metadata and durable inputs."""

from copy import deepcopy
from pathlib import Path

from conformance.coverage import derive_observed_fact_ids
from conformance.packs import load_and_validate_pack


def test_crashgen_observations_require_every_native_field() -> None:
    """Omitted report fields and mutated inputs cannot claim a completed check."""
    from conformance.families.crashgen_check import CRASHGEN_CHECK_COVERAGE_POLICY

    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/crashgen_check/v1.json")
    ).document()
    assert any(scenario["expected"]["issues"] for scenario in pack["scenarios"])
    for scenario in pack["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            pack, scenario, expected, CRASHGEN_CHECK_COVERAGE_POLICY
        )
        for key in expected:
            changed = deepcopy(expected)
            del changed[key]
            assert not derive_observed_fact_ids(
                pack, scenario, changed, CRASHGEN_CHECK_COVERAGE_POLICY
            )
        changed = deepcopy(expected)
        changed["files"].append({"path": "invented", "content": "mutation"})
        assert not derive_observed_fact_ids(
            pack, scenario, changed, CRASHGEN_CHECK_COVERAGE_POLICY
        )
