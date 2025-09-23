"""
Integration tests for async_yaml_batch - integration logic testing.

This file contains integration tests that test interactions between components.
"""

import asyncio
from pathlib import Path

import pytest
import ruamel.yaml

pytestmark = pytest.mark.integration

@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncYamlBatchOperations:
    """Test suite for batch and concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_loads(self, async_yaml_core, tmp_path):
        """Test concurrent YAML loading."""
        files = []
        for i in range(5):
            yaml_file = tmp_path / f'test_{i}.yaml'
            data = {'index': i, 'value': f'test_{i}'}
            yaml = ruamel.yaml.YAML()
            with Path(yaml_file).open('w') as f:
                yaml.dump(data, f)
            files.append(yaml_file)
        tasks = [async_yaml_core.file_ops.load_yaml_file(f) for f in files]
        results = await asyncio.gather(*tasks)
        for i, result in enumerate(results):
            assert result['index'] == i
            assert result['value'] == f'test_{i}'
