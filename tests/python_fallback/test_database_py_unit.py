"""Unit tests for ClassicLib.python.database_py module.

This module tests the PythonDatabasePool class, which provides the pure Python
fallback implementation for async database connection pooling when Rust
acceleration is not available.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from ClassicLib.integration.python.database_py import PythonDatabasePool

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create a temporary SQLite database for testing.

    Args:
        tmp_path: Pytest temporary path fixture.

    Returns:
        Path to temporary database file.
    """
    db_path = tmp_path / "test_formids.db"

    # Create database with test data
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE formids (
            formid TEXT,
            plugin TEXT,
            description TEXT,
            PRIMARY KEY (formid, plugin)
        )
    """)
    cursor.execute(
        "INSERT INTO formids VALUES (?, ?, ?)",
        ("001234", "TestPlugin.esp", "Test Weapon"),
    )
    cursor.execute(
        "INSERT INTO formids VALUES (?, ?, ?)",
        ("005678", "TestPlugin.esp", "Test Armor"),
    )
    cursor.execute(
        "INSERT INTO formids VALUES (?, ?, ?)",
        ("001234", "OtherPlugin.esp", "Other Item"),
    )
    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def empty_db_path(tmp_path: Path) -> Path:
    """Create an empty SQLite database.

    Args:
        tmp_path: Pytest temporary path fixture.

    Returns:
        Path to empty database file.
    """
    db_path = tmp_path / "empty.db"

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE formids (
            formid TEXT,
            plugin TEXT,
            description TEXT,
            PRIMARY KEY (formid, plugin)
        )
    """)
    conn.commit()
    conn.close()

    return db_path


# ============================================================================
# PythonDatabasePool Initialization Tests
# ============================================================================


class TestPythonDatabasePoolInit:
    """Tests for PythonDatabasePool initialization."""

    @pytest.mark.unit
    def test_init_with_path_string(self, tmp_path: Path) -> None:
        """Test pool initializes with string path."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        db_path = str(tmp_path / "test.db")
        pool = PythonDatabasePool(db_path, pool_size=3)

        assert pool.db_path == Path(db_path)
        assert pool.pool_size == 3
        assert pool.connections == []
        assert pool._initialized is False

    @pytest.mark.unit
    def test_init_with_path_object(self, tmp_path: Path) -> None:
        """Test pool initializes with Path object."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        db_path = tmp_path / "test.db"
        pool = PythonDatabasePool(db_path)

        assert pool.db_path == db_path
        assert pool.pool_size == 5  # Default

    @pytest.mark.unit
    def test_init_default_pool_size(self, tmp_path: Path) -> None:
        """Test pool uses default pool size of 5."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        pool = PythonDatabasePool(tmp_path / "test.db")

        assert pool.pool_size == 5


# ============================================================================
# initialize Tests
# ============================================================================


class TestPythonDatabasePoolInitialize:
    """Tests for PythonDatabasePool.initialize method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_creates_connections(self, temp_db_path: Path) -> None:
        """Test initialize creates database connections."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        pool = PythonDatabasePool(temp_db_path, pool_size=5)
        try:
            await pool.initialize()

            assert pool._initialized is True
            assert len(pool.connections) > 0
            assert len(pool.connections) <= 3  # Initial connections capped at 3
        finally:
            await pool.close()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_raises_on_missing_db(self, tmp_path: Path) -> None:
        """Test initialize raises FileNotFoundError for missing database."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        pool = PythonDatabasePool(tmp_path / "nonexistent.db")

        with pytest.raises(FileNotFoundError, match="Database not found"):
            await pool.initialize()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, temp_db_path: Path) -> None:
        """Test initialize is idempotent (safe to call multiple times)."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        pool = PythonDatabasePool(temp_db_path)
        try:
            await pool.initialize()
            initial_conn_count = len(pool.connections)

            # Call again
            await pool.initialize()

            assert len(pool.connections) == initial_conn_count
        finally:
            await pool.close()


# ============================================================================
# get_entry Tests
# ============================================================================


class TestPythonDatabasePoolGetEntry:
    """Tests for PythonDatabasePool.get_entry method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_entry_returns_description(self, temp_db_path: Path) -> None:
        """Test get_entry returns correct description."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        async with PythonDatabasePool(temp_db_path) as pool:
            result = await pool.get_entry("001234", "TestPlugin.esp")

        assert result == "Test Weapon"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_entry_returns_none_for_missing(self, temp_db_path: Path) -> None:
        """Test get_entry returns None for non-existent entry."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        async with PythonDatabasePool(temp_db_path) as pool:
            result = await pool.get_entry("999999", "MissingPlugin.esp")

        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_entry_auto_initializes(self, temp_db_path: Path) -> None:
        """Test get_entry auto-initializes pool if needed."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        pool = PythonDatabasePool(temp_db_path)
        assert pool._initialized is False

        result = await pool.get_entry("001234", "TestPlugin.esp")

        assert pool._initialized is True
        assert result == "Test Weapon"

        await pool.close()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_entry_same_formid_different_plugin(self, temp_db_path: Path) -> None:
        """Test get_entry distinguishes same FormID in different plugins."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        async with PythonDatabasePool(temp_db_path) as pool:
            result1 = await pool.get_entry("001234", "TestPlugin.esp")
            result2 = await pool.get_entry("001234", "OtherPlugin.esp")

        assert result1 == "Test Weapon"
        assert result2 == "Other Item"


