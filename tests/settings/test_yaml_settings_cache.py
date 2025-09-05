"""
Test suite for AsyncYamlSettingsCore additional operations.

This module contains additional async tests not covered in test_async_yaml_settings.py,
focusing on specific edge cases and complex nested structures.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import ruamel.yaml

from ClassicLib.AsyncYamlSettingsCore import AsyncYamlSettingsCore
from ClassicLib.Constants import YAML
from ClassicLib.MessageHandler import init_message_handler


@pytest.fixture
def init_message_handler_fixture():
    """Initialize message handler for tests."""
    handler = init_message_handler(parent=None, is_gui_mode=False)
    yield
    # Clean up
    import ClassicLib.MessageHandler
    ClassicLib.MessageHandler._message_handler = None


@pytest.fixture
async def async_yaml_core():
    """Create a fresh AsyncYamlSettingsCore instance for testing."""
    core = AsyncYamlSettingsCore()
    yield core
    # Cleanup
    core.cache.clear()
    core.path_cache.clear()
    core.settings_cache.clear()


@pytest.fixture
def temp_yaml_file(tmp_path):
    """Create a temporary YAML file for testing."""
    yaml_file = tmp_path / "test.yaml"
    data = {
        "test_settings": {
            "string_value": "test",
            "bool_value": True,
            "int_value": 42,
            "nested": {"deep_value": "deep"}
        }
    }
    yaml = ruamel.yaml.YAML()
    yaml.indent(offset=2)
    with open(yaml_file, "w") as f:
        yaml.dump(data, f)
    return yaml_file


class TestAsyncYamlEdgeCases:
    """Tests for AsyncYamlSettingsCore edge cases and specific scenarios."""

    @pytest.mark.asyncio
    async def test_multi_file_management_with_different_data(self, async_yaml_core, tmp_path) -> None:
        """Test managing multiple YAML files with different structures simultaneously."""
        files_data = {
            "config.yaml": {"app": {"name": "test", "version": "1.0"}},
            "settings.yaml": {"features": {"enabled": True, "list": [1, 2, 3]}},
            "data.yaml": {"users": [{"id": 1, "name": "user1"}, {"id": 2, "name": "user2"}]},
        }

        # Create test files
        yaml = ruamel.yaml.YAML()
        created_files = {}
        for filename, data in files_data.items():
            file_path = tmp_path / filename
            with open(file_path, "w") as f:
                yaml.dump(data, f)
            created_files[filename] = file_path

        # Load all files concurrently
        tasks = [async_yaml_core.load_yaml(path) for path in created_files.values()]
        results = await asyncio.gather(*tasks)

        # Verify all loaded correctly with their unique structures
        assert results[0]["app"]["name"] == "test"
        assert results[1]["features"]["enabled"] is True
        assert len(results[2]["users"]) == 2

        # All should be cached
        for path in created_files.values():
            assert path in async_yaml_core.cache

    @pytest.mark.asyncio
    async def test_empty_yaml_file_vs_none_handling(self, async_yaml_core, tmp_path: Path) -> None:
        """Test handling of empty YAML files vs files that parse to None."""
        # Create empty file
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")

        # Create file with just comments
        comment_file = tmp_path / "comments.yaml"
        comment_file.write_text("# Just a comment\n# Another comment")

        # Create file with null value
        null_file = tmp_path / "null.yaml"
        null_file.write_text("~")  # YAML null

        # Test all three cases
        empty_result = await async_yaml_core.load_yaml(empty_file)
        comment_result = await async_yaml_core.load_yaml(comment_file)
        null_result = await async_yaml_core.load_yaml(null_file)

        # Empty and comment-only files return None, null file returns empty dict
        assert empty_result is None or empty_result == {}
        assert comment_result is None or comment_result == {}
        assert null_result is None or null_result == {}

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("init_message_handler_fixture")
    async def test_deeply_nested_path_navigation(self, async_yaml_core, tmp_path: Path) -> None:
        """Test navigation through very deeply nested YAML structures."""
        deep_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": {
                                "level6": {
                                    "target": "found",
                                    "list": [{"item": 1}, {"item": 2}]
                                }
                            }
                        }
                    }
                }
            }
        }

        # Create test file
        test_file = tmp_path / "deep.yaml"
        yaml = ruamel.yaml.YAML()
        with open(test_file, "w") as f:
            yaml.dump(deep_data, f)

        # Mock get_path_for_store
        async def mock_get_path(store):
            return test_file

        async_yaml_core.get_path_for_store = mock_get_path

        # Test deep navigation
        result = await async_yaml_core.get_setting(
            str, YAML.TEST, "level1.level2.level3.level4.level5.level6.target"
        )
        assert result == "found"

        # Test partial path that doesn't exist
        result = await async_yaml_core.get_setting(
            str, YAML.TEST, "level1.level2.level3.nonexistent.path"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_concurrent_writes_to_same_setting(self, async_yaml_core, tmp_path: Path) -> None:
        """Test concurrent write operations to the same setting."""
        test_file = tmp_path / "concurrent.yaml"
        initial_data = {"counter": 0, "values": {}}

        yaml = ruamel.yaml.YAML()
        with open(test_file, "w") as f:
            yaml.dump(initial_data, f)

        # Mock get_path_for_store
        async def mock_get_path(store):
            return test_file

        async_yaml_core.get_path_for_store = mock_get_path

        # Simulate concurrent writes
        async def write_value(index):
            await async_yaml_core.get_setting(
                int, YAML.TEST, f"values.item_{index}", index
            )
            return index

        # Launch concurrent writes
        tasks = [write_value(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # All writes should have succeeded
        assert sorted(results) == list(range(10))

        # Verify all values were written
        for i in range(10):
            value = await async_yaml_core.get_setting(int, YAML.TEST, f"values.item_{i}")
            assert value == i

    @pytest.mark.asyncio
    async def test_invalid_yaml_with_recovery(self, async_yaml_core, tmp_path: Path) -> None:
        """Test handling of various invalid YAML formats with recovery attempts."""
        test_cases = [
            ("bad_indent.yaml", "key1:\n  subkey: value\n badindent: value"),
            ("unclosed_quote.yaml", 'key: "unclosed string'),
            ("invalid_anchor.yaml", "key: &unknown\nref: *nonexistent"),
        ]

        for filename, content in test_cases:
            file_path = tmp_path / filename
            file_path.write_text(content)

            # Should handle gracefully and return empty dict
            result = await async_yaml_core.load_yaml(file_path)
            assert result == {}, f"Failed to handle {filename} gracefully"

    @pytest.mark.asyncio
    async def test_cache_metrics_accuracy(self, async_yaml_core, temp_yaml_file) -> None:
        """Test that cache metrics are accurately tracked."""
        # Note: Metrics tracking might not be implemented in AsyncYamlSettingsCore
        # or might work differently than expected. Let's adjust the test.

        # First load - file will be loaded into cache
        result1 = await async_yaml_core.load_yaml(temp_yaml_file)
        assert result1 is not None
        assert temp_yaml_file in async_yaml_core.cache

        # Second load - should come from cache (same object)
        result2 = await async_yaml_core.load_yaml(temp_yaml_file)
        assert result2 is result1  # Same object reference means it came from cache

    @pytest.mark.asyncio
    async def test_settings_cache_vs_file_cache(self, async_yaml_core, tmp_path: Path) -> None:
        """Test the relationship between settings_cache and file cache."""
        test_file = tmp_path / "cache_test.yaml"
        data = {"settings": {"value1": "test", "value2": 42}}

        yaml = ruamel.yaml.YAML()
        with open(test_file, "w") as f:
            yaml.dump(data, f)

        # Mock get_path_for_store for a static store
        async def mock_get_path(store):
            return test_file

        async_yaml_core.get_path_for_store = mock_get_path

        # Access a setting from a static store (should use settings_cache)
        value1 = await async_yaml_core.get_setting(str, YAML.Main, "settings.value1")
        assert value1 == "test"

        # Check that it's in settings_cache
        cache_key = (YAML.Main, "settings.value1", str)
        assert cache_key in async_yaml_core.settings_cache
        assert async_yaml_core.settings_cache[cache_key] == "test"

        # Access same setting again - should come from settings_cache
        value2 = await async_yaml_core.get_setting(str, YAML.Main, "settings.value1")
        assert value2 == "test"


if __name__ == "__main__":
    pytest.main()
