"""Unit tests for ClassicLib.YamlSettings.async_.cache module.

This module tests the YamlCache class for YAML file caching with
modification detection, metrics tracking, and thread safety.
"""

import pytest
import asyncio
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class TestYamlCacheInitialization:
    """Tests for YamlCache initialization."""

    def test_initializes_empty_cache(self) -> None:
        """Test that YamlCache initializes with empty cache."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()

        assert cache.cache == {}

    def test_initializes_empty_file_mod_times(self) -> None:
        """Test that file modification times dict is empty initially."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()

        assert cache.file_mod_times == {}

    def test_initializes_empty_path_cache(self) -> None:
        """Test that path cache dict is empty initially."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()

        assert cache.path_cache == {}

    def test_initializes_empty_settings_cache(self) -> None:
        """Test that settings cache dict is empty initially."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()

        assert cache.settings_cache == {}

    def test_initializes_last_check_time_to_zero(self) -> None:
        """Test that last check time is initialized to zero."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()

        assert cache.last_check_time == 0

    def test_initializes_metrics(self) -> None:
        """Test that metrics are initialized with correct keys."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()
        metrics = cache.get_metrics()

        assert metrics["cache_hits"] == 0
        assert metrics["cache_misses"] == 0
        assert metrics["file_reloads"] == 0
        assert metrics["total_reads"] == 0


class TestYamlCacheGetFileLock:
    """Tests for get_file_lock method."""

    async def test_returns_asyncio_lock(self) -> None:
        """Test that get_file_lock returns an asyncio.Lock."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()

        lock = await cache.get_file_lock("/path/to/file.yaml")

        assert isinstance(lock, asyncio.Lock)

    async def test_returns_same_lock_for_same_path(self) -> None:
        """Test that same path gets same lock."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()
        file_path = "/path/to/file.yaml"

        lock1 = await cache.get_file_lock(file_path)
        lock2 = await cache.get_file_lock(file_path)

        assert lock1 is lock2

    async def test_returns_different_locks_for_different_paths(self) -> None:
        """Test that different paths get different locks."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()

        lock1 = await cache.get_file_lock("/path/to/file1.yaml")
        lock2 = await cache.get_file_lock("/path/to/file2.yaml")

        assert lock1 is not lock2


class TestYamlCacheCheckFileModification:
    """Tests for check_file_modification method."""

    async def test_returns_true_for_nonexistent_file(self, tmp_path: Path) -> None:
        """Test that nonexistent file returns True (needs reload)."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()
        nonexistent = tmp_path / "nonexistent.yaml"

        result = await cache.check_file_modification(nonexistent)

        assert result is True

    async def test_returns_true_for_new_file(self, tmp_path: Path) -> None:
        """Test that a new file (not in cache) returns True."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()
        test_file = tmp_path / "test.yaml"
        test_file.write_text("content: value")

        result = await cache.check_file_modification(test_file)

        assert result is True

    async def test_returns_false_for_unmodified_file(self, tmp_path: Path) -> None:
        """Test that unmodified file returns False on second check."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()
        test_file = tmp_path / "test.yaml"
        test_file.write_text("content: value")

        # First check - should return True and cache the mod time
        await cache.check_file_modification(test_file)
        # Set last_check_time to current time to avoid TTL expiration
        cache.last_check_time = time.time()

        # Second check - should return False
        result = await cache.check_file_modification(test_file)

        assert result is False

    async def test_returns_true_for_modified_file(self, tmp_path: Path) -> None:
        """Test that modified file returns True."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()
        test_file = tmp_path / "test.yaml"
        test_file.write_text("content: value1")

        # First check
        await cache.check_file_modification(test_file)
        cache.last_check_time = time.time()

        # Modify the file (need to wait a bit for different mtime)
        time.sleep(0.01)
        test_file.write_text("content: value2")

        result = await cache.check_file_modification(test_file)

        assert result is True

    async def test_returns_true_when_ttl_expired(self, tmp_path: Path) -> None:
        """Test that returns True when cache TTL has expired."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()
        # Set a very short TTL for testing
        original_ttl = YamlCache.CACHE_TTL
        YamlCache.CACHE_TTL = 0.001

        try:
            test_file = tmp_path / "test.yaml"
            test_file.write_text("content: value")

            # First check
            await cache.check_file_modification(test_file)

            # Wait for TTL to expire
            time.sleep(0.01)

            result = await cache.check_file_modification(test_file)

            # Should return True because TTL expired
            assert result is True
        finally:
            YamlCache.CACHE_TTL = original_ttl


