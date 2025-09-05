"""
Tests for async caching components.

This module contains tests for caching implementations used in the async pipeline,
including AsyncCacheBase and related caching utilities.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import asyncio
import time

import pytest

from ClassicLib.AsyncCore.base import AsyncCacheBase, AsyncFileProcessor


class TestAsyncCacheBase:
    """Test AsyncCacheBase class"""

    @pytest.mark.asyncio
    async def test_basic_cache_operations(self):
        """Test basic cache get/set operations"""

        class TestCache(AsyncCacheBase):
            async def _load_value(self, key):
                # Simulate loading delay
                await asyncio.sleep(0.001)
                return f"loaded_{key}"

        cache = TestCache()

        # First access should load
        value1 = await cache.get("key1")
        assert value1 == "loaded_key1"

        # Second access should use cache
        start = time.perf_counter()
        value2 = await cache.get("key1")
        elapsed = time.perf_counter() - start
        assert value2 == "loaded_key1"
        assert elapsed < 0.001  # Should be instant from cache

    @pytest.mark.asyncio
    async def test_cache_ttl(self):
        """Test cache time-to-live functionality"""

        class TestCache(AsyncCacheBase):
            def __init__(self):
                super().__init__(ttl=0.05)  # 50ms TTL
                self.load_count = 0

            async def _load_value(self, key):
                self.load_count += 1
                return f"loaded_{key}_{self.load_count}"

        cache = TestCache()

        # First load
        value1 = await cache.get("key1")
        assert value1 == "loaded_key1_1"
        assert cache.load_count == 1

        # Should use cache
        value2 = await cache.get("key1")
        assert value2 == "loaded_key1_1"
        assert cache.load_count == 1

        # Wait for TTL to expire
        await asyncio.sleep(0.06)

        # Should reload
        value3 = await cache.get("key1")
        assert value3 == "loaded_key1_2"
        assert cache.load_count == 2

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """Test cache invalidation"""

        class TestCache(AsyncCacheBase):
            def __init__(self):
                super().__init__()
                self.version = 1

            async def _load_value(self, key):
                return f"{key}_v{self.version}"

        cache = TestCache()

        # Load initial value
        value1 = await cache.get("key1")
        assert value1 == "key1_v1"

        # Change version and invalidate
        cache.version = 2
        await cache.invalidate("key1")

        # Should reload with new version
        value2 = await cache.get("key1")
        assert value2 == "key1_v2"

    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test clearing entire cache"""

        class TestCache(AsyncCacheBase):
            def __init__(self):
                super().__init__()
                self.load_count = 0

            async def _load_value(self, key):
                self.load_count += 1
                return f"loaded_{key}"

        cache = TestCache()

        # Load multiple keys
        await cache.get("key1")
        await cache.get("key2")
        await cache.get("key3")
        assert cache.load_count == 3

        # Clear cache
        await cache.clear()

        # All keys should reload
        await cache.get("key1")
        await cache.get("key2")
        await cache.get("key3")
        assert cache.load_count == 6

    @pytest.mark.asyncio
    async def test_cache_max_size(self):
        """Test cache maximum size limit"""

        class TestCache(AsyncCacheBase):
            def __init__(self):
                super().__init__(max_size=2)

            async def _load_value(self, key):
                return f"loaded_{key}"

        cache = TestCache()

        # Load 3 keys with max size of 2
        await cache.get("key1")
        await cache.get("key2")
        await cache.get("key3")

        # Cache should only have 2 items
        assert len(cache._cache) <= 2

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self):
        """Test concurrent access to same cache key"""

        class TestCache(AsyncCacheBase):
            def __init__(self):
                super().__init__()
                self.load_count = 0

            async def _load_value(self, key):
                self.load_count += 1
                await asyncio.sleep(0.01)  # Simulate slow load
                return f"loaded_{key}"

        cache = TestCache()

        # Launch multiple concurrent requests for same key
        tasks = [cache.get("key1") for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # All should get same value
        assert all(r == "loaded_key1" for r in results)
        # Should only load once despite concurrent access
        assert cache.load_count == 1


class TestAsyncFileProcessor:
    """Test AsyncFileProcessor class"""

    @pytest.mark.asyncio
    async def test_file_processor_caching(self, tmp_path):
        """Test file processor with caching"""

        class TestFileProcessor(AsyncFileProcessor):
            async def process_file(self, file_path):
                content = file_path.read_text()
                return content.upper()

        # Create test files
        file1 = tmp_path / "file1.txt"
        file1.write_text("hello world")

        file2 = tmp_path / "file2.txt"
        file2.write_text("goodbye world")

        processor = TestFileProcessor(cache_enabled=True)

        # First process should read and cache
        result1 = await processor.process(file1)
        assert result1 == "HELLO WORLD"

        # Second process should use cache
        start = time.perf_counter()
        result2 = await processor.process(file1)
        elapsed = time.perf_counter() - start
        assert result2 == "HELLO WORLD"
        assert elapsed < 0.001  # Should be instant from cache

    @pytest.mark.asyncio
    async def test_file_processor_batch(self, tmp_path):
        """Test batch file processing"""

        class TestFileProcessor(AsyncFileProcessor):
            async def process_file(self, file_path):
                content = file_path.read_text()
                return len(content)

        # Create test files
        files = []
        for i in range(5):
            file = tmp_path / f"file{i}.txt"
            file.write_text("x" * (i + 1))
            files.append(file)

        processor = TestFileProcessor()
        results = await processor.process_batch(files)

        assert results == [1, 2, 3, 4, 5]

    @pytest.mark.asyncio
    async def test_file_processor_error_handling(self, tmp_path):
        """Test file processor error handling"""

        class TestFileProcessor(AsyncFileProcessor):
            async def process_file(self, file_path):
                if "error" in file_path.name:
                    raise ValueError(f"Error processing {file_path.name}")
                return file_path.name

        # Create test files
        file1 = tmp_path / "good.txt"
        file1.write_text("content")

        file2 = tmp_path / "error.txt"
        file2.write_text("content")

        file3 = tmp_path / "also_good.txt"
        file3.write_text("content")

        processor = TestFileProcessor()

        # Process with skip_errors
        results = await processor.process_batch(
            [file1, file2, file3], skip_errors=True
        )

        # Should skip error file
        assert len(results) == 2
        assert "good.txt" in results
        assert "also_good.txt" in results
        assert "error.txt" not in results

    @pytest.mark.asyncio
    async def test_file_processor_cache_invalidation(self, tmp_path):
        """Test file processor cache invalidation on file change"""

        class TestFileProcessor(AsyncFileProcessor):
            async def process_file(self, file_path):
                content = file_path.read_text()
                return len(content)

        file = tmp_path / "changing.txt"
        file.write_text("initial")

        processor = TestFileProcessor(cache_enabled=True)

        # Process initial file
        result1 = await processor.process(file)
        assert result1 == 7  # len("initial")

        # Modify file
        file.write_text("modified content")

        # Should detect change and reprocess
        result2 = await processor.process(file)
        assert result2 == 16  # len("modified content")
