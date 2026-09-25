"""Executable receipt contracts for maintained User Settings frontend seams."""

import json
from pathlib import Path

import pytest
from conformance.consumers import (
    derive_consumer_coverage,
    load_consumer_obligations,
    prepare_consumer_run,
)
from conformance.packs import load_and_validate_pack
from conformance.receipts import validate_prepared_run

ROOT = Path(__file__).resolve().parents[3]


def test_gui_consumer_launcher_preserves_the_requested_build_preset() -> None:
    """Receipt execution reuses the caller's Qt build configuration and records that choice."""
    launcher = (
            ROOT
            / "tools/binding_compliance/conformance/adapters/run_gui_consumer_conformance.ps1"
    ).read_text(encoding="utf-8")
    assert '[string]$Preset = "default"' in launcher
    child = launcher.split("$ChildCommand = @'", 1)[1].split("'@", 1)[0]
    assert "-Preset $env:CLASSIC_CONSUMER_CONFORMANCE_PRESET" in child
    assert (
            '$StartInfo.Environment["CLASSIC_CONSUMER_CONFORMANCE_PRESET"] = $Preset'
            in launcher
    )
    recorded = launcher.split("$RecordedCommand = @(", 1)[1].split("\n    )", 1)[0]
    assert "-Preset $Preset" in recorded


@pytest.mark.parametrize("participant", ["cli", "gui", "tui"])
def test_user_settings_consumer_plans_expose_only_maintained_obligations(
        participant: str,
) -> None:
    """Each maintained frontend gets source-bound obligations without semantic expectations."""
    pack = load_and_validate_pack(
        ROOT, Path("tests/conformance/packs/user_settings/v1.json")
    )
    catalog = load_consumer_obligations(ROOT)
    consumer = catalog.participant("user-settings", participant)
    assert consumer.obligations
    assert not any("restore" in item.id for item in consumer.obligations)
    run = prepare_consumer_run(
        pack,
        participant_id=participant,
        execution_instance_id="tui" if participant == "tui" else "windows-msvc",
        artifact_root=ROOT / "tools/binding_compliance/artifacts/consumer-tests",
        catalog=catalog,
    )
    plan = run.document()
    assert plan["familyId"] == "user-settings"
    assert plan["participant"]["role"] == "consumer"
    assert "scenarios" not in plan
    assert all(set(item) == {"id", "scenarioIds"} for item in plan["obligations"])


@pytest.mark.parametrize("participant", ["cli", "gui", "tui"])
@pytest.mark.parametrize(
    "damage", ["none", "missing", "stale", "malformed", "skipped", "mismatch"]
)
def test_user_settings_consumer_receipts_fail_closed(
        participant: str, damage: str
) -> None:
    """Every maintained consumer requires a complete current receipt that actually matches."""
    pack = load_and_validate_pack(
        ROOT, Path("tests/conformance/packs/user_settings/v1.json")
    )
    catalog = load_consumer_obligations(ROOT)
    consumer = catalog.participant("user-settings", participant)
    instance = "tui" if participant == "tui" else "windows-msvc"
    run = prepare_consumer_run(
        pack,
        participant_id=participant,
        execution_instance_id=instance,
        artifact_root=ROOT / "tools/binding_compliance/artifacts/consumer-tests",
        catalog=catalog,
    )
    plan = run.document()
    receipt = {
        key: plan[key]
        for key in (
            "schemaVersion",
            "familyId",
            "familyVersion",
            "expectationDigest",
            "invocation",
            "participant",
        )
    }
    receipt["runner"] = {
        "id": "consumer-validator-test",
        "version": 1,
        "platform": "windows",
        "toolchain": "msvc",
    }
    receipt["obligations"] = [
        {
            "id": item.id,
            "executionStatus": "completed",
            "observation": dict(item.expected),
            "failure": None,
        }
        for item in consumer.obligations
    ]
    if damage == "stale":
        receipt["invocation"] = {**plan["invocation"], "id": "earlier-invocation"}
    elif damage == "skipped":
        receipt["obligations"][0]["executionStatus"] = "skipped"
    elif damage == "mismatch":
        receipt["obligations"][0]["observation"] = {"incorrect": True}
    if damage != "missing":
        run.receipt_path.write_text(
            "{" if damage == "malformed" else json.dumps(receipt), encoding="utf-8"
        )
    report = validate_prepared_run(pack, run, consumer_catalog=catalog)
    coverage = derive_consumer_coverage(
        pack.document(),
        catalog,
        (report,),
        scope_participant_id=participant,
        scope_execution_instance_id=instance,
    )
    assert coverage.document()["result"] == ("pass" if damage == "none" else "fail")
    assert report.scenarios == ()
