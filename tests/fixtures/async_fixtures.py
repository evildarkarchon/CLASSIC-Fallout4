"""Async test fixtures for proper resource management and event loop handling."""

import asyncio
import contextlib
import logging
import sys
from collections.abc import AsyncIterator
from typing import Any

import pytest

logger = logging.getLogger(__name__)


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
                if asyncio.iscoroutinefunction(resource.close):
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
    """
    if sys.platform == "win32":
        # Windows requires ProactorEventLoop for subprocess support
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    return asyncio.get_event_loop_policy()


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
