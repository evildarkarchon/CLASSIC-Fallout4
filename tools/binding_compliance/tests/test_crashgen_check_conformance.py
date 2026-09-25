"""Crashgen receipts require native issue details, report metadata and durable inputs."""

from copy import deepcopy
from pathlib import Path

from conformance.coverage import (
    derive_observed_fact_ids,
    derive_row_coverage,
    load_source_parity_rows,
)
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


def test_python_crashgen_settings_row_requires_a_runtime_receipt() -> None:
    """Keep the public settings facade in the crashgen family's source denominator."""
    from conformance.families.crashgen_check import CRASHGEN_CHECK_COVERAGE_POLICY

    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/crashgen_check/v1.json")
    ).document()
    row_id = "parity:python:scangame.crashgen_orchestrator.check_crashgen_settings"
    rows = tuple(row for row in load_source_parity_rows(root) if row.obligation_id == row_id)
    assert len(rows) == 1

    coverage = derive_row_coverage(pack, rows, CRASHGEN_CHECK_COVERAGE_POLICY, ())
    assert [failure.obligation_id for failure in coverage.failures] == [row_id]
