"""Public contract tests for the final Python Crash Log Scan Run adapter."""

import json
import shutil
import threading
import time
from pathlib import Path

import pytest


MAIN_YAML = """schema_version: "2.0"
CLASSIC_Info:
  version: "9.0.0"
  version_date: "2026-02-25"
  default_ignorefile: |
    CLASSIC_Ignore_Fallout4: []
catch_log_records:
  - "LAND"
"""

GAME_YAML = """schema_version: "1.0"
Game_Info:
  XSE_Acronym: "F4SE"
  GameVersion: "1.10.163"
  GameVersionNEW: "1.10.984"
  CRASHGEN_LatestVer: "1.37.0"
  CRASHGEN_LogName: "Buffout 4"
  Main_Root_Name: "Fallout4"
Warnings_CRASHGEN:
  Warn_NOPlugins: "No plugins found"
  Warn_Outdated: "Outdated"
Crashlog_Plugins_Exclude: []
Crashlog_Records_Exclude: []
Crashlog_Error_Check: []
Crashlog_Stack_Check: []
Mods_CONF: []
Mods_CORE: []
Mods_FREQ: []
Mods_SOLU: []
"""

IGNORE_YAML = """
CLASSIC_Ignore_Fallout4: []
"""

SAMPLE_CRASH_LOG = """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512

SYSTEM SPECS:
    OS: Microsoft Windows 11 Pro
    GPU #1: Nvidia RTX

PROBABLE CALL STACK:
    [0] Fallout4.exe+0733512

MODULES:
    Fallout4.exe v1.10.163.0

PLUGINS:
    [00] Fallout4.esm
"""

SHARED_SCAN_RUN_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "crash_log_scan_run"
)
SHARED_SCAN_RUN_MANIFEST = json.loads(
    (SHARED_SCAN_RUN_FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
)


@pytest.fixture(autouse=True)
def _isolate_installed_yaml_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep installed-data selection independent of the developer's real update cache."""

    cache_root = tmp_path / "isolated-cache"
    monkeypatch.setenv("LOCALAPPDATA", str(cache_root))
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_root))


def _write_scan_run_data_root(root: Path) -> None:
    """Write the minimal YAML Data required by a real Crash Log Scan Run."""

    database_dir = root / "CLASSIC Data" / "databases"
    database_dir.mkdir(parents=True)
    (database_dir / "CLASSIC Main.yaml").write_text(MAIN_YAML, encoding="utf-8")
    (database_dir / "CLASSIC Fallout4.yaml").write_text(
        GAME_YAML,
        encoding="utf-8",
    )
    (root / "CLASSIC Data" / "CLASSIC Ignore.yaml").write_text(
        IGNORE_YAML,
        encoding="utf-8",
    )


def _write_logs(directory: Path, names: list[str]) -> list[Path]:
    """Create valid Crash Logs in the requested deterministic name order."""

    directory.mkdir(parents=True, exist_ok=True)
    paths = [directory / name for name in names]
    for path in paths:
        path.write_text(SAMPLE_CRASH_LOG, encoding="utf-8")
    return paths


def _copy_shared_scan_run_data_root(root: Path) -> None:
    """Copy the language-neutral YAML corpus into one temporary Python run root."""

    shutil.copytree(
        SHARED_SCAN_RUN_FIXTURE_ROOT / "CLASSIC Data",
        root / "CLASSIC Data",
    )


def _write_shared_scan_run_logs(root: Path, relatives: list[str]) -> list[Path]:
    """Materialize shared valid logs at manifest-relative paths."""

    source = SHARED_SCAN_RUN_FIXTURE_ROOT / "valid-crash.log"
    paths = [root / relative for relative in relatives]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, path)
    return paths


def _shared_relative(root: Path, path: str) -> str:
    """Normalize one temporary path to the manifest's slash-separated form."""

    return Path(path).relative_to(root).as_posix()


def _configuration(
    classic_scanlog: object,
    root: Path,
    *,
    max_concurrent: int | None = None,
) -> object:
    """Create explicit scan facts shared by Standard and Targeted requests."""

    import classic_shared

    return classic_scanlog.ScanRunConfiguration(
        installation_root=str(root),
        game=classic_shared.GameId.Fallout4,
        game_version="auto",
        show_formid_values=False,
        simplify_logs=False,
        formid_database_paths=[],
        unsolved_logs_destination=None,
        max_concurrent=max_concurrent,
    )


@pytest.mark.parametrize(
    "game_attribute",
    ["Fallout4", "Fallout4VR", "Skyrim", "Starfield"],
)
def test_configuration_accepts_every_typed_shared_game_id(
    tmp_path: Path,
    game_attribute: str,
) -> None:
    """Configuration maps every shared typed game value without parsing strings."""

    import classic_scanlog
    import classic_shared

    configuration = classic_scanlog.ScanRunConfiguration(
        installation_root=str(tmp_path),
        game=getattr(classic_shared.GameId, game_attribute),
        game_version="auto",
        show_formid_values=False,
        simplify_logs=False,
        formid_database_paths=[],
    )
    assert configuration is not None

    with pytest.raises(TypeError, match="classic_shared.GameId"):
        classic_scanlog.ScanRunConfiguration(
            installation_root=str(tmp_path),
            game=game_attribute,
            game_version="auto",
            show_formid_values=False,
            simplify_logs=False,
            formid_database_paths=[],
        )


