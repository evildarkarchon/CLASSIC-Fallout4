"""
Efficient bridge between synchronous and asynchronous code.

This module provides a high-performance bridge for running async code from sync contexts
without the overhead of creating new event loops for each operation.

IMPORTANT: This module supports two design phases:

Phase 1: Direct AsyncBridge Usage (STABLE - Recommended for GUI contexts)
-------------------------------------------------------------------------
Use AsyncBridge directly for synchronous GUI code that needs to call async functions.

Basic Usage:
    from ClassicLib.AsyncBridge import AsyncBridge, run_async

    # Method 1: Get instance and use directly
    bridge = AsyncBridge.get_instance()
    result = bridge.run_async(async_function())

    # Method 2: Convenience function
    result = run_async(async_function())

    # Method 3: Context manager for explicit lifecycle
    with AsyncBridge.get_instance() as bridge:
        result = bridge.run_async(async_function())

    # With timeout support
    result = bridge.run_async_with_timeout(async_function(), timeout=5.0)

Metrics Collection:
    def metrics_handler(event: str, metrics: dict):
        print(f"{event}: duration={metrics['duration']}, success={metrics['success']}")

    AsyncBridge.set_metrics_callback(metrics_handler)

Phase 2: Context-Aware Wrappers (EXPERIMENTAL - Migration in progress)
-----------------------------------------------------------------------
Provides utilities that automatically adapt to GUI vs CLI/TUI modes. Use for transitional
code during migration from synchronous to async patterns.

Context-Aware Decorator:
    from ClassicLib.AsyncBridge import context_aware_sync

    @context_aware_sync
    async def my_async_function():
        # Implementation
        pass

    # In GUI mode: my_async_function() returns sync result via AsyncBridge
    # In CLI/TUI mode: my_async_function() returns coroutine, use await

Explicit GUI-Only Sync Wrapper:
    from ClassicLib.AsyncBridge import create_sync_wrapper

    class MyClass:
        async def process_data(self):
            # Implementation
            pass

        # GUI workers ONLY - errors in CLI/TUI mode
        process_data_sync = create_sync_wrapper(process_data)

Mode Detection:
    from ClassicLib import GlobalRegistry

    if GlobalRegistry.is_gui_mode():
        # GUI mode - use sync wrappers
        result = obj.method_sync()
    else:
        # CLI/TUI mode - use native async
        result = await obj.method()

When to Use What:
    - AsyncBridge.run_async(): GUI workers, QThread contexts (STABLE)
    - Native await: CLI, TUI, all internal async code (PREFERRED)
    - @context_aware_sync: Transitional code during migration (EXPERIMENTAL)
    - create_sync_wrapper(): Explicit GUI-only sync methods (EXPERIMENTAL)

See Also:
    - docs/ASYNC_BRIDGE_ELIMINATION_PLAN.md - Migration strategy
    - docs/testing_async_bridge.md - Testing guide
"""

import asyncio
import atexit
import logging
import sys
import threading
import time
from collections.abc import Callable, Coroutine
from concurrent.futures import TimeoutError as FutureTimeoutError
from functools import wraps
from typing import Any, ClassVar, TypeVar

from ClassicLib import GlobalRegistry

# Module exports
__all__ = [
    # Main class
    "AsyncBridge",
    # Convenience functions
    "run_async",
    "run_async_with_timeout",
    # Phase 2: Context-aware wrappers
    "context_aware_sync",
    "smart_await",
    "create_sync_wrapper",
]

