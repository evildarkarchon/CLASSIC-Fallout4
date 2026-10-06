"""Controlled folder resolution must be executable and cannot fall into discovery."""

import json
from pathlib import Path

import pytest
from conformance.enforcement import enforcement_for_family
from conformance.packs import load_and_validate_pack

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("tests/conformance/packs/xse_folder/v1.json")


def test_xse_folder_pack_is_blocking_and_has_controlled_precedence_cases():
    """The public resolver covers precedence, VR folder naming and fail-soft absence."""
    pack = load_and_validate_pack(ROOT, PACK).document()
    assert enforcement_for_family(pack["familyId"]) == "blocking"
    assert {case["id"] for case in pack["scenarios"]} == {
        "explicit",
        "local-docs",
        "configured-docs",
        "vr-docs",
        "malformed",
        "missing",
        *DERIVATION_SCENARIOS,
    }


#: Local.yaml composition scenarios (scangame's `resolve_xse_folder_for_scan`).
COMPOSITION_SCENARIOS = {
    "explicit",
    "local-docs",
    "configured-docs",
    "vr-docs",
    "malformed",
    "missing",
}
#: Derivation scenarios (XSE's facts-based resolver, supplied facts only).
DERIVATION_SCENARIOS = {
    "derive-explicit",
    "derive-local-docs",
    "derive-configured-docs",
    "derive-vr-docs",
    "derive-absent",
}


def test_xse_folder_credits_derivation_to_xse_and_composition_to_scangame():
    """XSE owns XSE Folder derivation; scangame owns only the Local.yaml composition.

    The derivation capability defaults to the pack's domain owner and is
    exercised through XSE's facts-based resolver. The composition keeps its
    original capability and scenario IDs but names scangame explicitly.
    """
    pack = load_and_validate_pack(ROOT, PACK).document()
    assert pack["domainOwner"] == {"rustCrate": "classic-xse-core"}
    capabilities = {capability["id"]: capability for capability in pack["capabilities"]}
    assert set(capabilities) == {"xse-folder.derive", "xse-folder.resolve"}
    derive = capabilities["xse-folder.derive"]
    assert "rustCrate" not in derive
    assert derive["rustSymbols"] == ["resolve_xse_folder_from_game_local_facts"]
    compose = capabilities["xse-folder.resolve"]
    assert compose["rustCrate"] == "classic-scangame-core"
    assert compose["rustSymbols"] == ["resolve_xse_folder_for_scan"]
    actions: dict[str, set[str]] = {}
    for case in pack["scenarios"]:
        assert case["capabilityIds"] == [case["action"]]
        actions.setdefault(case["action"], set()).add(case["id"])
    assert actions == {
        "xse-folder.resolve": COMPOSITION_SCENARIOS,
        "xse-folder.derive": DERIVATION_SCENARIOS,
    }


def test_xse_folder_derivation_is_rust_only_and_cxx_runs_only_the_composition():
    """No binding exposes the facts resolver, so only Rust executes derivation."""
    from conformance.applicability import derive_applicability
    from conformance.coverage import load_source_parity_rows

    document = load_and_validate_pack(ROOT, PACK).document()
    participants = {
        participant.id: participant
        for participant in derive_applicability(
            document, load_source_parity_rows(ROOT)
        ).participants
    }
    assert set(participants) == {"rust", "cxx"}
    assert participants["rust"].capability_ids == (
        "xse-folder.derive",
        "xse-folder.resolve",
    )
    assert set(participants["rust"].scenario_ids) == (
        COMPOSITION_SCENARIOS | DERIVATION_SCENARIOS
    )
    assert participants["cxx"].capability_ids == ("xse-folder.resolve",)
    assert set(participants["cxx"].scenario_ids) == COMPOSITION_SCENARIOS


def test_xse_folder_derivation_rejects_uncontrolled_game_local_facts(tmp_path):
    """Derivation facts are a closed set, so no case can probe host folders."""
    from conformance.families.xse_folder import validate_xse_folder_pack

    pack = load_and_validate_pack(ROOT, PACK).document()
    pack["scenarios"] = [
        case for case in pack["scenarios"] if case["id"] == "derive-explicit"
    ]
    relative = pack["fixtures"]["derive-explicit"]
    fixture = json.loads((ROOT / pack["fixtureRoot"] / relative).read_text())
    fixture["gameLocalFacts"]["docsFolderXse"] = "C:/Users"
    target = tmp_path / pack["fixtureRoot"] / relative
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(fixture))
    with pytest.raises(ValueError, match="controlled"):
        validate_xse_folder_pack(pack, tmp_path)


def test_xse_folder_rejects_registry_metadata_that_can_trigger_discovery(tmp_path):
    """A missing XSE record must not turn configured-path tests into OS probes."""
    from conformance.families.xse_folder import validate_xse_folder_pack

    pack = load_and_validate_pack(ROOT, PACK).document()
    pack["scenarios"] = pack["scenarios"][:1]
    source = ROOT / pack["fixtureRoot"] / pack["fixtures"]["explicit"]
    fixture = json.loads(source.read_text())
    fixture["registryYaml"] = "Version_Registry: {}\n"
    target = tmp_path / pack["fixtureRoot"] / pack["fixtures"]["explicit"]
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(fixture))
    with pytest.raises(ValueError, match="registry"):
        validate_xse_folder_pack(pack, tmp_path)


def test_xse_folder_receipts_cover_public_resolver_and_reject_path_drift(tmp_path):
    """Only applicable public adapters grant resolver evidence from exact observations."""
    from conformance.applicability import derive_applicability
    from conformance.coverage import derive_row_coverage, load_source_parity_rows
    from conformance.families.xse_folder import XSE_FOLDER_COVERAGE_POLICY
    from conformance.receipts import validate_prepared_run
    from receipt_test_support import prepare_receipt_case

    document = load_and_validate_pack(ROOT, PACK).document()
    rows = load_source_parity_rows(ROOT)
    participants = derive_applicability(document, rows)
    assert {participant.id for participant in participants.participants} == {
        "rust",
        "cxx",
    }
    pack, run, receipt = prepare_receipt_case(
        ROOT, tmp_path, PACK, "cxx", runner_id="xse-folder-boundary"
    )
    report = validate_prepared_run(
        pack, run, coverage_policy=XSE_FOLDER_COVERAGE_POLICY
    )
    assert not report.failures
    coverage = derive_row_coverage(
        document,
        rows,
        XSE_FOLDER_COVERAGE_POLICY,
        (report,),
        scope_participant_id="cxx",
    )
    assert coverage.rows and not coverage.failures
    receipt["scenarios"][3]["observation"]["folder"] = "configured-docs/F4SEVR"
    run.receipt_path.write_text(json.dumps(receipt))
    report = validate_prepared_run(
        pack, run, coverage_policy=XSE_FOLDER_COVERAGE_POLICY
    )
    assert report.scenarios[3].result == "fail"


def test_xse_folder_expectation_cannot_hide_modified_fixture_bytes():
    """Read-only resolver expectations must preserve the supplied YAML exactly."""
    from conformance.families.xse_folder import validate_xse_folder_pack

    document = load_and_validate_pack(ROOT, PACK).document()
    document["scenarios"][0]["expected"]["files"][0]["content"] = "changed"
    with pytest.raises(ValueError, match="inventory"):
        validate_xse_folder_pack(document, ROOT)
