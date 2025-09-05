"""
Tests for AsyncDatabasePool component.

This module contains tests for the async database connection pooling
used for FormID lookups in the crash log processing pipeline.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from ClassicLib.ScanLog.AsyncUtil import AsyncDatabasePool


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncDatabasePool:
    """Integration tests for AsyncDatabasePool."""

    async def test_database_pool_context_manager(self) -> None:
        """Test AsyncDatabasePool as context manager."""
        with patch("ClassicLib.Constants.DB_PATHS", []):
            async with AsyncDatabasePool() as pool:
                assert pool is not None
                assert isinstance(pool.connections, dict)
                assert isinstance(pool.query_cache, dict)

    async def test_database_pool_initialization(self) -> None:
        """Test database pool initialization with proper cleanup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test database file
            db_path: Path = Path(temp_dir) / "test.db"
            db_path.write_text("dummy content")  # Not a real SQLite file, but exists

            # Mock aiosqlite.connect to avoid actual database operations
            async def mock_connect(_path: Path) -> AsyncMock:
                mock_conn: AsyncMock = AsyncMock()
                # Ensure the mock has a proper async close method
                mock_conn.close = AsyncMock(return_value=None)
                return mock_conn

            with (
                patch("ClassicLib.ScanLog.AsyncUtil.DB_PATHS", [db_path]),
                patch("aiosqlite.connect", side_effect=mock_connect) as mock_connect_patch,
            ):
                pool: AsyncDatabasePool = AsyncDatabasePool()
                await pool.initialize()

                # Verify connection was attempted
                mock_connect_patch.assert_called_once_with(db_path)
                assert db_path in pool.connections

                # Store the mock connection for verification
                mock_conn = pool.connections[db_path]

                # Test cleanup
                await pool.close()

                # Verify close was called on the connection
                assert mock_conn.close.called
                # Verify pool connections were cleared
                assert len(pool.connections) == 0

    async def test_database_pool_multiple_databases(self) -> None:
        """Test pool with multiple database connections."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple test database files
            db_paths = [
                Path(temp_dir) / "db1.db",
                Path(temp_dir) / "db2.db",
                Path(temp_dir) / "db3.db",
            ]
            for db_path in db_paths:
                db_path.write_text("dummy")

            mock_connections = {}

            async def mock_connect(path: Path) -> AsyncMock:
                mock_conn: AsyncMock = AsyncMock()
                mock_conn.close = AsyncMock(return_value=None)
                mock_connections[path] = mock_conn
                return mock_conn

            with (
                patch("ClassicLib.ScanLog.AsyncUtil.DB_PATHS", db_paths),
                patch("aiosqlite.connect", side_effect=mock_connect),
            ):
                pool: AsyncDatabasePool = AsyncDatabasePool()
                await pool.initialize()

                # Verify all databases were connected
                assert len(pool.connections) == 3
                for db_path in db_paths:
                    assert db_path in pool.connections

                # Test cleanup
                await pool.close()

                # Verify all connections were closed
                for mock_conn in mock_connections.values():
                    assert mock_conn.close.called

    async def test_database_pool_query_caching(self) -> None:
        """Test query result caching in database pool."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path: Path = Path(temp_dir) / "cache_test.db"
            db_path.write_text("dummy")

            mock_conn: AsyncMock = AsyncMock()
            mock_conn.close = AsyncMock(return_value=None)

            # Mock execute to return query results
            mock_cursor: AsyncMock = AsyncMock()
            mock_cursor.fetchone = AsyncMock(return_value=("Test Result",))
            mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
            mock_cursor.__aexit__ = AsyncMock(return_value=None)

            mock_conn.execute = AsyncMock(return_value=mock_cursor)

            with (
                patch("ClassicLib.ScanLog.AsyncUtil.DB_PATHS", [db_path]),
                patch("aiosqlite.connect", return_value=mock_conn),
            ):
                pool: AsyncDatabasePool = AsyncDatabasePool()
                await pool.initialize()

                # First query - should hit database
                result1 = await pool.get_entry(db_path, "12345678")
                assert result1 == "Test Result"
                mock_conn.execute.assert_called_once()

                # Second query with same FormID - should use cache
                result2 = await pool.get_entry(db_path, "12345678")
                assert result2 == "Test Result"
                # Execute should still have been called only once (cached)
                assert mock_conn.execute.call_count == 1

                # Query with different FormID - should hit database again
                result3 = await pool.get_entry(db_path, "87654321")
                assert mock_conn.execute.call_count == 2

                await pool.close()

    async def test_database_pool_error_handling(self) -> None:
        """Test error handling in database pool operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path: Path = Path(temp_dir) / "error_test.db"
            db_path.write_text("dummy")

            # Mock connection that raises an error
            async def mock_connect_error(_path: Path):
                raise Exception("Database connection failed")

            with (
                patch("ClassicLib.ScanLog.AsyncUtil.DB_PATHS", [db_path]),
                patch("aiosqlite.connect", side_effect=mock_connect_error),
            ):
                pool: AsyncDatabasePool = AsyncDatabasePool()

                # Initialize should handle connection errors gracefully
                await pool.initialize()

                # Pool should be initialized but without successful connections
                assert pool is not None
                # Connection might not be in pool due to error
                assert len(pool.connections) == 0 or db_path not in pool.connections

    async def test_database_pool_concurrent_queries(self) -> None:
        """Test concurrent query execution in database pool."""
        import asyncio

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path: Path = Path(temp_dir) / "concurrent_test.db"
            db_path.write_text("dummy")

            mock_conn: AsyncMock = AsyncMock()
            mock_conn.close = AsyncMock(return_value=None)

            # Counter for unique results
            call_count = 0

            async def mock_execute(_query):
                nonlocal call_count
                call_count += 1
                mock_cursor: AsyncMock = AsyncMock()
                mock_cursor.fetchone = AsyncMock(return_value=(f"Result {call_count}",))
                mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
                mock_cursor.__aexit__ = AsyncMock(return_value=None)
                return mock_cursor

            mock_conn.execute = mock_execute

            with (
                patch("ClassicLib.ScanLog.AsyncUtil.DB_PATHS", [db_path]),
                patch("aiosqlite.connect", return_value=mock_conn),
            ):
                pool: AsyncDatabasePool = AsyncDatabasePool()
                await pool.initialize()

                # Execute multiple queries concurrently
                formids = [f"{i:08X}" for i in range(10)]
                tasks = [pool.get_entry(db_path, formid) for formid in formids]
                results = await asyncio.gather(*tasks)

                # Verify all queries completed
                assert len(results) == 10
                assert all(r is not None for r in results)

                await pool.close()

    async def test_database_pool_empty_db_paths(self) -> None:
        """Test database pool with no databases configured."""
        with patch("ClassicLib.ScanLog.AsyncUtil.DB_PATHS", []):
            pool: AsyncDatabasePool = AsyncDatabasePool()
            await pool.initialize()

            # Should handle empty DB_PATHS gracefully
            assert len(pool.connections) == 0

            # Getting entry with no databases should return None or handle gracefully
            result = await pool.get_entry(Path("nonexistent.db"), "12345678")
            assert result is None or result == ""

            await pool.close()
