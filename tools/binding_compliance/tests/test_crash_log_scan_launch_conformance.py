"""Crash Log Scan Launch receipts need every adapter and honest launch observations."""

from pathlib import Path

import pytest
from conformance.applicability import derive_applicability
from conformance.consumers import load_consumer_obligations, prepare_consumer_run
from conformance.coverage import (
    derive_row_coverage,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
)
from conformance.enforcement import enforcement_for_family
from conformance.families.crash_log_scan_launch import (
    CRASH_LOG_SCAN_LAUNCH_COVERAGE_POLICY as POLICY,
)
from conformance.packs import load_and_validate_pack
from conformance.receipts import validate_prepared_run

from receipt_test_support import prepare_receipt_case

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("tests/conformance/packs/crash_log_scan_launch/v1.json")


def test_launch_requires_all_four_semantic_adapters() -> None:
    """Every binding maps the launch crate, so none may skip its runner.

    Frontends that launch through Crash Log Scan Launch join as consumers, never as semantic
    adapters; the native CLI (#289), the GUI (#288) and the TUI (#287) are among them.
    """
    pack = load_and_validate_pack(ROOT, PACK).document()
    matrix = derive_applicability(
        pack,
        load_source_parity_rows(ROOT),
        consumer_catalog=load_consumer_obligations(ROOT),
    )
    participants = {p.id for p in matrix.participants}
    assert {"rust", "cxx", "node", "python"} <= participants
    assert "cli" in participants
    assert "gui" in participants
    assert "tui" in participants
    assert participants - {"rust", "cxx", "node", "python"} <= {"cli", "gui", "tui"}
    assert next(
        p for p in matrix.participants if p.id == "cxx"
    ).execution_instance_ids == ("windows-clang-cl", "windows-msvc")
    assert enforcement_for_family("crash-log-scan-launch") == "blocking"


def test_tui_consumer_plan_names_the_launch_obligation_without_expectations() -> None:
    """The TUI proves it launches through Crash Log Scan Launch from an input-only plan."""
    pack = load_and_validate_pack(ROOT, PACK)
    catalog = load_consumer_obligations(ROOT)
    run = prepare_consumer_run(
        pack,
        participant_id="tui",
        execution_instance_id="tui",
        artifact_root=ROOT / "tools/binding_compliance/artifacts/consumer-tests",
        catalog=catalog,
    )
    plan = run.document()
    assert plan["familyId"] == "crash-log-scan-launch"
    assert plan["participant"]["role"] == "consumer"
    assert "scenarios" not in plan
    assert [item["id"] for item in plan["obligations"]] == ["tui.scan-launch"]
    assert all(set(item) == {"id", "scenarioIds"} for item in plan["obligations"])


@pytest.mark.parametrize("participant", ("cxx", "node", "python"))
def test_pack_observations_cover_every_binding_launch_row(
        tmp_path: Path, participant: str
) -> None:
    """The pack's own launched and refused scenarios credit each binding's launch rows."""
    pack, run, _ = prepare_receipt_case(
        ROOT, tmp_path, PACK, participant, runner_id="scan-launch-coverage"
    )
    report = validate_prepared_run(pack, run, coverage_policy=POLICY)
    assert not report.failures
    coverage = derive_row_coverage(
        pack.document(),
        load_source_parity_rows(ROOT),
        POLICY,
        (report,),
        scope_participant_id=participant,
        retained_analyzers=load_retained_analyzer_kinds(ROOT),
    )
    assert not coverage.failures
    assert coverage.rows


def _launched_observation() -> dict:
    """Return the managed-game observation the pack expects, as a mutable copy."""
    pack = load_and_validate_pack(ROOT, PACK).document()
    scenario = next(
        item for item in pack["scenarios"] if item["id"] == "managed-game-saved-values"
    )
    return dict(scenario["expected"])


def _predicate(fact_id: str):
    return next(predicate for predicate in POLICY.predicates if predicate.id == fact_id)


def test_a_launch_that_wrote_user_settings_earns_no_credit() -> None:
    """Launch is read-only; an observation reporting a changed document is not a launch fact."""
    observation = _launched_observation()
    assert _predicate("crash-log-scan-launch.launched").matches(observation)
    observation["settingsUnchanged"] = False
    assert not _predicate("crash-log-scan-launch.launched").matches(observation)


def test_only_a_withheld_saved_value_credits_the_game_differs_rule() -> None:
    """The game-differs fact needs a typed withheld-value diagnostic whose code is its kind."""
    observation = _launched_observation()
    game_differs = _predicate("crash-log-scan-launch.game-differs")
    assert not game_differs.matches(observation)

    observation["diagnostics"] = [
        {"kind": "fcx_mode_not_applied", "code": "fcx_mode_not_applied"}
    ]
    assert game_differs.matches(observation)

    observation["diagnostics"] = [
        {"kind": "fcx_mode_not_applied", "code": "game_version_not_applied"}
    ]
    assert not game_differs.matches(observation)
    assert not _predicate("crash-log-scan-launch.launched").matches(observation)


def test_diagnostics_must_carry_codes_not_prose() -> None:
    """A diagnostic with a message field would make prose part of the contract."""
    observation = _launched_observation()
    observation["diagnostics"] = [
        {"kind": "user_settings", "code": "malformed_document", "message": "prose"}
    ]
    assert not _predicate("crash-log-scan-launch.launched").matches(observation)


def test_fcx_launch_without_its_setup_context_earns_no_credit() -> None:
    """FCX Mode on must carry the four setup facts; FCX Mode off must carry none (#286)."""
    observation = _launched_observation()
    observation["request"] = dict(observation["request"], fcxEnabled=True)
    assert not _predicate("crash-log-scan-launch.launched").matches(observation)
    observation["request"]["setupContext"] = {
        "gameRoot": "Fallout 4",
        "docsRoot": "Documents",
        "gameExePath": "Fallout 4/Fallout4.exe",
        "xseLogPath": None,
    }
    assert _predicate("crash-log-scan-launch.launched").matches(observation)
    observation["request"]["fcxEnabled"] = False
    assert not _predicate("crash-log-scan-launch.launched").matches(observation)
