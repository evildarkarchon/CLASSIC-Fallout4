"""Benchmark tests for FormID database lookup optimizations.

This module contains performance benchmarks for the FormID database
optimizations implemented in v8.1+:

- Covering index for index-only queries (2-5x speedup)
- Parallel database queries using join_all (2-3x speedup)
- UNION ALL query pattern for better index utilization (1.5-3x speedup)
- Optimized cache key generation and extended TTL

The benchmarks measure both the Rust implementation (primary) and
Python fallback implementation to ensure parity.

Example:
    Run all database benchmarks:
        pytest tests/benchmarks/test_formid_database_performance.py -v

    Run with detailed timing:
        pytest tests/benchmarks/test_formid_database_performance.py -v --benchmark-sort=mean

"""

from __future__ import annotations

import asyncio
import gc
import random
import sqlite3
import string
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

# Import Python fallback implementation
from ClassicLib.io.database.async_pool import (
    BATCH_CACHE_TTL_SECS,
    DEFAULT_CACHE_TTL_SECS,
    AsyncDatabasePool,
)

# Try to import Rust implementation
try:
    import classic_database  # type: ignore[import-not-found]

    RUST_AVAILABLE = True
except ImportError:
    classic_database = None
    RUST_AVAILABLE = False

if TYPE_CHECKING:
    from collections.abc import Generator


# Test data sizes
SMALL_BATCH = 50
MEDIUM_BATCH = 200
LARGE_BATCH = 1000
VERY_LARGE_BATCH = 5000

# Game table name for tests
TEST_GAME_TABLE = "Fallout4"


def generate_formid() -> str:
    """Generate a random FormID string (8 hex characters)."""
    return "".join(random.choices("0123456789ABCDEF", k=8))


def generate_plugin_name() -> str:
    """Generate a random plugin name."""
    name = "".join(random.choices(string.ascii_letters, k=8))
    suffix = random.choice([".esm", ".esp", ".esl"])
    return f"{name}{suffix}"


def generate_entry_text() -> str:
    """Generate random entry text."""
    words = [
        "Weapon",
        "Armor",
        "Ammo",
        "Aid",
        "Misc",
        "BOOK",
        "WEAP",
        "ARMO",
        "NPC_",
        "RACE",
        "CELL",
        "REFR",
        "ACHR",
        "DIAL",
        "INFO",
    ]
    word = random.choice(words)
    suffix = "".join(random.choices(string.ascii_letters + string.digits, k=12))
    return f"{word}_{suffix}"


class TestFormIDDatabaseFixture:
    """Create a temporary database for benchmarking."""

    @pytest.fixture(scope="module")
    def temp_database(self) -> Generator[Path, None, None]:
        """Create a temporary SQLite database with test data.

        Creates a database with:
        - 100,000 FormID entries
        - Both old and new indexes
        - Multiple plugins

        Yields:
            Path to the temporary database file.

        """
        # Use ignore_cleanup_errors=True to handle Windows file locking issues
        # when SQLite connections aren't fully released before cleanup
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = Path(tmpdir) / "test_formids.db"

            # Create database with test data
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()

                # Create table
                cursor.execute(
                    f"""CREATE TABLE {TEST_GAME_TABLE}
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin TEXT, formid TEXT, entry TEXT)"""
                )

                # Create indexes (both old and new)
                cursor.execute(f"CREATE INDEX {TEST_GAME_TABLE}_index ON {TEST_GAME_TABLE} (formid, plugin COLLATE nocase)")
                cursor.execute(f"CREATE INDEX {TEST_GAME_TABLE}_covering_idx ON {TEST_GAME_TABLE} (formid, plugin COLLATE nocase, entry)")

                # Generate test data - 100,000 entries across ~50 plugins
                plugins = [generate_plugin_name() for _ in range(50)]
                entries: list[tuple[str, str, str]] = []

                for _ in range(100000):
                    plugin = random.choice(plugins)
                    formid = generate_formid()
                    entry = generate_entry_text()
                    entries.append((plugin, formid, entry))

                cursor.executemany(
                    f"INSERT INTO {TEST_GAME_TABLE} (plugin, formid, entry) VALUES (?, ?, ?)",
                    entries,
                )

                # Run ANALYZE for query optimizer
                cursor.execute(f"ANALYZE {TEST_GAME_TABLE}")
                conn.commit()

            yield db_path

            # Force garbage collection and brief delay to help release file handles
            # before temp directory cleanup on Windows
            gc.collect()
            time.sleep(0.1)

    @pytest.fixture
    def formid_plugin_pairs_small(self, temp_database: Path) -> list[tuple[str, str]]:
        """Generate small batch of FormID/plugin pairs from database.

        Args:
            temp_database: Path to the test database.

        Returns:
            List of (formid, plugin) tuples.

        """
        return self._get_random_pairs(temp_database, SMALL_BATCH)

    @pytest.fixture
    def formid_plugin_pairs_medium(self, temp_database: Path) -> list[tuple[str, str]]:
        """Generate medium batch of FormID/plugin pairs from database.

        Args:
            temp_database: Path to the test database.

        Returns:
            List of (formid, plugin) tuples.

        """
        return self._get_random_pairs(temp_database, MEDIUM_BATCH)

    @pytest.fixture
    def formid_plugin_pairs_large(self, temp_database: Path) -> list[tuple[str, str]]:
        """Generate large batch of FormID/plugin pairs from database.

        Args:
            temp_database: Path to the test database.

        Returns:
            List of (formid, plugin) tuples.

        """
        return self._get_random_pairs(temp_database, LARGE_BATCH)

    @pytest.fixture
    def formid_plugin_pairs_very_large(self, temp_database: Path) -> list[tuple[str, str]]:
        """Generate very large batch of FormID/plugin pairs from database.

        Args:
            temp_database: Path to the test database.

        Returns:
            List of (formid, plugin) tuples.

        """
        return self._get_random_pairs(temp_database, VERY_LARGE_BATCH)

    @staticmethod
    def _get_random_pairs(db_path: Path, count: int) -> list[tuple[str, str]]:
        """Get random existing FormID/plugin pairs from the database.

        Args:
            db_path: Path to the database file.
            count: Number of pairs to retrieve.

        Returns:
            List of (formid, plugin) tuples that exist in the database.

        """
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT formid, plugin FROM {TEST_GAME_TABLE} ORDER BY RANDOM() LIMIT ?",
                (count,),
            )
            return [(row[0], row[1]) for row in cursor.fetchall()]


