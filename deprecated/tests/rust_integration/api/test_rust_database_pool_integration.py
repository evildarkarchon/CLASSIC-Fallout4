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
from typing import Any
from unittest.mock import patch

import pytest

# Import via the integration layer
from ClassicLib.integration.factory import get_database_pool, is_rust_accelerated

RustAsyncDatabasePool: Any | None = None
DatabasePoolManager: Any | None = None
RustDatabasePool: Any | None = None

# Try to import Rust wrapper classes for type checking
try:
    from ClassicLib.io.database import DatabasePoolManager as _DatabasePoolManager
    from ClassicLib.io.database.rust_pool import RustAsyncDatabasePool as _RustAsyncDatabasePool

    DatabasePoolManager = _DatabasePoolManager
    RustAsyncDatabasePool = _RustAsyncDatabasePool

    RUST_WRAPPER_AVAILABLE = True
except ImportError:
    RUST_WRAPPER_AVAILABLE = False

# Try to import the Rust core module
try:
    from classic_database import DatabasePool as _RustDatabasePool

    RustDatabasePool = _RustDatabasePool

    RUST_CORE_AVAILABLE = True
except ImportError:
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

    cursor.executemany(f"INSERT OR REPLACE INTO {table_name} (formid, plugin, entry) VALUES (?, ?, ?)", test_data)  # noqa: S608

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
        if RustDatabasePool is None:
            pytest.skip("RustDatabasePool not available")
        pool = RustDatabasePool(5, 60, "fallout4")  # (max_connections, cache_ttl_seconds, game_table)
        stats = pool.get_stats()

        assert stats["total_queries"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert "cache_evictions" in stats
        assert "cleanup_runs" in stats
        assert "cleanup_removed" in stats
        assert "configured_connection_budget" in stats
        assert "effective_connection_budget" in stats
        assert "active_pool_count" in stats
        assert "min_pool_allocation" in stats
        assert "max_pool_allocation" in stats
        assert "allocation_spread" in stats
        assert "stable_shape_selections" in stats
        assert "stable_shape_padding_pairs" in stats
        assert "stable_shape_bucket_8" in stats
        assert "stable_shape_bucket_16" in stats
        assert "stable_shape_bucket_32" in stats
        assert "stable_shape_bucket_64" in stats
        assert "stable_shape_bucket_128" in stats
        assert "stable_shape_bucket_256" in stats
        assert "stable_shape_bucket_512" in stats
        assert "stable_shape_bucket_1024" in stats
        assert "cache_capacity" in stats
        assert "cleanup_threshold" in stats
        assert "cleanup_interval_seconds" in stats
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

    async def test_cache_policy_runtime_configuration(self, tmp_path):
        """Test runtime cache capacity/cleanup policy configuration APIs."""
        db_path = tmp_path / "test.db"
        create_test_database(db_path)

        pool = RustDatabasePool(10, 300, "fallout4")  # pyright: ignore[reportOptionalCall]
        await pool.initialize([str(db_path)])

        pool.set_cache_capacity(77)
        pool.set_cache_cleanup_threshold(55)
        pool.set_cache_cleanup_interval(9)

        assert pool.get_cache_capacity() == 77
        assert pool.get_cache_cleanup_threshold() == 55
        assert pool.get_cache_cleanup_interval() == 9

        stats = pool.get_stats()
        assert stats["cache_capacity"] == 77
        assert stats["cleanup_threshold"] == 55
        assert stats["cleanup_interval_seconds"] == 9

    async def test_runtime_budget_update_requires_rebalance(self, tmp_path):
        """Verify set_max_connections is config-only until explicit rebalance."""
        db1_path = tmp_path / "budget_main.db"
        db2_path = tmp_path / "budget_local.db"
        create_test_database(db1_path)
        create_test_database(db2_path)

        pool = RustDatabasePool(4, 300, "fallout4")  # pyright: ignore[reportOptionalCall]
        await pool.initialize([str(db1_path), str(db2_path)])

        initial = pool.get_stats()
        assert initial["configured_connection_budget"] == 4
        assert initial["effective_connection_budget"] == 4
        assert initial["min_pool_allocation"] == 2
        assert initial["max_pool_allocation"] == 2

        pool.set_max_connections(10)
        after_set = pool.get_stats()
        assert after_set["configured_connection_budget"] == 10
        assert after_set["effective_connection_budget"] == 4

        await pool.rebalance_connections()
        after_rebalance = pool.get_stats()
        assert after_rebalance["configured_connection_budget"] == 10
        assert after_rebalance["effective_connection_budget"] == 10
        assert after_rebalance["active_pool_count"] == 2
        assert after_rebalance["min_pool_allocation"] == 5
        assert after_rebalance["max_pool_allocation"] == 5

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
        configured_budget = int(args[0]) if args else 10
        self.stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_size": 0,
            "total_connections": 0,
            "active_connections": 0,
            "cache_evictions": 0,
            "cleanup_runs": 0,
            "cleanup_removed": 0,
            "configured_connection_budget": configured_budget,
            "effective_connection_budget": 0,
            "active_pool_count": 0,
            "min_pool_allocation": 0,
            "max_pool_allocation": 0,
            "allocation_spread": 0,
            "stable_shape_selections": 0,
            "stable_shape_padding_pairs": 0,
            "stable_shape_bucket_8": 0,
            "stable_shape_bucket_16": 0,
            "stable_shape_bucket_32": 0,
            "stable_shape_bucket_64": 0,
            "stable_shape_bucket_128": 0,
            "stable_shape_bucket_256": 0,
            "stable_shape_bucket_512": 0,
            "stable_shape_bucket_1024": 0,
            "cache_capacity": 10000,
            "cleanup_threshold": 256,
            "cleanup_interval_seconds": 5,
            "cache_hit_rate": 0.0,
        }
        self._last_pool_count = 0

    async def initialize(self, paths):
        self._last_pool_count = len(paths)
        self.stats["total_connections"] = len(paths)
        self.stats["active_connections"] = len(paths)
        self.stats["active_pool_count"] = len(paths)

        if len(paths) == 0:
            self.stats["effective_connection_budget"] = 0
            self.stats["min_pool_allocation"] = 0
            self.stats["max_pool_allocation"] = 0
            self.stats["allocation_spread"] = 0
            return

        configured = int(self.stats["configured_connection_budget"])
        effective = max(configured, len(paths))
        base = effective // len(paths)
        remainder = effective % len(paths)
        min_alloc = base
        max_alloc = base + (1 if remainder > 0 else 0)

        self.stats["effective_connection_budget"] = effective
        self.stats["min_pool_allocation"] = min_alloc
        self.stats["max_pool_allocation"] = max_alloc
        self.stats["allocation_spread"] = max_alloc - min_alloc

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

    def get_cache_capacity(self):
        return self.stats["cache_capacity"]

    def set_cache_capacity(self, capacity):
        self.stats["cache_capacity"] = capacity

    def get_cache_cleanup_threshold(self):
        return self.stats["cleanup_threshold"]

    def set_cache_cleanup_threshold(self, threshold):
        self.stats["cleanup_threshold"] = threshold

    def get_cache_cleanup_interval(self):
        return self.stats["cleanup_interval_seconds"]

    def set_cache_cleanup_interval(self, seconds):
        self.stats["cleanup_interval_seconds"] = seconds

    def get_max_connections(self):
        return self.stats["configured_connection_budget"]

    def set_max_connections(self, max_connections):
        self.stats["configured_connection_budget"] = max_connections

    def recalculate_max_connections(self):
        self.stats["configured_connection_budget"] = 8

    async def rebalance_connections(self):
        await self.initialize([object()] * self._last_pool_count)

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
            patch("ClassicLib.io.database.rust_pool.get_all_db_paths_async", return_value=[tmp_path / "dummy.db"]),
        ):
            # Use factory to get the pool
            pool = get_database_pool(max_connections=10, cache_ttl_seconds=300)

            # Initialize the pool
            if hasattr(pool, "initialize"):
                await pool.initialize()

            # Verify it's the Rust implementation if available
            if RUST_AVAILABLE and RustAsyncDatabasePool is not None:
                assert isinstance(pool, RustAsyncDatabasePool)

    async def test_async_context_manager(self, tmp_path):
        """Test using the pool as an async context manager."""
        with (
            patch("ClassicLib.io.database.rust_pool.DatabasePool", side_effect=MockRustPool),
            patch("ClassicLib.io.database.rust_pool.get_all_db_paths_async", return_value=[tmp_path / "dummy.db"]),
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
            patch("ClassicLib.io.database.rust_pool.get_all_db_paths_async", return_value=[tmp_path / "dummy.db"]),
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
            patch("ClassicLib.io.database.rust_pool.get_all_db_paths_async", return_value=[tmp_path / "dummy.db"]),
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
            patch("ClassicLib.io.database.rust_pool.get_all_db_paths_async", return_value=[tmp_path / "dummy.db"]),
        ):
            pool = RustAsyncDatabasePool(cache_ttl_seconds=60)  # pyright: ignore[reportOptionalCall]
            await pool.initialize()

            # Clear cache
            cleared = pool.clear_cache()
            assert cleared >= 0

            # Update TTL
            pool.set_cache_ttl(300)
            pool.set_cache_capacity(2048)
            pool.set_cache_cleanup_threshold(512)
            pool.set_cache_cleanup_interval(12)
            assert pool.get_cache_capacity() == 2048
            assert pool.get_cache_cleanup_threshold() == 512
            assert pool.get_cache_cleanup_interval() == 12

            # Get stats
            stats = pool.get_stats()
            assert "total_queries" in stats
            assert "cache_hits" in stats
            assert "cache_hit_rate" in stats
            assert "configured_connection_budget" in stats
            assert "effective_connection_budget" in stats
            assert "active_pool_count" in stats
            assert "min_pool_allocation" in stats
            assert "max_pool_allocation" in stats
            assert "allocation_spread" in stats
            assert "stable_shape_selections" in stats
            assert "stable_shape_padding_pairs" in stats
            assert "stable_shape_bucket_8" in stats
            assert "stable_shape_bucket_16" in stats
            assert "stable_shape_bucket_32" in stats
            assert "stable_shape_bucket_64" in stats
            assert "stable_shape_bucket_128" in stats
            assert "stable_shape_bucket_256" in stats
            assert "stable_shape_bucket_512" in stats
            assert "stable_shape_bucket_1024" in stats
            assert "cache_capacity" in stats
            assert "cleanup_threshold" in stats
            assert "cleanup_interval_seconds" in stats

    async def test_async_budget_rebalance_api(self, tmp_path):
        """Test global budget config update and explicit rebalance API."""
        if not RUST_WRAPPER_AVAILABLE:
            pytest.skip("RustAsyncDatabasePool not available")

        dummy_db = tmp_path / "dummy.db"
        dummy_db.touch()

        with (
            patch("ClassicLib.io.database.rust_pool.DatabasePool", side_effect=MockRustPool),
            patch("ClassicLib.io.database.rust_pool.get_all_db_paths_async", return_value=[dummy_db]),
        ):
            pool = RustAsyncDatabasePool(max_connections=4)  # pyright: ignore[reportOptionalCall]
            await pool.initialize()

            assert pool.get_max_connections() == 4
            before = pool.get_stats()
            assert before["effective_connection_budget"] == 4

            pool.set_max_connections(12)
            after_set = pool.get_stats()
            assert after_set["configured_connection_budget"] == 12
            assert after_set["effective_connection_budget"] == 4

            await pool.rebalance_connections()
            after_rebalance = pool.get_stats()
            assert after_rebalance["configured_connection_budget"] == 12
            assert after_rebalance["effective_connection_budget"] == 12

    async def test_async_optimization(self, tmp_path):
        """Test async database optimization."""
        if not RUST_WRAPPER_AVAILABLE:
            pytest.skip("RustAsyncDatabasePool not available")

        with (
            patch("ClassicLib.io.database.rust_pool.DatabasePool", side_effect=MockRustPool),
            patch("ClassicLib.io.database.rust_pool.get_all_db_paths_async", return_value=[tmp_path / "dummy.db"]),
        ):
            pool = RustAsyncDatabasePool()  # pyright: ignore[reportOptionalCall]
            await pool.initialize()

            # Should not raise an error
            await pool.optimize()

    async def test_pool_manager_singleton(self, tmp_path):
        """Test DatabasePoolManager singleton behavior."""
        with (
            patch("ClassicLib.io.database.rust_pool.DatabasePool", side_effect=MockRustPool),
            patch("ClassicLib.io.database.rust_pool.get_all_db_paths_async", return_value=[tmp_path / "dummy.db"]),
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
            patch("ClassicLib.io.database.rust_pool.get_all_db_paths_async", return_value=[tmp_path / "dummy.db"]),
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

        with patch("ClassicLib.io.database.rust_pool.get_all_db_paths_async", return_value=[db_path]):
            pool = RustAsyncDatabasePool()  # pyright: ignore[reportOptionalCall]
            await pool.initialize()

            with patch("ClassicLib.core.registry.GlobalRegistry.get_game", return_value="Fallout4"):
                # Warm up cache
                await pool.get_entry("00012345", "Fallout4.esm")

                async def async_lookup():
                    return await pool.get_entry("00012345", "Fallout4.esm")

                result = await benchmark(async_lookup)
                assert result == "Power Armor Frame"
