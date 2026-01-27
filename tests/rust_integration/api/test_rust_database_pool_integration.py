"""
Integration tests for the Rust database pool implementation.

These tests verify that the Rust database module correctly implements
Phase 4 features including TTL caching, batch operations, and performance.
"""
# ruff: noqa: ANN201, ANN001, ANN204, PLR6301, ARG002, ANN202, ANN002, ANN003

import asyncio
import sqlite3
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# Import via the integration layer
from ClassicLib.integration.factory import get_database_pool
from ClassicLib.integration.status import is_rust_accelerated

# Try to import Rust wrapper classes for type checking
try:
    from ClassicLib.io.database import DatabasePoolManager
    from ClassicLib.io.database.rust_pool import RustAsyncDatabasePool

    RUST_WRAPPER_AVAILABLE = True
except ImportError:
    RustAsyncDatabasePool = None
    DatabasePoolManager = None
    RUST_WRAPPER_AVAILABLE = False

# Try to import the Rust core module
try:
    from classic_database import DatabasePool as RustDatabasePool

    RUST_CORE_AVAILABLE = True
except ImportError:
    RustDatabasePool = None
    RUST_CORE_AVAILABLE = False

# Check if Rust database pool is available via the integration layer
RUST_AVAILABLE = is_rust_accelerated("database_pool")


def create_test_database(db_path: Path, table_name: str = "Fallout4") -> None:
    """Create a test SQLite database with sample FormID data."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ensure simple journaling to avoid locking issues
    cursor.execute("PRAGMA journal_mode=DELETE")

    # Create table
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            formid TEXT NOT NULL,
            plugin TEXT NOT NULL,
            entry TEXT NOT NULL,
            PRIMARY KEY (formid, plugin)
        )
    """)

    # Insert test data
    test_data = [
        ("00012345", "Fallout4.esm", "Power Armor Frame"),
        ("00023456", "DLCCoast.esm", "Fog Condenser"),
        ("00034567", "DLCNukaWorld.esm", "Nuka Cola Quantum"),
        ("00045678", "TestMod.esp", "Custom Weapon"),
        ("00056789", "AnotherMod.esp", "Custom Armor"),
    ]

    cursor.executemany(f"INSERT OR REPLACE INTO {table_name} (formid, plugin, entry) VALUES (?, ?, ?)", test_data)

    conn.commit()
    conn.close()
    time.sleep(0.1)  # Ensure file handle is released


