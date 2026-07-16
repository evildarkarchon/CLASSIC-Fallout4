"""Public contract tests for the final Python Crash Log Scan Run adapter."""

import json
import shutil
from pathlib import Path

import pytest


MAIN_YAML = """
CLASSIC_Info:
  version: "9.0.0"
  version_date: "2026-02-25"
catch_log_records:
  - "LAND"
"""

GAME_YAML = """
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


def _write_scan_run_data_root(root: Path) -> None:
    """Write the minimal YAML Data required by a real Crash Log Scan Run."""

    database_dir = root / "CLASSIC Data" / "databases"
    database_dir.mkdir(parents=True)
    (database_dir / "CLASSIC Main.yaml").write_text(MAIN_YAML, encoding="utf-8")
    (database_dir / "CLASSIC Fallout4.yaml").write_text(
        GAME_YAML,
        encoding="utf-8",
    )
    (root / "CLASSIC Ignore.yaml").write_text(IGNORE_YAML, encoding="utf-8")


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
    shutil.copyfile(
        SHARED_SCAN_RUN_FIXTURE_ROOT / "CLASSIC Ignore.yaml",
        root / "CLASSIC Ignore.yaml",
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

    return classic_scanlog.ScanRunConfiguration(
        yaml_dir_root=str(root),
        yaml_dir_data=str(root / "CLASSIC Data"),
        game="Fallout4",
        game_version="auto",
        show_formid_values=False,
        simplify_logs=False,
        formid_database_paths=[],
        unsolved_logs_destination=None,
        max_concurrent=max_concurrent,
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
    assert empty.result.effective_concurrency is None
    assert [event.kind for event in events] == ["discovery_completed"]

    cancellation = classic_scanlog.ScanRunCancellation()
    cancellation.cancel()
    cancelled = classic_scanlog.scan_run_execute(request, cancellation)

    assert cancelled.error is None
    assert cancelled.result.status == "cancelled_before_discovery"
    assert cancelled.result.discovery is None
    assert cancelled.result.setup is None
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
