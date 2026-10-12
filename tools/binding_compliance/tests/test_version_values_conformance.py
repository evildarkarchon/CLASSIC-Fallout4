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
    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/game_version_parse/v1.json")
    ).document()
    assert any(s["expected"] == {"parsed": "0.0.0.0"} for s in pack["scenarios"])
    assert any(s["expected"] == {"parsed": "1.10.163.0"} for s in pack["scenarios"])


@pytest.mark.parametrize(
    "family,participant",
    [
        (family, participant)
        for family, participants in {
        "game-version-parse": ("cxx",),
        "fallout4-identity": ("cxx",),
        "fallout4-paths": ("cxx",),
    }.items()
        for participant in participants
    ],
)
def test_version_value_receipts_pass_for_each_enrolled_participant(
        tmp_path, family, participant
):
    """Complete receipts from an enrolled adapter validate and derive their facts."""
    from conformance.applicability import derive_applicability
    from conformance.families.version_values import version_values_coverage_policy
    from conformance.participants import load_participants
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
    assert participant in {
        item.id
        for item in derive_applicability(
            pack.document(), load_participants(root)
        ).participants
    }
    policy = version_values_coverage_policy(family)
    report = validate_prepared_run(pack, run, coverage_policy=policy)
    assert not report.failures
    assert report.scenarios
    assert all(scenario.observed_fact_ids for scenario in report.scenarios)
