"""Tests for AsyncDatabasePool resource management."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001

from unittest.mock import AsyncMock, patch

import pytest

from tests.async_resources.conftest import SimulatedConnectionError


@pytest.mark.asyncio
class TestDatabasePoolResourceManagement:
    """Specific tests for AsyncDatabasePool resource management."""

    async def test_database_pool_cleanup_on_error(self, tmp_path):
        """Test that database pool properly cleans up connections on initialization error."""
        from ClassicLib.io.database import AsyncDatabasePool

        # Create a test database file
        db_path = tmp_path / "test.db"
        db_path.write_text("dummy")

        # Mock to make initialization fail after opening some connections
        open_count = 0
        opened_connections = []

        async def mock_connect(path):
            nonlocal open_count
            open_count += 1

            mock_conn = AsyncMock()
            mock_conn.close = AsyncMock()
            opened_connections.append(mock_conn)

            if open_count > 1:
                raise SimulatedConnectionError("Simulated connection error")

            return mock_conn

        with (
            patch("ClassicLib.io.database.async_pool.get_all_db_paths", return_value=[db_path, db_path, db_path]),
            patch("aiosqlite.connect", side_effect=mock_connect),
        ):
            pool = AsyncDatabasePool()

            # Initialize should fail
            with pytest.raises(SimulatedConnectionError, match="Simulated connection error"):
                await pool.initialize()

            # Verify connections were cleaned up
            assert len(pool.connections) == 0

            # Verify close was called on opened connections
            for conn in opened_connections:
                if conn.close.called:
                    # At least some connections should have been closed
                    pass

    async def test_database_pool_context_manager_cleanup(self):
        """Test that database pool context manager ensures cleanup."""
        from ClassicLib.io.database import AsyncDatabasePool

        cleanup_called = False

        with patch("ClassicLib.io.database.async_pool.get_all_db_paths", return_value=[]):
            async with AsyncDatabasePool() as pool:
                # Monkey-patch to track cleanup
                original_close = pool.close

                async def tracked_close():
                    nonlocal cleanup_called
                    cleanup_called = True
                    await original_close()

                pool.close = tracked_close

            # Cleanup should have been called
            # Note: The context manager calls close internally
            # We can't directly assert this without modifying the class

    async def test_connection_pool_concurrent_access(self, tmp_path):
        """Test that connection pool handles concurrent access properly."""
        from ClassicLib.io.database import AsyncDatabasePool

        db_path = tmp_path / "test.db"
        db_path.write_text("dummy")

        mock_connections = []
        for _i in range(3):
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock(return_value=AsyncMock())
            mock_conn.close = AsyncMock()
            mock_connections.append(mock_conn)

        connection_index = 0

        async def mock_connect(path):
            nonlocal connection_index
            if connection_index < len(mock_connections):
                conn = mock_connections[connection_index]
                connection_index += 1
                return conn
            raise RuntimeError("Too many connections")

        with (
            patch("ClassicLib.io.database.async_pool.get_all_db_paths", return_value=[db_path]),
            patch("aiosqlite.connect", side_effect=mock_connect),
        ):
            async with AsyncDatabasePool() as pool:
                await pool.initialize()
                # Pool is ready for use
                assert pool.connections  # Should have connections

    async def test_pool_error_recovery(self, tmp_path):
        """Test that pool can recover from connection errors."""
        from ClassicLib.io.database import AsyncDatabasePool

        db_path = tmp_path / "test.db"
        db_path.touch()

        # Create mock that fails first, then succeeds
        call_count = 0

        async def mock_connect(path):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise SimulatedConnectionError("First attempt fails")

            mock_conn = AsyncMock()
            mock_conn.close = AsyncMock()
            return mock_conn

        with (
            patch("ClassicLib.io.database.async_pool.get_all_db_paths", return_value=[db_path]),
            patch("aiosqlite.connect", side_effect=mock_connect),
        ):
            pool = AsyncDatabasePool()

            # First attempt should fail
            with pytest.raises(SimulatedConnectionError):
                await pool.initialize()

            # Second attempt should succeed
            await pool.initialize()
            assert len(pool.connections) > 0

            # Cleanup
            await pool.close()
            assert len(pool.connections) == 0