def test_request_factories_make_invalid_scan_intents_unrepresentable(
    tmp_path: Path,
) -> None:
    """Request factories require FCX context and omit Targeted movement policy."""

    import classic_scanlog

    configuration = _configuration(classic_scanlog, tmp_path)
    standard_source = classic_scanlog.ScanRunStandardSource(
        base_directory=str(tmp_path),
        custom_scan_directory=None,
        configured_documents_root=None,
    )
    targeted_source = classic_scanlog.ScanRunTargetedSource(
        inputs=[str(tmp_path / "crash-one.log")]
    )
    setup_context = classic_scanlog.ScanRunSetupContext()
    movement = classic_scanlog.ScanRunUnsolvedLogs.leave_in_place()
    configured_movement = (
        classic_scanlog.ScanRunUnsolvedLogs.move_to_configured_or_default()
    )
    custom_movement = classic_scanlog.ScanRunUnsolvedLogs.move_to_custom(
        str(tmp_path / "Unsolved Logs")
    )

    assert (
        classic_scanlog.ScanRunRequest.standard(
            configuration, standard_source, movement
        )
        is not None
    )
    assert (
        classic_scanlog.ScanRunRequest.standard_with_fcx(
            configuration, standard_source, movement, setup_context
        )
        is not None
    )
    assert (
        classic_scanlog.ScanRunRequest.standard(
            configuration, standard_source, configured_movement
        )
        is not None
    )
    assert (
        classic_scanlog.ScanRunRequest.standard(
            configuration, standard_source, custom_movement
        )
        is not None
    )
    assert (
        classic_scanlog.ScanRunRequest.targeted(configuration, targeted_source)
        is not None
    )
    assert (
        classic_scanlog.ScanRunRequest.targeted_with_fcx(
            configuration, targeted_source, setup_context
        )
        is not None
    )

    with pytest.raises(TypeError):
        classic_scanlog.ScanRunRequest.targeted(
            configuration, targeted_source, movement
        )
    with pytest.raises(TypeError):
        classic_scanlog.ScanRunRequest.targeted_with_fcx(configuration, targeted_source)


def test_scan_run_cancellation_is_opaque_and_monotonic() -> None:
    """Final-contract cancellation can be requested but never reset or replaced."""

    import classic_scanlog

    cancellation = classic_scanlog.ScanRunCancellation()

    assert cancellation.is_cancelled is False
    cancellation.cancel()
    assert cancellation.is_cancelled is True
    assert not hasattr(cancellation, "reset")


def test_scan_run_execute_maps_typed_request_validation_error(tmp_path: Path) -> None:
    """Run-wide validation failures retain their stable stage and optional path."""

    import classic_scanlog

    request = classic_scanlog.ScanRunRequest.targeted(
        _configuration(classic_scanlog, tmp_path, max_concurrent=0),
        classic_scanlog.ScanRunTargetedSource(inputs=[]),
    )

    execution = classic_scanlog.scan_run_execute(
        request,
        classic_scanlog.ScanRunCancellation(),
    )

    assert execution.result is None
    assert execution.error.stage == "request_validation"
    assert execution.error.path is None
    assert execution.observer_error is None


def test_scan_run_maps_no_logs_and_pre_discovery_cancellation(tmp_path: Path) -> None:
    """Expected empty and pre-discovery cancellation states remain typed results."""

    import classic_scanlog

    source = classic_scanlog.ScanRunTargetedSource(inputs=[])
    request = classic_scanlog.ScanRunRequest.targeted(
        _configuration(classic_scanlog, tmp_path),
        source,
    )
    events: list[object] = []
    empty = classic_scanlog.scan_run_execute(
        request,
        classic_scanlog.ScanRunCancellation(),
        events.append,
    )

    assert empty.error is None
    assert empty.result.status == "no_crash_logs_found"
    assert empty.result.discovery.source == "targeted"
    assert empty.result.discovery.accepted_logs == []
    assert empty.result.installed_yaml_data is None
    assert empty.result.effective_concurrency is None
    assert [event.kind for event in events] == ["discovery_completed"]

    cancellation = classic_scanlog.ScanRunCancellation()
    cancellation.cancel()
    cancelled = classic_scanlog.scan_run_execute(request, cancellation)

    assert cancelled.error is None
    assert cancelled.result.status == "cancelled_before_discovery"
    assert cancelled.result.discovery is None
    assert cancelled.result.setup is None
    assert cancelled.result.installed_yaml_data is None
    assert cancelled.result.logs == []


