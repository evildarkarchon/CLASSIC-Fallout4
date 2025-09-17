"""
Efficient bridge between synchronous and asynchronous code.

This module provides a high-performance bridge for running async code from sync contexts
without the overhead of creating new event loops for each operation.
"""

import asyncio
import atexit
import threading
from collections.abc import Coroutine
from typing import Any, ClassVar, TypeVar

T = TypeVar("T")


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
