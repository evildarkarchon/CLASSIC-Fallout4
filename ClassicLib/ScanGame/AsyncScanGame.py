"""
DEPRECATED: Async implementations for CLASSIC_ScanGame.py operations.

This module is deprecated as of the async-first refactoring.
All functionality has been moved to ScanGameCore.py.
This module now provides compatibility aliases to maintain backwards compatibility.
"""

import asyncio
from pathlib import Path
from typing import Any

from ClassicLib.ScanGame.ScanGameCore import ScanGameCore

# Deprecated - for compatibility only
MAX_CONCURRENT_SUBPROCESSES = 4
MAX_CONCURRENT_FILE_OPS = 10
MAX_CONCURRENT_LOG_READS = 20
MAX_CONCURRENT_DDS_READS = 50


async def scan_mods_archived_async() -> str:
    """
    DEPRECATED: Use ScanGameCore.scan_mods_archived() instead.

    This function is maintained for backwards compatibility only.
    """
    core = ScanGameCore()
    return await core.scan_mods_archived()


async def check_log_errors_async(folder_path: Path | str) -> str:
    """
    DEPRECATED: Use ScanGameCore.check_log_errors() instead.

    This function is maintained for backwards compatibility only.
    """
    core = ScanGameCore()
    return await core.check_log_errors(folder_path)


# Wrapper functions to run async functions from synchronous code
def run_async(coro: asyncio.Future | asyncio.Task) -> Any:
    """Helper to run async function from sync code."""
    try:
        # Try to get existing event loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, create new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    else:
        # We're already in an async context
        return asyncio.create_task(coro)


# Synchronous wrapper functions for backwards compatibility
def scan_mods_archived_async_wrapper() -> str:
    """
    DEPRECATED: Use CLASSIC_ScanGame.scan_mods_archived() instead.

    Synchronous wrapper maintained for backwards compatibility only.
    """
    return run_async(scan_mods_archived_async())


def check_log_errors_async_wrapper(folder_path: Path | str) -> str:
    """
    DEPRECATED: Use CLASSIC_ScanGame.check_log_errors() instead.

    Synchronous wrapper maintained for backwards compatibility only.
    """
    return run_async(check_log_errors_async(folder_path))


async def scan_mods_unpacked_async() -> str:
    """
    DEPRECATED: Use ScanGameCore.scan_mods_unpacked() instead.

    This function is maintained for backwards compatibility only.
    """
    core = ScanGameCore()
    return await core.scan_mods_unpacked()


def scan_mods_unpacked_async_wrapper() -> str:
    """
    DEPRECATED: Use CLASSIC_ScanGame.scan_mods_unpacked() instead.

    Synchronous wrapper maintained for backwards compatibility only.
    """
    return run_async(scan_mods_unpacked_async())
