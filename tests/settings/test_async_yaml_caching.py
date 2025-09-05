"""Tests for caching and TTL behavior in AsyncYamlSettingsCore."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, F841

import time
from pathlib import Path
from unittest.mock import patch

import pytest
import ruamel.yaml

from ClassicLib.AsyncYamlSettingsCore import AsyncYamlSettingsCore


@pytest.fixture
async def async_yaml_core():
    """Create a fresh AsyncYamlSettingsCore instance for testing."""
    core = AsyncYamlSettingsCore()
    yield core
    # Cleanup if needed
    core.cache.clear()
    core.path_cache.clear()
    core.settings_cache.clear()


@pytest.fixture
def temp_yaml_file(tmp_path):
    """Create a temporary YAML file for testing."""
    yaml_file = tmp_path / "test.yaml"
    data = {"test_settings": {"string_value": "test", "bool_value": True, "int_value": 42, "nested": {"deep_value": "deep"}}}

    yaml = ruamel.yaml.YAML()
    yaml.indent(offset=2)
    with open(yaml_file, "w") as f:
        yaml.dump(data, f)

    return yaml_file


class TestAsyncYamlCaching:
    """Test suite for caching and TTL functionality."""

    @pytest.mark.asyncio
    async def test_ttl_cache_invalidation(self, async_yaml_core, temp_yaml_file):
        """Test TTL-based cache invalidation for dynamic files."""
        import aiofiles
        import aiofiles.os

        # Load file first time
        data1 = await async_yaml_core.load_yaml(temp_yaml_file)
        original_value = data1["test_settings"]["string_value"]

        # Modify the file - using async I/O
        yaml = ruamel.yaml.YAML()
        async with aiofiles.open(temp_yaml_file, mode='r') as f:
            content = await f.read()
            data = yaml.load(content)
        data["test_settings"]["string_value"] = "modified"
        from io import StringIO
        stream = StringIO()
        yaml.dump(data, stream)
        async with aiofiles.open(temp_yaml_file, mode='w') as f:
            await f.write(stream.getvalue())

        # Immediate load should still use cache
        data2 = await async_yaml_core.load_yaml(temp_yaml_file)
        assert data2["test_settings"]["string_value"] == original_value

        # Mock time to simulate TTL expiration
        with patch("time.time", return_value=time.time() + 10):
            # After TTL, should reload from file
            data3 = await async_yaml_core.load_yaml(temp_yaml_file)
            assert data3["test_settings"]["string_value"] == "modified"

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cache_hit_performance(self, async_yaml_core, temp_yaml_file):
        """Test performance of cache hits."""
        # Prime the cache
        await async_yaml_core.load_yaml(temp_yaml_file)

        # Time 1000 cache hits
        start = time.time()
        for _ in range(1000):
            await async_yaml_core.load_yaml(temp_yaml_file)
        elapsed = time.time() - start

        # Cache hits should be very fast (adjust for system variance)
        assert elapsed < 0.5, f"1000 cache hits took {elapsed:.2f}s, expected < 0.5s"