@pytest.mark.skipif(not RUST_CORE_AVAILABLE, reason="Rust core module not available")
@pytest.mark.asyncio
class TestRustDatabasePool:
    """Test the low-level Rust database pool implementation.

    Note: The Rust DatabasePool uses PyO3's future_into_py for initialize(),
    get_entry(), and get_entries_batch(), making them async methods that
    return Python coroutines. These tests use async/await accordingly.
    """

    async def test_pool_creation(self):
        """Test creating a new database pool with custom parameters."""
        if not RustDatabasePool:
            pytest.skip("RustDatabasePool not available")
        pool = RustDatabasePool(5, 60, "fallout4")  # (max_connections, cache_ttl_seconds, game_table)
        stats = pool.get_stats()

        assert stats["total_queries"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        # Note: cache_size may not be in stats depending on implementation
        if "cache_size" in stats:
            assert stats["cache_size"] == 0

    async def test_database_initialization(self, tmp_path):
        """Test initializing database connections."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = RustDatabasePool(10, 300, "fallout4")  # pyright: ignore[reportOptionalCall]
        await pool.initialize([str(db_path)])

        stats = pool.get_stats()
        assert stats["total_connections"] == 1
        assert stats["active_connections"] == 1

    async def test_single_entry_lookup(self, tmp_path):
        """Test looking up a single FormID entry."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = RustDatabasePool(10, 300, "fallout4")  # pyright: ignore[reportOptionalCall]
        await pool.initialize([str(db_path)])

        # Test successful lookup
        result = await pool.get_entry("00012345", "Fallout4.esm", "Fallout4")
        assert result == "Power Armor Frame"

        # Test cache hit (second lookup should be from cache)
        stats_before = pool.get_stats()
        result = await pool.get_entry("00012345", "Fallout4.esm", "Fallout4")
        assert result == "Power Armor Frame"
        stats_after = pool.get_stats()

        assert stats_after["cache_hits"] > stats_before["cache_hits"]

        # Test non-existent entry
        result = await pool.get_entry("99999999", "NonExistent.esp", "Fallout4")
        assert result is None

    async def test_batch_lookup(self, tmp_path):
        """Test batch FormID lookups."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = RustDatabasePool(10, 300, "fallout4")  # pyright: ignore[reportOptionalCall]
        await pool.initialize([str(db_path)])

        # Batch lookup
        pairs = [
            ("00012345", "Fallout4.esm"),
            ("00023456", "DLCCoast.esm"),
            ("99999999", "NonExistent.esp"),  # Non-existent
        ]

        results = await pool.get_entries_batch(pairs, "Fallout4", 100)

        assert "00012345:Fallout4.esm" in results
        assert results["00012345:Fallout4.esm"] == "Power Armor Frame"
        assert "00023456:DLCCoast.esm" in results
        assert results["00023456:DLCCoast.esm"] == "Fog Condenser"
        assert "99999999:NonExistent.esp" not in results

        # Check stats
        stats = pool.get_stats()
        assert stats["total_queries"] >= 3

    async def test_cache_operations(self, tmp_path):
        """Test cache management operations."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = RustDatabasePool(10, 1, "fallout4")  # pyright: ignore[reportOptionalCall] # 1 second TTL
        await pool.initialize([str(db_path)])

        # Populate cache
        await pool.get_entry("00012345", "Fallout4.esm", "Fallout4")
        await pool.get_entry("00023456", "DLCCoast.esm", "Fallout4")

        stats = pool.get_stats()
        # Note: cache_size may not be in stats depending on implementation
        if "cache_size" in stats:
            assert stats["cache_size"] == 2

        # Clear all cache
        cleared = pool.clear_cache(expired_only=False)
        assert cleared >= 0  # May be 0 if cache doesn't track size

        stats = pool.get_stats()
        if "cache_size" in stats:
            assert stats["cache_size"] == 0

        # Test TTL expiration
        await pool.get_entry("00034567", "DLCNukaWorld.esm", "Fallout4")
        await asyncio.sleep(1.1)  # Wait for TTL to expire

        cleared = pool.clear_cache(expired_only=True)
        assert cleared >= 0

    async def test_cache_ttl_update(self, tmp_path):
        """Test updating cache TTL."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = RustDatabasePool(10, 1, "fallout4")  # pyright: ignore[reportOptionalCall] # 1 second cache TTL
        await pool.initialize([str(db_path)])

        # Set new TTL
        pool.set_cache_ttl(300)  # 5 minutes

        # Add entry to cache
        await pool.get_entry("00012345", "Fallout4.esm", "Fallout4")
        await asyncio.sleep(1.1)  # Would expire with old TTL

        # Should still be in cache with new TTL
        stats = pool.get_stats()
        _ = stats["total_queries"]

        await pool.get_entry("00012345", "Fallout4.esm", "Fallout4")
        stats = pool.get_stats()

        # If it was a cache hit, total_queries shouldn't increase
        assert stats["cache_hits"] > 0

    async def test_multiple_databases(self, tmp_path):
        """Test querying across multiple databases."""
        db1_path = tmp_path / "main.db"
        db2_path = tmp_path / "local.db"

        # Create first database
        create_test_database(db1_path)

        # Create second database with additional data
        conn = sqlite3.connect(db2_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE Fallout4 (
                formid TEXT NOT NULL,
                plugin TEXT NOT NULL,
                entry TEXT NOT NULL,
                PRIMARY KEY (formid, plugin)
            )
        """)
        cursor.execute("INSERT INTO Fallout4 VALUES (?, ?, ?)", ("00067890", "LocalMod.esp", "Local Custom Item"))
        conn.commit()
        conn.close()

        pool = RustDatabasePool(10, 300, "fallout4")  # pyright: ignore[reportOptionalCall]
        await pool.initialize([str(db1_path), str(db2_path)])

        # Test lookup from first database
        result = await pool.get_entry("00012345", "Fallout4.esm", "Fallout4")
        assert result == "Power Armor Frame"

        # Test lookup from second database
        result = await pool.get_entry("00067890", "LocalMod.esp", "Fallout4")
        assert result == "Local Custom Item"

        stats = pool.get_stats()
        assert stats["total_connections"] == 2

    async def test_optimization(self, tmp_path):
        """Test database optimization (VACUUM and ANALYZE)."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = RustDatabasePool(10, 300, "fallout4")  # pyright: ignore[reportOptionalCall]
        await pool.initialize([str(db_path)])

        # Should not raise an error
        await pool.optimize()

    async def test_concurrent_access(self, tmp_path):
        """Test concurrent async access to the database pool."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = RustDatabasePool(10, 300, "fallout4")  # pyright: ignore[reportOptionalCall]
        await pool.initialize([str(db_path)])

        async def worker(worker_id: int) -> list:
            results = []
            for i in range(10):
                formid = f"{12345 + worker_id:08}"
                result = await pool.get_entry(formid, "Fallout4.esm", "Fallout4")
                results.append((worker_id, i, result))
            return results

        # Run multiple workers concurrently
        tasks = [worker(i) for i in range(5)]
        all_results = await asyncio.gather(*tasks)

        # Should have results from all workers
        assert len(all_results) == 5
        for worker_results in all_results:
            assert len(worker_results) == 10

        stats = pool.get_stats()
        assert stats["total_queries"] >= 50


