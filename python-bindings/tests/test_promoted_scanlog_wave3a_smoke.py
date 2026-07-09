"""Per-class smoke tests for Phase 3 Plan 04 - scanlog Wave 3a
(orchestration core).

Covers 50 promoted contract rows across 6 scanlog sub-modules:
orchestrator, papyrus, version, crashgen_registry, segment_key, error.
The ``report`` sub-module is intentionally excluded — it lives in
Plan 05 (Wave 3b) because of its heavier 5-class test surface.

Each ``#[pyclass]`` with a Python wrapper gets at least one test that
constructs it and calls one real method (per Phase 3 D-07). Related
free functions are grouped into one test each. Constructor signatures
were verified in
``.planning/phases/03-python-tier-collapse/03-04-CONSTRUCTOR-INVENTORY.md``.

Rust-only symbols promoted as ``@rust`` proxy rows (``ScanProgressPhase``,
``CrashgenRegistry``, ``ScanLogError``, ``PapyrusError``,
``segment_key``, etc.) do NOT have Python wrappers at runtime. Tests
cannot construct them directly. The parity contract rows enforce that
the rust symbols exist in the parsed ``-core`` surface, and a single
``test_rust_only_symbols_in_core_surface`` sanity check asserts that
the ``-core`` crate still exports them.

The autouse FCX reset fixture from Plan 03's ``conftest.py`` is still
active, but Wave 3a does not touch FCX state.
"""

from __future__ import annotations

import classic_scanlog


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


def _write_scan_run_data_root(root) -> None:
    database_dir = root / "CLASSIC Data" / "databases"
    database_dir.mkdir(parents=True)
    (database_dir / "CLASSIC Main.yaml").write_text(MAIN_YAML, encoding="utf-8")
    (database_dir / "CLASSIC Fallout4.yaml").write_text(GAME_YAML, encoding="utf-8")
    (root / "CLASSIC Ignore.yaml").write_text(IGNORE_YAML, encoding="utf-8")

# =============================================================================
# orchestrator sub-module: AnalysisConfig
# =============================================================================


def test_analysis_config_construct_and_getter_roundtrip() -> None:
    """``AnalysisConfig(game, game_version)`` stores game and exposes setters for runtime metadata.

    Verified from -core orchestrator.rs:288-319: ``new`` accepts the second arg as
    ``selected_game_version`` and resolves it through the Version Registry, storing
    the result internally as ``selected_version``. The public ``game_version`` getter
    starts empty and is populated later via the setter or by ``from_yamldata``.
    """
    config = classic_scanlog.AnalysisConfig("Fallout4", "Original")
    # Getters verified from orchestrator.rs:557-614
    assert config.game == "Fallout4"
    # game_version starts empty; set via setter to exercise the writer path
    config.game_version = "1.10.163"
    assert config.game_version == "1.10.163"
    # Default crashgen_name is empty; setter roundtrip exercises another writer path
    config.crashgen_name = "Buffout 4"
    assert config.crashgen_name == "Buffout 4"


def test_analysis_config_ignore_lists_default_empty() -> None:
    """Default ``AnalysisConfig`` starts with empty ignore lists (verified from -core defaults)."""
    config = classic_scanlog.AnalysisConfig("Fallout4", "Original")
    assert config.ignore_plugins == []
    assert config.ignore_records == []
    assert config.ignore_list == []


# =============================================================================
# orchestrator sub-module: CancellationToken
# =============================================================================


def test_cancellation_token_default_is_not_cancelled() -> None:
    """``CancellationToken()`` starts in the not-cancelled state."""
    token = classic_scanlog.CancellationToken()
    assert token.is_cancelled() is False


def test_cancellation_token_cancel_flips_state() -> None:
    """``token.cancel()`` sets ``is_cancelled()`` to True (Arc<AtomicBool> backing)."""
    token = classic_scanlog.CancellationToken()
    token.cancel()
    assert token.is_cancelled() is True


def test_cancellation_token_reset_clears_cancelled_state() -> None:
    """``token.reset()`` clears the cancelled flag so the token can be reused."""
    token = classic_scanlog.CancellationToken()
    token.cancel()
    assert token.is_cancelled() is True
    token.reset()
    assert token.is_cancelled() is False


