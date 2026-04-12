"""Per-class smoke tests for Phase 3 Plan 02 - scanlog Wave 1 (parsing primitives).

Covers 74 promoted contract rows across 6 sub-modules: parser, formid,
formid_analyzer, record_scanner, plugin_analyzer, patterns.

Each #[pyclass] gets at least one test that constructs it and calls one
real method (per Phase 3 D-07). Related free functions are grouped into
one test each.

Constructor signatures verified in
.planning/phases/03-python-tier-collapse/03-02-CONSTRUCTOR-INVENTORY.md.
"""

from __future__ import annotations

from pathlib import Path

import classic_scanlog


# ============================================================================
# parser sub-module: LogParser + ScanOutput (factory output)
# ============================================================================


def test_log_parser_construct_default() -> None:
    """LogParser() with no custom boundaries (parameterless smoke)."""
    parser = classic_scanlog.LogParser()
    assert parser is not None


def test_log_parser_construct_with_custom_boundaries() -> None:
    """LogParser(custom_boundaries=...) with explicit boundary list."""
    parser = classic_scanlog.LogParser([("[Start]", "[End]")])
    assert parser is not None


def test_log_parser_parse_all_sections_returns_dict() -> None:
    """LogParser.parse_all_sections([]) returns dict[str, list[str]]."""
    parser = classic_scanlog.LogParser()
    result = parser.parse_all_sections([])
    assert isinstance(result, dict)


def test_log_parser_get_stats_returns_dict() -> None:
    """LogParser.get_stats() returns dict[str, int] of cache stats."""
    parser = classic_scanlog.LogParser()
    stats = parser.get_stats()
    assert isinstance(stats, dict)


def test_log_parser_extract_addresses_returns_list() -> None:
    """LogParser.extract_addresses([]) returns list[str]."""
    parser = classic_scanlog.LogParser()
    addrs = parser.extract_addresses([])
    assert isinstance(addrs, list)


def test_log_parser_clear_caches_returns_none() -> None:
    """LogParser.clear_caches() runs without raising."""
    parser = classic_scanlog.LogParser()
    parser.clear_caches()  # No return value


def test_log_parser_add_pattern_smoke() -> None:
    """LogParser.add_pattern(name, pattern) compiles a custom regex."""
    parser = classic_scanlog.LogParser()
    parser.add_pattern("test_pattern", r"\bERROR\b")


def test_log_parser_get_segment_sizes_returns_dict() -> None:
    """LogParser.get_segment_sizes([]) returns dict[str, int]."""
    parser = classic_scanlog.LogParser()
    sizes = parser.get_segment_sizes([])
    assert isinstance(sizes, dict)


def test_log_parser_parse_complete_returns_scan_output(tmp_path: Path) -> None:
    """LogParser.parse_complete([]) returns a ScanOutput factory product."""
    parser = classic_scanlog.LogParser()
    output = parser.parse_complete([])
    # The factory always returns a ScanOutput; field access exercises getters
    assert output is not None
    assert isinstance(output.game_version, str)
    assert isinstance(output.crashgen_version, str)
    assert isinstance(output.main_error, str)
    assert isinstance(output.segments, dict)


def test_scan_output_field_access_via_factory() -> None:
    """ScanOutput is constructed via LogParser.parse_complete factory chain.

    ScanOutput has no #[new]; smoke coverage exercises the four
    #[pyo3(get)] getters: game_version, crashgen_version, main_error, segments.
    """
    parser = classic_scanlog.LogParser()
    output = parser.parse_complete([])
    # Empty input triggers UNKNOWN sentinel from parse_crash_header fallback
    assert output.game_version == "UNKNOWN"
    assert output.crashgen_version == "UNKNOWN"
    assert output.main_error == "UNKNOWN"
    # segments dict always has 8 named keys when parse_all_sections_arc runs
    assert "callstack" in output.segments
    assert "plugins" in output.segments


# ============================================================================
# formid sub-module: PyRustFormIDAnalyzer (Python name FormIDAnalyzer)
# ============================================================================


