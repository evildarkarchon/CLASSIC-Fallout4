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


def test_null_version_query_has_positive_and_negative_executable_inputs():
    """The CXX null helper must be exercised for both null and non-null parsed versions."""
    from conformance.coverage import load_source_parity_rows
    from conformance.families.version_values import version_values_coverage_policy
    from retirement_readiness import candidate_predicates

    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/game_version_parse/v1.json")
    ).document()
    row = next(
        r
        for r in load_source_parity_rows(root)
        if r.obligation_id == "parity:cxx:76de962f36a6993c"
    )
    assert candidate_predicates(
        row, pack, version_values_coverage_policy("game-version-parse")
    )
    assert any(s["expected"] == {"parsed": "0.0.0.0"} for s in pack["scenarios"])
    assert any(s["expected"] == {"parsed": "1.10.163.0"} for s in pack["scenarios"])


def test_config_owned_executable_name_has_cross_owner_evidence():
    """The CXX config resolver must retain its real Rust owner in version-value evidence."""
    from conformance.coverage import load_source_parity_rows
    from conformance.families.version_values import version_values_coverage_policy
    from retirement_readiness import candidate_predicates

    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/fallout4_paths/v1.json")
    ).document()
    row = next(
        r
        for r in load_source_parity_rows(root)
        if r.obligation_id == "parity:cxx:2cd440ef71f6e18d"
    )
    assert row.rust_crate == "classic-config-core"
    assert candidate_predicates(
        row, pack, version_values_coverage_policy("fallout4-paths")
    )


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
    if participant == "python":
        expected_operations = {
            "game-version-order": {
                "__eq__",
                "__lt__",
                "__le__",
                "__gt__",
                "__ge__",
                "__hash__",
            },
            "fallout4-paths": {"docs_folder_name", "is_standard", "registry_id"},
            "fallout4-metadata": {
                "__eq__",
                "__hash__",
                "__repr__",
                "__str__",
                "display_name",
                "from_str",
                "short_name",
                "xse_acronym",
            },
        }.get(family, set())
        covered = {row.obligation_id for row in coverage.rows}
        for operation in expected_operations:
            owner = (
                "GameVersion" if family == "game-version-order" else "Fallout4Version"
            )
            module = "version" if owner == "GameVersion" else "lib"
            assert (
                    f"parity:python:version_registry.{module}.{owner}.{operation}"
                    in covered
            )
