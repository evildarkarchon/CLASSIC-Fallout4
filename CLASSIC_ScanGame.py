"""Game integrity and mod scanning shared interface for CLASSIC.

This module provides sync wrappers for game file integrity checks and mod scanning
operations. It serves as a shared interface used by GUI workers and testing contexts.

Main functionality:
- Game file integrity checking and management (backup, restore, remove)
- Mod scanning for both unpacked and archived mods
- Combined result generation for comprehensive reports
- Phase 2 context-aware sync wrappers (for GUI workers and testing)

IMPORTANT Usage Patterns:
- GUI workers: Use sync wrappers (game_combined_result(), mods_combined_result())
- CLI production: Use async methods directly (see main() for reference pattern)
- Testing/benchmarking: Sync wrappers work via asyncio.run() fallback

Phase 4: Uses AsyncBridge.run_async() directly for GUI sync wrappers.
Phase 5: CLI entry point converted to async-first pattern (following classic_scanlogs.py).
"""

import asyncio
from pathlib import Path
from typing import Literal

from ClassicLib import msg_info
from ClassicLib.core.async_bridge import AsyncBridge
from ClassicLib.scanning.game import (
    generate_game_combined_result,
    generate_game_combined_result_async,
    generate_mods_combined_result,
    generate_mods_combined_result_async,
    manage_game_files,
    manage_game_files_async,
    write_combined_results_async,
)
from ClassicLib.scanning.game.config import TEST_MODE
from ClassicLib.scanning.game.core import ScanGameCore
from ClassicLib.support.setup import SetupCoordinator


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


def check_log_errors(*args: object, **kwargs: object) -> object:
    """Check for log errors synchronously via AsyncBridge (GUI-only).

    Args:
        *args: Positional arguments forwarded to ScanGameCore.check_log_errors.
        **kwargs: Keyword arguments forwarded to ScanGameCore.check_log_errors.

    Returns:
        The result of the async check_log_errors call.

    """
    return AsyncBridge.get_instance().run_async(_scan_game_core.check_log_errors(*args, **kwargs))


async def get_scan_settings() -> tuple[str, dict[str, set[str]], Path | None]:
    """Get common settings used by mod scanning functions.

    Returns:
        tuple[str, dict[str, set[str]], Path | None]: A tuple containing:
            - str: XSE acronym (e.g., 'F4SE', 'SKSE')
            - dict[str, set[str]]: Dictionary mapping script file patterns to their expected hashes
            - Path | None: Optional path to the mods folder, or None if not configured

    """
    core: ScanGameCore = get_scan_game_core()
    return await core.get_scan_settings()


def get_issue_messages(xse_acronym: str, mode: str) -> dict[str, list[str]]:
    """Return standardized issue messages for mod scan reports.

    Args:
        xse_acronym: The XSE acronym (e.g., 'F4SE', 'SKSE') for the current game.
        mode: The scanning mode or context for which to get issue messages.

    Returns:
        dict[str, list[str]]: Dictionary mapping issue categories to lists of
            standardized issue messages for mod scan reports.

    """
    core: ScanGameCore = get_scan_game_core()
    return core.get_issue_messages(xse_acronym, mode)


def scan_mods_unpacked(*args: object, **kwargs: object) -> object:
    """Scan unpacked mods synchronously via AsyncBridge (GUI-only).

    Args:
        *args: Positional arguments forwarded to ScanGameCore.scan_mods_unpacked.
        **kwargs: Keyword arguments forwarded to ScanGameCore.scan_mods_unpacked.

    Returns:
        The result of the async scan_mods_unpacked call.

    """
    return AsyncBridge.get_instance().run_async(_scan_game_core.scan_mods_unpacked(*args, **kwargs))


def scan_mods_archived(*args: object, **kwargs: object) -> object:
    """Scan archived mods synchronously via AsyncBridge (GUI-only).

    Args:
        *args: Positional arguments forwarded to ScanGameCore.scan_mods_archived.
        **kwargs: Keyword arguments forwarded to ScanGameCore.scan_mods_archived.

    Returns:
        The result of the async scan_mods_archived call.

    """
    return AsyncBridge.get_instance().run_async(_scan_game_core.scan_mods_archived(*args, **kwargs))


# ================================================
# GAME FILES MANAGEMENT - DELEGATE TO NEW MODULE
# ================================================
def game_files_manage(classic_list: str, mode: Literal["BACKUP", "RESTORE", "REMOVE"] = "BACKUP") -> None:
    """Manage game files by performing backup, restore, or removal operations.

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
    """Generate a combined result summarizing game-related checks and scans.

    This function delegates to the new GameIntegrityOrchestrator module.
    Note: This wrapper maintains backward compatibility by unpacking the tuple
    and returning only the report text, discarding detected issues.

    Returns:
        str: A string summarizing the results of all performed checks and scans.

    """
    report_text, _ = generate_game_combined_result()  # Unpack tuple, discard issues
    return report_text


def mods_combined_result() -> str:
    """Combine the results of scanning unpacked and archived mods.

    This function delegates to the new GameIntegrityOrchestrator module.

    Returns:
        str: The combined results of the unpacked and archived mods scans.

    """
    return generate_mods_combined_result()


async def main() -> None:
    """Serve as main entry point for game scanning - Async-First Pattern.

    This CLI entry point uses native async operations with a single asyncio.run()
    call, following the same pattern as classic_scanlogs.py.

    For GUI workers, use the sync wrappers (game_combined_result(), etc.) instead.
    """
    # Initialize application using SetupCoordinator
    coordinator = SetupCoordinator()
    coordinator.initialize_application(is_gui=False)
    # Note: run_initial_setup() removed - not needed for normal operation
    # Files are generated on-demand when needed, not at every startup

    if TEST_MODE:
        await write_combined_results_async()
    else:
        # Use async methods directly in CLI production code
        game_result, _ = await generate_game_combined_result_async()
        msg_info(game_result)

        mods_result = await generate_mods_combined_result_async()
        msg_info(mods_result)

        await manage_game_files_async("Backup ENB")


if __name__ == "__main__":
    # Single asyncio.run() call at entry point only (async-first pattern)
    asyncio.run(main())
    input("Press Enter to continue...")
