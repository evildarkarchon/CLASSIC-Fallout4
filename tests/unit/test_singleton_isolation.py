"""
Tests to verify that singleton isolation fixtures are working correctly.

These tests ensure that our test fixtures properly isolate singletons
and caches between test runs to prevent test pollution.
"""

import pytest

from ClassicLib.ScanLog.AsyncUtil import DatabasePoolManager
from ClassicLib.Utils.version_utils import crashgen_version_gen


class TestSingletonIsolation:
    """Test suite to verify singleton and cache isolation."""

    @pytest.mark.unit
    def test_database_pool_manager_starts_clean(self, verify_database_pool_isolation):
        """Verify DatabasePoolManager singleton starts in clean state."""
        # The fixture verifies clean state, so just check we can create instance
        manager = DatabasePoolManager()
        assert manager is not None
        # Verify no pool exists yet
        assert manager._pool is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_database_pool_manager_isolation_between_tests_1(self):
        """First test to verify singleton isolation - creates pool."""
        manager = DatabasePoolManager()
        # Mark this instance for identification
        manager._test_marker = "test_1"

        # Note: We don't actually create a pool here to avoid database dependencies
        # Just verify the singleton works
        assert manager._test_marker == "test_1"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_database_pool_manager_isolation_between_tests_2(self):
        """Second test to verify singleton isolation - should have fresh instance."""
        manager = DatabasePoolManager()

        # Should not have the marker from previous test
        assert not hasattr(manager, '_test_marker'), "Singleton not properly isolated between tests"

        # Set a different marker
        manager._test_marker = "test_2"
        assert manager._test_marker == "test_2"

    @pytest.mark.unit
    def test_version_cache_starts_empty(self, verify_version_cache_empty):
        """Verify version cache starts empty."""
        # The fixture verifies empty cache
        # Parse a version to confirm cache works
        version = crashgen_version_gen("1.10.163.0")
        assert str(version) == "1.10.163.0"

        # Check cache now has one entry
        cache_info = crashgen_version_gen.cache_info()
        assert cache_info.currsize == 1
        assert cache_info.misses == 1
        assert cache_info.hits == 0

    @pytest.mark.unit
    def test_version_cache_isolation_between_tests_1(self):
        """First test to verify cache isolation - populates cache."""
        # Parse several versions
        for _ in range(5):
            crashgen_version_gen("1.28.6")

        cache_info = crashgen_version_gen.cache_info()
        assert cache_info.currsize == 1  # Only one unique version
        assert cache_info.hits == 4  # First miss, then 4 hits
        assert cache_info.misses == 1

    @pytest.mark.unit
    def test_version_cache_isolation_between_tests_2(self):
        """Second test to verify cache isolation - should start empty."""
        # Cache should be empty due to fixture cleanup
        cache_info = crashgen_version_gen.cache_info()
        assert cache_info.currsize == 0, "Cache not properly cleared between tests"
        assert cache_info.hits == 0, "Cache hits not reset between tests"
        assert cache_info.misses == 0, "Cache misses not reset between tests"

        # Parse a different version
        crashgen_version_gen("1.2.72")
        cache_info = crashgen_version_gen.cache_info()
        assert cache_info.currsize == 1
        assert cache_info.misses == 1
        assert cache_info.hits == 0

    @pytest.mark.unit
    def test_populated_version_cache_fixture(self, populated_version_cache):
        """Test that populated_version_cache fixture works correctly."""
        # Cache should be pre-populated
        cache_info = crashgen_version_gen.cache_info()
        assert cache_info.currsize == len(set(populated_version_cache))

        # Parsing a cached version should result in a hit
        version = crashgen_version_gen("1.10.163.0")
        assert str(version) == "1.10.163.0"

        cache_info = crashgen_version_gen.cache_info()
        assert cache_info.hits >= 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_mock_database_pool_manager_fixture(self, mock_database_pool_manager):
        """Test that mock_database_pool_manager fixture works correctly."""
        manager = DatabasePoolManager()
        pool = await manager.get_pool()

        # Should be our mock pool
        assert pool is not None
        # Mock methods should be available
        result = await pool.get_entry("test_formid", "test_plugin")
        assert result is None  # Mock returns None by default

    @pytest.mark.unit
    def test_track_version_cache_usage_fixture(self, track_version_cache_usage):
        """Test that track_version_cache_usage fixture works correctly."""
        # Get initial stats (should be empty)
        stats = track_version_cache_usage()
        assert stats['size'] == 0
        assert stats['hits'] == 0
        assert stats['misses'] == 0

        # Parse some versions
        crashgen_version_gen("1.28.6")
        crashgen_version_gen("1.28.6")  # Should hit cache
        crashgen_version_gen("1.10.163")  # New version

        # Check stats
        stats = track_version_cache_usage()
        assert stats['size'] == 2
        assert stats['hits'] == 1
        assert stats['misses'] == 2
        assert stats['hit_rate'] == 1/3


class TestParallelIsolation:
    """Tests specifically for parallel execution isolation."""

    @pytest.mark.unit
    @pytest.mark.parametrize("iteration", range(3))
    def test_singleton_isolation_in_parallel(self, iteration):
        """Test that singletons are isolated even in parallel execution."""
        # Each parallel execution should get a clean singleton
        manager = DatabasePoolManager()

        # Set a unique marker
        manager._parallel_marker = f"parallel_{iteration}"

        # Verify it's set correctly
        assert manager._parallel_marker == f"parallel_{iteration}"

        # In next iteration, should not see previous markers
        # (This is ensured by the fixture, but let's verify)
        for i in range(3):
            if i != iteration:
                assert not hasattr(manager, f"_parallel_marker_{i}")

    @pytest.mark.unit
    @pytest.mark.parametrize("version_str", ["1.28.6", "1.10.163", "1.2.72"])
    def test_cache_isolation_in_parallel(self, version_str):
        """Test that caches are isolated in parallel execution."""
        # Each parallel test should start with empty cache
        cache_info = crashgen_version_gen.cache_info()
        assert cache_info.currsize == 0, f"Cache not empty for {version_str} test"

        # Parse the version
        version = crashgen_version_gen(version_str)
        assert version is not None

        # Should have exactly one entry
        cache_info = crashgen_version_gen.cache_info()
        assert cache_info.currsize == 1
        assert cache_info.misses == 1
        assert cache_info.hits == 0