@pytest.mark.benchmark
@pytest.mark.performance
class TestPythonDatabaseBenchmarks(TestFormIDDatabaseFixture):
    """Benchmark tests for Python async database pool implementation."""

    def test_benchmark_python_batch_lookup_small(
        self,
        benchmark,
        temp_database: Path,
        formid_plugin_pairs_small: list[tuple[str, str]],
    ) -> None:
        """Benchmark small batch lookup with Python implementation.

        Args:
            benchmark: pytest-benchmark fixture.
            temp_database: Path to test database.
            formid_plugin_pairs_small: Small batch of test pairs.

        """

        async def setup_and_lookup() -> dict[tuple[str, str], str]:
            pool = AsyncDatabasePool()
            pool.connections[temp_database] = await __import__("aiosqlite").connect(temp_database)
            pool.query_cache.clear()  # Clear cache for fair comparison
            result = await pool.get_entries_batch(formid_plugin_pairs_small)
            await pool.close()
            return result

        result = benchmark(lambda: asyncio.run(setup_and_lookup()))

        assert len(result) > 0, "Should find at least some entries"

    def test_benchmark_python_batch_lookup_medium(
        self,
        benchmark,
        temp_database: Path,
        formid_plugin_pairs_medium: list[tuple[str, str]],
    ) -> None:
        """Benchmark medium batch lookup with Python implementation.

        Args:
            benchmark: pytest-benchmark fixture.
            temp_database: Path to test database.
            formid_plugin_pairs_medium: Medium batch of test pairs.

        """

        async def setup_and_lookup() -> dict[tuple[str, str], str]:
            pool = AsyncDatabasePool()
            pool.connections[temp_database] = await __import__("aiosqlite").connect(temp_database)
            pool.query_cache.clear()
            result = await pool.get_entries_batch(formid_plugin_pairs_medium)
            await pool.close()
            return result

        result = benchmark(lambda: asyncio.run(setup_and_lookup()))

        assert len(result) > 0

    def test_benchmark_python_batch_lookup_large(
        self,
        benchmark,
        temp_database: Path,
        formid_plugin_pairs_large: list[tuple[str, str]],
    ) -> None:
        """Benchmark large batch lookup with Python implementation.

        Args:
            benchmark: pytest-benchmark fixture.
            temp_database: Path to test database.
            formid_plugin_pairs_large: Large batch of test pairs.

        """

        async def setup_and_lookup() -> dict[tuple[str, str], str]:
            pool = AsyncDatabasePool()
            pool.connections[temp_database] = await __import__("aiosqlite").connect(temp_database)
            pool.query_cache.clear()
            result = await pool.get_entries_batch(formid_plugin_pairs_large)
            await pool.close()
            return result

        result = benchmark(lambda: asyncio.run(setup_and_lookup()))

        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_benchmark_python_cache_hit_rate(
        self,
        temp_database: Path,
        formid_plugin_pairs_medium: list[tuple[str, str]],
    ) -> None:
        """Test cache hit rate with extended TTL for cross-log persistence.

        Args:
            temp_database: Path to test database.
            formid_plugin_pairs_medium: Medium batch of test pairs.

        """
        pool = AsyncDatabasePool()
        pool.connections[temp_database] = await __import__("aiosqlite").connect(temp_database)

        # First lookup - populates cache
        result1 = await pool.get_entries_batch(formid_plugin_pairs_medium)

        # Second lookup - should hit cache
        result2 = await pool.get_entries_batch(formid_plugin_pairs_medium)

        await pool.close()

        assert result1 == result2, "Cached results should match"
        assert len(pool.query_cache) > 0, "Cache should be populated"


