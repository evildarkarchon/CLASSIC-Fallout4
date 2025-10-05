"""
Efficient bridge between synchronous and asynchronous code.

This module provides a high-performance bridge for running async code from sync contexts
without the overhead of creating new event loops for each operation.

Phase 2: Context-Aware Wrappers
--------------------------------
Provides utilities for automatically using AsyncBridge only when needed (GUI mode).
In CLI/TUI modes, code should use native async patterns instead.

Basic Usage (Phase 1 - Still Supported):
    from ClassicLib.AsyncBridge import AsyncBridge, run_async

    # Manual bridge usage
    bridge = AsyncBridge.get_instance()
    result = bridge.run_async(async_function())

    # Convenience function
    result = run_async(async_function())

Context-Aware Usage (Phase 2 - Recommended):
    from ClassicLib.AsyncBridge import context_aware_sync, create_sync_wrapper

    # Decorator pattern - automatically adapts to mode
    @context_aware_sync
    async def my_async_function():
        # Implementation
        pass

    # In GUI mode: my_async_function() returns sync result
    # In CLI/TUI mode: my_async_function() is still async, use await

    # Explicit sync wrapper for GUI-only methods
    class MyClass:
        async def process_data(self):
            # Implementation
            pass

        # GUI workers should use this
        process_data_sync = create_sync_wrapper(process_data)

Migration Pattern Examples:
    # BEFORE (Phase 1): Always uses AsyncBridge
    def sync_method(self):
        return run_async(self.async_method())

    # AFTER Option A (Phase 2): Context-aware decorator
    @context_aware_sync
    async def method(self):
        # Implementation
        pass

    # AFTER Option B (Phase 2): Explicit GUI-only wrapper
    class MyClass:
        async def method(self):
            # Implementation
            pass

        # For GUI workers ONLY
        method_sync = create_sync_wrapper(method)

Mode Detection:
    from ClassicLib.AsyncBridge import is_gui_mode, should_use_async_bridge

    if should_use_async_bridge():
        # GUI mode - use sync wrappers
        result = obj.method_sync()
    else:
        # CLI/TUI mode - use native async
        result = await obj.method()

When to Use What:
    - AsyncBridge.run_async(): GUI workers, QThread contexts
    - @context_aware_sync: Transitional code during migration
    - create_sync_wrapper(): Explicit GUI-only sync methods
    - Native await: CLI, TUI, all internal async code (PREFERRED)

See Also:
    - docs/ASYNC_BRIDGE_ELIMINATION_PLAN.md - Migration strategy
    - docs/testing_async_bridge.md - Testing guide
"""

import asyncio
import atexit
import threading
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, ClassVar, TypeVar

T = TypeVar("T")


# noinspection PyTypeChecker
class AsyncBridge:
    """
    High-performance bridge between sync and async code using persistent thread-local event loops.

    This class maintains a single event loop per thread, avoiding the expensive overhead
    of creating and destroying event loops for each sync-to-async call.

    Testing Note:
    -------------
    When testing code that uses AsyncBridge, mock the bridge's run_async method,
    NOT the underlying async functions. This avoids RuntimeWarning about unawaited coroutines.

    Example for testing:
    ```python
    from unittest.mock import MagicMock, patch

    with patch("module.AsyncBridge") as mock_bridge_class:
        mock_bridge = MagicMock()
        mock_bridge_class.get_instance.return_value = mock_bridge
        mock_bridge.run_async.return_value = "expected_result"

        # Now test your sync wrapper that uses AsyncBridge
        result = your_sync_function()
        assert result == "expected_result"
    ```

    For comprehensive testing guidance, see: docs/testing_async_bridge.md
    """

    # Class-level storage for thread-local instances
    _instances: ClassVar[dict[int, "AsyncBridge"]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()
    _cleanup_registered: ClassVar[bool] = False

    def __init__(self) -> None:
        """Initialize the async bridge for the current thread."""
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._thread_id = threading.get_ident()
        self._shutdown = False

    @classmethod
    def get_instance(cls) -> "AsyncBridge":
        """
        Get or create the AsyncBridge instance for the current thread.

        Returns:
            AsyncBridge: Thread-local bridge instance
        """
        thread_id = threading.get_ident()

        # Fast path - instance already exists
        if thread_id in cls._instances:
            instance = cls._instances[thread_id]
            if not instance._shutdown:
                return instance

        # Slow path - need to create new instance
        with cls._lock:
            # Double-check pattern
            if thread_id in cls._instances:
                instance = cls._instances[thread_id]
                if not instance._shutdown:
                    return instance

            # Create new instance
            instance = cls()
            cls._instances[thread_id] = instance

            # Register cleanup on first instance
            if not cls._cleanup_registered:
                atexit.register(cls._cleanup_all)
                cls._cleanup_registered = True

            return instance

    def ensure_loop(self) -> None:
        """
        Ensure an event loop is running for this thread.

        Creates a new event loop and runs it in a background thread if needed.
        """
        if self._loop is not None and not self._loop.is_closed():
            return

        # Create new event loop
        self._loop = asyncio.new_event_loop()

        # Start the loop in a background thread
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name=f"AsyncBridge-{self._thread_id}")
        self._thread.start()

        # Wait for loop to be ready
        while self._loop and not self._loop.is_running():
            threading.Event().wait(0.001)

    def _run_loop(self) -> None:
        """Run the event loop in the background thread."""
        if self._loop is None:
            return  # Should never happen, but satisfies type checker

        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()

    def run_async(self, coro: Coroutine[Any, Any, T]) -> T:
        """
        Run an async coroutine from a sync context.

        Args:
            coro: The coroutine to run

        Returns:
            The result of the coroutine

        Raises:
            RuntimeError: If called from within an async context
        """
        # Check if we're already in an async context
        try:
            asyncio.get_running_loop()
            # We're in an async context, this shouldn't happen
            raise RuntimeError(  # noqa: TRY301
                "Cannot use AsyncBridge.run_async() from within an async context. Use 'await' directly instead."
            )
        except RuntimeError:
            # Good, we're not in an async context
            pass

        # Ensure we have a running loop
        self.ensure_loop()

        # Submit the coroutine to the loop
        assert self._loop is not None, "Event loop should be available after ensure_loop()"
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)

        # Wait for and return the result
        return future.result()

    def run_async_with_timeout(self, coro: Coroutine[Any, Any, T], timeout: float) -> T:
        """
        Run an async coroutine with a timeout.

        Args:
            coro: The coroutine to run
            timeout: Maximum time to wait in seconds

        Returns:
            The result of the coroutine

        Raises:
            TimeoutError: If the coroutine doesn't complete within the timeout
        """
        # Ensure we have a running loop
        self.ensure_loop()

        # Wrap the coroutine with a timeout
        async def with_timeout() -> T:
            return await asyncio.wait_for(coro, timeout)

        # Submit and wait
        assert self._loop is not None, "Event loop should be available after ensure_loop()"
        future = asyncio.run_coroutine_threadsafe(with_timeout(), self._loop)
        return future.result()

    def shutdown(self) -> None:
        """
        Shutdown the event loop for this thread.

        This is called automatically on program exit but can be called
        manually if needed.
        """
        if self._shutdown:
            return

        self._shutdown = True

        if self._loop and self._loop.is_running():
            # Schedule loop stop
            self._loop.call_soon_threadsafe(self._loop.stop)

            # Wait for thread to finish
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.0)

    @classmethod
    def _cleanup_all(cls) -> None:
        """Cleanup all event loops on program exit."""
        with cls._lock:
            for instance in cls._instances.values():
                # noinspection PyBroadException
                try:  # noqa: SIM105
                    instance.shutdown()
                except Exception:  # noqa: BLE001
                    # Ignore errors during cleanup
                    pass
            cls._instances.clear()