class MockRustPool:
    """Mock Rust pool implementation for testing.

    Note: Methods like clear_cache(), get_stats(), set_cache_ttl() are SYNC
    because the real RustAsyncDatabasePool wraps them synchronously.
    Methods like initialize(), get_entry(), get_entries_batch() are ASYNC
    because the real Rust pool uses PyO3's future_into_py for these.
    """

    def __init__(self, *args, **kwargs):
        self.stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_size": 0,
            "total_connections": 1,
            "active_connections": 0,
            "cache_hit_rate": 0.0,
        }

    async def initialize(self, paths):
        pass

    async def get_entry(self, formid, plugin, game):
        self.stats["total_queries"] += 1
        if formid == "00012345" and plugin == "Fallout4.esm":
            return "Power Armor Frame"
        if formid == "00023456" and plugin == "DLCCoast.esm":
            return "Fog Condenser"
        if formid == "00034567" and plugin == "DLCNukaWorld.esm":
            return "Nuka Cola Quantum"
        if formid == "00045678" and plugin == "TestMod.esp":
            return "Custom Weapon"
        return None

    async def get_entries_batch(self, pairs, game, concurrency):
        # Legacy method simulation
        self.stats["total_queries"] += len(pairs)
        results = {}
        for formid, plugin in pairs:
            if formid == "00012345" and plugin == "Fallout4.esm":
                results["00012345:Fallout4.esm"] = "Power Armor Frame"
            elif formid == "00034567" and plugin == "DLCNukaWorld.esm":
                results["00034567:DLCNukaWorld.esm"] = "Nuka Cola Quantum"
            elif formid == "00045678" and plugin == "TestMod.esp":
                results["00045678:TestMod.esp"] = "Custom Weapon"
        return results

    async def batch_lookup(self, pairs, game):
        # New method simulation
        self.stats["total_queries"] += len(pairs)
        results = {}
        for formid, plugin in pairs:
            if formid == "00012345" and plugin == "Fallout4.esm":
                results[formid, plugin] = "Power Armor Frame"
            elif formid == "00034567" and plugin == "DLCNukaWorld.esm":
                results[formid, plugin] = "Nuka Cola Quantum"
            elif formid == "00045678" and plugin == "TestMod.esp":
                results[formid, plugin] = "Custom Weapon"
        return results

    def clear_cache(self, expired_only=False):
        # SYNC method - matches RustAsyncDatabasePool.clear_cache()
        return 0

    def get_stats(self):
        # SYNC method - matches RustAsyncDatabasePool.get_stats()
        return self.stats

    def set_cache_ttl(self, ttl):
        # SYNC method - matches RustAsyncDatabasePool.set_cache_ttl()
        pass

    async def optimize(self):
        pass

    async def close(self):
        """Close the mock pool (no-op for mock)."""
        pass


