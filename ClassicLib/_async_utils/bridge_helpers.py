"""Context-aware async/sync bridge helper functions.

This module provides convenience functions and decorators for bridging between
synchronous and asynchronous code contexts. These utilities automatically adapt
behavior based on whether the application is running in GUI or CLI/TUI mode.

The helpers integrate with AsyncBridge for GUI contexts and support native async
patterns for CLI/TUI contexts.

Note:
    These helpers were extracted from ClassicLib.AsyncBridge to improve modularity.
    Import from ClassicLib.AsyncBridge for backward compatibility.

"""

from __future__ import annotations

import asyncio
from functools import wraps
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from ClassicLib.AsyncBridge import AsyncBridge


def _get_bridge() -> AsyncBridge:
    """Get AsyncBridge instance lazily to avoid circular imports.

    Returns:
        The singleton AsyncBridge instance.

    """
    from ClassicLib.AsyncBridge import AsyncBridge

    return AsyncBridge.get_instance()


def _is_gui_mode() -> bool:
    """Check GUI mode lazily to avoid circular imports.

    Returns:
        True if running in GUI mode, False otherwise.

    """
    from ClassicLib import GlobalRegistry

    return GlobalRegistry.is_gui_mode()


def run_async[T](coro: Coroutine[Any, Any, T]) -> T:
    """Provide convenience wrapper to run async code from sync context.

    Args:
        coro: The coroutine to run

    Returns:
        The result of the coroutine

    Usage:
        result = run_async(my_async_func())

    """
    bridge = _get_bridge()
    return bridge.run_async(coro)


def run_async_with_timeout[T](coro: Coroutine[Any, Any, T], timeout: float) -> T:
    """Provide convenience wrapper to run async code with timeout.

    Args:
        coro: The coroutine to run
        timeout: Maximum time to wait in seconds

    Returns:
        The result of the coroutine

    Raises:
        TimeoutError: If the coroutine doesn't complete within the timeout

    Usage:
        result = run_async_with_timeout(my_async_func(), 5.0)

    """
    bridge = _get_bridge()
    return bridge.run_async_with_timeout(coro, timeout)


# Phase 2: Context-Aware Wrappers
# ================================


def context_aware_sync[T](async_func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T | Coroutine[Any, Any, T]]:
    """Decorate to makes an async function context-aware.

    In GUI mode: Returns sync result via AsyncBridge
    In CLI/TUI mode: Returns coroutine for await

    Note: Mode is checked at CALL time, not decoration time, allowing runtime mode changes.

    Usage:
        @context_aware_sync
        async def my_function(arg1, arg2):
            # Implementation
            pass

        # In GUI mode: my_function() returns sync result via AsyncBridge
        # In CLI/TUI mode: my_function() returns coroutine, use await my_function()

    Args:
        async_func: The async function to wrap

    Returns:
        A wrapper that adapts based on runtime mode

    """

    @wraps(async_func)
    def wrapper(*args: Any, **kwargs: Any) -> T | Coroutine[Any, Any, T]:
        """Context-aware wrapper that checks mode at runtime.

        Returns:
            T | Coroutine[Any, Any, T]: In GUI mode, returns the sync result of type T.
                In CLI/TUI mode, returns a coroutine that must be awaited.

        """
        coro = async_func(*args, **kwargs)

        # Check mode at CALL time for maximum flexibility
        if _is_gui_mode():
            # GUI mode - run synchronously via AsyncBridge
            bridge = _get_bridge()
            # Type checker can't understand runtime mode branching - we return T here
            return bridge.run_async(coro)  # type: ignore[return-value]  # Runtime mode check determines return type

        # CLI/TUI mode - return coroutine for await
        # Type checker can't understand runtime mode branching - we return Coroutine here
        return coro  # type: ignore[return-value]  # Runtime mode check determines return type

    # Type checker can't validate runtime-dependent return type
    return wrapper  # type: ignore[return-value]  # Wrapper return type depends on runtime mode


def smart_await[T](coro: Coroutine[Any, Any, T]) -> T:
    """Smart await that automatically chooses between AsyncBridge and native await.

    In GUI mode: Uses AsyncBridge
    In CLI/TUI mode: Raises error (caller should use native await)

    Usage:
        # Instead of:
        # result = bridge.run_async(my_async_func())

        # Use:
        # result = smart_await(my_async_func())  # Only in GUI mode
        # result = await my_async_func()         # In CLI/TUI mode

    Args:
        coro: The coroutine to execute

    Returns:
        The result of the coroutine

    Raises:
        RuntimeError: If called in CLI/TUI mode (should use native await)

    """
    if _is_gui_mode():
        bridge = _get_bridge()
        return bridge.run_async(coro)

    raise RuntimeError(
        "Cannot use smart_await() in CLI/TUI mode. Use native 'await' instead.\n"
        "This error indicates code that should be using async patterns but is using sync wrappers."
    )


def create_sync_wrapper[T](async_func: Callable[..., Coroutine[Any, Any, T]], strict: bool = False) -> Callable[..., T]:
    """Create a sync wrapper for an async function with context-aware execution.

    This wrapper automatically chooses the appropriate async execution method:
    - GUI mode: Uses AsyncBridge (Qt event loop integration)
    - CLI/TUI mode: Uses asyncio.run() (creates new event loop per call)

    Args:
        async_func: The async function to wrap
        strict: If True, raises RuntimeError in CLI/TUI mode instead of falling back
               to asyncio.run(). Use this for functions that must only be called
               in GUI contexts to prevent performance "footguns".

    Returns:
        A sync wrapper that works in both GUI and CLI modes (unless strict=True)

    Raises:
        RuntimeError: If strict=True and called in CLI/TUI mode.

    """

    @wraps(async_func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        coro = async_func(*args, **kwargs)

        if _is_gui_mode():
            # GUI mode: Use AsyncBridge for Qt event loop integration
            bridge = _get_bridge()
            return bridge.run_async(coro)

        # Strict mode check - prevent inefficient usage in CLI
        if strict:
            raise RuntimeError(
                f"Strict mode: Cannot use sync wrapper for '{async_func.__name__}' in CLI/TUI mode.\n"
                "This function creates a new event loop for every call, which is inefficient.\n"
                "Use 'await' and call the async function directly instead."
            )

        # CLI/TUI mode: Use standard asyncio.run()
        return asyncio.run(coro)

    return wrapper


__all__ = [
    "run_async",
    "run_async_with_timeout",
    "context_aware_sync",
    "smart_await",
    "create_sync_wrapper",
]
