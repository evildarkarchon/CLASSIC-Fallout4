"""Backward-compatibility status helpers for integration factory."""

from __future__ import annotations

from typing import Any

COMPONENT_KEY_MAP: dict[str, tuple[str, str | None]] = {
    "parser": ("classic_scanlog", "LogParser"),
    "formid_analyzer": ("classic_scanlog", "FormIDAnalyzer"),
    "plugin_analyzer": ("classic_scanlog", "PluginAnalyzer"),
    "record_scanner": ("classic_scanlog", "RecordScanner"),
    "report_generation": ("classic_scanlog", "ReportGenerator"),
    "suspect_scanner": ("classic_scanlog", "SuspectScanner"),
    "settings_validator": ("classic_scanlog", "SettingsValidator"),
    "gpu_detector": ("classic_scanlog", "GpuDetector"),
    "fcx_handler": ("classic_scanlog", "FcxModeHandler"),
    "orchestrator": ("classic_scanlog", "Orchestrator"),
    "mod_detector": ("classic_scanlog", "detect_mods_batch"),
    "database": ("classic_database", None),
    "database_pool": ("classic_database", "DatabasePool"),
    "file_io": ("classic_file_io", None),
    "file_io_core": ("classic_file_io", "FileIOCore"),
    "yaml": ("classic_yaml", None),
    "yaml_operations": ("classic_yaml", "YamlOperations"),
    "path": ("classic_path", None),
    "path_operations": ("classic_path", "PathValidator"),
    "yamldata": ("classic_config", "YamlData"),
    "constants": ("classic_constants", None),
    "version_utils": ("classic_version", None),
    "pe_version": ("classic_version", "extract_pe_version"),
    "similarity": ("classic_file_io", "calculate_similarity"),
    "resource_mgmt": ("classic_resource", None),
    "xse_utils": ("classic_xse", None),
    "web_utils": ("classic_web", None),
    "scangame": ("classic_scangame", None),
    "ba2_scanner": ("classic_scangame", "BA2Scanner"),
    "config_duplicates": ("classic_scangame", "ConfigDuplicateDetector"),
    "unpacked_scanner": ("classic_scangame", "UnpackedScanner"),
    "log_processor": ("classic_scangame", "LogProcessor"),
    "ini_validator": ("classic_scangame", "IniValidator"),
    "crashgen_checker": ("classic_scangame", "CrashgenChecker"),
    "xse_checker": ("classic_scangame", "XseChecker"),
    "integrity_checker": ("classic_scangame", "GameIntegrityChecker"),
    "wrye_parser": ("classic_scangame", "WryeBashParser"),
    "crashgen_orchestrator": ("classic_scangame", "CrashgenCheckOrchestrator"),
    "config_file_cache": ("classic_scangame", "RustConfigFileCache"),
    "mod_ini_scanner": ("classic_scangame", "RustModIniScanner"),
    "game_scan_orchestrator": ("classic_scangame", "GameScanOrchestrator"),
    "game_scan_config": ("classic_scangame", "GameScanConfig"),
    "game_scan_result": ("classic_scangame", "GameScanResult"),
    "mod_scan_result": ("classic_scangame", "ModScanResult"),
    "dds_analyzer": ("classic_file_io", "DDSAnalyzer"),
    "scan_report_builder": ("classic_scangame", "build_unpacked_report"),
    "setup_checks": ("classic_scangame", "run_setup_checks"),
    "papyrus_analyzer": ("classic_scanlog", "PapyrusAnalyzer"),
    "papyrus_stats": ("classic_scanlog", "PapyrusStats"),
    "report_fragment": ("classic_scanlog", "ReportFragment"),
    "report_composer": ("classic_scanlog", "ReportComposer"),
    "string_pool": ("classic_scanlog", "StringPool"),
}


def compute_rust_component_status(availability: dict[str, bool]) -> dict[str, Any]:
    """Build the legacy status payload from component availability flags."""
    active_count = sum(1 for is_available in availability.values() if is_available)
    total_count = len(availability)
    percentage = (active_count / total_count * 100) if total_count > 0 else 0

    if percentage >= 90:
        level = "FULLY ACCELERATED"
    elif percentage >= 70:
        level = "HIGHLY ACCELERATED"
    elif percentage >= 30:
        level = "PARTIALLY ACCELERATED"
    elif active_count > 0:
        level = "MINIMAL ACCELERATION"
    else:
        level = "NO ACCELERATION"

    return {
        "available": availability,
        "initialized": {},
        "failed": {},
        "performance_gains": {},
        "active_count": active_count,
        "total_count": total_count,
        "percentage": percentage,
        "acceleration_active": active_count > 0,
        "acceleration_level": level,
        "versions": {},
        "disabled": False,
    }