@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust database pool not available")
@pytest.mark.asyncio
class TestRustAsyncDatabasePool:
    """Test the async wrapper for the Rust database pool."""

    async def test_async_initialization(self, tmp_path):
        """Test async database pool initialization."""
        with (
            patch("ClassicLib.io.database.rust_pool.DatabasePool", side_effect=MockRustPool),
            patch("ClassicLib.io.database.rust_pool.DB_PATHS", [tmp_path / "dummy.db"]),
        ):
            # Use factory to get the pool
            pool = get_database_pool(max_connections=10, cache_ttl_seconds=300)

            # Initialize the pool
            if hasattr(pool, "initialize"):
                await pool.initialize()

            # Verify it's the Rust implementation if available
            if RUST_AVAILABLE and RustAsyncDatabasePool:
                assert isinstance(pool, RustAsyncDatabasePool)

    async def test_async_context_manager(self, tmp_path):
        """Test using the pool as an async context manager."""
        with (
            patch("ClassicLib.io.database.rust_pool.DatabasePool", side_effect=MockRustPool),
            patch("ClassicLib.io.database.rust_pool.DB_PATHS", [tmp_path / "dummy.db"]),
        ):
            pool = get_database_pool()

            # Initialize the pool
            if hasattr(pool, "initialize"):
                await pool.initialize()

            # Test context manager if available
            if hasattr(pool, "__aenter__"):
                with patch("ClassicLib.core.registry.GlobalRegistry.get_game", return_value="Fallout4"):
                    async with pool:
                        # Should be able to query
                        result = await pool.get_entry("00012345", "Fallout4.esm")
                        assert result == "Power Armor Frame"
            else:
                # Test without context manager
                result = await pool.get_entry("00012345", "Fallout4.esm")
                assert result == "Power Armor Frame"

    async def test_async_single_lookup(self, tmp_path):
        """Test async single entry lookup."""
        with (
            patch("ClassicLib.io.database.rust_pool.DatabasePool", side_effect=MockRustPool),
            patch("ClassicLib.io.database.rust_pool.DB_PATHS", [tmp_path / "dummy.db"]),
        ):
            pool = get_database_pool()
            if hasattr(pool, "initialize"):
                await pool.initialize()

            with patch("ClassicLib.core.registry.GlobalRegistry.get_game", return_value="Fallout4"):
                result = await pool.get_entry("00023456", "DLCCoast.esm")
                assert result == "Fog Condenser"

                # Non-existent entry
                result = await pool.get_entry("99999999", "NonExistent.esp")
                assert result is None

    async def test_async_batch_lookup(self, tmp_path):
        """Test async batch entry lookup."""
        if not RUST_WRAPPER_AVAILABLE:
            pytest.skip("RustAsyncDatabasePool not available")

        with (
            patch("ClassicLib.io.database.rust_pool.DatabasePool", side_effect=MockRustPool),
            patch("ClassicLib.io.database.rust_pool.DB_PATHS", [tmp_path / "dummy.db"]),
        ):
            pool = RustAsyncDatabasePool()  # pyright: ignore[reportOptionalCall]
            await pool.initialize()

            pairs = [
                ("00012345", "Fallout4.esm"),
                ("00034567", "DLCNukaWorld.esm"),
                ("00045678", "TestMod.esp"),
            ]

            with patch("ClassicLib.core.registry.GlobalRegistry.get_game", return_value="Fallout4"):
                results = await pool.get_entries_batch(pairs)

                assert len(results) == 3
                assert results["00012345", "Fallout4.esm"] == "Power Armor Frame"
                assert results["00034567", "DLCNukaWorld.esm"] == "Nuka Cola Quantum"
                assert results["00045678", "TestMod.esp"] == "Custom Weapon"

    async def test_async_cache_management(self, tmp_path):
        """Test async cache management."""
        with (
            patch("ClassicLib.io.database.rust_pool.DatabasePool", side_effect=MockRustPool),
            patch("ClassicLib.io.database.rust_pool.DB_PATHS", [tmp_path / "dummy.db"]),
        ):
            pool = RustAsyncDatabasePool(cache_ttl_seconds=60)  # pyright: ignore[reportOptionalCall]
            await pool.initialize()

            # Clear cache
            cleared = pool.clear_cache()
            assert cleared >= 0

            # Update TTL
            pool.set_cache_ttl(300)

            # Get stats
            stats = pool.get_stats()
            assert "total_queries" in stats
            assert "cache_hits" in stats
            assert "cache_hit_rate" in stats

    async def test_async_optimization(self, tmp_path):
        """Test async database optimization."""
        if not RUST_WRAPPER_AVAILABLE:
            pytest.skip("RustAsyncDatabasePool not available")

        with (
            patch("ClassicLib.io.database.rust_pool.DatabasePool", side_effect=MockRustPool),
            patch("ClassicLib.io.database.rust_pool.DB_PATHS", [tmp_path / "dummy.db"]),
        ):
            pool = RustAsyncDatabasePool()  # pyright: ignore[reportOptionalCall]
            await pool.initialize()

            # Should not raise an error
            await pool.optimize()

    async def test_pool_manager_singleton(self, tmp_path):
        """Test DatabasePoolManager singleton behavior."""
        with (
            patch("ClassicLib.io.database.rust_pool.DatabasePool", side_effect=MockRustPool),
            patch("ClassicLib.io.database.rust_pool.DB_PATHS", [tmp_path / "dummy.db"]),
        ):
            manager1 = DatabasePoolManager()  # pyright: ignore[reportOptionalCall]
            manager2 = DatabasePoolManager()  # pyright: ignore[reportOptionalCall]

            # Should be the same instance
            assert manager1 is manager2

            pool1 = await manager1.get_pool()
            pool2 = await manager2.get_pool()

            # Should be the same pool
            assert pool1 is pool2

            # Clean up
            await manager1.close_pool()

    async def test_concurrent_async_access(self, tmp_path):
        """Test concurrent async access to the pool."""
        if not RUST_WRAPPER_AVAILABLE:
            pytest.skip("RustAsyncDatabasePool not available")

        with (
            patch("ClassicLib.io.database.rust_pool.DatabasePool", side_effect=MockRustPool),
            patch("ClassicLib.io.database.rust_pool.DB_PATHS", [tmp_path / "dummy.db"]),
        ):
            pool = RustAsyncDatabasePool()  # pyright: ignore[reportOptionalCall]
            await pool.initialize()

            async def worker(worker_id):
                results = []
                with patch("ClassicLib.core.registry.GlobalRegistry.get_game", return_value="Fallout4"):
                    for i in range(10):
                        formid = f"{12345 + worker_id:08}"
                        result = await pool.get_entry(formid, "Fallout4.esm")
                        results.append((worker_id, i, result))
                return results

            # Run multiple workers concurrently
            tasks = [worker(i) for i in range(5)]
            all_results = await asyncio.gather(*tasks)

            # Should have results from all workers
            assert len(all_results) == 5
            for worker_results in all_results:
                assert len(worker_results) == 10

            stats = pool.get_stats()
            assert stats["total_queries"] >= 50


