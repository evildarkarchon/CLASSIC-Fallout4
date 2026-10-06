"""DDS observations require complete parsed fields and native validation results."""

from copy import deepcopy
from pathlib import Path

from conformance.coverage import derive_observed_fact_ids, load_source_parity_rows
from conformance.packs import load_and_validate_pack


def test_dds_observation_predicates_reject_missing_and_changed_fields() -> None:
    """Every public header result participates in independently checked facts."""
    from conformance.families.dds_header import DDS_HEADER_COVERAGE_POLICY

    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/dds_header/v1.json")
    ).document()
    assert any(
        capability["id"] == "dds-header.files" for capability in pack["capabilities"]
    )
    for scenario in pack["scenarios"]:
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            pack, scenario, expected, DDS_HEADER_COVERAGE_POLICY
        )
        for field in expected:
            changed = deepcopy(expected)
            del changed[field]
            assert not derive_observed_fact_ids(
                pack, scenario, changed, DDS_HEADER_COVERAGE_POLICY
            )
        if expected.get("header") is not None:
            changed = deepcopy(expected)
            changed["header"]["powerOfTwo"] = not changed["header"]["powerOfTwo"]
            assert not derive_observed_fact_ids(
                pack, scenario, changed, DDS_HEADER_COVERAGE_POLICY
            )
    exported = [
        row
        for row in load_source_parity_rows(root)
        if row.rust_symbol == "DDSHeader" and row.mapping_origin == "canonical_rust"
    ]
    assert {row.participant_id for row in exported} == {"python"}


def test_dds_capabilities_route_parsing_to_file_io_and_game_rules_to_resource() -> None:
    """Neutral header parsing stays with file I/O; game-target rules belong to resource.

    The pack's domain owner covers the parse and file-reader capabilities,
    while the game-target validation capability names resource core (#249).
    Every live parity row for the moved analyzer, issue, and target types must
    name that owner too, so a stale same-named file I/O mapping cannot satisfy
    source parity.
    """

    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/dds_header/v1.json")
    ).document()
    owner = pack["domainOwner"]["rustCrate"]
    routes = {
        capability["id"]: capability.get("rustCrate", owner)
        for capability in pack["capabilities"]
    }
    assert routes == {
        "dds-header.parse": "classic-file-io-core",
        "dds-header.files": "classic-file-io-core",
        "dds-header.validate": "classic-resource-core",
    }

    moved = {"DDSAnalyzer", "DDSIssue", "GameTarget"}
    rows = [
        row
        for row in load_source_parity_rows(root)
        if row.rust_symbol is not None
        and row.rust_symbol.removesuffix("@rust") in moved
    ]
    assert {row.participant_id for row in rows} == {"node", "python"}
    assert {row.rust_crate for row in rows} == {"classic-resource-core"}
