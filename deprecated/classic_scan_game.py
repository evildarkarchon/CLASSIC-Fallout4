"""Game integrity and mod scanning shared interface for CLASSIC.

This module provides sync wrappers for game file integrity checks and mod
scanning operations. It is intentionally separate from the Rust
``classic_scangame`` binding module to avoid namespace conflicts.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import TYPE_CHECKING, Any, Literal, cast

from ClassicLib import msg_info
from ClassicLib.core.async_bridge import AsyncBridge
from ClassicLib.scanning.game import (
    ScanGameCore,
    generate_game_combined_result,
    generate_game_combined_result_async,
    generate_mods_combined_result,
    generate_mods_combined_result_async,
    manage_game_files,
    manage_game_files_async,
    write_combined_results_async,
)
from ClassicLib.scanning.game.config import TEST_MODE
from ClassicLib.support.setup import SetupCoordinator

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from pathlib import Path


def get_scan_game_core() -> ScanGameCore:
    """Get singleton ScanGameCore instance from GlobalRegistry."""
    return ScanGameCore()


def _ensure_coroutine(value: object) -> Coroutine[Any, Any, object]:
    if inspect.iscoroutine(value):
        return cast("Coroutine[Any, Any, object]", value)

    async def _wrapped() -> object:
        if inspect.isawaitable(value):
            return await value
        return value

    return _wrapped()


def check_log_errors(folder_path: Path | str) -> object:
    """Check for log errors synchronously via AsyncBridge (GUI-only)."""
    core = get_scan_game_core()
    return AsyncBridge.get_instance().run_async(_ensure_coroutine(core.check_log_errors(folder_path)))


async def get_scan_settings() -> tuple[str, dict[str, set[str]], Path | None]:
    """Get common settings used by mod scanning functions."""
    core = get_scan_game_core()
    return await core.get_scan_settings()


def get_issue_messages(xse_acronym: str, mode: str) -> dict[str, list[str]]:
    """Return standardized issue messages for mod scan reports."""
    core = get_scan_game_core()
    return core.get_issue_messages(xse_acronym, mode)


def scan_mods_unpacked(*args: object, **kwargs: object) -> object:
    """Scan unpacked mods synchronously via AsyncBridge (GUI-only)."""
    core = get_scan_game_core()
    return AsyncBridge.get_instance().run_async(_ensure_coroutine(core.scan_mods_unpacked(*args, **kwargs)))


def scan_mods_archived(*args: object, **kwargs: object) -> object:
    """Scan archived mods synchronously via AsyncBridge (GUI-only)."""
    core = get_scan_game_core()
    return AsyncBridge.get_instance().run_async(_ensure_coroutine(core.scan_mods_archived(*args, **kwargs)))


def game_files_manage(classic_list: str, mode: Literal["BACKUP", "RESTORE", "REMOVE"] = "BACKUP") -> None:
    """Manage game files by performing backup, restore, or removal operations."""
    manage_game_files(classic_list, mode)


def game_combined_result() -> str:
    """Generate combined game check report text for compatibility callers."""
    report_text, _ = generate_game_combined_result()
    return report_text


def mods_combined_result() -> str:
    """Combine the results of scanning unpacked and archived mods."""
    return generate_mods_combined_result()


async def main() -> None:
    """Serve as main entry point for game scanning - async-first pattern."""
    coordinator = SetupCoordinator()
    coordinator.initialize_application(is_gui=False)

    if TEST_MODE:
        await write_combined_results_async()
    else:
        game_result, _ = await generate_game_combined_result_async()
        msg_info(game_result)

        mods_result = await generate_mods_combined_result_async()
        msg_info(mods_result)

        await manage_game_files_async("Backup ENB")


if __name__ == "__main__":
    asyncio.run(main())
