"""Runtime boundary helpers for sync/async execution.

This module centralizes execution rules for code that must bridge between
sync and async contexts:
- ``run_sync``: sync caller on main thread, delegates to AsyncBridge
- ``run_worker_thread``: sync caller in worker thread, uses ``asyncio.run``

Both helpers reject usage from an already-running async context.
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

from ClassicLib.core.async_bridge import AsyncBridge

T = TypeVar("T")


def _ensure_sync_context(coro: Coroutine[Any, Any, T], caller: str) -> None:
    """Validate helper usage from a synchronous context only.

    Args:
        coro: The coroutine passed by the caller.
        caller: Helper name for diagnostics.

    Raises:
        RuntimeError: If called from an async context.

    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return

    # Prevent unawaited coroutine warnings when rejecting usage.
    coro.close()
    raise RuntimeError(f"Cannot call {caller} from an async context. Use 'await' directly.")


def run_sync(coro: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine from synchronous main-thread code via AsyncBridge.

    Args:
        coro: Coroutine to execute.

    Returns:
        The coroutine result.

    """
    _ensure_sync_context(coro, "run_sync")
    return AsyncBridge.get_instance().run_async(coro)


def run_worker_thread(coro: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine from synchronous worker-thread code via ``asyncio.run``.

    Args:
        coro: Coroutine to execute.

    Returns:
        The coroutine result.

    """
    _ensure_sync_context(coro, "run_worker_thread")
    return asyncio.run(coro)
