"""Unit tests for ClassicLib.io.database module initialization.

This module tests the database module's cleanup functions and exports.
"""

import sqlite3
from pathlib import Path
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

        with patch("ClassicLib.scanning.logs.util_legacy.SyncDatabasePool") as mock_class:
            mock_class._instance = mock_instance
            # Should not raise
            cleanup_database_pools()

    def test_handles_manager_error(self) -> None:
        """Test handles errors when closing DatabasePoolManager."""
        from ClassicLib.io.database import cleanup_database_pools

        with patch("ClassicLib.scanning.logs.util_legacy.SyncDatabasePool") as mock_sync:
            mock_sync._instance = None
            # Should not raise
            cleanup_database_pools()

    def test_attempts_sync_pool_cleanup(self) -> None:
        """Test attempts to cleanup SyncDatabasePool."""
        from ClassicLib.io.database import cleanup_database_pools

        mock_instance = MagicMock()

        with patch("ClassicLib.scanning.logs.util_legacy.SyncDatabasePool") as mock_class:
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

        with patch("ClassicLib.scanning.logs.util_legacy.SyncDatabasePool") as mock_class:
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


class TestQueryLegacyEntrySync:
    """Tests for query_legacy_entry_sync helper."""

    def test_returns_cached_entry_without_pool_lookup(self) -> None:
        """Cached results should return without touching the database pool."""
        from ClassicLib.io.database import query_legacy_entry_sync

        cache = {("0001", "Test.esp"): "Cached Entry"}
        mock_get_pool = MagicMock()

        result = query_legacy_entry_sync(
            "0001",
            "Test.esp",
            query_cache=cache,
            db_paths=[],
            get_pool=mock_get_pool,
            game_table="Fallout4",
        )

        assert result == "Cached Entry"
        mock_get_pool.assert_not_called()

    def test_queries_database_and_caches_result(self, tmp_path: Path) -> None:
        """Uncached lookups should query databases and cache successful matches."""
        from ClassicLib.io.database import query_legacy_entry_sync

        db_path = tmp_path / "legacy.db"
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE Fallout4 (formid TEXT, plugin TEXT, entry TEXT)")
        conn.execute("INSERT INTO Fallout4 VALUES ('0002', 'Mod.esp', 'Database Entry')")
        conn.commit()

        mock_pool = MagicMock()
        mock_pool.get_connection.return_value = conn
        cache: dict[tuple[str, str], str] = {}

        try:
            result = query_legacy_entry_sync(
                "0002",
                "Mod.esp",
                query_cache=cache,
                db_paths=[db_path],
                get_pool=lambda: mock_pool,
                game_table="Fallout4",
            )
        finally:
            conn.close()

        assert result == "Database Entry"
        assert cache[("0002", "Mod.esp")] == "Database Entry"

    def test_handles_sqlite_error_and_returns_none(self, tmp_path: Path) -> None:
        """SQLite failures should be handled and return None."""
        from ClassicLib.io.database import query_legacy_entry_sync

        db_path = tmp_path / "broken.db"
        db_path.write_text("not a sqlite database")

        mock_pool = MagicMock()
        mock_pool.get_connection.side_effect = sqlite3.Error("open failed")

        result = query_legacy_entry_sync(
            "0003",
            "Broken.esp",
            query_cache={},
            db_paths=[db_path],
            get_pool=lambda: mock_pool,
            game_table="Fallout4",
        )

        assert result is None


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
