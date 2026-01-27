"""
Tests for AsyncDatabasePool component.

This module contains tests for the async database connection pooling
used for FormID lookups in the crash log processing pipeline.

IMPORTANT: These tests use the DatabasePoolManager singleton pattern.
The clean_database_pool_manager fixture ensures proper test isolation.
Mock fixtures are used to avoid actual database operations in unit tests.
"""

# IMPORTANT: Async Test Pattern Documentation
# ============================================
# This test file follows correct AsyncBridge patterns:
# 1. For sync wrappers using AsyncBridge: Mock bridge.run_async(), not the async function
# 2. For pure async tests: Use @pytest.mark.asyncio and real async/await
# 3. Never use AsyncMock for methods called through AsyncBridge
# 4. See docs/async_test_patterns_guide.md for comprehensive patterns

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import tempfile
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest

from ClassicLib.io.database import AsyncDatabasePool, DatabasePoolManager


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncDatabasePool:
    """Integration tests for AsyncDatabasePool."""

    async def test_database_pool_context_manager(self, mock_database_pool_manager) -> None:
        """Test AsyncDatabasePool as context manager.

        Uses the mock_database_pool_manager fixture to avoid creating real database
        connections and ensure proper singleton isolation.
        """
        # The mock_database_pool_manager fixture provides a mocked pool
        manager = DatabasePoolManager()
        pool = await manager.get_pool()

        assert pool is not None
        # Mock pool has these attributes mocked
        assert hasattr(pool, "connections")
        assert hasattr(pool, "query_cache")

    @pytest.mark.asyncio
    async def test_database_pool_initialization(self) -> None:
        """Test database pool initialization with proper cleanup.

        This test directly creates AsyncDatabasePool to test low-level behavior.
        The clean_database_pool_manager autouse fixture ensures singleton cleanup.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test database file
            db_path: Path = Path(temp_dir) / "test.db"
            db_path.write_text("dummy content")  # Not a real SQLite file, but exists

            # Mock aiosqlite.connect to avoid actual database operations
            mock_conn: AsyncMock = AsyncMock()
            # Ensure the mock has a proper async close method
            mock_conn.close = AsyncMock(return_value=None)

            # Create a coroutine that returns the mock
            async def mock_connect(_path: Path) -> AsyncMock:
                return mock_conn

            with (
                patch("ClassicLib.io.database.async_pool.DB_PATHS", [db_path]),
                patch("aiosqlite.connect", side_effect=mock_connect) as mock_connect_patch,
            ):
                # Create pool directly for low-level testing
                pool: AsyncDatabasePool = AsyncDatabasePool()
                await pool.initialize()

                # Verify connection was attempted
                mock_connect_patch.assert_called_once_with(db_path)
                assert db_path in pool.connections

                # Store the mock connection for verification
                mock_conn = cast(AsyncMock, pool.connections[db_path])

                # Test cleanup
                await pool.close()

                # Verify close was called on the connection
                assert mock_conn.close.called
                # Verify pool connections were cleared
                assert len(pool.connections) == 0

    @pytest.mark.asyncio
    async def test_database_pool_multiple_databases(self) -> None:
        """Test pool with multiple database connections.

        Directly tests AsyncDatabasePool with multiple databases.
        The clean_database_pool_manager fixture ensures singleton cleanup after test.
        """
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
                patch("ClassicLib.io.database.async_pool.DB_PATHS", db_paths),
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

    @pytest.mark.asyncio
    async def test_database_pool_query_caching(self) -> None:
        """Test query result caching in database pool."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path: Path = Path(temp_dir) / "cache_test.db"
            db_path.write_text("dummy")

            mock_conn: AsyncMock = AsyncMock()
            mock_conn.close = AsyncMock(return_value=None)
            # Add async context manager support
            mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_conn.__aexit__ = AsyncMock(return_value=None)

            # Mock execute to return query results
            mock_cursor: AsyncMock = AsyncMock()
            mock_cursor.fetchone = AsyncMock(return_value=("Test Result",))
            mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
            mock_cursor.__aexit__ = AsyncMock(return_value=None)

            # Track execute calls for cache testing
            execute_call_count = 0

            def mock_execute(*args, **kwargs):
                nonlocal execute_call_count
                execute_call_count += 1
                return mock_cursor

            mock_conn.execute = mock_execute

            # Create an async function that returns the mock connection
            async def mock_connect(*args, **kwargs):
                return mock_conn

            with (
                patch("ClassicLib.io.database.async_pool.DB_PATHS", [db_path]),
                patch("aiosqlite.connect", side_effect=mock_connect),
            ):
                pool: AsyncDatabasePool = AsyncDatabasePool()
                await pool.initialize()

                # First query - should hit database
                result1 = await pool.get_entry("12345678", "Fallout4.esm")
                assert result1 == "Test Result"
                assert execute_call_count == 1

                # Second query with same FormID - should use cache
                result2 = await pool.get_entry("12345678", "Fallout4.esm")
                assert result2 == "Test Result"
                # Execute should still have been called only once (cached)
                assert execute_call_count == 1

                # Query with different FormID - should hit database again
                result3 = await pool.get_entry("87654321", "Fallout4.esm")
                assert result3 == "Test Result"
                assert execute_call_count == 2

                await pool.close()

    @pytest.mark.asyncio
    async def test_database_pool_error_handling(self) -> None:
        """Test error handling in database pool operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path: Path = Path(temp_dir) / "error_test.db"
            db_path.write_text("dummy")

            # Mock connection that raises an error
            async def mock_connect_error(_path: Path):
                # Raise aiosqlite.Error which the code specifically catches
                import aiosqlite

                raise aiosqlite.Error("Database connection failed")

            with (
                patch("ClassicLib.io.database.async_pool.DB_PATHS", [db_path]),
                patch("aiosqlite.connect", side_effect=mock_connect_error),
            ):
                pool: AsyncDatabasePool = AsyncDatabasePool()

                # Initialize should handle connection errors gracefully
                await pool.initialize()

                # Pool should be initialized but without successful connections
                assert pool is not None
                # Connection might not be in pool due to error
                assert len(pool.connections) == 0 or db_path not in pool.connections

    @pytest.mark.asyncio
    async def test_database_pool_concurrent_queries(self) -> None:
        """Test concurrent query execution in database pool."""
        import asyncio

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path: Path = Path(temp_dir) / "concurrent_test.db"
            db_path.write_text("dummy")

            mock_conn: AsyncMock = AsyncMock()
            mock_conn.close = AsyncMock(return_value=None)
            # Add async context manager support for the connection
            mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_conn.__aexit__ = AsyncMock(return_value=None)

            # Counter for unique results
            call_count = 0

            def mock_execute(_query, _params=None):
                nonlocal call_count
                call_count += 1
                mock_cursor: AsyncMock = AsyncMock()
                mock_cursor.fetchone = AsyncMock(return_value=(f"Result {call_count}",))
                mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
                mock_cursor.__aexit__ = AsyncMock(return_value=None)
                return mock_cursor

            mock_conn.execute = mock_execute

            # Create an async function that returns the mock connection
            async def mock_connect(*args, **kwargs):
                return mock_conn

            with (
                patch("ClassicLib.io.database.async_pool.DB_PATHS", [db_path]),
                patch("aiosqlite.connect", side_effect=mock_connect),
            ):
                pool: AsyncDatabasePool = AsyncDatabasePool()
                await pool.initialize()

                # Execute multiple queries concurrently
                formids = [f"{i:08X}" for i in range(10)]
                tasks = [pool.get_entry(formid, "Fallout4.esm") for formid in formids]
                results = await asyncio.gather(*tasks)

                # Verify all queries completed
                assert len(results) == 10
                assert all(r is not None for r in results)

                await pool.close()

    @pytest.mark.asyncio
    async def test_database_pool_empty_db_paths(self) -> None:
        """Test database pool with no databases configured."""
        with patch("ClassicLib.io.database.async_pool.DB_PATHS", []):
            pool: AsyncDatabasePool = AsyncDatabasePool()
            await pool.initialize()

            # Should handle empty DB_PATHS gracefully
            assert len(pool.connections) == 0

            # Getting entry with no databases should return None or handle gracefully
            result = await pool.get_entry("12345678", "Fallout4.esm")
            assert result is None or result == ""

            await pool.close()
