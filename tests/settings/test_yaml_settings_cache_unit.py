"""
Unit tests for yaml_settings_cache - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest
import ruamel.yaml
from ClassicLib.AsyncYamlSettings.core import AsyncYamlSettingsCore
from ClassicLib.Constants import YAML
from ClassicLib.MessageHandler import init_message_handler

pytestmark = pytest.mark.unit

class TestAsyncYamlEdgeCases:
    """Tests for AsyncYamlSettingsCore edge cases and specific scenarios."""

    @pytest.mark.asyncio
    async def test_empty_yaml_file_vs_none_handling(self, async_yaml_core, tmp_path: Path) -> None:
        """Test handling of empty YAML files vs files that parse to None."""
        empty_file = tmp_path / 'empty.yaml'
        empty_file.write_text('')
        comment_file = tmp_path / 'comments.yaml'
        comment_file.write_text('# Just a comment\n# Another comment')
        null_file = tmp_path / 'null.yaml'
        null_file.write_text('~')
        empty_result = await async_yaml_core.file_ops.load_yaml_file(empty_file)
        comment_result = await async_yaml_core.file_ops.load_yaml_file(comment_file)
        null_result = await async_yaml_core.file_ops.load_yaml_file(null_file)
        assert empty_result is None or empty_result == {}
        assert comment_result is None or comment_result == {}
        assert null_result is None or null_result == {}

    @pytest.mark.asyncio
    @pytest.mark.usefixtures('init_message_handler_fixture')
    async def test_deeply_nested_path_navigation(self, async_yaml_core, tmp_path: Path) -> None:
        """Test navigation through very deeply nested YAML structures."""
        deep_data = {'level1': {'level2': {'level3': {'level4': {'level5': {'level6': {'target': 'found', 'list': [{'item': 1}, {'item': 2}]}}}}}}}
        test_file = tmp_path / 'deep.yaml'
        yaml = ruamel.yaml.YAML()
        with open(test_file, 'w') as f:
            yaml.dump(deep_data, f)

        def mock_get_path(store):
            return test_file
        async_yaml_core.file_ops.get_path_for_store = mock_get_path
        result = await async_yaml_core.async_yaml_settings(str, YAML.TEST, 'level1.level2.level3.level4.level5.level6.target')
        assert result == 'found'
        result = await async_yaml_core.async_yaml_settings(str, YAML.TEST, 'level1.level2.level3.nonexistent.path')
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_yaml_with_recovery(self, async_yaml_core, tmp_path: Path) -> None:
        """Test handling of various invalid YAML formats with recovery attempts."""
        test_cases = [('bad_indent.yaml', 'key1:\n  subkey: value\n badindent: value'), ('unclosed_quote.yaml', 'key: "unclosed string'), ('invalid_anchor.yaml', 'key: &unknown\nref: *nonexistent')]
        for filename, content in test_cases:
            file_path = tmp_path / filename
            file_path.write_text(content)
            result = await async_yaml_core.file_ops.load_yaml_file(file_path)
            assert result == {}, f'Failed to handle {filename} gracefully'

    @pytest.mark.asyncio
    async def test_cache_metrics_accuracy(self, async_yaml_core, temp_yaml_file) -> None:
        """Test that cache metrics are accurately tracked."""
        result1 = await async_yaml_core.file_ops.load_yaml_file(temp_yaml_file)
        assert result1 is not None
        result2 = await async_yaml_core.file_ops.load_yaml_file(temp_yaml_file)
        assert result2 == result1

    @pytest.mark.asyncio
    async def test_settings_cache_vs_file_cache(self, async_yaml_core, tmp_path: Path) -> None:
        """Test the relationship between settings_cache and file cache."""
        test_file = tmp_path / 'cache_test.yaml'
        data = {'settings': {'value1': 'test', 'value2': 42}}
        yaml = ruamel.yaml.YAML()
        with open(test_file, 'w') as f:
            yaml.dump(data, f)

        def mock_get_path(store):
            return test_file
        async_yaml_core.file_ops.get_path_for_store = mock_get_path
        value1 = await async_yaml_core.async_yaml_settings(str, YAML.Main, 'settings.value1')
        assert value1 == 'test'
        cache_key = (str, YAML.Main, 'settings.value1')
        assert cache_key in async_yaml_core.cache.settings_cache
        assert async_yaml_core.cache.settings_cache[cache_key] == 'test'
        value2 = await async_yaml_core.async_yaml_settings(str, YAML.Main, 'settings.value1')
        assert value2 == 'test'
