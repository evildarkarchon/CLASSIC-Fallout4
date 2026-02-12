"""Game integrity and configuration scanning.

This package provides functionality for scanning game installations
to verify integrity and configuration correctness.

Subpackages:
- checks: Individual check modules (BA2, DDS, INI, XSE, etc.)
- models: Data models for game scanning
"""

from ClassicLib.scanning.game.check_crashgen import check_crashgen_settings
from ClassicLib.scanning.game.check_xse_plugins import (
    ALL_ADDRESS_LIB_INFO,
    AddressLibVersionInfo,
    check_xse_plugins,
)
from ClassicLib.scanning.game.config import ConfigFileCache, mod_toml_config
from ClassicLib.scanning.game.core import ScanGameCore
from ClassicLib.scanning.game.game_files_manager import (
    get_game_files_manager_core,
    manage_game_files,
    manage_game_files_async,
)
from ClassicLib.scanning.game.orchestrator import (
    generate_game_combined_result,
    generate_game_combined_result_async,
    generate_mods_combined_result,
    generate_mods_combined_result_async,
    get_game_integrity_orchestrator_core,
    write_combined_results,
    write_combined_results_async,
)
from ClassicLib.scanning.game.scan_mod_inis import (
    detect_all_ini_issues_async,
    scan_mod_inis,
)
from ClassicLib.scanning.game.wrye_check import scan_wryecheck

__all__ = [
    # CheckXsePlugins
    "ALL_ADDRESS_LIB_INFO",
    "AddressLibVersionInfo",
    # Config
    "ConfigFileCache",
    # Core
    "ScanGameCore",
    # CheckCrashgen
    "check_crashgen_settings",
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
    "check_xse_plugins",
    "detect_all_ini_issues_async",
    "mod_toml_config",
    "scan_mod_inis",
    # WryeCheck
    "scan_wryecheck",
]
