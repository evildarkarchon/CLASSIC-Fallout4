"""Async test fixtures for proper resource management and event loop handling.

This module provides:
- Event loop fixtures for consistent async testing
- Resource tracking fixtures for leak detection
- Cleanup utilities for async resources
"""

import asyncio
import contextlib
import gc
import inspect
import logging
import weakref
from collections.abc import AsyncIterator
from typing import Any

import pytest

logger = logging.getLogger(__name__)


# ============================================================================
# Async Resource Tracker
# ============================================================================


class AsyncResourceTracker:
    """Track async resources to detect leaks.

    This class uses weak references to track async resources,
    allowing detection of resources that haven't been properly cleaned up.
    """

    def __init__(self) -> None:
        """Initialize the resource tracker."""
        self.resources: set[weakref.ref] = set()
        self.leaked_resources: list[str] = []

    def register(self, resource: Any, name: str = "Unknown") -> None:
        """Register a resource for tracking.

        Args:
            resource: The async resource to track.
            name: Human-readable name for debugging.
        """

        def cleanup_callback(ref: weakref.ref) -> None:
            self.resources.discard(ref)

        ref = weakref.ref(resource, cleanup_callback)
        self.resources.add(ref)
        logger.debug(f"Registered async resource: {name}")

    def check_leaks(self) -> list[str]:
        """Check for leaked resources.

        Returns:
            List of string representations of leaked resources.
        """
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


@pytest.fixture
async def async_cleanup() -> AsyncIterator[list[Any]]:
    """
    Fixture that tracks async resources and ensures they are properly cleaned up.

    Usage:
        async def test_something(async_cleanup):
            resource = await create_async_resource()
            async_cleanup.append(resource)
            # Test code here
            # Resource will be automatically cleaned up
    """
    resources = []

    yield resources

    # Optimize cleanup with concurrent operations
    cleanup_tasks = []
    for resource in resources:
        if resource is None:
            continue

        try:
            if hasattr(resource, "aclose"):
                cleanup_tasks.append(resource.aclose())
            elif hasattr(resource, "close"):
                if inspect.iscoroutinefunction(resource.close):
                    cleanup_tasks.append(resource.close())
                else:
                    # Run sync close in executor
                    cleanup_tasks.append(asyncio.get_event_loop().run_in_executor(None, resource.close))
        except Exception as e:
            # Log but don't fail the test on cleanup errors
            logger.warning(f"Error preparing async resource cleanup: {e}")

    # Execute all cleanups concurrently
    if cleanup_tasks:
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for consistent behavior across platforms.

    This is session-scoped because the event loop policy only needs to be set
    once for the entire test session. This also allows module-scoped async
    fixtures to work correctly with pytest-asyncio 1.0+.

    Note:
        Since Python 3.10+, ProactorEventLoop is already the default on
        Windows, so no explicit policy configuration is needed. Returning
        None tells pytest-asyncio to use the default event loop policy.
    """
    return None


@pytest.fixture
async def clean_event_loop():
    """Ensure a clean event loop for each async test."""
    loop = asyncio.get_event_loop()

    # Track initial state
    initial_tasks = set(asyncio.all_tasks(loop))

    yield loop

    # Optimized task cleanup - use gather for concurrent cancellation
    current_tasks = set(asyncio.all_tasks(loop))
    new_tasks = current_tasks - initial_tasks

    if new_tasks:
        # Cancel all new tasks concurrently
        for task in new_tasks:
            if not task.done() and task != asyncio.current_task():
                task.cancel()

        # Wait for all cancellations with timeout to prevent hanging
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(
                asyncio.gather(*new_tasks, return_exceptions=True),
                timeout=1.0,  # Prevent tests from hanging on cleanup
            )

    # Single sleep instead of allowing event loop to process indefinitely
    await asyncio.sleep(0)


# ============================================================================
# Resource Tracking Fixtures
# ============================================================================


@pytest.fixture
def resource_tracker() -> AsyncResourceTracker:
    """Provide a fresh AsyncResourceTracker instance per test.

    Use this fixture when you need explicit control over the tracker
    instance or better test isolation.

    Yields:
        AsyncResourceTracker: Fresh tracker instance for the test.
    """
    tracker = AsyncResourceTracker()
    yield tracker
    tracker.clear()


@pytest.fixture
async def async_resource_manager() -> AsyncIterator[callable]:
    """Pytest fixture for managing async resources in tests.

    Provides a register function to track resources for automatic cleanup.

    Yields:
        Register function that tracks resources.
    """
    tracker = AsyncResourceTracker()
    resources: list[Any] = []

    def register(resource: Any, name: str = "Unknown") -> Any:
        """Register a resource for tracking and automatic cleanup.

        Args:
            resource: The resource to track.
            name: Human-readable name for the resource.

        Returns:
            The same resource for chaining.
        """
        resources.append(resource)
        tracker.register(resource, name)
        return resource

    yield register

    # Clean up all tracked resources
    gc.collect()

    for resource in resources:
        try:
            if hasattr(resource, "aclose"):
                await resource.aclose()
            elif hasattr(resource, "close"):
                if inspect.iscoroutinefunction(resource.close):
                    await resource.close()
                else:
                    resource.close()
        except Exception as e:
            logger.warning(f"Error cleaning up resource: {e}")

    # Check for leaks
    leaks = tracker.check_leaks()
    if leaks:
        logger.warning(f"Resource leaks detected: {leaks}")

    tracker.clear()