def test_targeted_directory_discovery_retains_paths_and_rejections(
    tmp_path: Path,
) -> None:
    """Rust owns recursive Targeted discovery and retains searched/rejected paths."""

    import classic_scanlog

    _write_scan_run_data_root(tmp_path)
    crash_log = _write_logs(
        tmp_path / "selected" / "nested",
        ["crash-directory.log"],
    )[0]
    missing = tmp_path / "missing"
    inputs = [str(tmp_path / "selected"), str(missing)]
    request = classic_scanlog.ScanRunRequest.targeted(
        _configuration(classic_scanlog, tmp_path, max_concurrent=1),
        classic_scanlog.ScanRunTargetedSource(inputs=inputs),
    )

    execution = classic_scanlog.scan_run_execute(
        request,
        classic_scanlog.ScanRunCancellation(),
    )

    assert execution.error is None
    discovery = execution.result.discovery
    assert discovery.source == "targeted"
    assert discovery.accepted_logs == [str(crash_log)]
    assert discovery.searched_locations == inputs
    assert [(item.path, item.reason) for item in discovery.rejected_inputs] == [
        (str(missing), "path does not exist")
    ]


def test_fcx_setup_materializes_typed_checks_and_path_updates(tmp_path: Path) -> None:
    """FCX results expose setup DTOs, including a detected game-root proposal."""

    import classic_scanlog

    _write_scan_run_data_root(tmp_path)
    crash_log = _write_logs(tmp_path / "selected", ["crash-fcx.log"])[0]
    game_root = tmp_path / "Fallout4"
    docs_root = tmp_path / "Documents"
    game_root.mkdir()
    docs_root.mkdir()
    for name in ("Fallout4.ini", "Fallout4Custom.ini", "Fallout4Prefs.ini"):
        (docs_root / name).write_text("[General]\n", encoding="utf-8")
    game_executable = game_root / "Fallout4Custom.exe"
    game_executable.write_bytes(b"not a real pe")
    (game_root / "f4se_loader.exe").write_bytes(b"loader")
    request = classic_scanlog.ScanRunRequest.targeted_with_fcx(
        _configuration(classic_scanlog, tmp_path),
        classic_scanlog.ScanRunTargetedSource(inputs=[str(crash_log)]),
        classic_scanlog.ScanRunSetupContext(
            docs_root=str(docs_root),
            game_exe_path=str(game_executable),
        ),
    )

    execution = classic_scanlog.scan_run_execute(
        request,
        classic_scanlog.ScanRunCancellation(),
    )

    assert execution.error is None
    assert execution.result.status == "setup_failed"
    setup = execution.result.setup
    assert isinstance(setup, classic_scanlog.ScanRunSetupResult)
    assert setup.checks
    assert all(
        isinstance(check, classic_scanlog.ScanRunSetupCheck) for check in setup.checks
    )
    assert [(update.kind, update.path) for update in setup.path_updates] == [
        ("game_root", str(game_root))
    ]
    assert isinstance(
        setup.path_updates[0],
        classic_scanlog.ScanRunSetupPathUpdate,
    )


def test_failed_log_materializes_structured_python_failures(tmp_path: Path) -> None:
    """A per-log analysis failure is retained as typed Python failure data."""

    import classic_scanlog

    _write_scan_run_data_root(tmp_path)
    malformed = tmp_path / "selected.log"
    malformed.write_text(SAMPLE_CRASH_LOG, encoding="utf-8")
    (tmp_path / "selected-AUTOSCAN.md").mkdir()
    request = classic_scanlog.ScanRunRequest.targeted(
        _configuration(classic_scanlog, tmp_path),
        classic_scanlog.ScanRunTargetedSource(inputs=[str(malformed)]),
    )

    execution = classic_scanlog.scan_run_execute(
        request,
        classic_scanlog.ScanRunCancellation(),
    )

    assert execution.error is None
    result = execution.result.logs[0]
    assert result.disposition == "failed"
    assert result.failures
    assert all(
        isinstance(failure, classic_scanlog.ScanRunLogFailure)
        for failure in result.failures
    )


