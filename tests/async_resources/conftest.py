"""Shared fixtures and utilities for async resource management tests."""

from tests.async_tests.test_async_utils import (
    AsyncResourceTracker,
    async_test_context,
    ensure_event_loop_cleanup,
    safe_async_cleanup,
    track_async_resources,
)


class SimulatedConnectionError(Exception):
    """Custom exception for simulating database connection errors in tests."""


class ContextTestError(Exception):
    """Custom exception for testing exception handling during context operations."""


# Export utilities for use in test files
__all__ = [
    "AsyncResourceTracker",
    "ContextTestError",
    "SimulatedConnectionError",
    "async_test_context",
    "ensure_event_loop_cleanup",
    "safe_async_cleanup",
    "track_async_resources",
]
