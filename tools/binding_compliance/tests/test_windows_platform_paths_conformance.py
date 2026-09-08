"""Windows path evidence compares independent read-only APIs without recording host paths."""

from pathlib import Path

from conformance.applicability import derive_applicability
from conformance.coverage import derive_observed_fact_ids, load_source_parity_rows
from conformance.packs import load_and_validate_pack


def test_windows_path_facts_require_each_native_reference_agreement():
    """Missing registry, documents agreement, and the Windows Steam result are distinct facts."""
    from conformance.families.windows_platform_paths import (
        WINDOWS_PLATFORM_PATHS_POLICY,
    )

    root = Path(__file__).resolve().parents[3]
    document = load_and_validate_pack(
        root, Path("tests/conformance/packs/windows_platform_paths/v1.json")
    ).document()
    assert {
        p.id
        for p in derive_applicability(
            document, load_source_parity_rows(root)
        ).participants
    } == {"rust", "node"}
    scenario = document["scenarios"][0]
    expected = scenario["expected"]
    assert derive_observed_fact_ids(
        document, scenario, expected, WINDOWS_PLATFORM_PATHS_POLICY
    )
    for key in expected:
        assert not derive_observed_fact_ids(
            document, scenario, {**expected, key: False}, WINDOWS_PLATFORM_PATHS_POLICY
        )