def test_standard_scan_run_persists_reports_in_discovery_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The shared Standard fixture retains Rust-owned facts and durable reports."""

    import classic_scanlog

    # shared Standard fixture
    fixture = SHARED_SCAN_RUN_MANIFEST["fixtures"]["standard"]
    expected = fixture["expected"]
    _copy_shared_scan_run_data_root(tmp_path)
    crash_logs = _write_shared_scan_run_logs(tmp_path, fixture["logs"])
    documents_root = tmp_path / "Documents"
    documents_root.mkdir()
    monkeypatch.chdir(tmp_path)
    request = classic_scanlog.ScanRunRequest.standard(
        _configuration(
            classic_scanlog,
            tmp_path,
            max_concurrent=fixture["maxConcurrent"],
        ),
        classic_scanlog.ScanRunStandardSource(
            base_directory=str(tmp_path),
            configured_documents_root=str(documents_root),
        ),
        classic_scanlog.ScanRunUnsolvedLogs.leave_in_place(),
    )
    events: list[object] = []

    execution = classic_scanlog.scan_run_execute(
        request,
        classic_scanlog.ScanRunCancellation(),
        events.append,
    )

    assert execution.error is None
    assert execution.observer_error is None
    result = execution.result
    assert result.status == "completed"
    installed = result.installed_yaml_data
    assert isinstance(
        installed,
        classic_scanlog.ScanRunInstalledYamlDataRunData,
    )
    assert isinstance(installed.main, classic_scanlog.ScanRunInspectedYamlDataFile)
    assert (installed.main.role, installed.main.provenance) == ("main", "bundled")
    assert (installed.main.schema_major, installed.main.schema_minor) == (2, 0)
    assert len(installed.main.sha256) == 64
    assert installed.main.byte_length > 0
    assert (installed.game_file.role, installed.game_file.provenance) == (
        "game",
        "bundled",
    )
    assert (installed.game_file.schema_major, installed.game_file.schema_minor) == (
        1,
        0,
    )
    assert installed.local_ignore_state == "existing"
    assert isinstance(
        installed.local_ignore_identity,
        classic_scanlog.ScanRunYamlDataContentIdentity,
    )
    assert len(installed.local_ignore_identity.sha256) == 64
    assert installed.local_ignore_identity.byte_len == len(
        (tmp_path / "CLASSIC Data" / "CLASSIC Ignore.yaml").read_bytes()
    )
    assert all(
        isinstance(
            diagnostic,
            classic_scanlog.ScanRunInstalledYamlDataDiagnostic,
        )
        for diagnostic in installed.diagnostics
    )
    with pytest.raises(AttributeError):
        installed.local_ignore_state = "generated"
    assert result.effective_concurrency == expected["effectiveConcurrency"]
    assert result.discovery.source == "standard"
    assert [
        _shared_relative(tmp_path, path) for path in result.discovery.accepted_logs
    ] == expected["acceptedLogs"]
    assert [log.discovery_index for log in result.logs] == expected["discoveryOrder"]
    assert [log.crash_log for log in result.logs] == [str(path) for path in crash_logs]
    assert [log.disposition for log in result.logs] == expected["dispositions"]
    assert all(Path(log.autoscan_report).is_file() for log in result.logs)
    assert all(
        Path(log.autoscan_report).read_text(encoding="utf-8") for log in result.logs
    )
    assert {
        "discovery_completed",
        "effective_concurrency_selected",
        "log_queued",
        "log_started",
        "log_phase",
        "log_finished",
    }.issubset({event.kind for event in events})


def test_missing_local_ignore_is_generated_and_reported_as_run_data(
    tmp_path: Path,
) -> None:
    """A generated Local Ignore is retained as structured run-level snapshot data."""

    import classic_scanlog

    _write_scan_run_data_root(tmp_path)
    local_ignore_path = tmp_path / "CLASSIC Data" / "CLASSIC Ignore.yaml"
    local_ignore_path.unlink()
    crash_log = _write_logs(tmp_path / "selected", ["crash-generated-ignore.log"])[0]
    request = classic_scanlog.ScanRunRequest.targeted(
        _configuration(classic_scanlog, tmp_path),
        classic_scanlog.ScanRunTargetedSource(inputs=[str(crash_log)]),
    )

    execution = classic_scanlog.scan_run_execute(
        request,
        classic_scanlog.ScanRunCancellation(),
    )

    assert execution.error is None
    installed = execution.result.installed_yaml_data
    assert installed.local_ignore_state == "generated"
    assert installed.local_ignore_identity.byte_len == len(
        local_ignore_path.read_bytes()
    )
    generated = [
        diagnostic
        for diagnostic in installed.diagnostics
        if diagnostic.kind == "local_ignore_generated"
    ]
    assert len(generated) == 1
    assert generated[0].role is None
    assert generated[0].candidate is None
    assert generated[0].path == local_ignore_path


def test_shared_local_ignore_recovery_continuation_retains_snapshot_and_rejects_replay(
    tmp_path: Path,
) -> None:
    """Proceed Without Ignore reuses exact retained discovery and YAML Data once."""

    import classic_scanlog

    fixture = SHARED_SCAN_RUN_MANIFEST["fixtures"]["installedYamlData"]
    _copy_shared_scan_run_data_root(tmp_path)
    crash_log = _write_shared_scan_run_logs(tmp_path, [fixture["input"]])[0]
    ignore_path = tmp_path / "CLASSIC Data" / "CLASSIC Ignore.yaml"
    request = classic_scanlog.ScanRunRequest.targeted(
        _configuration(classic_scanlog, tmp_path),
        classic_scanlog.ScanRunTargetedSource(inputs=[str(crash_log)]),
    )
    baseline = classic_scanlog.scan_run_execute(
        request,
        classic_scanlog.ScanRunCancellation(),
    ).result
    baseline_report = Path(baseline.logs[0].autoscan_report).read_bytes()
    ignore_path.write_text(fixture["malformedLocalIgnore"], encoding="utf-8")
    initial_events: list[object] = []
    initial = classic_scanlog.scan_run_execute(
        request,
        classic_scanlog.ScanRunCancellation(),
        initial_events.append,
    ).result

    assert initial.status == "local_ignore_recovery_required"
    assert initial.installed_yaml_data.local_ignore_state == "recovery_required"
    assert "parse" in {
        diagnostic.kind for diagnostic in initial.installed_yaml_data.diagnostics
    }
    assert [event.kind for event in initial_events] == ["discovery_completed"]
    continuation = initial.continuation
    assert isinstance(continuation, classic_scanlog.ScanRunContinuation)

    (tmp_path / "CLASSIC Data" / "databases" / "CLASSIC Main.yaml").write_text(
        "invalid: [unterminated",
        encoding="utf-8",
    )
    resumed_events: list[object] = []
    resumed = classic_scanlog.scan_run_resume(
        continuation,
        classic_scanlog.ScanRunLocalIgnoreRecoveryDecision.ProceedWithoutIgnore,
        classic_scanlog.ScanRunCancellation(),
        resumed_events.append,
    ).result

    assert resumed.status == "completed"
    assert resumed.discovery.accepted_logs == initial.discovery.accepted_logs
    assert resumed.installed_yaml_data.main.sha256 == initial.installed_yaml_data.main.sha256
    assert (
        resumed.installed_yaml_data.game_file.sha256
        == initial.installed_yaml_data.game_file.sha256
    )
    assert resumed.installed_yaml_data.local_ignore_state == "proceed_without_ignore"
    assert all(event.kind != "discovery_completed" for event in resumed_events)
    assert Path(resumed.logs[0].autoscan_report).read_bytes() == baseline_report
    assert ignore_path.read_text(encoding="utf-8") == fixture["malformedLocalIgnore"]

    with pytest.raises(classic_scanlog.ScanRunContinuationConsumedError) as replay:
        classic_scanlog.scan_run_resume(
            continuation,
            classic_scanlog.ScanRunLocalIgnoreRecoveryDecision.ProceedWithoutIgnore,
            classic_scanlog.ScanRunCancellation(),
        )
    assert replay.value.code == "scan_run_continuation_consumed"


def test_reset_to_default_returns_durable_metadata_and_unchanged_shared_report(
    tmp_path: Path,
) -> None:
    """Reset resumes retained discovery and selected bytes with verified backup metadata."""

    import classic_scanlog

    fixture = SHARED_SCAN_RUN_MANIFEST["fixtures"]["installedYamlData"]
    _copy_shared_scan_run_data_root(tmp_path)
    crash_log = _write_shared_scan_run_logs(tmp_path, [fixture["input"]])[0]
    ignore_path = tmp_path / "CLASSIC Data" / "CLASSIC Ignore.yaml"
    request = classic_scanlog.ScanRunRequest.targeted(
        _configuration(classic_scanlog, tmp_path),
        classic_scanlog.ScanRunTargetedSource(inputs=[str(crash_log)]),
    )
    baseline = classic_scanlog.scan_run_execute(
        request,
        classic_scanlog.ScanRunCancellation(),
    ).result
    baseline_report = Path(baseline.logs[0].autoscan_report).read_bytes()
    ignore_path.write_text(fixture["malformedLocalIgnore"], encoding="utf-8")
    initial = classic_scanlog.scan_run_execute(
        request,
        classic_scanlog.ScanRunCancellation(),
    ).result
    retained_main = initial.installed_yaml_data.main.sha256
    retained_game = initial.installed_yaml_data.game_file.sha256
    (tmp_path / "CLASSIC Data" / "databases" / "CLASSIC Main.yaml").write_text(
        "invalid: [unterminated",
        encoding="utf-8",
    )
    (tmp_path / "CLASSIC Data" / "databases" / "CLASSIC Fallout4.yaml").write_text(
        "invalid: [unterminated",
        encoding="utf-8",
    )
    events: list[object] = []

    reset = classic_scanlog.scan_run_resume(
        initial.continuation,
        classic_scanlog.ScanRunLocalIgnoreRecoveryDecision.ResetToDefault,
        classic_scanlog.ScanRunCancellation(),
        events.append,
    ).result

    assert reset.status == "completed"
    assert reset.discovery.accepted_logs == initial.discovery.accepted_logs
    assert reset.installed_yaml_data.main.sha256 == retained_main
    assert reset.installed_yaml_data.game_file.sha256 == retained_game
    assert reset.installed_yaml_data.local_ignore_state == "reset_to_default"
    assert "local_ignore_reset" in {
        diagnostic.kind for diagnostic in reset.installed_yaml_data.diagnostics
    }
    metadata = reset.installed_yaml_data.local_ignore_reset
    assert metadata is not None
    assert metadata.backup_path.read_bytes() == fixture["malformedLocalIgnore"].encode()
    assert metadata.malformed_identity.sha256 == metadata.backup_identity.sha256
    assert (
        metadata.replacement_identity.sha256
        == reset.installed_yaml_data.local_ignore_identity.sha256
    )
    assert Path(reset.logs[0].autoscan_report).read_bytes() == baseline_report
    assert all(event.kind != "discovery_completed" for event in events)
    with pytest.raises(classic_scanlog.ScanRunContinuationConsumedError) as replay:
        classic_scanlog.scan_run_resume(
            initial.continuation,
            classic_scanlog.ScanRunLocalIgnoreRecoveryDecision.ResetToDefault,
            classic_scanlog.ScanRunCancellation(),
        )
    assert replay.value.code == fixture["resetOutcomes"]["consumedCode"]


def test_reset_to_default_exposes_typed_conflict_and_backup_failure(
    tmp_path: Path,
) -> None:
    """Reset conflict and pre-replacement operational failure remain distinct exceptions."""

    import classic_scanlog

    fixture = SHARED_SCAN_RUN_MANIFEST["fixtures"]["installedYamlData"]

    def paused(root: Path) -> tuple[object, Path]:
        _copy_shared_scan_run_data_root(root)
        crash_log = _write_shared_scan_run_logs(root, [fixture["input"]])[0]
        ignore_path = root / "CLASSIC Data" / "CLASSIC Ignore.yaml"
        ignore_path.write_text(fixture["malformedLocalIgnore"], encoding="utf-8")
        result = classic_scanlog.scan_run_execute(
            classic_scanlog.ScanRunRequest.targeted(
                _configuration(classic_scanlog, root),
                classic_scanlog.ScanRunTargetedSource(inputs=[str(crash_log)]),
            ),
            classic_scanlog.ScanRunCancellation(),
        ).result
        return result.continuation, ignore_path

    conflict_continuation, conflict_ignore = paused(tmp_path / "conflict")
    conflict_ignore.write_text("CLASSIC_Ignore_Fallout4: []\n", encoding="utf-8")
    with pytest.raises(classic_scanlog.ScanRunLocalIgnoreResetConflictError) as conflict:
        classic_scanlog.scan_run_resume(
            conflict_continuation,
            classic_scanlog.ScanRunLocalIgnoreRecoveryDecision.ResetToDefault,
            classic_scanlog.ScanRunCancellation(),
        )
    assert conflict.value.code == fixture["resetOutcomes"]["conflictCode"]
    assert conflict.value.expected_identity.sha256 != conflict.value.actual_identity.sha256

    failure_root = tmp_path / "backup-failure"
    failure_continuation, failure_ignore = paused(failure_root)
    (failure_root / "CLASSIC Backup").write_text("not a directory", encoding="utf-8")
    with pytest.raises(classic_scanlog.ScanRunLocalIgnoreResetBackupError) as failure:
        classic_scanlog.scan_run_resume(
            failure_continuation,
            classic_scanlog.ScanRunLocalIgnoreRecoveryDecision.ResetToDefault,
            classic_scanlog.ScanRunCancellation(),
        )
    assert failure.value.code == fixture["resetOutcomes"]["backupFailureCode"]
    assert failure.value.stage is None
    assert failure_ignore.read_text(encoding="utf-8") == fixture["malformedLocalIgnore"]


def test_pre_resume_cancellation_wins_without_mutating_local_ignore(
    tmp_path: Path,
) -> None:
    """Cancellation at resume returns a normal post-discovery cancelled result."""

    import classic_scanlog

    fixture = SHARED_SCAN_RUN_MANIFEST["fixtures"]["installedYamlData"]
    _copy_shared_scan_run_data_root(tmp_path)
    crash_log = _write_shared_scan_run_logs(tmp_path, [fixture["input"]])[0]
    ignore_path = tmp_path / "CLASSIC Data" / "CLASSIC Ignore.yaml"
    ignore_path.write_text(fixture["malformedLocalIgnore"], encoding="utf-8")
    initial = classic_scanlog.scan_run_execute(
        classic_scanlog.ScanRunRequest.targeted(
            _configuration(classic_scanlog, tmp_path),
            classic_scanlog.ScanRunTargetedSource(inputs=[str(crash_log)]),
        ),
        classic_scanlog.ScanRunCancellation(),
    ).result
    cancellation = classic_scanlog.ScanRunCancellation()
    cancellation.cancel()
    events: list[object] = []

    resumed = classic_scanlog.scan_run_resume(
        initial.continuation,
        classic_scanlog.ScanRunLocalIgnoreRecoveryDecision.ResetToDefault,
        cancellation,
        events.append,
    ).result

    assert resumed.status == "cancelled"
    assert resumed.cancelled == resumed.total
    assert all(log.disposition == "cancelled_before_start" for log in resumed.logs)
    assert events == []
    assert ignore_path.read_text(encoding="utf-8") == fixture["malformedLocalIgnore"]
    assert (tmp_path / "CLASSIC Backup").exists() is fixture["resetOutcomes"][
        "preResetCancellationMutates"
    ]


def test_post_critical_cancellation_waits_for_durable_reset(tmp_path: Path) -> None:
    """Cancellation after reset lock acquisition waits for backup and replacement durability."""

    import classic_scanlog

    fixture = SHARED_SCAN_RUN_MANIFEST["fixtures"]["installedYamlData"]
    _copy_shared_scan_run_data_root(tmp_path)
    crash_log = _write_shared_scan_run_logs(tmp_path, [fixture["input"]])[0]
    ignore_path = tmp_path / "CLASSIC Data" / "CLASSIC Ignore.yaml"
    large_malformed_ignore = fixture["malformedLocalIgnore"] + "x" * (16 * 1024 * 1024)
    ignore_path.write_text(large_malformed_ignore, encoding="utf-8")
    initial = classic_scanlog.scan_run_execute(
        classic_scanlog.ScanRunRequest.targeted(
            _configuration(classic_scanlog, tmp_path),
            classic_scanlog.ScanRunTargetedSource(inputs=[str(crash_log)]),
        ),
        classic_scanlog.ScanRunCancellation(),
    ).result
    cancellation = classic_scanlog.ScanRunCancellation()
    reset_lock = tmp_path / ".classic-local-ignore-reset.lock"
    observed_reset_entry = threading.Event()

    def cancel_after_reset_entry() -> None:
        """Request cancellation only after config core has entered its reset transaction."""

        deadline = time.monotonic() + 5
        while not reset_lock.exists() and time.monotonic() < deadline:
            time.sleep(0.001)
        if reset_lock.exists():
            observed_reset_entry.set()
            cancellation.cancel()

    canceller = threading.Thread(target=cancel_after_reset_entry)
    canceller.start()
    cancelled = classic_scanlog.scan_run_resume(
        initial.continuation,
        classic_scanlog.ScanRunLocalIgnoreRecoveryDecision.ResetToDefault,
        cancellation,
    ).result
    canceller.join()

    assert observed_reset_entry.is_set()
    assert cancelled.status == fixture["resetOutcomes"]["postCriticalCancellationStatus"]
    assert all(log.autoscan_report is None for log in cancelled.logs)
    backup_directory = tmp_path / "CLASSIC Backup" / "YAML Data" / "Local Ignore"
    backups = list(backup_directory.iterdir())
    assert len(backups) == 1
    if fixture["resetOutcomes"]["backupMustEqualMalformedBytes"]:
        assert backups[0].read_text(encoding="utf-8") == large_malformed_ignore
    assert ignore_path.read_text(encoding="utf-8") != large_malformed_ignore


def test_targeted_scan_run_preserves_input_order_and_never_moves(
    tmp_path: Path,
) -> None:
    """The shared Targeted fixture retains order, rejections, and no-move behavior."""

    import classic_scanlog

    # shared Targeted fixture
    fixture = SHARED_SCAN_RUN_MANIFEST["fixtures"]["targeted"]
    expected = fixture["expected"]
    _copy_shared_scan_run_data_root(tmp_path)
    _write_shared_scan_run_logs(
        tmp_path,
        [path for path in fixture["inputs"] if path.endswith(".log")],
    )
    caller_order = [tmp_path / path for path in fixture["inputs"]]
    request = classic_scanlog.ScanRunRequest.targeted(
        _configuration(
            classic_scanlog,
            tmp_path,
            max_concurrent=fixture["maxConcurrent"],
        ),
        classic_scanlog.ScanRunTargetedSource(
            inputs=[str(path) for path in caller_order]
        ),
    )

    execution = classic_scanlog.scan_run_execute(
        request,
        classic_scanlog.ScanRunCancellation(),
    )

    assert execution.error is None
    assert execution.observer_error is None
    result = execution.result
    assert result.discovery.source == "targeted"
    assert [
        _shared_relative(tmp_path, path) for path in result.discovery.accepted_logs
    ] == expected["acceptedLogs"]
    assert [
        _shared_relative(tmp_path, rejected.path)
        for rejected in result.discovery.rejected_inputs
    ] == expected["rejectedInputs"]
    assert result.effective_concurrency == expected["effectiveConcurrency"]
    assert [log.discovery_index for log in result.logs] == expected["discoveryOrder"]
    assert [
        _shared_relative(tmp_path, log.crash_log) for log in result.logs
    ] == expected["acceptedLogs"]
    assert [log.disposition for log in result.logs] == expected["dispositions"]
    assert all(log.moved_to_unsolved_logs is False for log in result.logs)
    assert all(Path(log.autoscan_report).is_file() for log in result.logs)
    assert expected["unsolvedLogsArtifacts"] == []
    assert not (tmp_path / "Unsolved Logs").exists()


def test_shared_cancellation_fixture_distinguishes_safe_seams(tmp_path: Path) -> None:
    """Pre-discovery, queued, and admitted cancellation retain distinct facts."""

    import classic_scanlog

    fixture = SHARED_SCAN_RUN_MANIFEST["fixtures"]["targeted"]
    expected_logs = fixture["expected"]["acceptedLogs"]

    pre_root = tmp_path / "pre"
    pre_root.mkdir()
    _copy_shared_scan_run_data_root(pre_root)
    pre_logs = _write_shared_scan_run_logs(pre_root, expected_logs)
    pre_cancellation = classic_scanlog.ScanRunCancellation()
    pre_cancellation.cancel()
    pre_execution = classic_scanlog.scan_run_execute(
        classic_scanlog.ScanRunRequest.targeted(
            _configuration(classic_scanlog, pre_root),
            classic_scanlog.ScanRunTargetedSource(
                inputs=[str(path) for path in pre_logs]
            ),
        ),
        pre_cancellation,
    )
    assert pre_execution.result.status == "cancelled_before_discovery"
    assert pre_execution.result.discovery is None
    assert pre_execution.result.logs == []

    queued_root = tmp_path / "queued"
    queued_root.mkdir()
    _copy_shared_scan_run_data_root(queued_root)
    queued_logs = _write_shared_scan_run_logs(queued_root, expected_logs)
    queued_cancellation = classic_scanlog.ScanRunCancellation()
    queued_events: list[str] = []

    def cancel_while_queued(event: object) -> None:
        """Cancel after queueing begins but before any log is admitted."""

        queued_events.append(event.kind)
        if event.kind == "log_queued":
            queued_cancellation.cancel()

    queued_execution = classic_scanlog.scan_run_execute(
        classic_scanlog.ScanRunRequest.targeted(
            _configuration(classic_scanlog, queued_root, max_concurrent=1),
            classic_scanlog.ScanRunTargetedSource(
                inputs=[str(path) for path in queued_logs]
            ),
        ),
        queued_cancellation,
        cancel_while_queued,
    )
    assert len(queued_execution.result.discovery.accepted_logs) == 2
    assert [log.disposition for log in queued_execution.result.logs] == [
        "cancelled_before_start",
        "cancelled_before_start",
    ]
    assert all(log.autoscan_report is None for log in queued_execution.result.logs)
    assert "log_started" not in queued_events

    admitted_root = tmp_path / "admitted"
    admitted_root.mkdir()
    _copy_shared_scan_run_data_root(admitted_root)
    admitted_logs = _write_shared_scan_run_logs(admitted_root, expected_logs)
    admitted_cancellation = classic_scanlog.ScanRunCancellation()

    def cancel_after_admission(event: object) -> None:
        """Cancel after the first log starts so its durable unit must finish."""

        if (
            event.kind == "log_started"
            and event.log is not None
            and event.log.discovery_index == 0
        ):
            admitted_cancellation.cancel()

    admitted_execution = classic_scanlog.scan_run_execute(
        classic_scanlog.ScanRunRequest.targeted(
            _configuration(classic_scanlog, admitted_root, max_concurrent=1),
            classic_scanlog.ScanRunTargetedSource(
                inputs=[str(path) for path in admitted_logs]
            ),
        ),
        admitted_cancellation,
        cancel_after_admission,
    )
    assert admitted_execution.result.logs[0].disposition == "succeeded"
    assert Path(admitted_execution.result.logs[0].autoscan_report).is_file()
    assert admitted_execution.result.logs[1].disposition == "cancelled_before_start"
    assert admitted_execution.result.logs[1].autoscan_report is None


def test_observer_failure_is_adapter_data_and_can_request_safe_cancellation(
    tmp_path: Path,
) -> None:
    """A callback exception stays outside core errors and can cancel future work."""

    import classic_scanlog

    _write_scan_run_data_root(tmp_path)
    crash_log = _write_logs(tmp_path / "selected", ["crash-observed.log"])[0]
    request = classic_scanlog.ScanRunRequest.targeted(
        _configuration(classic_scanlog, tmp_path, max_concurrent=1),
        classic_scanlog.ScanRunTargetedSource(inputs=[str(crash_log)]),
    )
    cancellation = classic_scanlog.ScanRunCancellation()

    def broken_observer(event: object) -> None:
        raise RuntimeError(f"cannot deliver {event.kind}")

    execution = classic_scanlog.scan_run_execute(
        request,
        cancellation,
        broken_observer,
        cancel_on_observer_error=True,
    )

    assert execution.error is None
    assert "cannot deliver discovery_completed" in execution.observer_error
    assert cancellation.is_cancelled is True
    assert execution.result.status == "cancelled"
    assert execution.result.logs[0].disposition == "cancelled_before_start"