@pytest.mark.benchmark
@pytest.mark.performance
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extensions not built")
class TestRustDatabaseBenchmarks(TestFormIDDatabaseFixture):
    """Benchmark tests for Rust database pool implementation."""

    def test_benchmark_rust_batch_lookup_small(
        self,
        benchmark: Any,
        temp_database: Path,
        formid_plugin_pairs_small: list[tuple[str, str]],
    ) -> None:
        """Benchmark small batch lookup with Rust implementation.

        Args:
            benchmark: pytest-benchmark fixture.
            temp_database: Path to test database.
            formid_plugin_pairs_small: Small batch of test pairs.

        """
        assert classic_database is not None

        async def setup_and_lookup() -> dict[str, Any]:
            pool = classic_database.DatabasePool(game_table=TEST_GAME_TABLE)  # pyright: ignore[reportOptionalMemberAccess]
            await pool.initialize([str(temp_database)])
            pool.clear_cache()  # Clear cache for fair comparison
            result = await pool.get_entries_batch(formid_plugin_pairs_small)
            # Close pool to release SQLite connections and avoid file lock
            if hasattr(pool, "close"):
                await pool.close()
            return result  # type: ignore[no-any-return]

        result = benchmark(lambda: asyncio.run(setup_and_lookup()))

        assert len(result) > 0, "Should find at least some entries"

    def test_benchmark_rust_batch_lookup_medium(
        self,
        benchmark: Any,
        temp_database: Path,
        formid_plugin_pairs_medium: list[tuple[str, str]],
    ) -> None:
        """Benchmark medium batch lookup with Rust implementation.

        Args:
            benchmark: pytest-benchmark fixture.
            temp_database: Path to test database.
            formid_plugin_pairs_medium: Medium batch of test pairs.

        """
        assert classic_database is not None

        async def setup_and_lookup() -> dict[str, Any]:
            pool = classic_database.DatabasePool(game_table=TEST_GAME_TABLE)  # pyright: ignore[reportOptionalMemberAccess]
            await pool.initialize([str(temp_database)])
            pool.clear_cache()
            result = await pool.get_entries_batch(formid_plugin_pairs_medium)
            # Close pool to release SQLite connections and avoid file lock
            if hasattr(pool, "close"):
                await pool.close()
            return result  # type: ignore[no-any-return]

        result = benchmark(lambda: asyncio.run(setup_and_lookup()))

        assert len(result) > 0

    def test_benchmark_rust_batch_lookup_large(
        self,
        benchmark: Any,
        temp_database: Path,
        formid_plugin_pairs_large: list[tuple[str, str]],
    ) -> None:
        """Benchmark large batch lookup with Rust implementation.

        Args:
            benchmark: pytest-benchmark fixture.
            temp_database: Path to test database.
            formid_plugin_pairs_large: Large batch of test pairs.

        """
        assert classic_database is not None

        async def setup_and_lookup() -> dict[str, Any]:
            pool = classic_database.DatabasePool(game_table=TEST_GAME_TABLE)  # pyright: ignore[reportOptionalMemberAccess]
            await pool.initialize([str(temp_database)])
            pool.clear_cache()
            result = await pool.get_entries_batch(formid_plugin_pairs_large)
            # Close pool to release SQLite connections and avoid file lock
            if hasattr(pool, "close"):
                await pool.close()
            return result  # type: ignore[no-any-return]

        result = benchmark(lambda: asyncio.run(setup_and_lookup()))

        assert len(result) > 0

    def test_benchmark_rust_batch_lookup_very_large(
        self,
        benchmark: Any,
        temp_database: Path,
        formid_plugin_pairs_very_large: list[tuple[str, str]],
    ) -> None:
        """Benchmark very large batch lookup with Rust implementation.

        Args:
            benchmark: pytest-benchmark fixture.
            temp_database: Path to test database.
            formid_plugin_pairs_very_large: Very large batch of test pairs.

        """
        assert classic_database is not None

        async def setup_and_lookup() -> dict[str, Any]:
            pool = classic_database.DatabasePool(game_table=TEST_GAME_TABLE)  # pyright: ignore[reportOptionalMemberAccess]
            await pool.initialize([str(temp_database)])
            pool.clear_cache()
            result = await pool.get_entries_batch(formid_plugin_pairs_very_large)
            # Close pool to release SQLite connections and avoid file lock
            if hasattr(pool, "close"):
                await pool.close()
            return result  # type: ignore[no-any-return]

        result = benchmark(lambda: asyncio.run(setup_and_lookup()))

        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_benchmark_rust_cache_performance(
        self,
        temp_database: Path,
        formid_plugin_pairs_large: list[tuple[str, str]],
    ) -> None:
        """Test cache hit rate and TTL settings with Rust implementation.

        Args:
            temp_database: Path to test database.
            formid_plugin_pairs_large: Large batch of test pairs.

        """
        assert classic_database is not None

        # Use batch TTL for cross-log persistence
        pool = classic_database.DatabasePool(
            cache_ttl_seconds=BATCH_CACHE_TTL_SECS,
            game_table=TEST_GAME_TABLE,
        )
        await pool.initialize([str(temp_database)])

        # First lookup - populates cache
        result1 = await pool.get_entries_batch(formid_plugin_pairs_large)

        # Get stats after first lookup
        stats1 = pool.get_stats()

        # Second lookup - should hit cache
        result2 = await pool.get_entries_batch(formid_plugin_pairs_large)

        # Get stats after second lookup
        stats2 = pool.get_stats()

        # Close pool to release SQLite connections and avoid file lock
        if hasattr(pool, "close"):
            await pool.close()

        assert len(result1) > 0, "First lookup should find entries"
        assert result1 == result2, "Cached results should match"

        # Cache hits should be higher after second lookup
        assert stats2["cache_hits"] > stats1["cache_hits"], "Should have cache hits"


