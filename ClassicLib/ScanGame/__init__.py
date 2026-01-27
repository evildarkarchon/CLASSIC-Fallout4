"""Backward compatibility module for ScanGame.

This package has been moved to ClassicLib.scanning.game.
All imports are re-exported for backward compatibility.

.. deprecated::
    Import from ClassicLib.scanning.game instead.
"""

import warnings

warnings.warn(
    "ClassicLib.ScanGame is deprecated, import from ClassicLib.scanning.game instead",
    DeprecationWarning,
    stacklevel=2,
)

from ClassicLib.scanning.game import *  # noqa: F403, E402, I001
from ClassicLib.scanning.game import (  # noqa: E402
    ALL_ADDRESS_LIB_INFO as ALL_ADDRESS_LIB_INFO,
    AddressLibVersionInfo as AddressLibVersionInfo,
    ConfigFile as ConfigFile,
    ConfigFileCache as ConfigFileCache,
    CrashgenChecker as CrashgenChecker,
    ScanGameCore as ScanGameCore,
    check_crashgen_settings as check_crashgen_settings,
    check_duplicate_files as check_duplicate_files,
    check_starting_console_command as check_starting_console_command,
    check_vsync_settings as check_vsync_settings,
    check_xse_plugins as check_xse_plugins,
    compare_ini_files as compare_ini_files,
    detect_all_ini_issues_async as detect_all_ini_issues_async,
    detect_ini_issue_async as detect_ini_issue_async,
    extract_plugins_from_section as extract_plugins_from_section,
    format_section_header as format_section_header,
    generate_game_combined_result as generate_game_combined_result,
    generate_game_combined_result_async as generate_game_combined_result_async,
    generate_mods_combined_result as generate_mods_combined_result,
    generate_mods_combined_result_async as generate_mods_combined_result_async,
    get_game_files_manager_core as get_game_files_manager_core,
    get_game_integrity_orchestrator_core as get_game_integrity_orchestrator_core,
    manage_game_files as manage_game_files,
    manage_game_files_async as manage_game_files_async,
    mod_toml_config as mod_toml_config,
    parse_wrye_report as parse_wrye_report,
    scan_mod_inis as scan_mod_inis,
    scan_wryecheck as scan_wryecheck,
    write_combined_results as write_combined_results,
    write_combined_results_async as write_combined_results_async,
)
