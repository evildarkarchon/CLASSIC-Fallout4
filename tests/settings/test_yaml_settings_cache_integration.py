"""
Integration tests for yaml_settings_cache - integration logic testing.

This file contains integration tests that test interactions between components.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest
import ruamel.yaml
from ClassicLib.AsyncYamlSettings.core import AsyncYamlSettingsCore
from ClassicLib.Constants import YAML

# Note: MessageHandler initialization is now handled by standardized
# fixtures in tests/fixtures/registry_fixtures.py which provide:
# - message_handler: For non-GUI tests
# - gui_message_handler: For GUI tests (from qt_fixtures.py)
# - Automatic cleanup via ensure_message_handler_cleanup

pytestmark = pytest.mark.integration

class TestAsyncYamlEdgeCases:
    """Tests for AsyncYamlSettingsCore edge cases and specific scenarios."""

    @pytest.mark.asyncio
    async def test_multi_file_management_with_different_data(self, async_yaml_core, tmp_path) -> None:
        """Test managing multiple YAML files with different structures simultaneously."""
        files_data = {'config.yaml': {'app': {'name': 'test', 'version': '1.0'}}, 'settings.yaml': {'features': {'enabled': True, 'list': [1, 2, 3]}}, 'data.yaml': {'users': [{'id': 1, 'name': 'user1'}, {'id': 2, 'name': 'user2'}]}}
        yaml = ruamel.yaml.YAML()
        created_files = {}
        for filename, data in files_data.items():
            file_path = tmp_path / filename
            with open(file_path, 'w') as f:
                yaml.dump(data, f)
            created_files[filename] = file_path
        tasks = [async_yaml_core.file_ops.load_yaml_file(path) for path in created_files.values()]
        results = await asyncio.gather(*tasks)
        assert results[0]['app']['name'] == 'test'
        assert results[1]['features']['enabled'] is True
        assert len(results[2]['users']) == 2

    @pytest.mark.asyncio
    async def test_concurrent_writes_to_same_setting(self, async_yaml_core, tmp_path: Path) -> None:
        """Test concurrent write operations to the same setting."""
        test_file = tmp_path / 'concurrent.yaml'
        initial_data = {'counter': 0, 'values': {}}
        yaml = ruamel.yaml.YAML()
        with open(test_file, 'w') as f:
            yaml.dump(initial_data, f)

        def mock_get_path(store):
            return test_file
        async_yaml_core.file_ops.get_path_for_store = mock_get_path

        async def write_value(index):
            await async_yaml_core.async_yaml_settings(int, YAML.TEST, f'values.item_{index}', index)
            return index
        tasks = [write_value(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        assert sorted(results) == list(range(10))
        for i in range(10):
            value = await async_yaml_core.async_yaml_settings(int, YAML.TEST, f'values.item_{i}')
            assert value == i