# =============================================================================
# orchestrator sub-module: Orchestrator (aka PyRustOrchestrator)
# =============================================================================


def test_orchestrator_construct_from_config() -> None:
    """``Orchestrator(config)`` constructs successfully from an ``AnalysisConfig``."""
    config = classic_scanlog.AnalysisConfig("Fallout4", "Original")
    orch = classic_scanlog.Orchestrator(config)
    assert orch is not None


def test_orchestrator_config_returns_analysis_config() -> None:
    """``orchestrator.config()`` returns an ``AnalysisConfig`` clone of the stored config.

    Only ``game`` and ``crashgen_name`` are verified here because ``game_version``
    starts empty after construction (see test_analysis_config_construct_and_getter_roundtrip
    for the rationale).
    """
    config = classic_scanlog.AnalysisConfig("Fallout4", "Original")
    config.crashgen_name = "Buffout 4"
    orch = classic_scanlog.Orchestrator(config)
    returned = orch.config()
    assert returned.game == "Fallout4"
    assert returned.crashgen_name == "Buffout 4"


def test_orchestrator_feature_complete_is_bool() -> None:
    """``is_feature_complete()`` returns a bool (exact value is implementation-dependent)."""
    config = classic_scanlog.AnalysisConfig("Fallout4", "Original")
    orch = classic_scanlog.Orchestrator(config)
    assert isinstance(orch.is_feature_complete(), bool)


def test_orchestrator_has_database_pool_default_false() -> None:
    """A fresh orchestrator has no database pool attached until ``attach_database`` is called."""
    config = classic_scanlog.AnalysisConfig("Fallout4", "Original")
    orch = classic_scanlog.Orchestrator(config)
    assert orch.has_database_pool() is False


def test_orchestrator_check_loadorder_exists_missing_path() -> None:
    """``check_loadorder_exists`` is a static method that returns False for a missing directory."""
    # Static method - no self needed
    result = classic_scanlog.Orchestrator.check_loadorder_exists("/nonexistent/path/loadorder")
    assert result is False


def test_orchestrator_process_logs_parallel_is_declared_if_present() -> None:
    """Defensive: the .pyi declares ``process_logs_parallel`` but the PyO3 wrapper does not.

    This test guards against import-time errors if the wrapper ever gets added, and
    verifies that if it is available it is callable. The contract row exists because
    ``classic_scanlog.pyi`` declares this method; runtime absence is tracked as a
    known stub-vs-runtime divergence documented in 03-04-CONSTRUCTOR-INVENTORY.md.
    """
    config = classic_scanlog.AnalysisConfig("Fallout4", "Original")
    orch = classic_scanlog.Orchestrator(config)
    if hasattr(orch, "process_logs_parallel"):
        # If the method exists, an empty batch should return an empty list (cheap smoke call)
        result = orch.process_logs_parallel([])
        assert isinstance(result, list)
    # Else: known stub-vs-runtime divergence, documented in Plan 04 inventory


def test_scan_run_execute_returns_targeted_rejections_as_discovery_data(tmp_path) -> None:
    """``scan_run_execute`` exposes rejected Targeted inputs as run-level data."""
    _write_scan_run_data_root(tmp_path)
    missing_log = tmp_path / "missing.log"

    scan_result = classic_scanlog.scan_run_execute(
        str(tmp_path),
        str(tmp_path / "CLASSIC Data"),
        "Fallout4",
        "auto",
        [str(missing_log)],
        targeted_mode=True,
        max_concurrent=1,
    )

    assert isinstance(scan_result, classic_scanlog.ScanRunResult)
    assert scan_result.status == "no_crash_logs_found"
    assert scan_result.discovery.source == "targeted"
    assert scan_result.discovery.accepted_logs == []
    assert scan_result.discovery.rejected_inputs[0].path == str(missing_log)
    assert scan_result.logs == []
    assert scan_result.to_dict()["status"] == "no_crash_logs_found"


