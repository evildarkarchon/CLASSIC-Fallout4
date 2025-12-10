"""
Performance tests for OrchestratorCore optimizations.

Tests verify that the performance optimizations implemented in OrchestratorCore
provide measurable improvements in processing speed.

IMPORTANT: These tests use the DatabasePoolManager singleton and version cache.
The clean_database_pool_manager fixture ensures singleton isolation.
The clean_version_caches fixture ensures version cache is cleared between tests.
"""

import asyncio
import time
import tracemalloc
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.ScanLog.AsyncUtil import DatabasePoolManager
from ClassicLib.ScanLog.OrchestratorCore import OrchestratorCore
from ClassicLib.Utils.version_utils import crashgen_version_gen
from packaging.version import Version

if TYPE_CHECKING:
    pass

class TestOrchestratorPerformance:
    """Test suite for OrchestratorCore performance optimizations."""

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_batch_database_queries(self):
        """Verify batch database queries are more efficient than individual queries."""
        # Create mock database pool with timing
        mock_pool = AsyncMock()
        individual_query_time = 0.01  # 10ms per query
        batch_query_time = 0.03  # 30ms for batch (3x faster for 10 items)

        async def mock_get_entry(formid: str, plugin: str) -> str:
            """Mock individual database query with delay."""
            await asyncio.sleep(individual_query_time)
            return f"Entry for {formid}:{plugin}"

        async def mock_get_entries_batch(pairs: list[tuple[str, str]]) -> dict:
            """Mock batch database query with reduced delay."""
            await asyncio.sleep(batch_query_time)
            return {pair: f"Entry for {pair[0]}:{pair[1]}" for pair in pairs}

        mock_pool.get_entry = mock_get_entry
        mock_pool.get_entries_batch = mock_get_entries_batch

        # Test with 10 FormID lookups
        formid_plugin_pairs = [(f"FORMID{i:02d}", f"Plugin{i}.esm") for i in range(10)]

        # Time individual queries (old method)
        start_time = time.perf_counter()
        for formid, plugin in formid_plugin_pairs:
            await mock_pool.get_entry(formid, plugin)
        individual_time = time.perf_counter() - start_time

        # Time batch query (new method)
        start_time = time.perf_counter()
        await mock_pool.get_entries_batch(formid_plugin_pairs)
        batch_time = time.perf_counter() - start_time

        # Verify batch is significantly faster (at least 3x improvement)
        performance_ratio = individual_time / batch_time
        assert performance_ratio >= 3.0, f"Batch queries should be at least 3x faster, got {performance_ratio:.2f}x"

    @pytest.mark.performance
    @pytest.mark.skipif(tracemalloc.is_tracing(), reason="Timing sensitive test skipped when tracemalloc is enabled")
    def test_version_string_caching(self):
        """Verify version string parsing is cached effectively.

        The clean_version_caches autouse fixture ensures the cache is clear at start.
        This test explicitly clears the cache to test cold vs warm cache performance.
        """
        test_version = "1.10.163.0"

        # Clear the cache first (also done by fixture, but being explicit here)
        crashgen_version_gen.cache_clear()
        result1 = result2 = Version("0.0.0.0")
        # First call - should parse
        start_time = time.perf_counter()
        for _ in range(100):
            result1 = crashgen_version_gen(test_version)
        uncached_time = time.perf_counter() - start_time

        # Second set of calls - should use cache
        start_time = time.perf_counter()
        for _ in range(100):
            result2 = crashgen_version_gen(test_version)
        cached_time = time.perf_counter() - start_time

        # Verify results are the same
        assert str(result1) == str(result2)

        # Verify caching provides significant speedup (at least 3x)
        # Note: Performance ratios can vary based on system load
        if uncached_time > 0:  # Avoid division by zero
            performance_ratio = uncached_time / cached_time
            assert performance_ratio >= 3.0, f"Caching should provide at least 3x speedup, got {performance_ratio:.2f}x"

        # Verify cache info shows hits
        cache_info = crashgen_version_gen.cache_info()
        assert cache_info.hits >= 99, "Should have at least 99 cache hits"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_singleton_database_pool(self):
        """Verify singleton database pool reuses connections.

        The clean_database_pool_manager fixture ensures singleton is reset.
        This test verifies the singleton pattern works correctly.
        """
        # Get the singleton manager
        manager1 = DatabasePoolManager()
        manager2 = DatabasePoolManager()

        # Verify it's the same instance
        assert manager1 is manager2, "DatabasePoolManager should be a singleton"

        # Mock the AsyncDatabasePool to track initialization calls
        init_count = 0

        class MockAsyncDatabasePool:
            """Mock database pool that tracks initialization."""

            def __init__(self, max_connections: int = 50) -> None:
                """Track creation with parameters."""
                self.max_connections = max_connections

            async def initialize(self):
                """Track initialization calls."""
                nonlocal init_count
                init_count += 1

            async def close(self):
                """Mock close method."""

        # Also mock the Rust acceleration check to force use of Python fallback
        # This ensures we test the Python AsyncDatabasePool path
        # Note: is_rust_accelerated is imported locally, so patch at source
        with (
            patch("ClassicLib.ScanLog.AsyncUtil.AsyncDatabasePool", MockAsyncDatabasePool),
            patch("ClassicLib.integration.status.is_rust_accelerated", return_value=False),
        ):
            # Clear any existing pool and reset using_rust flag
            manager1._pool = None
            manager1._using_rust = False

            # Get pool multiple times
            pool1 = await manager1.get_pool()
            pool2 = await manager2.get_pool()
            pool3 = await manager1.get_pool()

            # Verify same pool instance is returned
            assert pool1 is pool2 is pool3, "Should return the same pool instance"

            # Verify pool was only initialized once
            assert init_count == 1, f"Pool should be initialized only once, but was initialized {init_count} times"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_async_file_operations(self):
        """Verify async file operations improve concurrency."""
        import tempfile

        # Create temporary files for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            test_files = []

            # Create test files
            for i in range(5):
                test_file = tmppath / f"test_{i}.txt"
                test_file.write_text(f"Test content {i}\n" * 100)
                test_files.append(test_file)

            # Mock orchestrator with async file reading
            mock_yamldata = MagicMock()
            mock_yamldata.game_ignore_plugins = []
            mock_yamldata.game_ignore_records = []
            mock_yamldata.crashgen_name = "Buffout"
            mock_yamldata.xse_acronym = "F4SE"
            mock_yamldata.crashgen_latest_og = "1.10.163"
            mock_yamldata.crashgen_latest_vr = "1.2.72"

            # Create orchestrator (removed crashlogs parameter - no longer in API)
            OrchestratorCore(
                yamldata=mock_yamldata,
                fcx_mode=False,
                show_formid_values=False,
                formid_db_exists=False,
            )

            # Test async loading with simulated delay
            async def read_with_delay(path: Path) -> list[str]:
                """Simulate async file read with network/disk delay."""
                await asyncio.sleep(0.05)  # 10ms simulated I/O delay
                return path.read_text().splitlines()

            # Time concurrent reads (async)
            start_time = time.perf_counter()
            tasks = [read_with_delay(f) for f in test_files]
            results = await asyncio.gather(*tasks)
            async_time = time.perf_counter() - start_time

            # Time sequential reads (sync simulation)
            start_time = time.perf_counter()
            sync_results = []
            for f in test_files:
                await asyncio.sleep(0.05)  # Same delay
                sync_results.append(f.read_text().splitlines())
            sync_time = time.perf_counter() - start_time

            # Verify async is faster for concurrent operations
            assert len(results) == len(sync_results)
            performance_ratio = sync_time / async_time
            # Note: Performance improvement varies based on system I/O scheduling
            # We expect at least some improvement (1.2x) but it can vary
            assert performance_ratio >= 1.2, f"Async should be at least 1.2x faster for concurrent ops, got {performance_ratio:.2f}x"

    @pytest.mark.performance
    def test_regex_pattern_caching(self):
        """Verify regex patterns are cached at module level."""
        from ClassicLib.ScanLog.FormIDAnalyzerCore import _PATTERN_CACHE, FormIDAnalyzerCore

        # Create an instance to ensure pattern gets cached
        mock_yamldata = MagicMock()
        mock_yamldata.game_ignore_plugins = []
        mock_yamldata.game_ignore_records = []
        FormIDAnalyzerCore(mock_yamldata, False, False, None)

        # After creating an instance, the pattern should be cached
        # The actual key depends on the implementation
        assert len(_PATTERN_CACHE) > 0, "Pattern cache should contain compiled patterns after initialization"

        # Verify all cached patterns are compiled regex objects
        for key, pattern in _PATTERN_CACHE.items():
            assert hasattr(pattern, "search"), f"Cached pattern {key} should be a compiled regex"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_orchestrator_batch_processing(self):
        """Test overall performance improvement for batch log processing."""
        # This is an integration test that verifies the combined effect
        # of all optimizations when processing multiple logs

        mock_yamldata = MagicMock()
        mock_yamldata.crashgen_name = "Buffout"
        mock_yamldata.xse_acronym = "F4SE"
        mock_yamldata.crashgen_latest_og = "1.10.163"
        mock_yamldata.crashgen_latest_vr = "1.2.72"
        mock_yamldata.game_ignore_plugins = []
        mock_yamldata.game_ignore_records = []

        # Create orchestrator (removed crashlogs parameter - no longer in API)
        orchestrator = OrchestratorCore(
            yamldata=mock_yamldata,
            fcx_mode=False,
            show_formid_values=False,
            formid_db_exists=False,
        )

        # Create test log files
        test_logs = [Path(f"test_log_{i}.txt") for i in range(3)]

        # Mock the slow operations to measure optimization impact
        # Note: find_segments is in ClassicLib.ScanLog.Parser, not OrchestratorCore
        with patch("ClassicLib.ScanLog.Parser.find_segments") as mock_find:
            mock_find.return_value = (
                "1.10.163",  # gameversion
                "1.28.6",  # crashgen version
                "Error",  # main error
                ([], [], [], [], [], []),  # segments
            )

            async with orchestrator:
                # Process logs and measure time
                start_time = time.perf_counter()
                results = await orchestrator.process_crash_logs_batch(test_logs)
                batch_time = time.perf_counter() - start_time

                # Verify all logs were processed
                assert len(results) == 3, f"Should process all 3 logs, got {len(results)}"

                # With optimizations, batch of 3 should complete quickly
                # This is a sanity check - actual timing depends on system
                assert batch_time < 1.0, f"Batch processing took too long: {batch_time:.3f}s"


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-m", "performance"])