# ============================================================================
# get_entries_batch Tests
# ============================================================================


class TestPythonDatabasePoolGetEntriesBatch:
    """Tests for PythonDatabasePool.get_entries_batch method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_entries_batch_returns_dict(self, temp_db_path: Path) -> None:
        """Test get_entries_batch returns dictionary of results."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        async with PythonDatabasePool(temp_db_path) as pool:
            pairs = [
                ("001234", "TestPlugin.esp"),
                ("005678", "TestPlugin.esp"),
            ]
            results = await pool.get_entries_batch(pairs)

        assert isinstance(results, dict)
        assert results[("001234", "TestPlugin.esp")] == "Test Weapon"
        assert results[("005678", "TestPlugin.esp")] == "Test Armor"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_entries_batch_empty_list(self, temp_db_path: Path) -> None:
        """Test get_entries_batch with empty list returns empty dict."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        async with PythonDatabasePool(temp_db_path) as pool:
            results = await pool.get_entries_batch([])

        assert results == {}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_entries_batch_partial_results(self, temp_db_path: Path) -> None:
        """Test get_entries_batch with mix of existing and missing entries."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        async with PythonDatabasePool(temp_db_path) as pool:
            pairs = [
                ("001234", "TestPlugin.esp"),  # Exists
                ("999999", "MissingPlugin.esp"),  # Missing
            ]
            results = await pool.get_entries_batch(pairs)

        assert ("001234", "TestPlugin.esp") in results
        assert ("999999", "MissingPlugin.esp") not in results


# ============================================================================
# Connection Pool Management Tests
# ============================================================================


class TestPythonDatabasePoolConnectionManagement:
    """Tests for connection pool management."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connection_returned_to_pool(self, temp_db_path: Path) -> None:
        """Test connections are returned to pool after use."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        pool = PythonDatabasePool(temp_db_path, pool_size=3)
        await pool.initialize()
        initial_count = len(pool.connections)

        # Use a connection (get_entry borrows and returns)
        await pool.get_entry("001234", "TestPlugin.esp")

        # Connection should be back in pool
        assert len(pool.connections) == initial_count

        await pool.close()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_excess_connections_closed(self, temp_db_path: Path) -> None:
        """Test excess connections are closed when returned."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        pool = PythonDatabasePool(temp_db_path, pool_size=1)
        await pool.initialize()

        # Fill pool to capacity
        while len(pool.connections) < pool.pool_size:
            conn = pool._create_connection()
            if conn:
                pool.connections.append(conn)

        # Create an extra connection
        extra_conn = pool._create_connection()
        assert extra_conn is not None

        # Return it - should be closed, not added
        await pool._return_connection(extra_conn)

        assert len(pool.connections) <= pool.pool_size

        await pool.close()


# ============================================================================
# _create_connection Tests
# ============================================================================


class TestPythonDatabasePoolCreateConnection:
    """Tests for PythonDatabasePool._create_connection method."""

    @pytest.mark.unit
    def test_create_connection_sets_wal_mode(self, temp_db_path: Path) -> None:
        """Test created connection has WAL mode enabled."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        pool = PythonDatabasePool(temp_db_path)
        conn = pool._create_connection()

        assert conn is not None

        # Verify WAL mode
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal"

        conn.close()

    @pytest.mark.unit
    def test_create_connection_sets_row_factory(self, temp_db_path: Path) -> None:
        """Test created connection has Row factory enabled."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        pool = PythonDatabasePool(temp_db_path)
        conn = pool._create_connection()

        assert conn is not None
        assert conn.row_factory == sqlite3.Row

        conn.close()

    @pytest.mark.unit
    def test_create_connection_returns_none_on_error(self, tmp_path: Path) -> None:
        """Test _create_connection returns None on error."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        # Use invalid path that will fail
        pool = PythonDatabasePool(tmp_path / "nonexistent_dir" / "test.db")

        with patch("sqlite3.connect", side_effect=sqlite3.Error("Connection failed")):
            result = pool._create_connection()

        assert result is None


