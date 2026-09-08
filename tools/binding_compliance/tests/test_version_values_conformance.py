"""Value families obey public pack schema and narrow observable operations."""

from pathlib import Path

from conformance.packs import load_and_validate_pack


def test_version_value_packs_are_executable():
    """Every public version value family has a schema-valid input-only pack."""
    root = Path(__file__).resolve().parents[3]
    for family in (
        "game_version_parse",
        "game_version_distance",
        "game_version_order",
        "fallout4_identity",
        "fallout4_paths",
        "fallout4_metadata",
    ):
        load_and_validate_pack(
            root, Path("tests/conformance/packs") / family / "v1.json"
        )


import pytest


@pytest.mark.parametrize(
    "family,participant",
    [
        (family, participant)
        for family, participants in {
            "game-version-parse": ("cxx", "node", "python"),
            "game-version-distance": ("node", "python"),
            "game-version-order": ("python",),
            "fallout4-identity": ("cxx", "node", "python"),
            "fallout4-paths": ("cxx", "python"),
            "fallout4-metadata": ("python",),
        }.items()
        for participant in participants
    ],
)
def test_version_value_receipts_cover_only_applicable_rows(
    tmp_path, family, participant
):
    """Complete receipts cover actual source rows while no nonexistent adapter is enrolled."""
    from conformance.coverage import (
        derive_row_coverage,
        load_retained_analyzer_kinds,
        load_source_parity_rows,
    )
    from conformance.families.version_values import version_values_coverage_policy
    from conformance.receipts import validate_prepared_run
    from receipt_test_support import prepare_receipt_case

    root = Path(__file__).resolve().parents[3]
    pack, run, _ = prepare_receipt_case(
        root,
        tmp_path,
        Path("tests/conformance/packs") / family.replace("-", "_") / "v1.json",
        participant,
        runner_id="version-value-test",
    )
    policy = version_values_coverage_policy(family)
    report = validate_prepared_run(pack, run, coverage_policy=policy)
    assert not report.failures
    coverage = derive_row_coverage(
        pack.document(),
        load_source_parity_rows(root),
        policy,
        (report,),
        scope_participant_id=participant,
        retained_analyzers=load_retained_analyzer_kinds(root),
    )
    assert coverage.rows
    assert not coverage.failures