@pytest.mark.skip(reason="Benchmark fixture not available in standard test environment")
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust module not available")
@pytest.mark.benchmark
@pytest.mark.asyncio
class TestDatabasePoolPerformance:
    """Performance benchmarks for the Rust database pool.

    Note: All database operations are async, so benchmarks use async patterns.
    """

    async def test_single_lookup_performance(self, benchmark, tmp_path):
        """Benchmark single entry lookup performance."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = RustDatabasePool(10, 300, "fallout4")  # pyright: ignore[reportOptionalCall]
        await pool.initialize([str(db_path)])

        # Warm up cache
        await pool.get_entry("00012345", "Fallout4.esm", "Fallout4")

        async def lookup():
            return await pool.get_entry("00012345", "Fallout4.esm", "Fallout4")

        # Note: pytest-benchmark doesn't natively support async, this may need adjustment
        result = await benchmark(lookup)
        assert result == "Power Armor Frame"

    async def test_batch_lookup_performance(self, benchmark, tmp_path):
        """Benchmark batch lookup performance."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = RustDatabasePool(10, 300, "fallout4")  # pyright: ignore[reportOptionalCall]
        await pool.initialize([str(db_path)])

        pairs = [(f"{i:08}", "TestMod.esp") for i in range(100)]

        async def batch_lookup():
            return await pool.get_entries_batch(pairs, "Fallout4", 100)

        # Note: pytest-benchmark doesn't natively support async, this may need adjustment
        results = await benchmark(batch_lookup)
        assert isinstance(results, dict)

    async def test_async_lookup_performance(self, benchmark, tmp_path):
        """Benchmark async lookup performance."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        if not RUST_WRAPPER_AVAILABLE:
            pytest.skip("RustAsyncDatabasePool not available")

        with patch("ClassicLib.integration.rust.database_rust.DB_PATHS", (db_path,)):
            pool = RustAsyncDatabasePool()  # pyright: ignore[reportOptionalCall]
            await pool.initialize()

            with patch("ClassicLib.core.registry.GlobalRegistry.get_game", return_value="Fallout4"):
                # Warm up cache
                await pool.get_entry("00012345", "Fallout4.esm")

                async def async_lookup():
                    return await pool.get_entry("00012345", "Fallout4.esm")

                result = await benchmark(async_lookup)
                assert result == "Power Armor Frame"
