"""Smoke tests for independently useful scanlog utilities.

Crash Log Scan Run orchestration is covered through the final contract tests;
this module retains the Papyrus, version, registry, segment-key, and error
coverage that remains outside complete scan execution.
"""

from __future__ import annotations

from pathlib import Path

import classic_scanlog


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