def test_scan_run_execute_targeted_ignores_move_and_destination(tmp_path) -> None:
    """Targeted scan-run intent wins over move and destination inputs."""
    _write_scan_run_data_root(tmp_path)
    log_dir = tmp_path / "incoming"
    log_dir.mkdir()
    crash_log = log_dir / "crash-2026-03-06-12-00-00.log"
    crash_log.write_text(SAMPLE_CRASH_LOG, encoding="utf-8")

    scan_result = classic_scanlog.scan_run_execute(
        str(tmp_path),
        str(tmp_path / "CLASSIC Data"),
        "Fallout4",
        "auto",
        [str(crash_log)],
        move_unsolved_logs=True,
        targeted_mode=True,
        max_concurrent=1,
        unsolved_logs_destination="relative-destination",
    )
    results = scan_result.logs

    assert len(results) == 1
    assert results[0].success is True
    assert results[0].moved_to_unsolved_logs is False


def test_scan_run_execute_ignores_destination_when_movement_disabled(tmp_path) -> None:
    """A custom destination does not imply movement for Standard runs."""
    _write_scan_run_data_root(tmp_path)
    log_dir = tmp_path / "Crash Logs"
    log_dir.mkdir()
    crash_log = log_dir / "crash-2026-03-06-12-00-00.log"
    crash_log.write_text(SAMPLE_CRASH_LOG, encoding="utf-8")

    scan_result = classic_scanlog.scan_run_execute(
        str(tmp_path),
        str(tmp_path / "CLASSIC Data"),
        "Fallout4",
        "auto",
        [],
        move_unsolved_logs=False,
        max_concurrent=1,
        unsolved_logs_destination="relative-destination",
        configured_documents_root=str(tmp_path / "Docs"),
    )
    results = scan_result.logs

    assert len(results) == 1
    assert results[0].success is True
    assert results[0].moved_to_unsolved_logs is False


def test_scan_run_execute_relative_destination_fails_when_movement_enabled(tmp_path) -> None:
    """Relative custom destinations are setup errors only when movement is requested."""
    _write_scan_run_data_root(tmp_path)
    log_dir = tmp_path / "Crash Logs"
    log_dir.mkdir()
    crash_log = log_dir / "crash-2026-03-06-12-00-00.log"
    crash_log.write_text(SAMPLE_CRASH_LOG, encoding="utf-8")

    try:
        classic_scanlog.scan_run_execute(
            str(tmp_path),
            str(tmp_path / "CLASSIC Data"),
            "Fallout4",
            "auto",
            [],
            move_unsolved_logs=True,
            max_concurrent=1,
            unsolved_logs_destination="relative-destination",
            configured_documents_root=str(tmp_path / "Docs"),
        )
    except Exception as exc:  # noqa: BLE001 - binding maps through project-specific PyErr types.
        assert "absolute path" in str(exc).lower()
    else:
        raise AssertionError("relative destination should fail setup")


# =============================================================================
# papyrus sub-module: PapyrusStats
# =============================================================================


def test_papyrus_stats_default_zeroed() -> None:
    """Default ``PapyrusStats()`` has all counters at 0."""
    stats = classic_scanlog.PapyrusStats()
    assert stats.dumps == 0
    assert stats.stacks == 0
    assert stats.warnings == 0
    assert stats.errors == 0
    assert stats.lines_processed == 0


def test_papyrus_stats_dumps_to_stacks_ratio_default_zero() -> None:
    """Ratio is 0.0 when both dumps and stacks are zero (verified from -core impl)."""
    stats = classic_scanlog.PapyrusStats()
    assert stats.dumps_to_stacks_ratio() == 0.0


# =============================================================================
# papyrus sub-module: PapyrusAnalyzer
# =============================================================================


def test_papyrus_analyzer_construct_and_log_exists_false_for_missing() -> None:
    """``PapyrusAnalyzer(log_path)`` constructs; ``log_exists()`` returns False for missing file."""
    analyzer = classic_scanlog.PapyrusAnalyzer("/nonexistent/papyrus.log")
    assert analyzer.log_exists() is False


