"""Backward-compatible script wrapper for classic_scan_game module."""

from __future__ import annotations

import asyncio

from classic_scan_game import (
    check_log_errors,
    game_combined_result,
    game_files_manage,
    get_issue_messages,
    get_scan_game_core,
    get_scan_settings,
    main,
    mods_combined_result,
    scan_mods_archived,
    scan_mods_unpacked,
)

__all__ = [
    "check_log_errors",
    "game_combined_result",
    "game_files_manage",
    "get_issue_messages",
    "get_scan_game_core",
    "get_scan_settings",
    "main",
    "mods_combined_result",
    "scan_mods_archived",
    "scan_mods_unpacked",
]

if __name__ == "__main__":
    asyncio.run(main())
    input("Press Enter to continue...")