def test_formid_analyzer_construct() -> None:
    """FormIDAnalyzer() (parameterless) wraps RustFormIDAnalyzer."""
    analyzer = classic_scanlog.FormIDAnalyzer()
    assert analyzer is not None


def test_formid_analyzer_extract_formids_empty() -> None:
    """FormIDAnalyzer.extract_formids([]) returns empty list."""
    analyzer = classic_scanlog.FormIDAnalyzer()
    result = analyzer.extract_formids([])
    assert isinstance(result, list)
    assert result == []


def test_formid_analyzer_parse_formid_invalid() -> None:
    """FormIDAnalyzer.parse_formid('') returns None for invalid input."""
    analyzer = classic_scanlog.FormIDAnalyzer()
    result = analyzer.parse_formid("")
    assert result is None or isinstance(result, int)


def test_formid_analyzer_cache_stats_tuple() -> None:
    """FormIDAnalyzer.cache_stats() returns tuple[int, int]."""
    analyzer = classic_scanlog.FormIDAnalyzer()
    stats = analyzer.cache_stats()
    assert isinstance(stats, tuple)
    assert len(stats) == 2


def test_formid_analyzer_clear_cache() -> None:
    """FormIDAnalyzer.clear_cache() runs without raising."""
    analyzer = classic_scanlog.FormIDAnalyzer()
    analyzer.clear_cache()


# ============================================================================
# formid_analyzer sub-module: PyFormIDAnalyzerCore + free functions
# ============================================================================


def test_formid_analyzer_core_construct_default() -> None:
    """FormIDAnalyzerCore() with all defaults."""
    core = classic_scanlog.FormIDAnalyzerCore()
    assert core is not None


def test_formid_analyzer_core_extract_formids_empty() -> None:
    """FormIDAnalyzerCore.extract_formids([]) returns list[str]."""
    core = classic_scanlog.FormIDAnalyzerCore()
    result = core.extract_formids([])
    assert isinstance(result, list)


def test_formid_analyzer_free_functions_group() -> None:
    """Grouped smoke test for extract_formids_batch / is_valid_formid / validate_formids_batch."""
    batch = classic_scanlog.extract_formids_batch([])
    assert isinstance(batch, list)

    # Valid hex form ID example
    assert classic_scanlog.is_valid_formid("FF001234") is True
    # Invalid form ID
    assert classic_scanlog.is_valid_formid("not-a-formid") is False

    validated = classic_scanlog.validate_formids_batch([])
    assert isinstance(validated, list)


# ============================================================================
# record_scanner sub-module: PyRecordScanner + free functions
# ============================================================================


def test_record_scanner_construct() -> None:
    """RecordScanner(target_records, ignore_records, crashgen_name) - all required positional."""
    scanner = classic_scanlog.RecordScanner([], [], "Buffout 4")
    assert scanner is not None


def test_record_scanner_extract_records_empty() -> None:
    """RecordScanner.extract_records([]) returns list[str]."""
    scanner = classic_scanlog.RecordScanner([], [], "Buffout 4")
    result = scanner.extract_records([])
    assert isinstance(result, list)


def test_record_scanner_scan_named_records_returns_tuple() -> None:
    """RecordScanner.scan_named_records([]) returns tuple[list[str], list[str]]."""
    scanner = classic_scanlog.RecordScanner([], [], "Buffout 4")
    result = scanner.scan_named_records([])
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_record_scanner_clear_cache() -> None:
    """RecordScanner.clear_cache() runs without raising."""
    scanner = classic_scanlog.RecordScanner([], [], "Buffout 4")
    scanner.clear_cache()


def test_record_scanner_free_functions_group() -> None:
    """Grouped smoke test for scan_records_batch / contains_record."""
    batch = classic_scanlog.scan_records_batch([], [], [])
    assert isinstance(batch, list)

    contains = classic_scanlog.contains_record("any line", [], [])
    assert isinstance(contains, bool)


