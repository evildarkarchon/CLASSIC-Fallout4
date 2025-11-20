"""
Integration tests for the Rust database pool implementation.

These tests verify that the Rust database module correctly implements
Phase 4 features including TTL caching, batch operations, and performance.
"""

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
    from ClassicLib.rust.database_rust import DatabasePoolManager, RustAsyncDatabasePool

    RUST_WRAPPER_AVAILABLE = True
except ImportError:
    RustAsyncDatabasePool = None
    DatabasePoolManager = None
    RUST_WRAPPER_AVAILABLE = False

# Try to import the Rust core module
try:
    from classic_database import RustDatabasePool

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


@pytest.mark.skipif(not RUST_CORE_AVAILABLE, reason="Rust core module not available")
class TestRustDatabasePool:
    """Test the low-level Rust database pool implementation."""

    def test_pool_creation(self):
        """Test creating a new database pool with custom parameters."""
        if not RustDatabasePool:
            pytest.skip("RustDatabasePool not available")
        pool = RustDatabasePool(5, 60, "fallout4")  # (max_connections, cache_ttl_seconds, game_table)
        stats = pool.get_stats()

        assert stats["total_queries"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["cache_size"] == 0

    def test_database_initialization(self, tmp_path):
        """Test initializing database connections."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = RustDatabasePool(10, 300, "fallout4")  # Default values
        pool.initialize([str(db_path)])

        stats = pool.get_stats()
        assert stats["total_connections"] == 1
        assert stats["active_connections"] == 1

    def test_single_entry_lookup(self, tmp_path):
        """Test looking up a single FormID entry."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = RustDatabasePool(10, 300, "fallout4")  # Default values
        pool.initialize([str(db_path)])

        # Test successful lookup
        result = pool.get_entry("00012345", "Fallout4.esm", "Fallout4")
        assert result == "Power Armor Frame"

        # Test cache hit (second lookup should be from cache)
        stats_before = pool.get_stats()
        result = pool.get_entry("00012345", "Fallout4.esm", "Fallout4")
        assert result == "Power Armor Frame"
        stats_after = pool.get_stats()

        assert stats_after["cache_hits"] > stats_before["cache_hits"]

        # Test non-existent entry
        result = pool.get_entry("99999999", "NonExistent.esp", "Fallout4")
        assert result is None

    def test_batch_lookup(self, tmp_path):
        """Test batch FormID lookups."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = RustDatabasePool(10, 300, "fallout4")  # Default values
        pool.initialize([str(db_path)])

        # Batch lookup
        pairs = [
            ("00012345", "Fallout4.esm"),
            ("00023456", "DLCCoast.esm"),
            ("99999999", "NonExistent.esp"),  # Non-existent
        ]

        results = pool.get_entries_batch(pairs, "Fallout4", 100)

        assert "00012345:Fallout4.esm" in results
        assert results["00012345:Fallout4.esm"] == "Power Armor Frame"
        assert "00023456:DLCCoast.esm" in results
        assert results["00023456:DLCCoast.esm"] == "Fog Condenser"
        assert "99999999:NonExistent.esp" not in results

        # Check stats
        stats = pool.get_stats()
        assert stats["total_queries"] >= 3

    def test_cache_operations(self, tmp_path):
        """Test cache management operations."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = RustDatabasePool(10, 1, "fallout4")  # 1 second cache TTL  # 1 second TTL
        pool.initialize([str(db_path)])

        # Populate cache
        pool.get_entry("00012345", "Fallout4.esm", "Fallout4")
        pool.get_entry("00023456", "DLCCoast.esm", "Fallout4")

        stats = pool.get_stats()
        assert stats["cache_size"] == 2

        # Clear all cache
        cleared = pool.clear_cache(expired_only=False)
        assert cleared == 2

        stats = pool.get_stats()
        assert stats["cache_size"] == 0

        # Test TTL expiration
        pool.get_entry("00034567", "DLCNukaWorld.esm", "Fallout4")
        time.sleep(1.1)  # Wait for TTL to expire

        cleared = pool.clear_cache(expired_only=True)
        assert cleared >= 1

    def test_cache_ttl_update(self, tmp_path):
        """Test updating cache TTL."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = RustDatabasePool(10, 1, "fallout4")  # 1 second cache TTL
        pool.initialize([str(db_path)])

        # Set new TTL
        pool.set_cache_ttl(300)  # 5 minutes

        # Add entry to cache
        pool.get_entry("00012345", "Fallout4.esm", "Fallout4")
        time.sleep(1.1)  # Would expire with old TTL

        # Should still be in cache with new TTL
        stats = pool.get_stats()
        stats["total_queries"]

        pool.get_entry("00012345", "Fallout4.esm", "Fallout4")
        stats = pool.get_stats()

        # If it was a cache hit, total_queries shouldn't increase
        assert stats["cache_hits"] > 0

    def test_multiple_databases(self, tmp_path):
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

        pool = RustDatabasePool(10, 300, "fallout4")  # Default values
        pool.initialize([str(db1_path), str(db2_path)])

        # Test lookup from first database
        result = pool.get_entry("00012345", "Fallout4.esm", "Fallout4")
        assert result == "Power Armor Frame"

        # Test lookup from second database
        result = pool.get_entry("00067890", "LocalMod.esp", "Fallout4")
        assert result == "Local Custom Item"

        stats = pool.get_stats()
        assert stats["total_connections"] == 2

    def test_optimization(self, tmp_path):
        """Test database optimization (VACUUM and ANALYZE)."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = RustDatabasePool(10, 300, "fallout4")  # Default values
        pool.initialize([str(db_path)])

        # Should not raise an error
        pool.optimize()

    def test_concurrent_access(self, tmp_path):
        """Test concurrent access to the database pool."""
        import threading

        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = RustDatabasePool(10, 300, "fallout4")  # Default values
        pool.initialize([str(db_path)])

        results = []
        errors = []

        def worker(thread_id):
            try:
                for i in range(10):
                    formid = f"{12345 + thread_id:08}"
                    result = pool.get_entry(formid, "Fallout4.esm", "Fallout4")
                    results.append((thread_id, i, result))
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 50  # 5 threads * 10 queries each

        stats = pool.get_stats()
        assert stats["total_queries"] >= 50


@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust database pool not available")
@pytest.mark.asyncio
class TestRustAsyncDatabasePool:
    """Test the async wrapper for the Rust database pool."""

    async def test_async_initialization(self, tmp_path):
        """Test async database pool initialization."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        # Use factory to get the pool
        pool = get_database_pool(max_connections=10, cache_ttl_seconds=300)

        # Initialize the pool
        # Python implementation uses global DB_PATHS, Rust can take paths
        if hasattr(pool, "initialize"):
            if RUST_AVAILABLE and hasattr(pool, "_rust_pool"):
                # Rust version can take paths
                await pool.initialize([str(db_path)])
            else:
                # Python version uses global DB_PATHS
                from unittest.mock import patch

                with patch("ClassicLib.Constants.DB_PATHS", (db_path,)):
                    await pool.initialize()

        # Verify it's the Rust implementation if available
        if RUST_AVAILABLE and RustAsyncDatabasePool:
            assert isinstance(pool, RustAsyncDatabasePool)

    async def test_async_context_manager(self, tmp_path):
        """Test using the pool as an async context manager."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = get_database_pool()

        # Initialize the pool
        if hasattr(pool, "initialize"):
            await pool.initialize([str(db_path)])

        # Test context manager if available
        if hasattr(pool, "__aenter__"):
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
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = get_database_pool()
        if hasattr(pool, "initialize"):
            if RUST_WRAPPER_AVAILABLE and isinstance(pool, RustAsyncDatabasePool):
                await pool.initialize([str(db_path)])
            else:
                with patch("ClassicLib.Constants.DB_PATHS", (db_path,)):
                    await pool.initialize()

        with patch("ClassicLib.registry.GlobalRegistry.get_game", return_value="Fallout4"):
            result = await pool.get_entry("00023456", "DLCCoast.esm")
            assert result == "Fog Condenser"

            # Non-existent entry
            result = await pool.get_entry("99999999", "NonExistent.esp")
            assert result is None

    async def test_async_batch_lookup(self, tmp_path):
        """Test async batch entry lookup."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        if not RUST_WRAPPER_AVAILABLE:
            pytest.skip("RustAsyncDatabasePool not available")

        with patch("ClassicLib.Constants.DB_PATHS", (db_path,)):
            pool = RustAsyncDatabasePool()
            await pool.initialize()

            pairs = [
                ("00012345", "Fallout4.esm"),
                ("00034567", "DLCNukaWorld.esm"),
                ("00045678", "TestMod.esp"),
            ]

            with patch("ClassicLib.registry.GlobalRegistry.get_game", return_value="Fallout4"):
                results = await pool.get_entries_batch(pairs)

                assert len(results) == 3
                assert results["00012345", "Fallout4.esm"] == "Power Armor Frame"
                assert results["00034567", "DLCNukaWorld.esm"] == "Nuka Cola Quantum"
                assert results["00045678", "TestMod.esp"] == "Custom Weapon"

    async def test_async_cache_management(self, tmp_path):
        """Test async cache management."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        with patch("ClassicLib.Constants.DB_PATHS", [db_path]):
            pool = RustAsyncDatabasePool(cache_ttl_seconds=60)
            await pool.initialize()

            # Clear cache
            cleared = await pool.clear_cache()
            assert cleared >= 0

            # Update TTL
            await pool.set_cache_ttl(300)

            # Get stats
            stats = await pool.get_stats()
            assert "total_queries" in stats
            assert "cache_hits" in stats
            assert "cache_hit_rate" in stats

    async def test_async_optimization(self, tmp_path):
        """Test async database optimization."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        if not RUST_WRAPPER_AVAILABLE:
            pytest.skip("RustAsyncDatabasePool not available")

        with patch("ClassicLib.Constants.DB_PATHS", (db_path,)):
            pool = RustAsyncDatabasePool()
            await pool.initialize()

            # Should not raise an error
            await pool.optimize()

    async def test_pool_manager_singleton(self, tmp_path):
        """Test DatabasePoolManager singleton behavior."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        with patch("ClassicLib.Constants.DB_PATHS", [db_path]):
            manager1 = DatabasePoolManager()
            manager2 = DatabasePoolManager()

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
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        if not RUST_WRAPPER_AVAILABLE:
            pytest.skip("RustAsyncDatabasePool not available")

        with patch("ClassicLib.Constants.DB_PATHS", (db_path,)):
            pool = RustAsyncDatabasePool()
            await pool.initialize()

            async def worker(worker_id):
                results = []
                with patch("ClassicLib.registry.GlobalRegistry.get_game", return_value="Fallout4"):
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

            stats = await pool.get_stats()
            assert stats["total_queries"] >= 50


@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust module not available")
@pytest.mark.benchmark
class TestDatabasePoolPerformance:
    """Performance benchmarks for the Rust database pool."""

    def test_single_lookup_performance(self, benchmark, tmp_path):
        """Benchmark single entry lookup performance."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = RustDatabasePool(10, 300, "fallout4")  # Default values
        pool.initialize([str(db_path)])

        # Warm up cache
        pool.get_entry("00012345", "Fallout4.esm", "Fallout4")

        def lookup():
            return pool.get_entry("00012345", "Fallout4.esm", "Fallout4")

        result = benchmark(lookup)
        assert result == "Power Armor Frame"

    def test_batch_lookup_performance(self, benchmark, tmp_path):
        """Benchmark batch lookup performance."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = RustDatabasePool(10, 300, "fallout4")  # Default values
        pool.initialize([str(db_path)])

        pairs = [(f"{i:08}", "TestMod.esp") for i in range(100)]

        def batch_lookup():
            return pool.get_entries_batch(pairs, "Fallout4", 100)

        results = benchmark(batch_lookup)
        assert isinstance(results, dict)

    @pytest.mark.asyncio
    async def test_async_lookup_performance(self, benchmark, tmp_path):
        """Benchmark async lookup performance."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        if not RUST_WRAPPER_AVAILABLE:
            pytest.skip("RustAsyncDatabasePool not available")

        with patch("ClassicLib.Constants.DB_PATHS", (db_path,)):
            pool = RustAsyncDatabasePool()
            await pool.initialize()

            with patch("ClassicLib.registry.GlobalRegistry.get_game", return_value="Fallout4"):
                # Warm up cache
                await pool.get_entry("00012345", "Fallout4.esm")

                async def async_lookup():
                    return await pool.get_entry("00012345", "Fallout4.esm")

                result = await benchmark(async_lookup)
                assert result == "Power Armor Frame"
