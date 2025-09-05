"""ScanGame package - Game file scanning and validation."""

from ClassicLib.ScanGame.CheckCrashgen import CrashgenChecker, check_crashgen_settings
from ClassicLib.ScanGame.CheckXsePlugins import (
    ALL_ADDRESS_LIB_INFO,
    AddressLibVersionInfo,
    check_xse_plugins,
)
from ClassicLib.ScanGame.Config import ConfigFile, ConfigFileCache, compare_ini_files, mod_toml_config
from ClassicLib.ScanGame.GameFilesManager import (
    get_game_files_manager_core,
    manage_game_files,
    manage_game_files_async,
)
from ClassicLib.ScanGame.GameIntegrityOrchestrator import (
    generate_game_combined_result,
    generate_game_combined_result_async,
    generate_mods_combined_result,
    generate_mods_combined_result_async,
    get_game_integrity_orchestrator_core,
    write_combined_results,
    write_combined_results_async,
)
from ClassicLib.ScanGame.ScanModInis import (
    apply_all_ini_fixes,
    apply_ini_fix,
    check_duplicate_files,
    check_starting_console_command,
    check_vsync_settings,
    scan_mod_inis,
)
from ClassicLib.ScanGame.WryeCheck import (
    extract_plugins_from_section,
    format_section_header,
    parse_wrye_report,
    scan_wryecheck,
)

__all__ = [
    # CheckXsePlugins
    "ALL_ADDRESS_LIB_INFO",
    "AddressLibVersionInfo",
    # Config
    "ConfigFile",
    "ConfigFileCache",
    # CheckCrashgen
    "CrashgenChecker",
    # GameFilesManager
    "manage_game_files",
    "manage_game_files_async",
    "get_game_files_manager_core",
    # GameIntegrityOrchestrator
    "generate_game_combined_result",
    "generate_game_combined_result_async",
    "generate_mods_combined_result",
    "generate_mods_combined_result_async",
    "write_combined_results",
    "write_combined_results_async",
    "get_game_integrity_orchestrator_core",
    # ScanModInis
    "apply_all_ini_fixes",
    "apply_ini_fix",
    "check_crashgen_settings",
    "check_duplicate_files",
    "check_starting_console_command",
    "check_vsync_settings",
    "check_xse_plugins",
    "compare_ini_files",
    # WryeCheck
    "extract_plugins_from_section",
    "format_section_header",
    "mod_toml_config",
    "parse_wrye_report",
    "scan_mod_inis",
    "scan_wryecheck",
]