class TestYamlCacheGetMetrics:
    """Tests for get_metrics method."""

    def test_returns_dict(self) -> None:
        """Test that get_metrics returns a dictionary."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()

        result = cache.get_metrics()

        assert isinstance(result, dict)

    def test_returns_copy(self) -> None:
        """Test that get_metrics returns a copy, not the original."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()

        metrics1 = cache.get_metrics()
        metrics1["cache_hits"] = 999

        metrics2 = cache.get_metrics()

        assert metrics2["cache_hits"] == 0

    def test_contains_expected_keys(self) -> None:
        """Test that metrics contain all expected keys."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()

        metrics = cache.get_metrics()

        expected_keys = {"cache_hits", "cache_misses", "file_reloads", "total_reads"}
        assert set(metrics.keys()) == expected_keys


class TestYamlCacheUpdateMetrics:
    """Tests for update_metrics method."""

    def test_increments_cache_hits(self) -> None:
        """Test incrementing cache_hits metric."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()

        cache.update_metrics("cache_hits")

        assert cache.get_metrics()["cache_hits"] == 1

    def test_increments_cache_misses(self) -> None:
        """Test incrementing cache_misses metric."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()

        cache.update_metrics("cache_misses")

        assert cache.get_metrics()["cache_misses"] == 1

    def test_increments_by_custom_value(self) -> None:
        """Test incrementing by custom value."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()

        cache.update_metrics("total_reads", 5)

        assert cache.get_metrics()["total_reads"] == 5

    def test_ignores_unknown_metric(self) -> None:
        """Test that unknown metric names are ignored."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()

        # Should not raise an error
        cache.update_metrics("unknown_metric")

        # Original metrics should be unchanged
        metrics = cache.get_metrics()
        assert all(v == 0 for v in metrics.values())


class TestYamlCacheClearCache:
    """Tests for clear_cache method."""

    def test_clears_all_caches_when_no_store(self) -> None:
        """Test clearing all caches when no store specified."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()
        cache.cache["test_store"] = {"key": "value"}
        cache.settings_cache[("type", "yaml", "key")] = "value"
        cache.path_cache[("yaml", "key")] = Path("/test")
        cache.file_mod_times["/test/file.yaml"] = 12345.0
        cache.last_check_time = 99999.0

        cache.clear_cache()

        assert cache.cache == {}
        assert cache.settings_cache == {}
        assert cache.path_cache == {}
        assert cache.file_mod_times == {}
        assert cache.last_check_time == 0

    def test_clears_specific_store(self) -> None:
        """Test clearing only specific store."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()
        cache.cache["store1"] = {"key": "value1"}
        cache.cache["store2"] = {"key": "value2"}

        cache.clear_cache("store1")

        assert "store1" not in cache.cache
        assert "store2" in cache.cache

    def test_preserves_other_caches_when_clearing_store(self) -> None:
        """Test that other caches are preserved when clearing specific store."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        cache = YamlCache()
        cache.cache["store1"] = {"key": "value"}
        cache.path_cache[("yaml", "key")] = Path("/test")
        cache.file_mod_times["/test/file.yaml"] = 12345.0

        cache.clear_cache("store1")

        # Path cache and file mod times should be preserved
        assert len(cache.path_cache) == 1
        assert len(cache.file_mod_times) == 1


class TestYamlCacheClassVariables:
    """Tests for YamlCache class variables."""

    def test_cache_ttl_default(self) -> None:
        """Test default CACHE_TTL value."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        assert YamlCache.CACHE_TTL == 300.0  # 5 minutes

    def test_cache_ttl_can_be_modified(self) -> None:
        """Test that CACHE_TTL can be modified."""
        from ClassicLib.YamlSettings.async_.cache import YamlCache

        original = YamlCache.CACHE_TTL
        try:
            YamlCache.CACHE_TTL = 600.0
            assert YamlCache.CACHE_TTL == 600.0
        finally:
            YamlCache.CACHE_TTL = original
