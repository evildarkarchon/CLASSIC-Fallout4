"""Registry-driven runtime parity smoke tests for maintained Python bindings."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, cast

import pytest

from .fixtures.runtime_coverage_registry import get_runtime_coverage_case_ids
from .fixtures.tier1_parity_fixtures import (
    PARITY_GAME_YAML,
    PARITY_IGNORE_YAML,
    PARITY_MAIN_YAML,
)


THIS_SUITE = "python-bindings/tests/test_tier1_parity_smoke.py"


def test_imports_and_versions() -> None:
    import classic_config
    import classic_scanlog
    import classic_version_registry

    assert isinstance(classic_config.__version__, str)
    assert isinstance(classic_scanlog.__version__, str)
    assert isinstance(classic_version_registry.__version__, str)

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("classic_pybridge")


def _run_config_tier1_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import classic_config

    data = classic_config.YamlData.from_yaml_content(
        PARITY_MAIN_YAML,
        PARITY_GAME_YAML,
        PARITY_IGNORE_YAML,
        "Fallout4",
        "auto",
    )
    assert data.classic_version == "9.0.0"
    assert data.xse_acronym == "F4SE"
    assert data.crashgen_name == "Buffout 4"

    structured_game_yaml = PARITY_GAME_YAML.replace(
        "Mods_SOLU: []",
        "\n".join(
            (
                "Mods_SOLU:",
                "  - id: solu-mod",
                "    criteria:",
                "      any:",
                '        - "SoluMod"',
                '    name: "Solution Mod"',
                '    description: "Solution mod"',
            )
        ),
    )
    structured_data = classic_config.YamlData.from_yaml_content(
        PARITY_MAIN_YAML,
        structured_game_yaml,
        PARITY_IGNORE_YAML,
        "Fallout4",
        "auto",
    )
    solu_entries = cast(list[dict[str, Any]], structured_data.game_mods_solu)
    assert solu_entries[0]["id"] == "solu-mod"
    assert cast(dict[str, Any], solu_entries[0]["criteria"])["any"] == ["SoluMod"]
    assert solu_entries[0]["name"] == "Solution Mod"
    classic_config.clear_yaml_cache()

    with pytest.raises(classic_config.RustConfigParseError) as exc_info:
        classic_config.YamlData.from_yaml_content(
            "{ invalid: yaml: content: }}}",
            PARITY_GAME_YAML,
            PARITY_IGNORE_YAML,
            "Fallout4",
            "auto",
        )
    assert "Failed to parse main YAML:" in str(exc_info.value)

    with pytest.raises(classic_config.RustConfigParseError):
        classic_config.YamlData.from_yaml_content(
            "",
            PARITY_GAME_YAML,
            PARITY_IGNORE_YAML,
            "Fallout4",
            "auto",
        )

    monkeypatch.chdir(tmp_path)
    local_yaml_dir = Path("CLASSIC Data")
    local_yaml_dir.mkdir()
    local_yaml = local_yaml_dir / "CLASSIC Fallout4 Local.yaml"
    local_yaml.write_text(
        "\n".join(
            (
                "Game_Info:",
                '  Root_Folder_Game: "C:/Games/Fallout4"',
                '  Root_Folder_Docs: "C:/Users/Test/Documents/My Games/Fallout4"',
            )
        ),
        encoding="utf-8",
    )

    classic_config.persist_game_local_paths(
        local_yaml,
        "D:/Games/Fallout4",
        None,
    )
    local_yaml_after = local_yaml.read_text(encoding="utf-8")
    assert 'Root_Folder_Game: "D:/Games/Fallout4"' in local_yaml_after
    assert (
        'Root_Folder_Docs: "C:/Users/Test/Documents/My Games/Fallout4"'
        in local_yaml_after
    )

    local_yaml.write_text("{ invalid: yaml: content: }}}", encoding="utf-8")
    with pytest.raises(classic_config.RustConfigParseError):
        classic_config.persist_game_local_paths(
            local_yaml,
            "D:/Games/Fallout4",
            None,
        )

    assert classic_config.YamlSource.MAIN.display_name() == "Main Database"
    assert (
        classic_config.YamlSource.GAME.display_name_with_game("Fallout4")
        == "Fallout4 Database"
    )
    assert classic_config.YamlSource.GAME.path("Fallout4").endswith(
        "CLASSIC Fallout4.yaml"
    )
    cache_path = classic_config.YamlSource.CACHE.path("")
    assert cache_path.endswith("cache.yaml")
    assert "CLASSIC" in cache_path


def _run_scanlog_tier1_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import classic_config
    import classic_scanlog

    parser = classic_scanlog.LogParser()
    assert parser.detect_vr_log("Fallout4VR.exe") is True
    assert isinstance(
        classic_scanlog.extract_formids_batch([["Form ID: FF001234"]]), list
    )

    repo_root = Path(__file__).resolve().parents[2]
    log_path = (
        repo_root
        / "business-logic"
        / "classic-scanlog-core"
        / "benches"
        / "fixtures"
        / "crash-12624.log"
    )
    log_lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()

    parsed_version = classic_scanlog.parse_crashgen_version("Buffout 4 v1.28.6")
    assert parsed_version is not None
    assert parsed_version.major == 1
    assert parsed_version.minor == 28
    assert parsed_version.patch == 6

    status = classic_scanlog.check_crashgen_version_status(
        "1.26.0",
        ["1.28.6", "1.37.0"],
    )
    assert status == classic_scanlog.CrashgenVersionStatus.OUTDATED

    yamldata = classic_config.YamlData.from_yaml_content(
        PARITY_MAIN_YAML,
        PARITY_GAME_YAML,
        PARITY_IGNORE_YAML,
        "Fallout4",
        "auto",
    )
    config = classic_scanlog.AnalysisConfig.from_yamldata(
        yamldata,
        "Fallout4",
        "auto",
        simplify_logs=True,
        remove_list=["skip-me"],
    )
    assert config.remove_list == ["skip-me"]

    structured_game_yaml = PARITY_GAME_YAML.replace(
        "Mods_SOLU: []",
        "\n".join(
            (
                "Mods_SOLU:",
                "  - id: solu-mod",
                "    criteria:",
                "      any:",
                '        - "SoluMod"',
                '    name: "Solution Mod"',
                '    description: "Solution mod"',
            )
        ),
    )
    structured_yamldata = classic_config.YamlData.from_yaml_content(
        PARITY_MAIN_YAML,
        structured_game_yaml,
        PARITY_IGNORE_YAML,
        "Fallout4",
        "auto",
    )
    structured_config = classic_scanlog.AnalysisConfig.from_yamldata(
        structured_yamldata,
        "Fallout4",
        "auto",
    )
    solu_entries = cast(list[dict[str, Any]], structured_config.mods_solu)
    assert solu_entries[0]["id"] == "solu-mod"
    assert cast(dict[str, Any], solu_entries[0]["criteria"])["any"] == ["SoluMod"]

    assert hasattr(parser, "parse_segments") is False
    assert hasattr(classic_scanlog.ParallelReportProcessor, "process_batch") is False
    assert hasattr(config, "crashgen_ignore") is False

    sections = parser.parse_all_sections(log_lines)
    assert isinstance(sections, dict)
    assert isinstance(parser.extract_formids(log_lines), list)
    assert isinstance(parser.extract_plugins(log_lines), list)

    matcher = classic_scanlog.PatternMatcher([r"Buffout"])
    assert matcher.find_first("Buffout 4 detected") is not None

    gpu_detector = classic_scanlog.GpuDetector()
    gpu_info = gpu_detector.extract_gpu_info(
        ["GPU #1: Nvidia GeForce RTX 4070", "GPU #2: Intel UHD Graphics"]
    )
    assert "Nvidia" in gpu_info.manufacturer

    papyrus_log = tmp_path / "Papyrus.0.log"
    papyrus_log.write_text(
        "\n".join(
            (
                "Dumping Stacks",
                "warning: sample warning",
                "error: sample error",
            )
        ),
        encoding="utf-8",
    )
    papyrus = classic_scanlog.PapyrusAnalyzer(str(papyrus_log))
    papyrus_stats = papyrus.analyze_full()
    assert papyrus_stats.dumps >= 1

    orchestrator = classic_scanlog.Orchestrator(config)
    result = orchestrator.process_log(str(log_path))
    assert isinstance(result.report_lines, list)

    batch_results = orchestrator.process_logs_batch([str(log_path)], max_concurrent=1)
    assert len(batch_results) == 1

    game_root = tmp_path / "GameRoot"
    docs_root = tmp_path / "DocsRoot"
    game_root.mkdir()
    docs_root.mkdir()
    (game_root / "Fallout4.exe").write_text("stub", encoding="utf-8")

    settings_path = tmp_path / "CLASSIC Settings.yaml"
    settings_path.write_text(
        "schema_version: \"1.0\"\n"
        "CLASSIC_Settings:\n"
        "  Managed Game: Fallout 4\n"
        "  Game Version: Original\n"
        "  FCX Mode: true\n"
        f"  Game Folder Path: '{game_root.as_posix()}'\n"
        f"  Documents Folder Path: '{docs_root.as_posix()}'\n",
        encoding="utf-8",
    )

    classic_scanlog.FcxModeHandler.reset_fcx_checks()
    first_handler = classic_scanlog.FcxModeHandler(True)
    first_handler.check_fcx_mode(str(tmp_path))
    first_messages = first_handler.get_fcx_messages()
    assert first_handler.has_results() is True

    second_handler = classic_scanlog.FcxModeHandler(True)
    second_handler.check_fcx_mode(str(tmp_path))
    assert second_handler.get_fcx_messages() == first_messages

    disabled_handler = classic_scanlog.FcxModeHandler(False)
    disabled_handler.check_fcx_mode(str(tmp_path))
    assert disabled_handler.fcx_mode is False
    assert disabled_handler.get_fcx_messages() == []

    reenabled_handler = classic_scanlog.FcxModeHandler(True)
    reenabled_handler.check_fcx_mode(str(tmp_path))
    assert reenabled_handler.get_fcx_messages() == first_messages

    second_root = tmp_path / "SecondRoot"
    second_game_root = second_root / "GameRoot"
    second_docs_root = second_root / "DocsRoot"
    second_game_root.mkdir(parents=True)
    second_docs_root.mkdir()
    (second_game_root / "Fallout4VR.exe").write_text("stub", encoding="utf-8")
    (second_root / "CLASSIC Settings.yaml").write_text(
        "schema_version: \"1.0\"\n"
        "CLASSIC_Settings:\n"
        "  Managed Game: Fallout 4 VR\n"
        "  Game Version: Original\n"
        "  FCX Mode: true\n"
        f"  Game Folder Path: '{second_game_root.as_posix()}'\n"
        f"  Documents Folder Path: '{second_docs_root.as_posix()}'\n",
        encoding="utf-8",
    )
    different_root_handler = classic_scanlog.FcxModeHandler(True)
    different_root_handler.check_fcx_mode(str(second_root))
    assert different_root_handler.get_fcx_messages() != first_messages


def _run_version_registry_tier1_smoke(
    _tmp_path: Path, _monkeypatch: pytest.MonkeyPatch
) -> None:
    import classic_version_registry

    registry = classic_version_registry.get_version_registry()
    assert registry is not None

    info = registry.get_by_id("FO4_OG")
    assert info is not None
    assert info.short_name == "OG"

    result = classic_version_registry.match_version_string(
        "1.10.163.0", "Fallout4", False
    )
    assert result.is_valid is True

    game_version = classic_version_registry.GameVersion("1.10.163.0")
    assert (
        game_version.semantic_distance(
            classic_version_registry.GameVersion("1.10.984.0")
        )
        > 0
    )

    registry = classic_version_registry.VersionRegistry()
    assert registry.get_by_version("1.10.163.0") is not None
    assert registry.get_by_short_name("OG") is not None
    assert len(registry.get_all()) >= 1
    assert len(registry.get_all_for_game("Fallout4")) >= 1
    assert len(registry.get_correct_versions(False)) >= 1
    assert isinstance(registry.get_wrong_versions(False), list)

    match_result = registry.match_version("1.10.163.0", "Fallout4", False)
    assert match_result.is_exact is True
    assert match_result.confidence_enum.is_high_confidence() is True

    assert registry.get_address_library_filename("1.10.163.0", False) is not None
    assert len(registry.get_crashgen_configs("FO4_OG")) >= 1
    assert len(registry.get_crashgen_versions("FO4_OG")) >= 1
    assert registry.get_crashgen_for_version("FO4_OG", "1.28.6") is not None
    assert isinstance(registry.get_all_exe_hashes(), set)
    assert isinstance(registry.get_all_script_hashes(), dict)
    assert isinstance(registry.get_script_hashes_for_version("FO4_OG"), dict)
    assert registry.unknown_version_handling.get_default("Fallout4") is not None


def _run_config_tier2_smoke(_tmp_path: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    import classic_config

    data = classic_config.YamlData.from_yaml_content(
        PARITY_MAIN_YAML,
        PARITY_GAME_YAML,
        PARITY_IGNORE_YAML,
        "Fallout4",
        "auto",
    )
    assert data.classic_version_date == "2026-02-25"
    assert data.warn_outdated == "Outdated"
    assert data.autoscan_text == "Autoscan Fallout 4"


def _run_scanlog_tier2_smoke(_tmp_path: Path, _monkeypatch: pytest.MonkeyPatch) -> None:
    import classic_scanlog

    version = classic_scanlog.parse_crashgen_version("Buffout 4 v1.28.6")
    assert version is not None
    assert version.to_tuple() == (1, 28, 6)

    parser = classic_scanlog.LogParser()
    errors = parser.find_errors(["INFO: ok", "ERROR: sample failure"])
    assert isinstance(errors, list)
    assert len(errors) >= 1

    matcher = classic_scanlog.PatternMatcher([r"Buffout", r"GPU"])
    assert len(matcher.find_all("Buffout 4 GPU warning")) >= 1
    assert matcher.has_match("GPU fallback detected") is True


def _run_version_registry_tier2_smoke(
    _tmp_path: Path, _monkeypatch: pytest.MonkeyPatch
) -> None:
    import classic_version_registry

    base = classic_version_registry.GameVersion("1.10.163.0")
    newer = classic_version_registry.GameVersion("1.10.984.0")
    assert base.semantic_distance(newer) > 0


def _run_cache_helpers_tier2_smoke(
    tmp_path: Path, _monkeypatch: pytest.MonkeyPatch
) -> None:
    import classic_file_io

    hashed_file = tmp_path / "hash-cache.txt"
    hashed_file.write_text("hash-cache", encoding="utf-8")

    classic_file_io.FileHasher.clear_cache()
    classic_file_io.FileHasher.reset_cache_stats()
    first_hash = classic_file_io.FileHasher.hash_file(str(hashed_file))
    second_hash = classic_file_io.FileHasher.hash_file(str(hashed_file))
    assert first_hash == second_hash

    hash_stats = classic_file_io.FileHasher.cache_stats()
    assert hash_stats["misses"] == 1
    assert hash_stats["hits"] == 1
    assert hash_stats["capacity"] >= hash_stats["size"]

    classic_file_io.FileHasher.reset_cache_stats()
    reset_stats = classic_file_io.FileHasher.cache_stats()
    assert reset_stats["hits"] == 0
    assert reset_stats["misses"] == 0

    classic_file_io.FileHasher.clear_cache()
    cleared_stats = classic_file_io.FileHasher.cache_stats()
    assert cleared_stats["size"] == 0


CASE_RUNNERS = {
    "config-tier1-smoke": _run_config_tier1_smoke,
    "scanlog-tier1-smoke": _run_scanlog_tier1_smoke,
    "version-registry-tier1-smoke": _run_version_registry_tier1_smoke,
    "config-tier2-smoke": _run_config_tier2_smoke,
    "cache-helpers-tier2-smoke": _run_cache_helpers_tier2_smoke,
    "scanlog-tier2-smoke": _run_scanlog_tier2_smoke,
    "version-registry-tier2-smoke": _run_version_registry_tier2_smoke,
}


def test_application_dir_override(tmp_path: Path) -> None:
    """Independent application-local YAML helpers expose the registry override."""
    import classic_config

    # Module auto-init should have set APP_DIR to cwd
    app_dir = classic_config.get_application_dir()
    assert app_dir is not None, "APP_DIR should be auto-set on import"

    classic_config.set_application_dir(str(tmp_path))
    assert classic_config.get_application_dir() == str(tmp_path)

    # Restore the original override so other tests are unaffected
    if app_dir is not None:
        classic_config.set_application_dir(app_dir)


def _run_application_dir_override(
    tmp_path: Path, _monkeypatch: pytest.MonkeyPatch
) -> None:
    test_application_dir_override(tmp_path)


CASE_RUNNERS["application-dir-override"] = _run_application_dir_override


def test_parse_segments_parallel_deprecation_warning() -> None:
    """parse_segments_parallel matches parse_all_sections output."""
    import classic_scanlog

    parser = classic_scanlog.LogParser()
    repo_root = Path(__file__).resolve().parents[2]
    log_path = (
        repo_root
        / "business-logic"
        / "classic-scanlog-core"
        / "benches"
        / "fixtures"
        / "crash-12624.log"
    )
    sample_lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    expected = parser.parse_all_sections(sample_lines)

    with pytest.warns(
        DeprecationWarning, match="parse_segments_parallel is deprecated"
    ):
        result = parser.parse_segments_parallel(sample_lines)

    assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"
    assert result == expected
    assert result["plugins"][:3] == [
        "\t[00]Fallout4.esm",
        "\t[01]DLCRobot.esm",
        "\t[02]DLCworkshop01.esm",
    ]


def test_generate_suspect_section_deprecation_warning() -> None:
    """generate_suspect_section matches header plus footer outputs."""
    import classic_scanlog

    report_gen = classic_scanlog.ReportGenerator()
    header_lines = report_gen.generate_suspect_section_header().to_list()
    empty_footer_lines = report_gen.generate_suspect_found_footer(False).to_list()
    found_footer_lines = report_gen.generate_suspect_found_footer(True).to_list()

    with pytest.warns(
        DeprecationWarning, match="generate_suspect_section is deprecated"
    ):
        empty_fragment = report_gen.generate_suspect_section([])

    with pytest.warns(
        DeprecationWarning, match="generate_suspect_section is deprecated"
    ):
        found_fragment = report_gen.generate_suspect_section(["SomeSuspect"])

    assert empty_fragment.to_list() == header_lines + empty_footer_lines
    assert found_fragment.to_list() == header_lines + found_footer_lines
    assert empty_fragment.to_list() == [
        "### Checking for Known Crash Messages, Errors and Suspects\n\n",
        "* **NO SUSPECTS DETECTED** *\n\n",
        "---\n\n",
    ]
    assert found_fragment.to_list() == [
        "### Checking for Known Crash Messages, Errors and Suspects\n\n",
        "* **ONE OR MORE SUSPECTS DETECTED! CHECK LOG ABOVE FOR MORE INFORMATION!** *\n\n",
        "---\n\n",
    ]


def test_formid_analyzer_legacy_dict_deprecation_warning() -> None:
    """PyFormIDAnalyzerCore.__init__ emits DeprecationWarning when mods_single is a dict."""
    import classic_scanlog

    legacy_mods_single = {"TestMod": "Install TestMod fix"}

    with pytest.warns(DeprecationWarning, match="mods_single as dict.*is deprecated"):
        analyzer = classic_scanlog.FormIDAnalyzerCore(
            show_formid_values=False,
            crashgen_name="Buffout 4",
            mods_single=legacy_mods_single,
        )

    assert analyzer is not None


@pytest.mark.parametrize("case_id", get_runtime_coverage_case_ids(THIS_SUITE))
def test_runtime_coverage_registry_cases(
    case_id: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    CASE_RUNNERS[case_id](tmp_path, monkeypatch)