# ============================================================================
# plugin_analyzer sub-module: PyPluginAnalyzer + free functions
# ============================================================================


def test_plugin_analyzer_construct() -> None:
    """PluginAnalyzer(game_ignore_plugins, ignore_list, crashgen_name) - first 3 required."""
    analyzer = classic_scanlog.PluginAnalyzer([], [], "Buffout 4")
    assert analyzer is not None


def test_plugin_analyzer_construct_with_versions() -> None:
    """PluginAnalyzer with optional game_version/game_version_vr."""
    analyzer = classic_scanlog.PluginAnalyzer([], [], "Buffout 4", "1.10.163", "1.2.72")
    assert analyzer is not None


def test_plugin_analyzer_loadorder_scan_log_empty() -> None:
    """PluginAnalyzer.loadorder_scan_log([]) returns (dict, bool, bool)."""
    analyzer = classic_scanlog.PluginAnalyzer([], [], "Buffout 4")
    plugins, limit_triggered, limit_disabled = analyzer.loadorder_scan_log([])
    assert isinstance(plugins, dict)
    assert isinstance(limit_triggered, bool)
    assert isinstance(limit_disabled, bool)


def test_plugin_analyzer_filter_ignored_plugins_empty() -> None:
    """PluginAnalyzer.filter_ignored_plugins({}) returns dict."""
    analyzer = classic_scanlog.PluginAnalyzer([], [], "Buffout 4")
    filtered = analyzer.filter_ignored_plugins({})
    assert isinstance(filtered, dict)


def test_plugin_analyzer_free_functions_group() -> None:
    """Grouped smoke test for detect_plugins_batch / contains_plugin."""
    batch = classic_scanlog.detect_plugins_batch([])
    assert isinstance(batch, list)

    contains = classic_scanlog.contains_plugin("any line")
    assert isinstance(contains, bool)


# ============================================================================
# patterns sub-module: PyPatternMatcher
# ============================================================================


def test_pattern_matcher_construct_empty() -> None:
    """PatternMatcher([]) with no patterns."""
    matcher = classic_scanlog.PatternMatcher([])
    assert matcher is not None


def test_pattern_matcher_construct_with_patterns() -> None:
    """PatternMatcher(['error', 'warning']) compiles two patterns."""
    matcher = classic_scanlog.PatternMatcher(["error", "warning"])
    assert matcher is not None


def test_pattern_matcher_find_all_returns_list() -> None:
    """PatternMatcher.find_all('') returns list[tuple[int, str]]."""
    matcher = classic_scanlog.PatternMatcher(["error"])
    result = matcher.find_all("")
    assert isinstance(result, list)


def test_pattern_matcher_find_first_returns_optional_tuple() -> None:
    """PatternMatcher.find_first('') returns Optional[tuple[int, str]]."""
    matcher = classic_scanlog.PatternMatcher(["error"])
    result = matcher.find_first("")
    assert result is None or isinstance(result, tuple)


def test_pattern_matcher_has_match_returns_bool() -> None:
    """PatternMatcher.has_match('') returns bool."""
    matcher = classic_scanlog.PatternMatcher(["error"])
    assert isinstance(matcher.has_match(""), bool)


def test_pattern_matcher_replace_all_returns_string() -> None:
    """PatternMatcher.replace_all('input', 'X') returns str."""
    matcher = classic_scanlog.PatternMatcher(["error"])
    result = matcher.replace_all("hello error world", "X")
    assert isinstance(result, str)


def test_pattern_matcher_get_stats_returns_tuple() -> None:
    """PatternMatcher.get_stats() returns tuple[int, int]."""
    matcher = classic_scanlog.PatternMatcher(["error"])
    stats = matcher.get_stats()
    assert isinstance(stats, tuple)
    assert len(stats) == 2


def test_pattern_matcher_clear_cache() -> None:
    """PatternMatcher.clear_cache() runs without raising."""
    matcher = classic_scanlog.PatternMatcher(["error"])
    matcher.clear_cache()