# Configure module logger
logger = logging.getLogger(__name__)

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
    _metrics_callback: ClassVar[Callable[[str, dict[str, Any]], None] | None] = None
    _thread_local: ClassVar[threading.local] = threading.local()

    def __init__(self) -> None:
        """Initialize the async bridge for the current thread."""
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._thread_id = threading.get_ident()
        self._creation_time = time.time()
        self._shutdown = False
        logger.debug(f"AsyncBridge initialized for thread {self._thread_id}")

    @classmethod
    def get_instance(cls) -> "AsyncBridge":
        """
        Get or create the AsyncBridge instance for the current thread.

        Uses thread-local caching for fast access without locks in the common case.

        Returns:
            AsyncBridge: Thread-local bridge instance
        """
        # Fast path - check thread-local cache (no lock needed)
        try:
            instance = cls._thread_local.instance
            if not instance._shutdown:
                logger.debug(f"AsyncBridge: Using cached instance for thread {threading.get_ident()}")
                return instance
            # Instance is shutdown - fall through to create new one
            logger.debug(f"AsyncBridge: Cached instance is shutdown for thread {threading.get_ident()}")
        except AttributeError:
            # No instance in thread-local yet
            logger.debug(f"AsyncBridge: No cached instance for thread {threading.get_ident()}")

        thread_id = threading.get_ident()

        # Check if instance exists and handle shutdown instances
        if thread_id in cls._instances:
            with cls._lock:
                # Recheck with lock - handle shutdown instances
                if thread_id in cls._instances:
                    instance = cls._instances[thread_id]
                    if not instance._shutdown:
                        # Cache in thread-local for fast access
                        cls._thread_local.instance = instance
                        return instance
                    # Instance is shutdown - remove and recreate
                    logger.debug(f"AsyncBridge: Removing shutdown instance for thread {thread_id}")
                    del cls._instances[thread_id]

        # Slow path - create new instance under lock
        with cls._lock:
            # Double-check - another thread might have created it
            if thread_id in cls._instances:
                instance = cls._instances[thread_id]
                if not instance._shutdown:
                    cls._thread_local.instance = instance
                    return instance

            # Create new instance
            logger.debug(f"AsyncBridge: Creating new instance for thread {thread_id}")
            instance = cls()
            cls._instances[thread_id] = instance

            # Register cleanup on first instance
            if not cls._cleanup_registered:
                atexit.register(cls._cleanup_all)
                cls._cleanup_registered = True

            # Cache in thread-local
            cls._thread_local.instance = instance

            return instance

    def ensure_loop(self) -> None:
        """
        Ensure an event loop is running for this thread.

        Creates a new event loop and runs it in a background thread if needed.

        Raises:
            RuntimeError: If the loop fails to start within 5 seconds or if
                         the background thread died
        """
        # Check if we have a healthy loop
        if self._loop is not None and not self._loop.is_closed() and self._loop.is_running():
            # Verify thread is still alive
            if self._thread and self._thread.is_alive():
                logger.debug(f"AsyncBridge: Loop already running for thread {self._thread_id}")
                return

            # Thread died - clean up the dead loop
            logger.warning(f"AsyncBridge: Background thread died for thread {self._thread_id}, recreating")
            try:
                self._loop.close()
            except (RuntimeError, OSError, AttributeError) as e:
                logger.debug(f"AsyncBridge: Error closing dead loop: {e}")
            self._loop = None
            self._thread = None

        # Create new event loop for background thread
        self._loop = asyncio.new_event_loop()

        # Create event for thread synchronization
        ready_event = threading.Event()

        # Start background thread FIRST (before any operations on the loop)
        # Pass ready_event so thread can signal when it's ready
        thread_name = f"AsyncBridge-{self._thread_id}-{self._creation_time:.0f}"
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(ready_event,),  # Pass ready_event as argument
            daemon=True,
            name=thread_name
        )
        self._thread.start()
        logger.debug(f"AsyncBridge: Started background thread {thread_name}")

        # Wait with timeout for thread to signal it's ready
        # Thread signals AFTER set_event_loop() but BEFORE run_forever()
        if not ready_event.wait(timeout=5.0):
            logger.error(f"AsyncBridge: Loop failed to start within 5 seconds for thread {self._thread_id}")
            raise RuntimeError(f"AsyncBridge event loop failed to start within 5 seconds for thread {self._thread_id}")

        logger.debug(f"AsyncBridge: Loop confirmed running for thread {self._thread_id}")

    def _run_loop(self, ready_event: threading.Event) -> None:
        """Run the event loop in the background thread.

        This method runs in a dedicated background thread and manages the event loop lifecycle.
        It signals when the loop is ready to accept work, then runs until shutdown.

        Args:
            ready_event: Threading event to signal when loop is ready for operations
        """
        if self._loop is None:
            return  # Should never happen, but satisfies type checker

        # Set this loop as the event loop for this thread
        asyncio.set_event_loop(self._loop)

        # Signal that we're ready AFTER set_event_loop() but BEFORE run_forever()
        # This ensures the loop is properly initialized before any operations are scheduled
        ready_event.set()
        logger.debug(f"AsyncBridge: Event loop ready for thread {self._thread_id}")

        try:
            # Run the event loop until shutdown() is called
            self._loop.run_forever()
        finally:
            # Cleanup pending tasks to ensure futures don't hang
            try:
                pending = asyncio.all_tasks(self._loop)
                if pending:
                    logger.warning(
                        f"AsyncBridge: {len(pending)} tasks still pending during shutdown for thread {self._thread_id}. "
                        "Cancelling them to ensure cleanup."
                    )
                    for task in pending:
                        task.cancel()

                    # Allow cancellation to propagate with timeout
                    # This ensures that futures returned by run_coroutine_threadsafe are properly notified
                    async def wait_for_cancellation() -> None:
                        await asyncio.gather(*pending, return_exceptions=True)

                    try:
                        # Run loop briefly to process cancellations
                        # 0.2s is enough to let CancelledError propagate to futures
                        # We don't need to wait for full task cleanup if it's stuck
                        self._loop.run_until_complete(asyncio.wait_for(wait_for_cancellation(), timeout=0.2))
                    except asyncio.TimeoutError:
                        logger.warning(f"AsyncBridge: Timeout (0.2s) waiting for tasks to cancel for thread {self._thread_id}")
                    except Exception as e:
                        logger.error(f"AsyncBridge: Error during task cancellation: {e}")
            except (RuntimeError, AttributeError) as e:
                logger.debug(f"AsyncBridge: Error handling pending tasks for thread {self._thread_id}: {e}")

            # Close the loop
            try:
                self._loop.close()
            except (RuntimeError, OSError, AttributeError) as e:
                logger.debug(f"AsyncBridge: Error closing loop for thread {self._thread_id}: {e}")

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
        start_time = time.perf_counter()
        success = False
        error_type: str | None = None

        # Check if we're already in an async context
        def _raise_async_context_error() -> None:
            """Raise error when called from async context.

            Raises:
                RuntimeError: Always raised to indicate misuse of run_async() from async context.
            """
            raise RuntimeError(
                "Cannot use AsyncBridge.run_async() from within an async context. "
                "Use 'await' directly instead.\n"
                f"Called from thread: {threading.current_thread().name}"
            ) from None

        try:
            asyncio.get_running_loop()
            # If we got here, we're in an async context - this is an error
            _raise_async_context_error()
        except RuntimeError as e:
            # Check if this is our error or asyncio's "no running loop" error
            if "Cannot use AsyncBridge" in str(e):
                raise
            # asyncio.get_running_loop() raised - we're not in async context (good)
            logger.debug(f"AsyncBridge: run_async called from sync context (thread: {threading.current_thread().name})")

        try:
            # Ensure we have a running loop
            self.ensure_loop()

            # Submit the coroutine to the loop
            assert self._loop is not None, "Event loop should be available after ensure_loop()"
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)

            # Wait for and return the result
            result = future.result()
            success = True

        except Exception as e:
            error_type = type(e).__name__
            logger.debug(f"AsyncBridge: run_async failed with {error_type}: {e}")
            raise
        else:
            return result

        finally:
            # Record metrics if callback is configured
            if AsyncBridge._metrics_callback:
                duration = time.perf_counter() - start_time
                AsyncBridge._metrics_callback(
                    "async_bridge_run",
                    {
                        "duration": duration,
                        "success": success,
                        "error_type": error_type,
                        "thread_id": self._thread_id,
                    },
                )

    def run_async_with_timeout(self, coro: Coroutine[Any, Any, T], timeout: float) -> T:
        """
        Run an async coroutine with a timeout.

        Implements defense-in-depth by applying timeout at both the asyncio level
        (asyncio.wait_for) and the future level (future.result).

        Args:
            coro: The coroutine to run
            timeout: Maximum time to wait in seconds

        Returns:
            The result of the coroutine

        Raises:
            TimeoutError: If the coroutine doesn't complete within the timeout
        """
        start_time = time.perf_counter()
        success = False
        error_type: str | None = None

        try:
            # Ensure we have a running loop
            self.ensure_loop()

            # Wrap the coroutine with a timeout
            async def with_timeout() -> T:
                return await asyncio.wait_for(coro, timeout)

            # Submit and wait with timeout on the future too
            assert self._loop is not None, "Event loop should be available after ensure_loop()"
            future = asyncio.run_coroutine_threadsafe(with_timeout(), self._loop)

            try:
                # Add timeout to future.result() as well (defense in depth)
                # Use slightly longer timeout to let asyncio.wait_for trigger first
                result = future.result(timeout=timeout + 1.0)
                success = True
            except FutureTimeoutError as e:
                # Future timed out - this shouldn't happen if asyncio.wait_for works
                # but provides defense in depth
                error_type = "FutureTimeoutError"
                logger.error(f"AsyncBridge: Future timeout after {timeout} seconds (thread: {self._thread_id})")
                raise TimeoutError(f"Operation timed out after {timeout} seconds (future level)") from e
            else:
                return result
        except TimeoutError as e:
            # Asyncio wait_for timeout (expected path)
            error_type = "AsyncioTimeoutError"
            logger.debug(f"AsyncBridge: Asyncio timeout after {timeout} seconds (thread: {self._thread_id})")
            raise TimeoutError(f"Operation timed out after {timeout} seconds") from e

        except Exception as e:
            error_type = type(e).__name__
            logger.debug(f"AsyncBridge: run_async_with_timeout failed with {error_type}: {e}")
            raise

        finally:
            # Record metrics if callback is configured
            if AsyncBridge._metrics_callback:
                duration = time.perf_counter() - start_time
                AsyncBridge._metrics_callback(
                    "async_bridge_run_with_timeout",
                    {
                        "duration": duration,
                        "timeout": timeout,
                        "success": success,
                        "error_type": error_type,
                        "thread_id": self._thread_id,
                    },
                )

    def shutdown(self) -> None:
        """
        Shutdown the event loop for this thread.

        This is called automatically on program exit but can be called
        manually if needed.

        Implements progressive shutdown:
        1. Stop the event loop gracefully
        2. Wait for thread to exit (2 second timeout)
        3. Force close the loop if thread doesn't stop
        """
        if self._shutdown:
            logger.debug(f"AsyncBridge: Already shutdown for thread {self._thread_id}")
            return

        logger.debug(f"AsyncBridge: Shutting down for thread {self._thread_id}")
        self._shutdown = True

        if self._loop and self._loop.is_running():
            # Schedule loop stop
            self._loop.call_soon_threadsafe(self._loop.stop)
            logger.debug(f"AsyncBridge: Scheduled loop stop for thread {self._thread_id}")

            # Wait for thread to finish - 2s timeout for cleanup
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)

                if self._thread.is_alive():
                    # Thread didn't stop - log warning and force close
                    print(
                        f"Warning: AsyncBridge thread {self._thread_id} did not stop within timeout. Forcing loop close.",
                        file=sys.stderr,
                    )
                    logger.warning(f"AsyncBridge: Thread {self._thread_id} did not stop, forcing close")

                    # Try to forcefully close the loop
                    try:
                        if self._loop and not self._loop.is_closed():
                            # Close from the current thread (risky but better than leak)
                            self._loop.close()
                            logger.debug(f"AsyncBridge: Forcefully closed loop for thread {self._thread_id}")
                    except (RuntimeError, OSError, AttributeError) as e:
                        print(f"Error forcing loop close: {e}", file=sys.stderr)
                        logger.error(f"AsyncBridge: Error forcing loop close for thread {self._thread_id}: {e}")
                else:
                    logger.debug(f"AsyncBridge: Thread {self._thread_id} stopped gracefully")

    def __enter__(self) -> "AsyncBridge":
        """
        Context manager entry - ensures loop is running.

        Usage:
            with AsyncBridge.get_instance() as bridge:
                result = bridge.run_async(my_async_func())

        Returns:
            AsyncBridge: The current bridge instance with an active event loop
        """
        self.ensure_loop()
        logger.debug(f"AsyncBridge: Entered context for thread {self._thread_id}")
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Context manager exit - shutdown loop."""
        logger.debug(f"AsyncBridge: Exiting context for thread {self._thread_id}")
        self.shutdown()

    @classmethod
    def set_metrics_callback(cls, callback: Callable[[str, dict[str, Any]], None] | None) -> None:
        """
        Set a callback for metrics collection.

        The callback will be invoked after each async operation with:
        - event_name: str - Name of the operation ("async_bridge_run", "async_bridge_run_with_timeout")
        - metrics: dict - Metrics dictionary with keys like:
            - duration: float - Operation duration in seconds
            - success: bool - Whether operation succeeded
            - error_type: str | None - Type of error if failed
            - timeout: float - Timeout value (for timeout operations)
            - thread_id: int - Thread ID where operation ran

        Args:
            callback: Function to call with metrics, or None to disable

        Usage:
            def my_metrics_handler(event: str, metrics: dict):
                print(f"{event}: {metrics}")

            AsyncBridge.set_metrics_callback(my_metrics_handler)
        """
        cls._metrics_callback = callback
        logger.debug(f"AsyncBridge: Metrics callback {'enabled' if callback else 'disabled'}")

    @classmethod
    def _cleanup_all(cls) -> None:
        """
        Cleanup all event loops on program exit.

        Attempts to shutdown all AsyncBridge instances gracefully, logging
        any errors encountered during cleanup for diagnostics.
        """
        logger.debug(f"AsyncBridge: Cleaning up {len(cls._instances)} instances")
        with cls._lock:
            for thread_id, instance in cls._instances.items():
                try:
                    instance.shutdown()
                    logger.debug(f"AsyncBridge: Successfully cleaned up instance for thread {thread_id}")
                except (RuntimeError, OSError, AttributeError, ValueError) as e:
                    # Log the error but continue cleanup - must not fail during atexit
                    # Note: Using print since MessageHandler may be shut down
                    print(
                        f"Warning: AsyncBridge cleanup failed for thread {thread_id}: {e}",
                        file=sys.stderr,
                    )
                    logger.error(f"AsyncBridge: Cleanup failed for thread {thread_id}: {e}")
            cls._instances.clear()
            logger.debug("AsyncBridge: Cleanup complete")


# Convenience functions
def run_async[T](coro: Coroutine[Any, Any, T]) -> T:
    """
    Convenience function to run async code from sync context.

    Args:
        coro: The coroutine to run

    Returns:
        The result of the coroutine

    Usage:
        result = run_async(my_async_func())
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

    Usage:
        result = run_async_with_timeout(my_async_func(), 5.0)
    """
    bridge = AsyncBridge.get_instance()
    return bridge.run_async_with_timeout(coro, timeout)


# Phase 2: Context-Aware Wrappers
# ================================


def context_aware_sync[T](async_func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T | Coroutine[Any, Any, T]]:
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
        """Context-aware wrapper that checks mode at runtime.

        Returns:
            T | Coroutine[Any, Any, T]: In GUI mode, returns the sync result of type T.
                In CLI/TUI mode, returns a coroutine that must be awaited.
        """
        coro = async_func(*args, **kwargs)

        # Check mode at CALL time for maximum flexibility
        if GlobalRegistry.is_gui_mode():
            # GUI mode - run synchronously via AsyncBridge
            bridge = AsyncBridge.get_instance()
            # Type checker can't understand runtime mode branching - we return T here
            return bridge.run_async(coro)  # type: ignore[return-value]  # Runtime mode check determines return type

        # CLI/TUI mode - return coroutine for await
        # Type checker can't understand runtime mode branching - we return Coroutine here
        return coro  # type: ignore[return-value]  # Runtime mode check determines return type

    # Type checker can't validate runtime-dependent return type
    return wrapper  # type: ignore[return-value]  # Wrapper return type depends on runtime mode


def smart_await[T](coro: Coroutine[Any, Any, T]) -> T:
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
    if GlobalRegistry.is_gui_mode():
        bridge = AsyncBridge.get_instance()
        return bridge.run_async(coro)

    raise RuntimeError(
        "Cannot use smart_await() in CLI/TUI mode. Use native 'await' instead.\n"
        "This error indicates code that should be using async patterns but is using sync wrappers."
    )


def create_sync_wrapper[T](async_func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    """
    Create a sync wrapper for an async function with context-aware execution.

    This wrapper automatically chooses the appropriate async execution method:
    - GUI mode: Uses AsyncBridge (Qt event loop integration)
    - CLI/TUI mode: Uses asyncio.run() (creates new event loop per call)

    IMPORTANT - Appropriate Usage:
    ✅ GUI workers (Qt threads, PySide6 slots)
    ✅ Testing and benchmarking isolated async functions
    ✅ One-off operations in sync contexts (initialization, cleanup)

    ❌ DO NOT USE in production CLI main flow
    ❌ DO NOT USE when already in async context
    ❌ DO NOT USE for repeated operations in CLI (inefficient)

    Best Practices:
    - Production CLI code should be async-first (use asyncio.run() once at entry point)
    - See CLASSIC_ScanLogs.py for reference async-first CLI pattern
    - In CLI, call async methods directly with await instead of using wrappers
    - Sync wrappers are primarily for GUI thread safety and testing purposes

    Usage:
        # Example 1: GUI worker (CORRECT)
        class CrashLogsScanWorker(QThread):
            def _perform_scan(self):
                sync_scan = create_sync_wrapper(async_scan_function)
                result = sync_scan()  # Uses AsyncBridge in GUI mode

        # Example 2: Testing (CORRECT)
        def test_async_function():
            sync_wrapper = create_sync_wrapper(async_function)
            result = sync_wrapper()  # Uses asyncio.run() in CLI mode

        # Example 3: CLI production (INCORRECT - don't do this)
        def main():
            sync_wrapper = create_sync_wrapper(async_function)
            result = sync_wrapper()  # Creates new event loop per call!

        # Example 4: CLI production (CORRECT - do this instead)
        async def main():
            result = await async_function()  # Direct async, one event loop

        if __name__ == "__main__":
            asyncio.run(main())  # Single event loop at entry point

    Args:
        async_func: The async function to wrap

    Returns:
        A sync wrapper that works in both GUI and CLI modes

    Note:
        The CLI/TUI mode asyncio.run() fallback is intentional for testing
        and benchmarking. Production CLI code should not rely on this pattern.
    """
    import asyncio

    @wraps(async_func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        coro = async_func(*args, **kwargs)

        if GlobalRegistry.is_gui_mode():
            # GUI mode: Use AsyncBridge for Qt event loop integration
            bridge = AsyncBridge.get_instance()
            return bridge.run_async(coro)
        # CLI/TUI mode: Use standard asyncio.run()
        return asyncio.run(coro)

    return wrapper
