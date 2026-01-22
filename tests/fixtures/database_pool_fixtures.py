"""
Test fixtures for database pool singleton isolation.

These fixtures ensure proper cleanup of the DatabasePoolManager and
SyncDatabasePool singletons between tests to prevent test pollution,
especially important for parallel test execution with pytest-xdist.
"""

import asyncio
from collections.abc import Generator
from unittest.mock import patch

import pytest

from ClassicLib.Database import DatabasePoolManager


@pytest.fixture(autouse=True)
def clean_database_pool_manager() -> Generator[None, None, None]:
    """
    Automatically clean up DatabasePoolManager singleton between tests.

    This fixture ensures that the singleton state is reset before and after
    each test to prevent test pollution. It's especially critical for parallel
    test execution where multiple test workers might be accessing the singleton.
    """
    # Clear singleton instance before test
    DatabasePoolManager._instance = None
    DatabasePoolManager._lock = None

    # Clear any pool if it exists
    if hasattr(DatabasePoolManager, "_pool"):
        DatabasePoolManager._pool = None

    yield

    # Clean up after test
    if DatabasePoolManager._instance is not None:
        # If there's an active pool, try to close it
        if hasattr(DatabasePoolManager._instance, "_pool") and DatabasePoolManager._instance._pool is not None:
            # We need to handle async cleanup carefully
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule cleanup for later if loop is running
                    asyncio.create_task(_cleanup_pool_async())
                else:
                    # Run cleanup synchronously if no loop is running
                    loop.run_until_complete(_cleanup_pool_async())
            except RuntimeError:
                # No event loop available, just reset the state
                pass

    # Reset singleton state
    DatabasePoolManager._instance = None
    DatabasePoolManager._lock = None
    if hasattr(DatabasePoolManager, "_pool"):
        DatabasePoolManager._pool = None


async def _cleanup_pool_async() -> None:
    """Helper function to clean up the database pool asynchronously."""
    manager = DatabasePoolManager._instance
    if manager and hasattr(manager, "_pool") and manager._pool is not None:
        try:
            await manager.close_pool()
        except Exception:
            # Ignore errors during cleanup
            pass


@pytest.fixture(autouse=True)
def clean_sync_database_pool() -> Generator[None, None, None]:
    """Reset SyncDatabasePool singleton and related caches between tests.

    This prevents ResourceWarnings about unclosed SQLite connections
    and ensures test isolation for any code using FormID lookups.

    Cleans up:
        - SyncDatabasePool singleton instance and its connections
        - query_cache module-level dict in Util.py
        - _cached_formid_lookup LRU cache in formid_py.py
    """
    from ClassicLib.python.formid_py import _cached_formid_lookup
    from ClassicLib.ScanLog.Util import SyncDatabasePool, query_cache

    # Clear singleton and caches before test
    if SyncDatabasePool._instance is not None:
        SyncDatabasePool._instance.close_all()
    SyncDatabasePool._instance = None
    query_cache.clear()
    _cached_formid_lookup.cache_clear()

    yield

    # Cleanup after test
    if SyncDatabasePool._instance is not None:
        SyncDatabasePool._instance.close_all()
    SyncDatabasePool._instance = None
    query_cache.clear()
    _cached_formid_lookup.cache_clear()


@pytest.fixture
def mock_database_pool_manager():
    """
    Provide a mock DatabasePoolManager for tests that need to control database behavior.

    This fixture patches the DatabasePoolManager to return a mock instance,
    useful for unit tests that don't need actual database connections.
    """
    from unittest.mock import AsyncMock, MagicMock

    mock_manager = MagicMock(spec=DatabasePoolManager)
    mock_pool = AsyncMock()

    # Setup mock pool with common methods
    mock_pool.get_entry = AsyncMock(return_value=None)
    mock_pool.get_entries_batch = AsyncMock(return_value={})
    mock_pool.initialize = AsyncMock()
    mock_pool.close = AsyncMock()

    # Make get_pool return the mock pool
    mock_manager.get_pool = AsyncMock(return_value=mock_pool)
    mock_manager.close_pool = AsyncMock()

    with patch("ClassicLib.ScanLog.AsyncUtil.DatabasePoolManager", return_value=mock_manager):
        yield mock_manager


@pytest.fixture
async def database_pool_manager_with_mock_pool():
    """
    Provide a real DatabasePoolManager with a mocked AsyncDatabasePool.

    This fixture is useful for testing the singleton behavior without
    actually connecting to databases.
    """
    from unittest.mock import AsyncMock, patch

    # Clear any existing singleton
    DatabasePoolManager._instance = None
    DatabasePoolManager._lock = None

    mock_pool = AsyncMock()
    mock_pool.get_entry = AsyncMock(return_value="test_entry")
    mock_pool.get_entries_batch = AsyncMock(return_value={})
    mock_pool.initialize = AsyncMock()
    mock_pool.close = AsyncMock()

    with patch("ClassicLib.ScanLog.AsyncUtil.AsyncDatabasePool", return_value=mock_pool):
        manager = DatabasePoolManager()
        yield manager

        # Cleanup
        if manager._pool is not None:
            await manager.close_pool()
        DatabasePoolManager._instance = None
        DatabasePoolManager._lock = None


@pytest.fixture(scope="session")
def database_pool_test_isolation_check():
    """
    Session-level fixture to verify DatabasePoolManager isolation across tests.

    This fixture runs once per test session and verifies that the singleton
    is properly isolated between test runs.
    """
    # At session start, singleton should be clean
    assert DatabasePoolManager._instance is None, "DatabasePoolManager singleton not clean at session start"

    # Note: We don't check at session end because the last test's state might persist
    # The important part is that each test starts with a clean slate


@pytest.fixture
def verify_database_pool_isolation():
    """
    Fixture to explicitly verify that DatabasePoolManager is isolated.

    Use this fixture in tests that are particularly sensitive to singleton state.
    """
    # Verify clean state at test start
    assert DatabasePoolManager._instance is None, "DatabasePoolManager not properly isolated"
    assert not hasattr(DatabasePoolManager, "_lock") or DatabasePoolManager._lock is None

    # The autouse fixture will handle cleanup
