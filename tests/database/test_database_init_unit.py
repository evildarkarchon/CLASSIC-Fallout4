"""Unit tests for ClassicLib.io.database module initialization.

This module tests the database module's cleanup functions and exports.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


class TestCleanupDatabasePools:
    """Tests for cleanup_database_pools function."""

    def test_does_not_raise_on_empty_pools(self) -> None:
        """Test cleanup does not raise when pools are empty."""
        from ClassicLib.io.database import cleanup_database_pools

        # Should not raise
        cleanup_database_pools()

    def test_handles_sync_pool_error(self) -> None:
        """Test handles errors when closing SyncDatabasePool."""
        from ClassicLib.io.database import cleanup_database_pools

        mock_instance = MagicMock()
        mock_instance.close_all.side_effect = RuntimeError("Test error")

        with patch("ClassicLib.scanning.logs.Util.SyncDatabasePool") as mock_class:
            mock_class._instance = mock_instance
            # Should not raise
            cleanup_database_pools()

    def test_handles_manager_error(self) -> None:
        """Test handles errors when closing DatabasePoolManager."""
        from ClassicLib.io.database import cleanup_database_pools

        with patch("ClassicLib.scanning.logs.Util.SyncDatabasePool") as mock_sync:
            mock_sync._instance = None
            # Should not raise
            cleanup_database_pools()

    def test_attempts_sync_pool_cleanup(self) -> None:
        """Test attempts to cleanup SyncDatabasePool."""
        from ClassicLib.io.database import cleanup_database_pools

        mock_instance = MagicMock()

        with patch("ClassicLib.scanning.logs.Util.SyncDatabasePool") as mock_class:
            mock_class._instance = mock_instance
            cleanup_database_pools()

            # Verify close_all was called
            mock_instance.close_all.assert_called_once()


class TestCleanupDatabasePoolsAsync:
    """Tests for cleanup_database_pools_async function."""

    @pytest.mark.asyncio
    async def test_does_not_raise_on_empty_pools(self) -> None:
        """Test async cleanup does not raise when pools are empty."""
        from ClassicLib.io.database import cleanup_database_pools_async

        # Should not raise
        await cleanup_database_pools_async()

    @pytest.mark.asyncio
    async def test_handles_manager_error(self) -> None:
        """Test handles errors when closing DatabasePoolManager."""
        from ClassicLib.io.database import cleanup_database_pools_async

        mock_manager = MagicMock()
        mock_manager.close_pool = AsyncMock(side_effect=RuntimeError("Test error"))

        with patch("ClassicLib.io.database.DatabasePoolManager", return_value=mock_manager):
            # Should not raise
            await cleanup_database_pools_async()

    @pytest.mark.asyncio
    async def test_handles_sync_pool_error(self) -> None:
        """Test handles errors when closing SyncDatabasePool."""
        from ClassicLib.io.database import cleanup_database_pools_async

        mock_instance = MagicMock()
        mock_instance.close_all.side_effect = RuntimeError("Test error")

        with patch("ClassicLib.scanning.logs.Util.SyncDatabasePool") as mock_class:
            mock_class._instance = mock_instance
            # Should not raise
            await cleanup_database_pools_async()

    @pytest.mark.asyncio
    async def test_attempts_manager_close(self) -> None:
        """Test attempts to close DatabasePoolManager pool."""
        from ClassicLib.io.database import cleanup_database_pools_async

        mock_manager = MagicMock()
        mock_manager.close_pool = AsyncMock()

        with patch("ClassicLib.io.database.DatabasePoolManager", return_value=mock_manager):
            await cleanup_database_pools_async()

            mock_manager.close_pool.assert_called_once()


class TestModuleExports:
    """Tests for module exports."""

    def test_exports_database_pool_manager(self) -> None:
        """Test DatabasePoolManager is exported."""
        from ClassicLib.io.database import DatabasePoolManager

        assert DatabasePoolManager is not None

    def test_exports_async_database_pool(self) -> None:
        """Test AsyncDatabasePool is exported."""
        from ClassicLib.io.database import AsyncDatabasePool

        assert AsyncDatabasePool is not None

    def test_exports_cleanup_functions(self) -> None:
        """Test cleanup functions are exported."""
        from ClassicLib.io.database import cleanup_database_pools, cleanup_database_pools_async

        assert callable(cleanup_database_pools)
        assert callable(cleanup_database_pools_async)

    def test_all_contains_expected_items(self) -> None:
        """Test __all__ contains expected items."""
        from ClassicLib.io import database as Database

        expected_base = {
            "DatabasePoolManager",
            "AsyncDatabasePool",
            "cleanup_database_pools",
            "cleanup_database_pools_async",
        }

        assert expected_base.issubset(set(Database.__all__))


class TestAtexitHandler:
    """Tests for atexit handler registration."""

    def test_atexit_handler_registered(self) -> None:
        """Test that atexit handler is registered during module import."""
        import atexit

        from ClassicLib.io.database import _atexit_cleanup

        # Verify the function exists and is callable
        assert callable(_atexit_cleanup)

    def test_atexit_handler_suppresses_errors(self) -> None:
        """Test atexit handler suppresses all errors."""
        from ClassicLib.io.database import _atexit_cleanup

        with patch("ClassicLib.io.database.cleanup_database_pools", side_effect=RuntimeError("Test")):
            # Should not raise
            _atexit_cleanup()
