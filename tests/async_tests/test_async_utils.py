"""
Utility functions and decorators for async test resource management.

This module provides utilities to track and manage async resources in tests,
helping to prevent resource leaks and ensure proper cleanup.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import asyncio
import functools
import gc
import weakref
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any, TypeVar

import pytest

from ClassicLib.Logger import logger

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

T = TypeVar("T")


class AsyncResourceTracker:
    """Track async resources to detect leaks."""

    def __init__(self):
        self.resources: set[weakref.ref] = set()
        self.leaked_resources: list[str] = []

    def register(self, resource: Any, name: str = "Unknown") -> None:
        """Register a resource for tracking."""

        def cleanup_callback(ref):
            self.resources.discard(ref)

        ref = weakref.ref(resource, cleanup_callback)
        self.resources.add(ref)
        logger.debug(f"Registered async resource: {name}")

    def check_leaks(self) -> list[str]:
        """Check for leaked resources."""
        leaked = []
        for ref in list(self.resources):
            obj = ref()
            if obj is not None:
                leaked.append(str(obj))
        return leaked

    def clear(self) -> None:
        """Clear all tracked resources."""
        self.resources.clear()
        self.leaked_resources.clear()


# Global tracker instance - used by track_async_resources decorator
# Note: Each test decorated with @track_async_resources gets a clean tracker
# state because the decorator clears it at start and end. For tests needing
# explicit tracker instances, use the resource_tracker fixture instead.
_resource_tracker = AsyncResourceTracker()


@pytest.fixture
def resource_tracker():
    """Provide a fresh AsyncResourceTracker instance per test.

    Use this fixture instead of the global _resource_tracker when you need
    explicit control over the tracker instance or better test isolation.

    Yields:
        AsyncResourceTracker: Fresh tracker instance for the test.
    """
    tracker = AsyncResourceTracker()
    yield tracker
    tracker.clear()


def track_async_resources(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """Decorator to track async resources in a test function."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        # Clear any existing tracked resources
        _resource_tracker.clear()

        try:
            # Run the test
            result = await func(*args, **kwargs)

            # Force garbage collection
            gc.collect()
            await asyncio.sleep(0)  # Allow event loop to process pending cleanups

            # Check for leaks
            leaks = _resource_tracker.check_leaks()
            if leaks:
                logger.warning(f"Potential resource leaks detected in {func.__name__}: {leaks}")

            return result
        finally:
            _resource_tracker.clear()

    return wrapper


@asynccontextmanager
async def async_test_context() -> AsyncIterator[None]:
    """
    Context manager for async tests that ensures proper cleanup.

    Usage:
        async with async_test_context():
            # Your test code here
            pass
    """
    # Store current event loop
    loop = asyncio.get_event_loop()

    # Track initial task count
    initial_tasks = len(asyncio.all_tasks(loop))

    try:
        yield
    finally:
        # Cancel any pending tasks created during the test
        current_tasks = asyncio.all_tasks(loop)
        new_tasks = [task for task in current_tasks if not task.done()]

        if len(new_tasks) > initial_tasks:
            logger.warning(f"Found {len(new_tasks) - initial_tasks} uncompleted tasks")

            # Cancel uncompleted tasks
            for task in new_tasks:
                if not task.done() and task != asyncio.current_task():
                    task.cancel()

            # Wait for cancellations to complete
            await asyncio.gather(*new_tasks, return_exceptions=True)

        # Force garbage collection
        gc.collect()


async def safe_async_cleanup(*resources: Any) -> None:
    """
    Safely cleanup multiple async resources.

    Args:
        *resources: Resources that have a close() or aclose() method
    """
    cleanup_tasks = []

    for resource in resources:
        if resource is None:
            continue

        # Check for async close method
        if hasattr(resource, "aclose"):
            cleanup_tasks.append(resource.aclose())
        elif hasattr(resource, "close"):
            if asyncio.iscoroutinefunction(resource.close):
                cleanup_tasks.append(resource.close())
            else:
                # Sync close - run in executor
                loop = asyncio.get_event_loop()
                cleanup_tasks.append(loop.run_in_executor(None, resource.close))

    if cleanup_tasks:
        # Wait for all cleanups with timeout
        try:
            await asyncio.wait_for(asyncio.gather(*cleanup_tasks, return_exceptions=True), timeout=5.0)
        except TimeoutError:
            logger.error("Timeout during resource cleanup")


class AsyncTestBase:
    """Base class for async test classes with automatic resource management."""

    def setup_method(self) -> None:
        """Setup before each test method."""
        # Clear resource tracker
        _resource_tracker.clear()

        # Store references to track
        self._async_resources: list[Any] = []

    def teardown_method(self) -> None:
        """Cleanup after each test method."""
        # Run async cleanup in new event loop if needed
        if self._async_resources:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(safe_async_cleanup(*self._async_resources))
            finally:
                loop.close()

        # Clear resources
        self._async_resources.clear()
        _resource_tracker.clear()

        # Force garbage collection
        gc.collect()

    def track_resource(self, resource: Any, name: str = "Unknown") -> Any:
        """Track an async resource for automatic cleanup."""
        self._async_resources.append(resource)
        _resource_tracker.register(resource, name)
        return resource


@pytest.fixture
async def async_resource_manager():
    """Pytest fixture for managing async resources in tests."""
    tracker = AsyncResourceTracker()
    resources = []

    def register(resource: Any, name: str = "Unknown") -> Any:
        resources.append(resource)
        tracker.register(resource, name)
        return resource

    # Provide the register function to tests
    yield register

    # Cleanup
    await safe_async_cleanup(*resources)

    # Check for leaks
    leaks = tracker.check_leaks()
    if leaks:
        logger.warning(f"Resource leaks detected: {leaks}")

    tracker.clear()


def ensure_event_loop_cleanup(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """
    Decorator that ensures the event loop is properly cleaned up after an async test.

    This decorator:
    1. Tracks all tasks before the test
    2. Runs the test
    3. Cancels any tasks created during the test
    4. Ensures the event loop is clean for the next test
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        loop = asyncio.get_event_loop()

        # Get initial state
        initial_tasks = set(asyncio.all_tasks(loop))

        try:
            # Run the test
            result = await func(*args, **kwargs)
            return result
        finally:
            # Find new tasks created during the test
            current_tasks = set(asyncio.all_tasks(loop))
            new_tasks = current_tasks - initial_tasks

            # Cancel any pending tasks
            for task in new_tasks:
                if not task.done() and task != asyncio.current_task():
                    task.cancel()

            # Wait for cancellations
            if new_tasks:
                await asyncio.gather(*new_tasks, return_exceptions=True)

            # Allow event loop to process
            await asyncio.sleep(0)

    return wrapper


# Export utilities
__all__ = [
    "AsyncResourceTracker",
    "AsyncTestBase",
    "async_resource_manager",
    "async_test_context",
    "ensure_event_loop_cleanup",
    "safe_async_cleanup",
    "track_async_resources",
]