def test_papyrus_analyzer_log_path_roundtrip() -> None:
    """``log_path()`` returns the path string that was passed to the constructor."""
    analyzer = classic_scanlog.PapyrusAnalyzer("/tmp/papyrus.0.log")
    path = analyzer.log_path()
    # PyO3 PathBuf -> str via os.fspath-compatible conversion; normalize to string
    assert str(path).replace("\\", "/").endswith("papyrus.0.log")


def test_papyrus_analyzer_stats_default() -> None:
    """Initial ``stats()`` snapshot is a zeroed ``PapyrusStats`` (no file read yet)."""
    analyzer = classic_scanlog.PapyrusAnalyzer("/nonexistent/papyrus.log")
    stats = analyzer.stats()
    assert stats.dumps == 0
    assert stats.stacks == 0
    assert stats.lines_processed == 0


def test_papyrus_analyzer_reset_runs_without_error() -> None:
    """``reset()`` is a no-op smoke test (verifies the method binding exists)."""
    analyzer = classic_scanlog.PapyrusAnalyzer("/nonexistent/papyrus.log")
    analyzer.reset()
    # After reset, stats should still be zero
    assert analyzer.stats().dumps == 0


# =============================================================================
# papyrus sub-module: papyrus_logging free function
# =============================================================================


def test_papyrus_logging_missing_file_returns_summary_tuple() -> None:
    """``papyrus_logging`` returns ``(summary_text, dumps_count)`` even for a missing log file.

    Verified from papyrus.rs:232-241: the function internally creates a ``PapyrusAnalyzer``
    and calls ``analyze_to_string``, which is tolerant of missing files (returns an error
    message string) rather than raising. This is a cheap smoke path.
    """
    summary, dumps = classic_scanlog.papyrus_logging("/nonexistent/papyrus.log")
    assert isinstance(summary, str)
    assert isinstance(dumps, int)
    # Missing file means zero dumps extracted
    assert dumps == 0


# =============================================================================
# version sub-module: CrashgenVersion
# =============================================================================


def test_crashgen_version_parse_basic_semver() -> None:
    """``CrashgenVersion('1.28.6')`` parses the three components."""
    v = classic_scanlog.CrashgenVersion("1.28.6")
    assert v.major == 1
    assert v.minor == 28
    assert v.patch == 6


def test_crashgen_version_to_tuple_returns_three_component_tuple() -> None:
    """``to_tuple()`` returns ``(major, minor, patch)`` as a 3-tuple of ints."""
    v = classic_scanlog.CrashgenVersion("1.28.6")
    tup = v.to_tuple()
    assert isinstance(tup, tuple)
    assert len(tup) == 3
    assert tup == (1, 28, 6)


def test_crashgen_version_equality_ignores_original_string() -> None:
    """Two ``CrashgenVersion`` instances are equal if their major/minor/patch match.

    Verified from -core impl: ``CrashgenVersion::eq`` compares only the numeric
    components, so ``'Buffout 4 v1.28.6'`` equals ``'1.28.6'``.
    """
    v1 = classic_scanlog.CrashgenVersion("Buffout 4 v1.28.6")
    v2 = classic_scanlog.CrashgenVersion("1.28.6")
    assert v1 == v2


def test_crashgen_version_hash_is_consistent_with_eq() -> None:
    """``__hash__`` matches for two equal ``CrashgenVersion`` instances."""
    v1 = classic_scanlog.CrashgenVersion("1.28.6")
    v2 = classic_scanlog.CrashgenVersion("v1.28.6")
    assert hash(v1) == hash(v2)


# =============================================================================
# version sub-module: CrashgenVersionStatus + free functions
# =============================================================================


def test_crashgen_version_status_has_expected_classattr_constants() -> None:
    """``CrashgenVersionStatus`` exposes four ``#[classattr]`` string constants.

    Verified from version.rs:89-100: these are ``&'static str`` classattrs, NOT
    class instances. Accessing them returns the corresponding string.
    """
    assert classic_scanlog.CrashgenVersionStatus.VALID == "valid"
    assert classic_scanlog.CrashgenVersionStatus.OUTDATED == "outdated"
    assert classic_scanlog.CrashgenVersionStatus.NEWER_THAN_KNOWN == "newer_than_known"
    assert classic_scanlog.CrashgenVersionStatus.NO_SUPPORTED_VERSION == "no_supported_version"