# ============================================================================
# close Tests
# ============================================================================


class TestPythonDatabasePoolClose:
    """Tests for PythonDatabasePool.close method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_closes_all_connections(self, temp_db_path: Path) -> None:
        """Test close closes all pooled connections."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        pool = PythonDatabasePool(temp_db_path)
        await pool.initialize()
        assert len(pool.connections) > 0

        await pool.close()

        assert len(pool.connections) == 0
        assert pool._initialized is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_idempotent(self, temp_db_path: Path) -> None:
        """Test close is safe to call multiple times."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        pool = PythonDatabasePool(temp_db_path)
        await pool.initialize()

        await pool.close()
        await pool.close()  # Should not raise

        assert pool._initialized is False


# ============================================================================
# Context Manager Tests
# ============================================================================


class TestPythonDatabasePoolContextManager:
    """Tests for async context manager protocol."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_context_manager_initializes(self, temp_db_path: Path) -> None:
        """Test async context manager initializes pool on enter."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        pool = PythonDatabasePool(temp_db_path)
        assert pool._initialized is False

        async with pool:
            assert pool._initialized is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_context_manager_closes_on_exit(self, temp_db_path: Path) -> None:
        """Test async context manager closes pool on exit."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        pool = PythonDatabasePool(temp_db_path)

        async with pool:
            assert pool._initialized is True

        assert pool._initialized is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_context_manager_returns_pool(self, temp_db_path: Path) -> None:
        """Test async context manager returns pool instance."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        pool = PythonDatabasePool(temp_db_path)

        async with pool as p:
            assert p is pool


# ============================================================================
# Static Method Tests
# ============================================================================


class TestPythonDatabasePoolStaticMethods:
    """Tests for static query execution methods."""

    @pytest.mark.unit
    def test_execute_query_single_returns_description(self, temp_db_path: Path) -> None:
        """Test _execute_query_single returns description."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        conn = sqlite3.connect(str(temp_db_path))
        conn.row_factory = sqlite3.Row

        result = PythonDatabasePool._execute_query_single(
            conn,
            "SELECT description FROM formids WHERE formid = ? AND plugin = ?",
            ("001234", "TestPlugin.esp"),
        )

        assert result == "Test Weapon"
        conn.close()

    @pytest.mark.unit
    def test_execute_query_single_returns_none_for_missing(self, temp_db_path: Path) -> None:
        """Test _execute_query_single returns None for missing entry."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        conn = sqlite3.connect(str(temp_db_path))
        conn.row_factory = sqlite3.Row

        result = PythonDatabasePool._execute_query_single(
            conn,
            "SELECT description FROM formids WHERE formid = ? AND plugin = ?",
            ("999999", "Missing.esp"),
        )

        assert result is None
        conn.close()

    @pytest.mark.unit
    def test_execute_query_batch_returns_list(self, temp_db_path: Path) -> None:
        """Test _execute_query_batch returns list of dicts."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        conn = sqlite3.connect(str(temp_db_path))
        conn.row_factory = sqlite3.Row

        result = PythonDatabasePool._execute_query_batch(
            conn,
            "SELECT formid, plugin, description FROM formids WHERE plugin = ?",
            ["TestPlugin.esp"],
        )

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(r, dict) for r in result)
        conn.close()

    @pytest.mark.unit
    def test_execute_query_batch_returns_empty_on_error(self, temp_db_path: Path) -> None:
        """Test _execute_query_batch returns empty list on error."""
        from ClassicLib.integration.python.database_py import PythonDatabasePool

        conn = sqlite3.connect(str(temp_db_path))

        # Invalid query
        result = PythonDatabasePool._execute_query_batch(
            conn,
            "SELECT * FROM nonexistent_table",
            [],
        )

        assert result == []
        conn.close()


# ============================================================================
# Alias Tests
# ============================================================================


class TestAsyncDatabasePoolAlias:
    """Tests for AsyncDatabasePool alias."""

    @pytest.mark.unit
    def test_async_database_pool_alias_exists(self) -> None:
        """Test AsyncDatabasePool is an alias for PythonDatabasePool."""
        from ClassicLib.integration.python.database_py import AsyncDatabasePool, PythonDatabasePool

        assert AsyncDatabasePool is PythonDatabasePool