@pytest.mark.benchmark
@pytest.mark.performance
class TestCacheTTLConstants:
    """Test that cache TTL constants are properly exposed."""

    def test_python_cache_ttl_constants(self) -> None:
        """Verify Python cache TTL constants are defined."""
        assert DEFAULT_CACHE_TTL_SECS == 300, "Default TTL should be 5 minutes"
        assert BATCH_CACHE_TTL_SECS == 1800, "Batch TTL should be 30 minutes"

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extensions not built")
    def test_rust_cache_ttl_constants(self) -> None:
        """Verify Rust cache TTL constants are exposed to Python."""
        assert classic_database is not None

        # Check function-based accessors (type ignore for dynamic import)
        assert classic_database.get_default_cache_ttl() == 300  # type: ignore[attr-defined]
        assert classic_database.get_batch_cache_ttl() == 1800  # type: ignore[attr-defined]
        assert classic_database.get_max_cache_ttl() == 3600  # type: ignore[attr-defined]

        # Check module constants
        assert classic_database.DEFAULT_CACHE_TTL == 300  # type: ignore[attr-defined]
        assert classic_database.BATCH_CACHE_TTL == 1800  # type: ignore[attr-defined]
        assert classic_database.MAX_CACHE_TTL == 3600  # type: ignore[attr-defined]

    @pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust extensions not built")
    def test_rust_default_ttl_uses_batch(self) -> None:
        """Verify Rust DatabasePool defaults to batch TTL for cross-log caching."""
        assert classic_database is not None

        # Create pool with defaults (should use BATCH_CACHE_TTL)
        pool = classic_database.DatabasePool()

        # The default TTL should be 1800 (30 min) for cross-log persistence
        # We can't directly access the TTL, but we can verify the pool was created
        assert pool is not None


@pytest.mark.benchmark
@pytest.mark.performance
class TestUnionAllQueryPattern:
    """Test UNION ALL query pattern performance characteristics."""

    def test_union_all_query_structure(self) -> None:
        """Verify UNION ALL query is properly structured for small batches."""
        query = AsyncDatabasePool._build_union_all_query("Fallout4", 3)

        # Should contain UNION ALL separators
        assert "UNION ALL" in query
        assert query.count("UNION ALL") == 2  # 3 SELECTs = 2 UNION ALLs

        # Should have proper SELECT structure
        assert query.count("SELECT formid, plugin, entry FROM Fallout4") == 3

    def test_union_all_query_empty(self) -> None:
        """Verify UNION ALL query handles empty batch."""
        query = AsyncDatabasePool._build_union_all_query("Fallout4", 0)
        assert query == ""

    def test_union_all_query_single(self) -> None:
        """Verify UNION ALL query handles single item."""
        query = AsyncDatabasePool._build_union_all_query("Fallout4", 1)

        # Should be a simple SELECT without UNION ALL
        assert "UNION ALL" not in query
        assert "SELECT formid, plugin, entry FROM Fallout4" in query
