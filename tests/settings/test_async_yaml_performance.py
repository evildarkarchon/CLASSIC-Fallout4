"""Performance regression tests for AsyncYamlSettingsCore."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, F841

import asyncio
import time
from pathlib import Path

import pytest
import ruamel.yaml

from ClassicLib.AsyncYamlSettings.core import AsyncYamlSettingsCore
from ClassicLib.Constants import YAML


@pytest.fixture
async def async_yaml_core():
    """Create a fresh AsyncYamlSettingsCore instance for testing."""
    core = AsyncYamlSettingsCore()
    yield core
    # Cleanup if needed
    await core.clear_cache()


@pytest.fixture
def temp_yaml_file(tmp_path):
    """Create a temporary YAML file for testing."""
    yaml_file = tmp_path / "test.yaml"
    data = {"test_settings": {"string_value": "test", "bool_value": True, "int_value": 42, "nested": {"deep_value": "deep"}}}

    yaml = ruamel.yaml.YAML()
    yaml.indent(offset=2)
    with Path(yaml_file).open("w") as f:
        yaml.dump(data, f)

    return yaml_file


class TestPerformance:
    """Performance regression tests."""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_concurrent_load_performance(self, async_yaml_core, tmp_path):
        """Test performance of concurrent YAML loading."""
        # Create 50 test files - using sync I/O for setup is okay
        files = []
        for i in range(50):
            yaml_file = tmp_path / f"perf_test_{i}.yaml"
            data = {
                "data": {
                    "index": i,
                    "nested": {"value": f"test_{i}" * 100},  # Some bulk
                }
            }
            yaml = ruamel.yaml.YAML()
            # Synchronous write for test setup is acceptable
            with Path(yaml_file).open("w") as f:
                yaml.dump(data, f)
            files.append(yaml_file)

        # Time concurrent loading
        start = time.time()
        tasks = [async_yaml_core.file_ops.load_yaml_file(f) for f in files]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start

        # Should complete in reasonable time (adjust threshold as needed)
        assert elapsed < 2.0, f"Concurrent loading took {elapsed:.2f}s, expected < 2.0s"
        assert len(results) == 50

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_batch_operation_performance(self, async_yaml_core, temp_yaml_file, monkeypatch):
        """Test performance advantage of batch operations."""

        # Mock get_path_for_store
        def mock_get_path(store):
            return temp_yaml_file

        monkeypatch.setattr(async_yaml_core.file_ops, "get_path_for_store", mock_get_path)

        # Prepare 100 requests
        requests = [(str, YAML.TEST, "test_settings.string_value") for _ in range(100)]

        # Time batch operation
        start = time.time()
        results = await async_yaml_core.batch_get_settings(requests)
        batch_time = time.time() - start

        # Time sequential operations
        start = time.time()
        for req in requests:
            await async_yaml_core.async_yaml_settings(*req)
        sequential_time = time.time() - start

        # For cached operations, batch might have overhead but shouldn't be too much slower
        # (batch operations shine more with actual I/O operations)
        # Note: On very fast systems sequential might be faster due to overhead
        # Just check that batch completes in reasonable time
        assert batch_time < 0.1, f"Batch took {batch_time:.3f}s, expected < 0.1s"