# Convenience functions
def run_async[T](coro: Coroutine[Any, Any, T]) -> T:
    """
    Convenience function to run async code from sync context.

    Args:
        coro: The coroutine to run

    Returns:
        The result of the coroutine
    """
    bridge = AsyncBridge.get_instance()
    return bridge.run_async(coro)


def run_async_with_timeout[T](coro: Coroutine[Any, Any, T], timeout: float) -> T:
    """
    Convenience function to run async code with timeout.

    Args:
        coro: The coroutine to run
        timeout: Maximum time to wait in seconds

    Returns:
        The result of the coroutine

    Raises:
        TimeoutError: If the coroutine doesn't complete within the timeout
    """
    bridge = AsyncBridge.get_instance()
    return bridge.run_async_with_timeout(coro, timeout)


# Phase 2: Context-Aware Wrappers
# ================================


def is_gui_mode() -> bool:
    """
    Check if application is running in GUI mode.

    Returns:
        True if in GUI mode (needs AsyncBridge), False otherwise (use native async)

    Note:
        Import here to avoid circular dependency with GlobalRegistry
    """
    from ClassicLib import GlobalRegistry

    return GlobalRegistry.is_gui_mode()


def should_use_async_bridge() -> bool:
    """
    Determine if AsyncBridge should be used in current context.

    Returns:
        True if AsyncBridge should be used (GUI mode), False if native async should be used (CLI/TUI mode)
    """
    return is_gui_mode()


def context_aware_sync(async_func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T | Coroutine[Any, Any, T]]:
    """
    Decorator that makes an async function context-aware.

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
        """Context-aware wrapper that checks mode at runtime."""
        coro = async_func(*args, **kwargs)

        # Check mode at CALL time for maximum flexibility
        if should_use_async_bridge():
            # GUI mode - run synchronously via AsyncBridge
            bridge = AsyncBridge.get_instance()
            return bridge.run_async(coro)  # type: ignore[return-value]

        # CLI/TUI mode - return coroutine for await
        return coro  # type: ignore[return-value]

    return wrapper  # type: ignore[return-value]


def smart_await(coro: Coroutine[Any, Any, T]) -> T:
    """
    Smart await that automatically chooses between AsyncBridge and native await.

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
    if should_use_async_bridge():
        bridge = AsyncBridge.get_instance()
        return bridge.run_async(coro)

    raise RuntimeError(
        "Cannot use smart_await() in CLI/TUI mode. Use native 'await' instead.\n"
        "This error indicates code that should be using async patterns but is using sync wrappers."
    )


def create_sync_wrapper(async_func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    """
    Create a sync wrapper for an async function that errors in non-GUI mode.

    This is useful for creating explicit sync methods that should ONLY be used by GUI code.

    Usage:
        class MyClass:
            async def my_async_method(self):
                # Implementation
                pass

            # Sync wrapper for GUI ONLY
            my_sync_method = create_sync_wrapper(my_async_method)

    Args:
        async_func: The async function to wrap

    Returns:
        A sync wrapper that errors in non-GUI mode

    Raises:
        RuntimeError: If called in CLI/TUI mode
    """

    @wraps(async_func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        if not should_use_async_bridge():
            func_name = getattr(async_func, "__name__", "function")
            raise RuntimeError(
                f"Cannot use sync wrapper '{func_name}' in CLI/TUI mode.\n"
                f"Use the async version with 'await' instead."
            )

        coro = async_func(*args, **kwargs)
        bridge = AsyncBridge.get_instance()
        return bridge.run_async(coro)

    return wrapper
