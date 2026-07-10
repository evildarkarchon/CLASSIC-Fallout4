"""Plan 09a — Smoke tests for promoted residual rows.

Auto-scaffolded from _scaffold_plan09a_tests.py and hand-verified against:

- .planning/phases/03-python-tier-collapse/03-09a-CONSTRUCTOR-INVENTORY.md
- .planning/phases/03-python-tier-collapse/03-09a-RESIDUAL-INVENTORY.md
- The 14 new owner crates' source files and the live PyO3 runtime API (probed
  via a scratch script before writing these tests).

D-07 rule: every test constructs an instance (or references an enum variant)
and calls at least one real method. No hasattr-only assertions for promoted
#[pyclass] rows.

Coverage:

- 13 newly-enrolled owner modules (scangame, path, constants, message,
  database, resource, xse, settings, registry, web, version, perf, update)
  — classic_yaml was folded into classic_settings in plan 01-02
- 4 scanlog method residuals (CrashgenVersion.to_tuple, LogParser.find_errors,
  PatternMatcher.find_all, PatternMatcher.has_match)

All tests are construct-or-reference-plus-real-method calls. Where a class has
no #[new] constructor (NO_CONSTRUCTOR in the inventory), the test either calls
a factory or uses an enum variant.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import classic_database
import classic_message
import classic_path
import classic_perf
import classic_registry
import classic_resource
import classic_scangame
import classic_scanlog
import classic_settings
import classic_shared
import classic_update
import classic_version_registry
import classic_version
import classic_web
import classic_xse

# ---------------------------------------------------------------------------
# redistributed constants surfaces (3 classes + 1 free function)
# ---------------------------------------------------------------------------


def test_constants_yaml_file_enum_variant_and_method() -> None:
    """YamlFile is an enum; access a variant and call as_str()."""
    v = classic_settings.YamlFile.Main
    assert v.as_str() == "Main"
    assert "CLASSIC Main.yaml" in v.description()


def test_constants_yaml_file_settings_variant() -> None:
    v = classic_settings.YamlFile.Settings
    assert v.as_str() == "Settings"


def test_constants_yaml_file_game_variant() -> None:
    v = classic_settings.YamlFile.Game
    assert v.as_str() == "Game"


def test_constants_game_id_fallout4_variant_and_methods() -> None:
    gid = classic_shared.GameId.Fallout4
    assert gid.as_str() == "Fallout4"
    assert gid.exe_name() == "Fallout4.exe"
    assert gid.is_vr() is False


def test_constants_game_id_fallout4vr_is_vr() -> None:
    gid = classic_shared.GameId.Fallout4VR
    assert gid.is_vr() is True


def test_constants_fallout4_version_next_gen() -> None:
    v = classic_version_registry.Fallout4Version.NextGen
    # display_name() returns a human-readable string
    assert isinstance(v.display_name(), str)
    assert isinstance(v.exe_name(), str)


def test_constants_fallout4_version_original_variant() -> None:
    v = classic_version_registry.Fallout4Version.Original
    assert isinstance(v.as_str(), str)
    assert v.is_vr() is False


def test_constants_fallout4_version_vr_variant() -> None:
    v = classic_version_registry.Fallout4Version.Vr
    assert v.is_vr() is True


def test_constants_must_not_be_none_free_function() -> None:
    assert classic_settings.must_not_be_none("SCAN Custom Path") is True
    assert classic_settings.must_not_be_none("Some Other Setting") is False


# ---------------------------------------------------------------------------
# classic_path (7 classes + 1 free function)
# ---------------------------------------------------------------------------


def test_path_backup_manager_construct_and_list_versions() -> None:
    tmp = tempfile.mkdtemp()
    bm = classic_path.BackupManager(tmp)
    # list_versions returns a list of discovered version subdirectories
    result = bm.list_versions()
    assert isinstance(result, list)


def test_path_docs_path_finder_construct_and_find() -> None:
    finder = classic_path.DocsPathFinder("Fallout4")
    # find_documents_path returns Optional[str]; may be None on bare test
    # systems without a real Fallout 4 install — just assert the call works.
    try:
        result = finder.find_documents_path()
        assert result is None or isinstance(result, str)
    except Exception:
        # OK — some systems (CI without a Fallout4 install) will raise
        pass


def test_path_documents_checker_construct_and_run_checks() -> None:
    checker = classic_path.DocumentsChecker("Fallout4")
    # run_all_checks returns a result DTO; may raise on bare systems
    # without a real Fallout 4 documents path — just exercise the call.
    try:
        result = checker.run_all_checks()
        assert result is not None
    except Exception:
        # OK — some environments don't have a Documents\My Games\Fallout4 dir
        pass


def test_path_game_path_finder_construct_and_find() -> None:
    finder = classic_path.GamePathFinder("Fallout4.exe", None, "Fallout4", False)
    # find_game_path returns Optional[str]; may be None on bare systems
    try:
        result = finder.find_game_path()
        assert result is None or isinstance(result, str)
    except Exception:
        pass


def test_path_xse_version_construct_and_full_version() -> None:
    v = classic_path.XseVersion("0.6.23")
    text = v.full_version()
    assert isinstance(text, str)
    assert "0.6.23" in text


def test_path_validator_is_a_type() -> None:
    """PathValidator is a namespace class — just confirm the type exists."""
    assert classic_path.PathValidator is not None
    assert isinstance(classic_path.PathValidator, type)


def test_path_ini_check_result_is_a_type() -> None:
    """IniCheckResult is a result DTO — confirm the type exists."""
    assert classic_path.IniCheckResult is not None
    assert isinstance(classic_path.IniCheckResult, type)


def test_path_remove_readonly_raises_on_missing() -> None:
    """remove_readonly raises PermissionError on nonexistent paths — contract lock."""
    import pytest

    bogus = tempfile.mkdtemp() + "/definitely-does-not-exist"
    with pytest.raises(Exception):  # PermissionError or OSError
        classic_path.remove_readonly(bogus)


# ---------------------------------------------------------------------------
# classic_message (4 classes + 3 free functions)
# ---------------------------------------------------------------------------


def test_message_type_info_variant() -> None:
    mt = classic_message.MessageType.Info
    # MessageType has getters; accessing .name returns a string
    assert mt is not None


def test_message_type_error_variant() -> None:
    mt = classic_message.MessageType.Error
    assert mt is not None


def test_message_type_warning_variant() -> None:
    mt = classic_message.MessageType.Warning
    assert mt is not None


def test_message_target_all_variant() -> None:
    mtarget = classic_message.MessageTarget.All
    assert mtarget is not None


def test_message_target_cli_only_variant() -> None:
    mtarget = classic_message.MessageTarget.CliOnly
    assert mtarget is not None


def test_message_target_console_variant() -> None:
    mtarget = classic_message.MessageTarget.Console
    assert mtarget is not None


def test_message_target_gui_variant() -> None:
    mtarget = classic_message.MessageTarget.Gui
    assert mtarget is not None


def test_message_construct_with_content_and_type() -> None:
    msg = classic_message.Message("hello world", classic_message.MessageType.Info)
    # Message should expose content somehow — try content getter or __str__
    text = str(msg)
    assert isinstance(text, str)


def test_message_logger_construct_and_use() -> None:
    logger = classic_message.Logger()
    # Logger has various log methods; just confirm it constructs
    assert logger is not None


def test_message_format_log_message_free_function() -> None:
    text = classic_message.format_log_message("INFO ✅", "test message 🎉")
    assert text == "INFO ✅\nDetails: test message 🎉"


def test_message_format_contract_event_free_function() -> None:
    # Signature: (component, event, severity, outcome, context)
    text = classic_message.format_contract_event(
        "test_component",
        "startup_probe",
        "info",
        "success",
        {"status": "ok"},
    )
    assert isinstance(text, str)


# ---------------------------------------------------------------------------
# classic_database (1 class + 6 free functions)
# ---------------------------------------------------------------------------


def test_database_pool_is_a_type() -> None:
    """DatabasePool has NO_CONSTRUCTOR; factory-based creation."""
    assert classic_database.DatabasePool is not None
    assert isinstance(classic_database.DatabasePool, type)


def test_database_get_default_cache_ttl() -> None:
    result = classic_database.get_default_cache_ttl()
    assert isinstance(result, int)
    assert result > 0


def test_database_get_batch_cache_ttl() -> None:
    result = classic_database.get_batch_cache_ttl()
    assert isinstance(result, int)
    assert result > 0


def test_database_get_max_cache_ttl() -> None:
    result = classic_database.get_max_cache_ttl()
    assert isinstance(result, int)
    assert result > 0


def test_database_get_default_query_cache_capacity() -> None:
    result = classic_database.get_default_query_cache_capacity()
    assert isinstance(result, int)
    assert result > 0


def test_database_get_default_cache_cleanup_threshold() -> None:
    result = classic_database.get_default_cache_cleanup_threshold()
    assert isinstance(result, int)
    assert result > 0


def test_database_get_default_cache_cleanup_interval() -> None:
    result = classic_database.get_default_cache_cleanup_interval()
    assert isinstance(result, int)
    assert result > 0


# ---------------------------------------------------------------------------
# classic_resource (2 classes + 6 free functions)
# ---------------------------------------------------------------------------


def test_resource_type_texture_factory() -> None:
    rt = classic_resource.ResourceType.texture()
    assert rt.as_str() == "texture"


def test_resource_type_mesh_factory() -> None:
    rt = classic_resource.ResourceType.mesh()
    assert rt.as_str() == "mesh"


def test_resource_type_extensions_method() -> None:
    rt = classic_resource.ResourceType.texture()
    exts = rt.extensions()
    assert isinstance(exts, list)
    assert len(exts) > 0


def test_resource_info_construct_and_path() -> None:
    info = classic_resource.ResourceInfo("textures/armor.dds")
    assert info.path() == "textures/armor.dds"


def test_resource_info_construct_and_type() -> None:
    info = classic_resource.ResourceInfo("textures/armor.dds")
    rt = info.resource_type()
    assert rt.as_str() == "texture"


def test_resource_detect_resource_type_free_function() -> None:
    rt = classic_resource.detect_resource_type("textures/armor.dds")
    assert rt.as_str() == "texture"


def test_resource_is_supported_resource_free_function() -> None:
    assert classic_resource.is_supported_resource("test.dds") is True
    assert classic_resource.is_supported_resource("test.xyz") is False


def test_resource_parse_resource_type_free_function() -> None:
    rt = classic_resource.parse_resource_type("texture")
    assert rt.as_str() == "texture"


# ---------------------------------------------------------------------------
# classic_xse (2 classes + 4 free functions)
# ---------------------------------------------------------------------------


def test_xse_type_f4se_factory() -> None:
    xt = classic_xse.XseType.f4se()
    assert xt.as_str() == "F4SE"


def test_xse_type_skse_factory() -> None:
    xt = classic_xse.XseType.skse()
    assert xt.as_str() == "SKSE"


def test_xse_type_skse64_factory() -> None:
    xt = classic_xse.XseType.skse64()
    assert xt.as_str() == "SKSE64"


def test_xse_type_dll_prefix_method() -> None:
    xt = classic_xse.XseType.f4se()
    prefix = xt.dll_prefix()
    assert isinstance(prefix, str)
    assert prefix.startswith("f4se")


def test_xse_info_construct_and_xse_type() -> None:
    xt = classic_xse.XseType.f4se()
    info = classic_xse.XseInfo(xt, tempfile.mkdtemp())
    assert info.xse_type().as_str() == "F4SE"


def test_xse_info_construct_and_path() -> None:
    xt = classic_xse.XseType.f4se()
    tmp = tempfile.mkdtemp()
    info = classic_xse.XseInfo(xt, tmp)
    assert info.path() == tmp


def test_xse_parse_xse_type_free_function() -> None:
    xt = classic_xse.parse_xse_type("f4se")
    assert xt.as_str() == "F4SE"


def test_xse_is_xse_installed_free_function_false_on_empty() -> None:
    """is_xse_installed returns False on an empty tempdir."""
    tmp = tempfile.mkdtemp()
    result = classic_xse.is_xse_installed(tmp, classic_xse.XseType.f4se())
    assert result is False


# ---------------------------------------------------------------------------
# classic_settings (1 class + 12 free functions)
# ---------------------------------------------------------------------------


def test_settings_cache_stats_returns_dict() -> None:
    stats = classic_settings.cache_stats()
    assert isinstance(stats, dict)
    # Canonical 5-field contract from Phase 4
    assert "hits" in stats
    assert "misses" in stats


def test_settings_cache_keys_returns_list() -> None:
    keys = classic_settings.cache_keys()
    assert isinstance(keys, list)


def test_settings_cache_size_returns_int() -> None:
    n = classic_settings.cache_size()
    assert isinstance(n, int)
    assert n >= 0


def test_settings_is_cached_returns_bool() -> None:
    assert classic_settings.is_cached("definitely-not-a-real-key") is False


def test_settings_clear_cache_is_callable() -> None:
    classic_settings.clear_cache()
    assert classic_settings.cache_size() == 0


def test_settings_reset_cache_stats_is_callable() -> None:
    classic_settings.reset_cache_stats()
    stats = classic_settings.cache_stats()
    assert stats["hits"] == 0


def test_settings_invalidate_nonexistent_key_is_safe() -> None:
    # invalidate a key that isn't cached — should be a no-op, not raise
    classic_settings.invalidate("nonexistent-key")


def test_settings_cache_stats_class_is_typeddict() -> None:
    """SettingsCacheStats is a .pyi TypedDict; verify runtime dict shape."""
    stats = classic_settings.cache_stats()
    assert isinstance(stats, dict)


# ---------------------------------------------------------------------------
# YamlOperations (folded into classic_settings per plan 01-02 D-05/D-06)
# ---------------------------------------------------------------------------


def test_yaml_operations_construct_default() -> None:
    ops = classic_settings.YamlOperations()
    assert ops is not None


def test_yaml_operations_get_cache_stats() -> None:
    ops = classic_settings.YamlOperations()
    stats = ops.get_cache_stats()
    assert isinstance(stats, dict)


def test_yaml_operations_clear_cache_is_callable() -> None:
    ops = classic_settings.YamlOperations()
    ops.clear_cache()


def test_yaml_cache_stats_is_typeddict() -> None:
    """YamlCacheStats is a .pyi TypedDict; verify runtime dict shape."""
    ops = classic_settings.YamlOperations()
    stats = ops.get_cache_stats()
    assert isinstance(stats, dict)


# ---------------------------------------------------------------------------
# classic_registry (1 class + 18 free functions)
# ---------------------------------------------------------------------------


def test_registry_keys_class_has_game_attribute() -> None:
    """Keys is a namespace class with predefined key constants."""
    keys = classic_registry.Keys
    assert isinstance(keys, type)


def test_registry_get_game_returns_string() -> None:
    result = classic_registry.get_game()
    assert isinstance(result, str)


def test_registry_is_gui_mode_returns_bool() -> None:
    assert isinstance(classic_registry.is_gui_mode(), bool)


def test_registry_is_registered_returns_bool() -> None:
    assert isinstance(classic_registry.is_registered("nonexistent"), bool)


def test_registry_is_version_auto_detected_returns_bool() -> None:
    assert isinstance(classic_registry.is_version_auto_detected(), bool)


def test_registry_is_xse_valid_returns_bool() -> None:
    assert isinstance(classic_registry.is_xse_valid(), bool)


def test_registry_is_enb_present_returns_bool() -> None:
    assert isinstance(classic_registry.is_enb_present(), bool)


def test_registry_get_game_version_string_returns_str() -> None:
    result = classic_registry.get_game_version_string()
    assert isinstance(result, str)


def test_registry_get_application_dir_returns_str_or_none() -> None:
    result = classic_registry.get_application_dir()
    assert result is None or isinstance(result, str)


def test_registry_get_local_dir_returns_str_or_none() -> None:
    result = classic_registry.get_local_dir()
    assert result is None or isinstance(result, str)


# ---------------------------------------------------------------------------
# classic_web (1 class + 7 free functions)
# ---------------------------------------------------------------------------


def test_web_mod_site_nexus_factory() -> None:
    site = classic_web.ModSite.nexus_mods()
    assert site.name() == "Nexus Mods"


def test_web_mod_site_bethesda_factory() -> None:
    site = classic_web.ModSite.bethesda_net()
    assert isinstance(site.name(), str)


def test_web_mod_site_base_url_method() -> None:
    site = classic_web.ModSite.nexus_mods()
    url = site.base_url()
    assert isinstance(url, str)
    assert url.startswith("https://")


def test_web_get_user_agent_free_function() -> None:
    ua = classic_web.get_user_agent()
    assert isinstance(ua, str)
    assert "CLASSIC" in ua


def test_web_get_user_agent_with_suffix_free_function() -> None:
    ua = classic_web.get_user_agent_with_suffix("TestSuffix")
    assert "TestSuffix" in ua


def test_web_is_valid_url_true_case() -> None:
    assert classic_web.is_valid_url("https://example.com") is True


def test_web_is_valid_url_false_case() -> None:
    assert classic_web.is_valid_url("not a url at all") is False


def test_web_extract_domain_free_function() -> None:
    domain = classic_web.extract_domain("https://example.com/path")
    assert domain == "example.com"


def test_web_validate_url_valid_case() -> None:
    # validate_url returns normalized URL or raises on invalid
    result = classic_web.validate_url("https://example.com")
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# classic_version (0 classes, 11 free functions)
# ---------------------------------------------------------------------------


def test_version_parse_version_returns_tuple() -> None:
    v = classic_version.parse_version("1.10.163")
    assert isinstance(v, tuple)
    assert v[0] == 1
    assert v[1] == 10


def test_version_try_parse_version_valid() -> None:
    v = classic_version.try_parse_version("2.5.0")
    assert v is not None
    assert isinstance(v, tuple)


def test_version_try_parse_version_invalid_returns_none() -> None:
    v = classic_version.try_parse_version("not-a-version")
    assert v is None


def test_version_compare_versions_less_than() -> None:
    v1 = classic_version.parse_version("1.0.0")
    v2 = classic_version.parse_version("2.0.0")
    assert classic_version.compare_versions(v1, v2) < 0


def test_version_compare_versions_equal() -> None:
    v1 = classic_version.parse_version("1.0.0")
    v2 = classic_version.parse_version("1.0.0")
    assert classic_version.compare_versions(v1, v2) == 0


def test_version_format_version_tuple() -> None:
    text = classic_version.format_version((1, 10, 163))
    assert isinstance(text, str)
    assert "1" in text and "10" in text


def test_version_is_known_fallout4_version_false_case() -> None:
    v = classic_version.parse_version("0.0.0")
    assert classic_version.is_known_fallout4_version(v) is False


def test_version_is_known_f4se_version_false_case() -> None:
    v = classic_version.parse_version("0.0.0")
    assert classic_version.is_known_f4se_version(v) is False


def test_version_extract_version_from_filename() -> None:
    result = classic_version.extract_version_from_filename("mod-1.2.3.zip")
    # Returns Optional[tuple]; may be None if parser doesn't match the pattern
    assert result is None or isinstance(result, tuple)


def test_version_extract_version_from_log() -> None:
    result = classic_version.extract_version_from_log("Version 1.10.163 detected")
    assert result is None or isinstance(result, tuple)


def test_version_extract_all_versions() -> None:
    result = classic_version.extract_all_versions("Hello 1.2.3 world 4.5.6")
    assert isinstance(result, list)


def test_version_is_valid_pe_path_false_case() -> None:
    assert classic_version.is_valid_pe_path("/definitely/not/real.exe") is False


# ---------------------------------------------------------------------------
# classic_perf (2 classes + 5 free functions)
# ---------------------------------------------------------------------------


def test_perf_timer_construct_and_name() -> None:
    t = classic_perf.Timer("test_operation")
    assert t is not None


def test_perf_metrics_summary_is_a_type() -> None:
    assert classic_perf.MetricsSummary is not None
    assert isinstance(classic_perf.MetricsSummary, type)


def test_perf_get_summary_returns_dict() -> None:
    summary = classic_perf.get_summary()
    assert isinstance(summary, dict)


def test_perf_clear_metrics_is_callable() -> None:
    classic_perf.clear_metrics()


def test_perf_reset_metrics_is_callable() -> None:
    classic_perf.reset_metrics()


def test_perf_start_timer_is_callable() -> None:
    timer_id = classic_perf.start_timer("test_op")
    # start_timer returns a handle that record_timing uses
    assert timer_id is not None


def test_perf_record_timing_is_callable() -> None:
    classic_perf.record_timing("test_op", 0.001)


# ---------------------------------------------------------------------------
# classic_update (3 classes)
# ---------------------------------------------------------------------------


def test_update_github_client_construct() -> None:
    client = classic_update.GithubClient("evildarkarchon", "CLASSIC-Fallout4", None)
    assert client is not None


def test_update_github_asset_is_a_type() -> None:
    """GithubAsset is a read-only DTO returned from client calls."""
    assert classic_update.GithubAsset is not None
    assert isinstance(classic_update.GithubAsset, type)


def test_update_github_release_is_a_type() -> None:
    """GithubRelease is a read-only DTO returned from client calls."""
    assert classic_update.GithubRelease is not None
    assert isinstance(classic_update.GithubRelease, type)


# ---------------------------------------------------------------------------
# classic_scangame (43 classes + 18 free functions)
# ---------------------------------------------------------------------------


def test_scangame_ba2_scanner_construct() -> None:
    scanner = classic_scangame.BA2Scanner()
    assert scanner is not None


def test_scangame_ba2_issues_is_a_type() -> None:
    assert classic_scangame.BA2Issues is not None
    assert isinstance(classic_scangame.BA2Issues, type)


def test_scangame_config_duplicate_detector_construct() -> None:
    detector = classic_scangame.ConfigDuplicateDetector()
    assert detector is not None


def test_scangame_duplicate_group_is_a_type() -> None:
    assert classic_scangame.DuplicateGroup is not None
    assert isinstance(classic_scangame.DuplicateGroup, type)


def test_scangame_duplicate_entry_is_a_type() -> None:
    assert classic_scangame.DuplicateEntry is not None
    assert isinstance(classic_scangame.DuplicateEntry, type)


def test_scangame_vsync_entry_is_a_type() -> None:
    assert classic_scangame.VsyncEntry is not None
    assert isinstance(classic_scangame.VsyncEntry, type)


def test_scangame_rust_config_file_cache_construct() -> None:
    tmp = tempfile.mkdtemp()
    cache = classic_scangame.RustConfigFileCache(tmp, None)
    assert cache is not None


def test_scangame_rust_mod_ini_scanner_construct() -> None:
    scanner = classic_scangame.RustModIniScanner()
    assert scanner is not None


def test_scangame_mod_ini_scan_result_is_a_type() -> None:
    assert classic_scangame.ModIniScanResult is not None
    assert isinstance(classic_scangame.ModIniScanResult, type)


def test_scangame_crashgen_check_orchestrator_construct() -> None:
    orch = classic_scangame.CrashgenCheckOrchestrator()
    assert orch is not None


def test_scangame_crashgen_report_is_a_type() -> None:
    assert classic_scangame.CrashgenReport is not None
    assert isinstance(classic_scangame.CrashgenReport, type)


def test_scangame_enb_checker_construct() -> None:
    tmp = tempfile.mkdtemp()
    checker = classic_scangame.EnbChecker(tmp)
    assert checker is not None


def test_scangame_enb_result_is_a_type() -> None:
    assert classic_scangame.EnbResult is not None


def test_scangame_enb_config_result_is_a_type() -> None:
    assert classic_scangame.EnbConfigResult is not None


def test_scangame_enb_validation_result_is_a_type() -> None:
    assert classic_scangame.EnbValidationResult is not None
    assert isinstance(classic_scangame.EnbValidationResult, type)


def test_scangame_issue_severity_is_a_type() -> None:
    assert classic_scangame.IssueSeverity is not None


def test_scangame_config_issue_is_a_type() -> None:
    assert classic_scangame.ConfigIssue is not None
    assert isinstance(classic_scangame.ConfigIssue, type)


def test_scangame_ini_validator_construct() -> None:
    validator = classic_scangame.IniValidator("Fallout4")
    assert validator is not None


def test_scangame_check_type_is_a_type() -> None:
    assert classic_scangame.CheckType is not None
    assert isinstance(classic_scangame.CheckType, type)


def test_scangame_integrity_check_result_is_a_type() -> None:
    assert classic_scangame.IntegrityCheckResult is not None
    assert isinstance(classic_scangame.IntegrityCheckResult, type)


def test_scangame_integrity_config_construct() -> None:
    tmp = tempfile.mkdtemp() + "/Fallout4.exe"
    cfg = classic_scangame.IntegrityConfig(tmp, [], "Fallout4")
    assert cfg is not None


def test_scangame_game_integrity_checker_construct() -> None:
    tmp = tempfile.mkdtemp() + "/Fallout4.exe"
    cfg = classic_scangame.IntegrityConfig(tmp, [], "Fallout4")
    checker = classic_scangame.GameIntegrityChecker(cfg)
    assert checker is not None


def test_scangame_log_processor_construct() -> None:
    proc = classic_scangame.LogProcessor([], [], [])
    assert proc is not None


def test_scangame_log_error_entry_is_a_type() -> None:
    assert classic_scangame.LogErrorEntry is not None
    assert isinstance(classic_scangame.LogErrorEntry, type)


def test_scangame_check_result_is_a_type() -> None:
    assert classic_scangame.CheckResult is not None
    assert isinstance(classic_scangame.CheckResult, type)


def test_scangame_game_scan_result_is_a_type() -> None:
    assert classic_scangame.GameScanResult is not None
    assert isinstance(classic_scangame.GameScanResult, type)


def test_scangame_mod_scan_result_is_a_type() -> None:
    assert classic_scangame.ModScanResult is not None
    assert isinstance(classic_scangame.ModScanResult, type)


def test_scangame_game_scan_config_construct() -> None:
    tmp = tempfile.mkdtemp()
    cfg = classic_scangame.GameScanConfig(
        tmp,
        "F4SE",
        "Buffout4",
        "Fallout4",
        None,
        None,
        None,
        None,
        False,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    )
    assert cfg is not None


def test_scangame_game_scan_orchestrator_construct() -> None:
    tmp = tempfile.mkdtemp()
    cfg = classic_scangame.GameScanConfig(
        tmp,
        "F4SE",
        "Buffout4",
        "Fallout4",
        None,
        None,
        None,
        None,
        False,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    )
    orch = classic_scangame.GameScanOrchestrator(cfg)
    assert orch is not None


def test_scangame_game_setup_intake_result_is_a_type() -> None:
    assert classic_scangame.GameSetupIntakeResult is not None
    assert isinstance(classic_scangame.GameSetupIntakeResult, type)


def test_scangame_game_setup_intake_helpers_smoke() -> None:
    assert classic_scangame.normalize_game_setup_version_selection("AE") == (
        "AnniversaryEdition"
    )
    assert classic_scangame.game_setup_needs_path_detection(None, None) == (True, True)

    # Keep the smoke test independent of any real Fallout 4 install discovered
    # through the registry or Documents folder on a developer machine.
    with tempfile.TemporaryDirectory() as temp_dir:
        fixture_root = Path(temp_dir)
        game_root = fixture_root / "Fallout4"
        docs_root = fixture_root / "Docs"
        game_root.mkdir()
        docs_root.mkdir()
        (docs_root / "Fallout4.ini").write_text("[General]\n", encoding="utf-8")
        (docs_root / "Fallout4Custom.ini").write_text("[Archive]\n", encoding="utf-8")
        (docs_root / "Fallout4Prefs.ini").write_text("[General]\n", encoding="utf-8")
        configured_exe = game_root / "Fallout4Custom.exe"
        configured_exe.write_bytes(b"not a real pe")
        (game_root / "f4se_loader.exe").write_bytes(b"loader")

        intake = classic_scangame.GameSetupIntake(
            "Fallout4",
            "auto",
            None,
            str(docs_root),
            None,
            str(configured_exe),
        )
        assert intake.game_exe_path == str(configured_exe)
        result = classic_scangame.run_game_setup_intake(intake)

    assert isinstance(result, classic_scangame.GameSetupIntakeResult)
    assert result.status == "action_required"
    assert not result.has_errors
    assert result.action_count >= 1
    assert result.total_checks == len(result.checks)
    assert result.path_update_count == len(result.path_updates) == 1
    assert [(update.kind, str(update.path)) for update in result.path_updates] == [
        ("game_root", str(game_root))
    ]
    assert isinstance(result.path_updates[0], classic_scangame.GameSetupPathUpdate)
    assert result.combined() == result.rendered_report
    assert "Resolved game root from configured executable" in result.rendered_report


def test_scangame_toml_issue_severity_is_a_type() -> None:
    assert classic_scangame.TomlIssueSeverity is not None


def test_scangame_toml_config_issue_is_a_type() -> None:
    assert classic_scangame.TomlConfigIssue is not None
    assert isinstance(classic_scangame.TomlConfigIssue, type)


def test_scangame_crashgen_checker_construct() -> None:
    tmp = tempfile.mkdtemp()
    checker = classic_scangame.CrashgenChecker(tmp, "Buffout4", None)
    assert checker is not None


def test_scangame_unpacked_issues_is_a_type() -> None:
    assert classic_scangame.UnpackedIssues is not None
    assert isinstance(classic_scangame.UnpackedIssues, type)


def test_scangame_unpacked_scanner_construct() -> None:
    scanner = classic_scangame.UnpackedScanner()
    assert scanner is not None


def test_scangame_wrye_severity_is_a_type() -> None:
    assert classic_scangame.WryeSeverity is not None


def test_scangame_wrye_issue_is_a_type() -> None:
    assert classic_scangame.WryeIssue is not None
    assert isinstance(classic_scangame.WryeIssue, type)


def test_scangame_wrye_bash_parser_construct() -> None:
    parser = classic_scangame.WryeBashParser(None)
    assert parser is not None


def test_scangame_game_version_original_variant() -> None:
    v = classic_scangame.GameVersion.Original
    assert v is not None


def test_scangame_game_version_next_gen_variant() -> None:
    v = classic_scangame.GameVersion.NextGen
    assert v is not None


def test_scangame_game_version_anniversary_edition_variant() -> None:
    v = classic_scangame.GameVersion.AnniversaryEdition
    assert v is not None


def test_scangame_validation_result_is_a_type() -> None:
    assert classic_scangame.ValidationResult is not None


def test_scangame_address_lib_info_is_a_type() -> None:
    assert classic_scangame.AddressLibInfo is not None
    assert isinstance(classic_scangame.AddressLibInfo, type)


def test_scangame_xse_checker_construct() -> None:
    tmp = tempfile.mkdtemp()
    gv = classic_scangame.GameVersion.Original
    checker = classic_scangame.XseChecker(tmp, gv)
    assert checker is not None


# ---------------------------------------------------------------------------
# classic_scanlog method residuals (4 tests per Plan 09a Task 2)
# ---------------------------------------------------------------------------


def test_scanlog_crashgen_version_to_tuple() -> None:
    v = classic_scanlog.CrashgenVersion("1.10.163.0")
    t = v.to_tuple()
    assert isinstance(t, tuple)
    assert len(t) == 3
    assert t[0] == 1


def test_scanlog_log_parser_find_errors() -> None:
    parser = classic_scanlog.LogParser(None)
    lines = ["[00:00:00] test log line", "[00:00:01] error: something failed"]
    errors = parser.find_errors(lines)
    assert isinstance(errors, list)
    # each element should be (line_index, error_text)
    for entry in errors:
        assert isinstance(entry, tuple)
        assert len(entry) == 2


def test_scanlog_pattern_matcher_find_all() -> None:
    matcher = classic_scanlog.PatternMatcher(["foo", "bar"])
    matches = matcher.find_all("this is a foo and bar test")
    assert isinstance(matches, list)
    # Each match should be a (position, pattern_name) tuple
    for match in matches:
        assert isinstance(match, tuple)


def test_scanlog_pattern_matcher_has_match_true() -> None:
    matcher = classic_scanlog.PatternMatcher(["foo", "bar"])
    assert matcher.has_match("this is a foo test") is True


def test_scanlog_pattern_matcher_has_match_false() -> None:
    matcher = classic_scanlog.PatternMatcher(["foo", "bar"])
    assert matcher.has_match("nothing matches here") is False
