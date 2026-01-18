"""Tests for caching and TTL behavior in AsyncYamlSettingsCore."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, F841

import time

import pytest
import ruamel.yaml

# Note: async_yaml_core and temp_yaml_file fixtures are provided by
# tests/fixtures/yaml_fixtures.py via the root conftest.py


class TestAsyncYamlCaching:
    """Test suite for caching and TTL functionality."""

    @pytest.mark.asyncio
    async def test_ttl_cache_invalidation(self, async_yaml_core, temp_yaml_file):
        """Test TTL-based cache invalidation for dynamic files."""
        import aiofiles

        # Load file first time using file_ops
        data1 = await async_yaml_core.file_ops.load_yaml_file(temp_yaml_file)
        original_value = data1["test_settings"]["string_value"]

        # Modify the file - using async I/O
        yaml = ruamel.yaml.YAML()
        async with aiofiles.open(temp_yaml_file) as f:
            content = await f.read()
            data = yaml.load(content)
        data["test_settings"]["string_value"] = "modified"
        from io import StringIO

        stream = StringIO()
        yaml.dump(data, stream)
        async with aiofiles.open(temp_yaml_file, mode="w") as f:
            await f.write(stream.getvalue())

        # Clear both FileIOCore cache and YAML cache to force reload
        async_yaml_core.file_ops.io_core.clear_cache()
        await async_yaml_core.clear_cache()

        # After cache clear, should reload from file
        data3 = await async_yaml_core.file_ops.load_yaml_file(temp_yaml_file)
        assert data3["test_settings"]["string_value"] == "modified"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cache_hit_performance(self, async_yaml_core, temp_yaml_file, monkeypatch):
        """Test performance of cache hits."""
        from ClassicLib.Constants import YAML

        # Mock get_path_for_store to return our test file
        def mock_get_path(store):
            return temp_yaml_file

        monkeypatch.setattr(async_yaml_core.file_ops, "get_path_for_store", mock_get_path)

        # Prime the cache
        await async_yaml_core.async_yaml_settings(str, YAML.TEST, "test_settings.string_value")

        # Time 1000 cache hits
        start = time.time()
        for _ in range(1000):
            await async_yaml_core.async_yaml_settings(str, YAML.TEST, "test_settings.string_value")
        elapsed = time.time() - start

        # Cache hits should be very fast (adjust for system variance)
        assert elapsed < 0.5, f"1000 cache hits took {elapsed:.2f}s, expected < 0.5s"