def test_parse_crashgen_version_returns_instance_for_valid_string() -> None:
    """``parse_crashgen_version`` is a free function returning ``Optional[CrashgenVersion]``."""
    v = classic_scanlog.parse_crashgen_version("1.28.6")
    assert v is not None
    assert v.major == 1
    assert v.minor == 28
    assert v.patch == 6


def test_parse_crashgen_version_returns_none_for_garbage() -> None:
    """Invalid version strings yield ``None`` (per -py wrapper returning ``Option``)."""
    v = classic_scanlog.parse_crashgen_version("totally not a version")
    assert v is None


def test_check_crashgen_version_status_reports_valid_for_matching() -> None:
    """``check_crashgen_version_status`` compares against a list of valid strings.

    Verified from version.rs:145-156: the second arg is ``Vec<String>`` (not
    ``Vec<CrashgenVersion>``), and the return value is a ``CrashgenVersionStatus``
    wrapper whose string form matches the ``#[classattr]`` constants.
    """
    status = classic_scanlog.check_crashgen_version_status("1.28.6", ["1.28.6", "1.37.0"])
    # PyCrashgenVersionStatus.__eq__ accepts a string comparison (version.rs:110-118)
    assert status == "valid"


def test_check_crashgen_version_status_reports_valid_above_floor() -> None:
    """Versions newer than the configured floor remain valid."""
    status = classic_scanlog.check_crashgen_version_status("1.40.0", ["1.28.6", "1.37.0"])
    assert status == "valid"


def test_check_crashgen_version_status_reports_outdated() -> None:
    """Version below the min valid entry reports ``outdated``."""
    status = classic_scanlog.check_crashgen_version_status("1.20.0", ["1.28.6", "1.37.0"])
    assert status == "outdated"


# =============================================================================
# Rust-only proxy rows — sanity check that @rust symbols resolve in -core surface
# =============================================================================


def test_rust_only_symbols_in_core_surface() -> None:
    """Every Wave 3a @rust contract row's rustSymbol must be in the parsed -core surface.

    This is the runtime side of the Pitfall 2 guard. The ``check_parity_gate.py``
    script already enforces this at gate time, but a pytest sanity check catches
    drift between gate refreshes. We assert against the committed baseline so
    the test is self-contained.
    """
    import json
    from pathlib import Path

    repo_root = Path(__file__).parent.parent.parent
    baseline_path = repo_root / "docs/implementation/python_api_parity/baseline/rust_api_surface.json"
    surface = json.loads(baseline_path.read_text(encoding="utf-8"))
    scanlog_symbols: set[str] = {
        s["symbol"]
        for s in surface["symbols"]
        if s.get("crate") == "classic-scanlog-core"
    }

    # These are the rust-only symbols promoted by Wave 3a (from
    # 03-04-CONSTRUCTOR-INVENTORY.md "Rust-only Symbols (Proxy Rows)" table).
    wave3a_rust_only = {
        # orchestrator sub-module (rust-only enum/module marker/free fn)
        "AnalysisResult",           # also has a Python wrapper; rust-only row is a duplicate marker
        "ScanProgressPhase",        # pure Rust enum, no pyclass
        "resolve_batch_concurrency",  # -core only free fn
        "orchestrator",             # module marker
        # papyrus sub-module
        "papyrus",                  # module marker
        "PapyrusError",             # thiserror enum, no pyclass
        "PapyrusStats",             # also has Python wrapper; rust-only row is duplicate marker
        # version sub-module
        "version",                  # module marker
        "crashgen_version_gen",     # -core free fn (wrapped via parse_crashgen_version)
        # crashgen_registry sub-module (pure Rust)
        "crashgen_registry",
        "CrashgenRegistry",
        "CrashgenEntry",
        # segment_key sub-module (constants only)
        "segment_key",
        # error sub-module (pure Rust)
        "error",
        "ScanLogError",
    }
    missing = wave3a_rust_only - scanlog_symbols
    assert not missing, (
        f"Wave 3a rust-only symbols not found in classic-scanlog-core surface: {sorted(missing)}"
    )
