"""Game integrity and mod scanning CLI entry point for CLASSIC.

This module provides the main entry point for game file integrity checks and mod scanning
operations. It serves as a high-level interface that delegates to the ScanGameCore and
related modules while maintaining backward compatibility with existing code.

Main functionality:
- Game file integrity checking and management (backup, restore, remove)
- Mod scanning for both unpacked and archived mods
- Combined result generation for comprehensive reports
- Synchronous adapters for async operations using AsyncBridge
- CLI entry point for standalone game scanning operations

The module follows the async-first orchestrator pattern by delegating core functionality
to ScanGameCore while providing sync wrappers for CLI usage.
"""

from pathlib import Path
from typing import Literal

from ClassicLib import msg_info
from ClassicLib.AsyncBridge import AsyncBridge
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
# DELEGATE FUNCTIONS TO SCANGAMECORE
# ================================================
def get_scan_game_core() -> ScanGameCore:
    """Get singleton ScanGameCore instance from GlobalRegistry.

    Returns:
        ScanGameCore: The singleton ScanGameCore instance managed by GlobalRegistry.
    """
    # ScanGameCore's __new__ method handles singleton via GlobalRegistry
    return ScanGameCore()


# Backwards compatibility functions for existing code
def check_log_errors(folder_path: Path | str) -> str:
    """Sync adapter for async check_log_errors.

    Args:
        folder_path: Path to the folder containing log files to check for errors.

    Returns:
        str: Results of the log error checking operation as a formatted string.
    """
    bridge: AsyncBridge = AsyncBridge.get_instance()
    core: ScanGameCore = get_scan_game_core()
    return bridge.run_async(core.check_log_errors(folder_path))


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


def scan_mods_unpacked() -> str:
    """Sync adapter for async scan_mods_unpacked.

    Returns:
        str: Results of the unpacked mods scanning operation as a formatted string.
    """
    bridge: AsyncBridge = AsyncBridge.get_instance()
    core: ScanGameCore = get_scan_game_core()
    return bridge.run_async(core.scan_mods_unpacked())


def scan_mods_archived() -> str:
    """Sync adapter for async scan_mods_archived.

    Returns:
        str: Results of the archived mods scanning operation as a formatted string.
    """
    bridge: AsyncBridge = AsyncBridge.get_instance()
    core: ScanGameCore = get_scan_game_core()
    return bridge.run_async(core.scan_mods_archived())


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
