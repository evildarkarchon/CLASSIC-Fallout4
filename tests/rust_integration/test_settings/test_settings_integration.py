"""Integration tests for classic-settings Rust module.

This module tests the YAML settings cache with both synchronous and asynchronous APIs.
Tests verify thread safety, cache operations, and Rust acceleration.
"""

import asyncio
from pathlib import Path
from typing import Any

import pytest

# Declare with Any type to satisfy static analysis while allowing dynamic import
classic_settings: Any = None
try:
    import classic_settings  # type: ignore[no-redef]

    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.rust,
    pytest.mark.skipif(not RUST_AVAILABLE, reason="classic_settings not available"),
]


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before and after each test."""
    if RUST_AVAILABLE:
        classic_settings.clear_cache()
    yield
    if RUST_AVAILABLE:
        classic_settings.clear_cache()


@pytest.fixture
def test_yaml(tmp_path):
    """Create a temporary test YAML file."""
    temp_file = tmp_path / "test_settings.yaml"
    content = """game: Fallout4
version: 1.0
settings:
  resolution:
    width: 1920
    height: 1080
  graphics:
    quality: ultra
    vsync: true
"""
    temp_file.write_text(content)
    return str(temp_file)


@pytest.fixture
def multi_yaml(tmp_path):
    """Create multiple temporary YAML files."""
    files = []
    for i in range(3):
        file_path = tmp_path / f"config_{i}.yaml"
        file_path.write_text(f"config: config_{i}\nvalue: {i * 10}\n")
        files.append(str(file_path))
    return files


class TestSyncLoading:
    """Test synchronous loading functions."""

    def test_load_settings_sync(self, test_yaml):
        """Test loading YAML file synchronously."""
        docs = classic_settings.load_settings_sync("test_config", test_yaml)

        assert isinstance(docs, list)
        assert len(docs) == 1

        doc = docs[0]
        assert isinstance(doc, dict)
        assert doc["game"] == "Fallout4"
        assert doc["version"] == 1.0
        assert "settings" in doc

    def test_load_settings_sync_caches_correctly(self, test_yaml):
        """Test that sync loading caches the result."""
        classic_settings.load_settings_sync("cached_test", test_yaml)

        assert classic_settings.is_cached("cached_test")
        assert classic_settings.cache_size() == 1

        # Verify we can retrieve cached data
        cached = classic_settings.get_cached("cached_test")
        assert cached is not None
        assert cached[0]["game"] == "Fallout4"

    def test_load_batch_sync(self, multi_yaml):
        """Test batch loading multiple files synchronously."""
        count = classic_settings.load_batch_sync(multi_yaml)

        assert count == 3
        assert classic_settings.cache_size() == 3

        # Verify all files are cached
        for path in multi_yaml:
            assert classic_settings.is_cached(path)

    def test_load_settings_sync_file_not_found(self):
        """Test error handling for non-existent file."""
        with pytest.raises(OSError):
            classic_settings.load_settings_sync("bad_key", "nonexistent.yaml")

    def test_load_settings_sync_invalid_yaml(self, tmp_path):
        """Test error handling for invalid YAML."""
        temp_file = tmp_path / "invalid.yaml"
        temp_file.write_text("invalid:\n\t- yaml\n")  # Tabs are invalid in YAML

        with pytest.raises(OSError):  # Parse errors are OSError
            classic_settings.load_settings_sync("invalid", str(temp_file))


class TestAsyncLoading:
    """Test asynchronous loading functions."""

    @pytest.mark.asyncio
    async def test_load_settings_async(self, test_yaml):
        """Test loading YAML file asynchronously."""
        docs = await classic_settings.load_settings_async("async_test", test_yaml)

        assert isinstance(docs, list)
        assert len(docs) == 1

        doc = docs[0]
        assert isinstance(doc, dict)
        assert doc["game"] == "Fallout4"
        assert doc["version"] == 1.0

    @pytest.mark.asyncio
    async def test_load_settings_async_caches_correctly(self, test_yaml):
        """Test that async loading caches the result."""
        await classic_settings.load_settings_async("async_cached", test_yaml)

        assert classic_settings.is_cached("async_cached")
        assert classic_settings.cache_size() == 1

        # Verify we can retrieve cached data
        cached = classic_settings.get_cached("async_cached")
        assert cached is not None
        assert cached[0]["game"] == "Fallout4"

    @pytest.mark.asyncio
    async def test_load_batch_async(self, multi_yaml):
        """Test batch loading multiple files asynchronously."""
        count = await classic_settings.load_batch_async(multi_yaml)

        assert count == 3
        assert classic_settings.cache_size() == 3

        # Verify all files are cached
        for path in multi_yaml:
            assert classic_settings.is_cached(path)

    @pytest.mark.asyncio
    async def test_load_settings_async_file_not_found(self):
        """Test async error handling for non-existent file."""
        with pytest.raises(OSError):
            await classic_settings.load_settings_async("bad_key", "nonexistent.yaml")

    @pytest.mark.asyncio
    async def test_concurrent_async_loads(self, multi_yaml):
        """Test concurrent async loads."""
        tasks = [classic_settings.load_settings_async(f"concurrent_{i}", path) for i, path in enumerate(multi_yaml)]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert classic_settings.cache_size() == 3

        for i, docs in enumerate(results):
            assert docs[0]["value"] == i * 10


class TestCacheOperations:
    """Test cache management operations."""

    def test_is_cached(self, test_yaml):
        """Test is_cached function."""
        assert not classic_settings.is_cached("not_loaded")

        classic_settings.load_settings_sync("loaded", test_yaml)
        assert classic_settings.is_cached("loaded")

    def test_get_cached(self, test_yaml):
        """Test get_cached function."""
        assert classic_settings.get_cached("not_loaded") is None

        classic_settings.load_settings_sync("loaded", test_yaml)
        cached = classic_settings.get_cached("loaded")

        assert cached is not None
        assert isinstance(cached, list)
        assert cached[0]["game"] == "Fallout4"

    def test_invalidate(self, test_yaml):
        """Test invalidate function."""
        classic_settings.load_settings_sync("to_invalidate", test_yaml)
        assert classic_settings.is_cached("to_invalidate")

        result = classic_settings.invalidate("to_invalidate")
        assert result is True
        assert not classic_settings.is_cached("to_invalidate")

        # Second invalidate should return False
        result = classic_settings.invalidate("to_invalidate")
        assert result is False

    def test_clear_cache(self, multi_yaml):
        """Test clear_cache function."""
        classic_settings.load_batch_sync(multi_yaml)
        assert classic_settings.cache_size() == 3

        classic_settings.clear_cache()
        assert classic_settings.cache_size() == 0

    def test_cache_size(self, multi_yaml):
        """Test cache_size function."""
        assert classic_settings.cache_size() == 0

        for i, path in enumerate(multi_yaml):
            classic_settings.load_settings_sync(f"key_{i}", path)
            assert classic_settings.cache_size() == i + 1

    def test_cache_keys(self, multi_yaml):
        """Test cache_keys function."""
        keys = ["key_0", "key_1", "key_2"]
        for key, path in zip(keys, multi_yaml):
            classic_settings.load_settings_sync(key, path)

        cached_keys = classic_settings.cache_keys()
        assert len(cached_keys) == 3
        assert set(cached_keys) == set(keys)


class TestYamlParsing:
    """Test YAML parsing accuracy."""

    def test_parse_nested_dict(self, test_yaml):
        """Test parsing nested dictionaries."""
        docs = classic_settings.load_settings_sync("nested", test_yaml)
        doc = docs[0]

        assert "settings" in doc
        assert isinstance(doc["settings"], dict)
        assert "resolution" in doc["settings"]
        assert doc["settings"]["resolution"]["width"] == 1920
        assert doc["settings"]["resolution"]["height"] == 1080

    def test_parse_bool_values(self, test_yaml):
        """Test parsing boolean values."""
        docs = classic_settings.load_settings_sync("bool_test", test_yaml)
        doc = docs[0]

        assert doc["settings"]["graphics"]["vsync"] is True

    def test_parse_numeric_values(self, test_yaml):
        """Test parsing numeric values."""
        docs = classic_settings.load_settings_sync("numeric", test_yaml)
        doc = docs[0]

        assert isinstance(doc["version"], (int, float))
        assert doc["version"] == 1.0
        assert isinstance(doc["settings"]["resolution"]["width"], int)
        assert doc["settings"]["resolution"]["width"] == 1920

    def test_parse_string_values(self, test_yaml):
        """Test parsing string values."""
        docs = classic_settings.load_settings_sync("string", test_yaml)
        doc = docs[0]

        assert isinstance(doc["game"], str)
        assert doc["game"] == "Fallout4"
        assert isinstance(doc["settings"]["graphics"]["quality"], str)
        assert doc["settings"]["graphics"]["quality"] == "ultra"

    def test_parse_lists(self, tmp_path):
        """Test parsing lists."""
        temp_file = tmp_path / "list_test.yaml"
        temp_file.write_text("items:\n  - item1\n  - item2\n  - item3\n")

        docs = classic_settings.load_settings_sync("list_test", str(temp_file))
        doc = docs[0]

        assert "items" in doc
        assert isinstance(doc["items"], list)
        assert len(doc["items"]) == 3
        assert doc["items"][0] == "item1"

    def test_parse_multi_document_yaml(self, tmp_path):
        """Test parsing YAML with multiple documents."""
        temp_file = tmp_path / "multi_doc.yaml"
        temp_file.write_text("---\ndoc: 1\n---\ndoc: 2\n")

        docs = classic_settings.load_settings_sync("multi_doc", str(temp_file))

        assert len(docs) == 2
        assert docs[0]["doc"] == 1
        assert docs[1]["doc"] == 2


class TestThreadSafety:
    """Test thread safety of cache operations."""

    @pytest.mark.slow
    def test_concurrent_sync_loads(self, multi_yaml):
        """Test concurrent sync loads from multiple threads."""
        import concurrent.futures

        def load_file(index, path):
            """Load a file with a unique key."""
            return classic_settings.load_settings_sync(f"thread_{index}", path)

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(load_file, i, path) for i, path in enumerate(multi_yaml)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 3
        assert classic_settings.cache_size() == 3

    @pytest.mark.slow
    def test_concurrent_cache_access(self, test_yaml):
        """Test concurrent cache access from multiple threads."""
        import concurrent.futures

        # Pre-load the cache
        classic_settings.load_settings_sync("shared", test_yaml)

        def access_cache():
            """Access cached data."""
            return classic_settings.get_cached("shared")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(access_cache) for _ in range(100)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All results should be the same
        assert all(r is not None for r in results)
        assert all(r[0]["game"] == "Fallout4" for r in results)


class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.slow
    def test_cache_hit_performance(self, test_yaml):
        """Test that cache hits are fast."""
        import time

        # Load once
        classic_settings.load_settings_sync("perf_test", test_yaml)

        # Time cache hits
        start = time.perf_counter()
        for _ in range(1000):
            classic_settings.get_cached("perf_test")
        elapsed = time.perf_counter() - start

        # Should be very fast (< 10ms for 1000 accesses)
        assert elapsed < 0.01

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_batch_async_faster_than_sequential(self, multi_yaml):
        """Test that batch async is faster than sequential loading."""
        import time

        # Sequential loading
        start = time.perf_counter()
        for i, path in enumerate(multi_yaml):
            await classic_settings.load_settings_async(f"seq_{i}", path)
        sequential_time = time.perf_counter() - start

        classic_settings.clear_cache()

        # Batch loading
        start = time.perf_counter()
        await classic_settings.load_batch_async(multi_yaml)
        batch_time = time.perf_counter() - start

        # Batch should be faster (or at least not significantly slower)
        # Allow some variance due to I/O overhead
        assert batch_time <= sequential_time * 1.5


class TestModuleInfo:
    """Test module information and Rust acceleration detection."""

    def test_module_imported(self):
        """Test that classic_settings module is available."""
        assert classic_settings is not None

    def test_all_functions_available(self):
        """Test that all expected functions are available."""
        expected_functions = [
            "load_settings_sync",
            "load_settings_async",
            "load_batch_sync",
            "load_batch_async",
            "get_cached",
            "is_cached",
            "invalidate",
            "clear_cache",
            "cache_size",
            "cache_keys",
        ]

        for func_name in expected_functions:
            assert hasattr(classic_settings, func_name)
            assert callable(getattr(classic_settings, func_name))

    def test_rust_acceleration_active(self):
        """Test that Rust acceleration is being used."""

        # The module should be in a directory with a .pyd file
        assert hasattr(classic_settings, "__file__")
        module_dir = Path(classic_settings.__file__).parent

        # Check if there's a .pyd file in the module directory
        pyd_files = list(module_dir.glob("*.pyd"))
        assert len(pyd_files) > 0, f"No .pyd files found in {module_dir}"
