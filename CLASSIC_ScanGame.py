"""Game integrity and mod scanning shared interface for CLASSIC.

This module provides sync wrappers for game file integrity checks and mod scanning
operations. It serves as a shared interface used by GUI workers, TUI, and scanning contexts.

Main functionality:
- Game file integrity checking and management (backup, restore, remove)
- Mod scanning for both unpacked and archived mods
- Combined result generation for comprehensive reports
- Phase 2 context-aware sync wrappers (work in GUI, error in CLI/TUI)

IMPORTANT: These are GUI-compatible sync wrappers. For pure async contexts:
- Use ScanGameCore directly with await
- TUI/CLI should use async methods, not these wrappers

Phase 4: Refactored to use create_sync_wrapper() for context awareness.
"""

from pathlib import Path
from typing import Literal

from ClassicLib import msg_info
from ClassicLib.AsyncBridge import create_sync_wrapper
from ClassicLib.ScanGame import (
    generate_game_combined_result,
    generate_mods_combined_result,
    manage_game_files,
    write_combined_results,
)
from ClassicLib.ScanGame.Config import TEST_MODE
from ClassicLib.ScanGame.ScanGameCore import ScanGameCore
from ClassicLib.SetupCoordinator import SetupCoordinator


# ================================================
# SCANGAMECORE SINGLETON ACCESS
# ================================================
def get_scan_game_core() -> ScanGameCore:
    """Get singleton ScanGameCore instance from GlobalRegistry.

    Returns:
        ScanGameCore: The singleton ScanGameCore instance managed by GlobalRegistry.
    """
    # ScanGameCore's __new__ method handles singleton via GlobalRegistry
    return ScanGameCore()


# Get core instance for wrapper creation
_scan_game_core = get_scan_game_core()

# ================================================
# PHASE 2 CONTEXT-AWARE SYNC WRAPPERS
# ================================================
# Created once at module load, reused for all calls
# Work in GUI mode, error in CLI/TUI mode

check_log_errors = create_sync_wrapper(_scan_game_core.check_log_errors)


def get_scan_settings() -> tuple[str, dict[str, str], Path | None]:
    """Gets common settings used by mod scanning functions.

    Returns:
        tuple[str, dict[str, str], Path | None]: A tuple containing:
            - str: XSE acronym (e.g., 'F4SE', 'SKSE')
            - dict[str, str]: Dictionary of scanning configuration settings
            - Path | None: Optional path to the mods folder, or None if not configured
    """
    core: ScanGameCore = get_scan_game_core()
    return core.get_scan_settings()


def get_issue_messages(xse_acronym: str, mode: str) -> dict[str, list[str]]:
    """Returns standardized issue messages for mod scan reports.

    Args:
        xse_acronym: The XSE acronym (e.g., 'F4SE', 'SKSE') for the current game.
        mode: The scanning mode or context for which to get issue messages.

    Returns:
        dict[str, list[str]]: Dictionary mapping issue categories to lists of
            standardized issue messages for mod scan reports.
    """
    core: ScanGameCore = get_scan_game_core()
    return core.get_issue_messages(xse_acronym, mode)


scan_mods_unpacked = create_sync_wrapper(_scan_game_core.scan_mods_unpacked)
scan_mods_archived = create_sync_wrapper(_scan_game_core.scan_mods_archived)


# ================================================
# GAME FILES MANAGEMENT - DELEGATE TO NEW MODULE
# ================================================
def game_files_manage(classic_list: str, mode: Literal["BACKUP", "RESTORE", "REMOVE"] = "BACKUP") -> None:
    """
    Manages game files by performing backup, restore, or removal operations.

    This function delegates to the new GameFilesManager module.

    Args:
        classic_list: The name of the list specifying which files need to be managed.
        mode: The operation mode ("BACKUP", "RESTORE", or "REMOVE").
    """
    manage_game_files(classic_list, mode)


# ================================================
# COMBINED RESULTS - DELEGATE TO NEW MODULE
# ================================================
def game_combined_result() -> str:
    """
    Generates a combined result summarizing game-related checks and scans.

    This function delegates to the new GameIntegrityOrchestrator module.

    Returns:
        str: A string summarizing the results of all performed checks and scans.
    """
    return generate_game_combined_result()


def mods_combined_result() -> str:
    """
    Combines the results of scanning unpacked and archived mods.

    This function delegates to the new GameIntegrityOrchestrator module.

    Returns:
        str: The combined results of the unpacked and archived mods scans.
    """
    return generate_mods_combined_result()


def main() -> None:
    """Main entry point for game scanning."""
    # Initialize application using SetupCoordinator
    coordinator = SetupCoordinator()
    coordinator.initialize_application(is_gui=False)
    # Note: run_initial_setup() removed - not needed for normal operation
    # Files are generated on-demand when needed, not at every startup

    if TEST_MODE:
        write_combined_results()
    else:
        msg_info(game_combined_result())
        msg_info(mods_combined_result())
        game_files_manage("Backup ENB")


if __name__ == "__main__":
    main()
    input("Press Enter to continue...")
