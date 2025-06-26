"""
Test suite for ClassicLib/YamlSettingsCache.py YAML settings cache.

This module contains tests for the YAML settings cache system including
file loading, caching mechanisms, and settings access functionality.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import pytest

from ClassicLib.Constants import YAML
from ClassicLib.YamlSettingsCache import (
    YamlSettingsCache,
    classic_settings,
    yaml_cache,
    yaml_settings,
)


class TestYamlSettingsCache:
    """Tests for the YamlSettingsCache class."""

    def test_cache_initialization(self) -> None:
        """Test YamlSettingsCache initialization."""
        cache = YamlSettingsCache()

        assert isinstance(cache.cache, dict)
        assert isinstance(cache.file_mod_times, dict)
        assert isinstance(cache.path_cache, dict)
        assert isinstance(cache.settings_cache, dict)

    def test_get_path_for_store_settings(self) -> None:
        """Test get_path_for_store for Settings YAML."""
        cache = YamlSettingsCache()

        path = cache.get_path_for_store(YAML.Settings)
        expected = Path("CLASSIC Settings.yaml")

        assert path == expected

    def test_get_path_for_store_main(self) -> None:
        """Test get_path_for_store for Main YAML."""
        cache = YamlSettingsCache()

        path = cache.get_path_for_store(YAML.Main)
        expected = Path("CLASSIC Data/databases/CLASSIC Main.yaml")

        assert path == expected

    def test_get_path_for_store_caching(self) -> None:
        """Test that get_path_for_store caches results."""
        cache = YamlSettingsCache()

        # First call
        path1 = cache.get_path_for_store(YAML.Settings)

        # Second call should use cache
        path2 = cache.get_path_for_store(YAML.Settings)

        assert path1 == path2
        assert YAML.Settings in cache.path_cache

    @patch("ClassicLib.YamlSettingsCache.open_file_with_encoding")
    def test_load_yaml_basic(self, mock_open_file: MagicMock, tmp_path: Path) -> None:
        """Test basic load_yaml functionality."""
        cache = YamlSettingsCache()
        yaml_file = tmp_path / "test.yaml"
        yaml_content = {"test_key": "test_value"}

        # Create the actual file for stat operations
        yaml_file.write_text("test_key: test_value")

        # Mock file operations
        mock_file_context = MagicMock()
        mock_file_context.__enter__.return_value = mock_file_context
        mock_file_context.__exit__.return_value = None
        mock_open_file.return_value = mock_file_context

        with patch("ruamel.yaml.YAML") as mock_yaml_class:
            mock_yaml_instance = MagicMock()
            mock_yaml_class.return_value = mock_yaml_instance
            mock_yaml_instance.load.return_value = yaml_content

            result = cache.load_yaml(yaml_file)

        assert result == yaml_content
        assert yaml_file in cache.cache

    def test_load_yaml_nonexistent_file(self) -> None:
        """Test load_yaml with nonexistent file."""
        cache = YamlSettingsCache()
        yaml_file = Path("nonexistent.yaml")

        with patch("pathlib.Path.exists", return_value=False):
            result = cache.load_yaml(yaml_file)

        assert result == {}

    def test_get_setting_read_operation(self, tmp_path: Path) -> None:
        """Test get_setting for read operations."""
        cache = YamlSettingsCache()
        test_data = {"level1": {"level2": {"target_key": "target_value"}}}

        with patch.object(cache, "get_path_for_store", return_value=tmp_path / "test.yaml"):
            with patch.object(cache, "load_yaml", return_value=test_data):
                result = cache.get_setting(str, YAML.Settings, "level1.level2.target_key")

        assert result == "target_value"

    @pytest.mark.usefixtures("init_message_handler_fixture")
    def test_get_setting_nonexistent_path(self, tmp_path: Path) -> None:
        """Test get_setting with nonexistent nested path."""
        cache = YamlSettingsCache()
        test_data = {"level1": {"level2": "value"}}

        with patch.object(cache, "get_path_for_store", return_value=tmp_path / "test.yaml"):
            with patch.object(cache, "load_yaml", return_value=test_data):
                result = cache.get_setting(str, YAML.Settings, "level1.nonexistent.key")

        assert result is None

    def test_get_setting_write_operation_static_file_error(self, tmp_path: Path) -> None:
        """Test get_setting raises ValueError for write operations on static files."""
        cache = YamlSettingsCache()

        test_file = tmp_path / "static.yaml"

        with patch.object(cache, "get_path_for_store", return_value=test_file):
            with patch.object(cache, "load_yaml", return_value={}):
                with pytest.raises(ValueError, match="Attempted to modify static YAML store"):
                    cache.get_setting(str, YAML.Main, "key", "value")  # Main is static

    def test_multi_file_management(self) -> None:
        """Test managing multiple YAML files simultaneously."""
        # Create a fresh cache instance to avoid contamination from other tests
        cache = YamlSettingsCache()
        # Clear any existing cache entries
        cache.cache.clear()
        cache.file_mod_times.clear()

        files_data = {
            "file1.yaml": {"content": "data1"},
            "file2.yaml": {"content": "data2"},
            "file3.yaml": {"content": "data3"},
        }

        for filename, data in files_data.items():
            file_path = Path(filename)
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_mtime = 1000.0
                    with patch("ClassicLib.YamlSettingsCache.open_file_with_encoding"):
                        with patch("ruamel.yaml.YAML") as mock_yaml:
                            mock_yaml.return_value.load.return_value = data
                            result = cache.load_yaml(file_path)
                            assert result == data

        # Verify all test files are cached (should be exactly 3)
        test_files = [f for f in cache.cache.keys() if any(str(f).endswith(name) for name in files_data.keys())]
        assert len(test_files) == 3

    def test_cache_invalidation_on_file_change(self, tmp_path: Path) -> None:
        """Test cache invalidation for dynamic files when modification time changes."""
        cache = YamlSettingsCache()

        # Mock dynamic file that changes
        test_file = tmp_path / "dynamic.yaml"
        # Create the actual file
        test_file.write_text("version: 1")
        initial_data = {"version": 1}
        updated_data = {"version": 2}

        # First load with real file operations
        with patch("ruamel.yaml.YAML") as mock_yaml_class:
            mock_yaml_instance = MagicMock()
            mock_yaml_class.return_value = mock_yaml_instance
            mock_yaml_instance.load.return_value = initial_data
            result1 = cache.load_yaml(test_file)

        # Verify initial load worked
        assert test_file in cache.cache
        original_mod_time = cache.file_mod_times[test_file]

        # Mock the second load with updated modification time
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_mtime = 2000.0  # Updated time
            with patch("ClassicLib.YamlSettingsCache.open_file_with_encoding"):
                with patch("ruamel.yaml.YAML") as mock_yaml:
                    mock_yaml.return_value.load.return_value = updated_data
                    cache.load_yaml(test_file)

        # Verify cache was updated
        assert test_file in cache.cache
        assert cache.file_mod_times[test_file] == 2000.0

    def test_empty_yaml_file_handling(self, tmp_path: Path) -> None:
        """Test handling of empty YAML files."""
        cache = YamlSettingsCache()
        empty_file = tmp_path / "empty.yaml"

        # Create the actual empty file
        empty_file.write_text("")

        with patch("ClassicLib.YamlSettingsCache.open_file_with_encoding"):
            with patch("ruamel.yaml.YAML") as mock_yaml:
                mock_yaml.return_value.load.return_value = None
                result = cache.load_yaml(empty_file)

        # Should handle None gracefully
        assert result is None


class TestYamlSettingsFunction:
    """Tests for the yaml_settings function."""

    def test_yaml_settings_basic_functionality(self) -> None:
        """Test basic yaml_settings functionality."""
        with patch.object(yaml_cache, "get_setting", return_value="test_result") as mock_get:
            result = yaml_settings(str, YAML.Settings, "test.key")

            assert result == "test_result"
            mock_get.assert_called_once_with(str, YAML.Settings, "test.key", None)

    def test_yaml_settings_with_new_value(self) -> None:
        """Test yaml_settings with new value (write operation)."""
        with patch.object(yaml_cache, "get_setting", return_value="new_value") as mock_get:
            result = yaml_settings(str, YAML.Settings, "test.key", "new_value")

            assert result == "new_value"
            mock_get.assert_called_once_with(str, YAML.Settings, "test.key", "new_value")

    def test_yaml_settings_path_type_conversion(self, tmp_path: Path) -> None:
        """Test yaml_settings converts string to Path for Path type."""
        test_path_str = str(tmp_path / "test" / "path")

        with patch.object(yaml_cache, "get_setting", return_value=test_path_str) as mock_get:
            result = yaml_settings(Path, YAML.Settings, "path.key")

            assert isinstance(result, Path)
            assert str(result) == test_path_str

    def test_yaml_settings_path_type_none_value(self) -> None:
        """Test yaml_settings returns None for Path type when setting is None."""
        with patch.object(yaml_cache, "get_setting", return_value=None) as mock_get:
            result = yaml_settings(Path, YAML.Settings, "nonexistent.path")

            assert result is None

    def test_yaml_settings_path_type_non_string_value(self) -> None:
        """Test yaml_settings returns None for Path type when setting is not string."""
        with patch.object(yaml_cache, "get_setting", return_value=123) as mock_get:
            result = yaml_settings(Path, YAML.Settings, "numeric.value")

            assert result is None


class TestClassicSettingsFunction:
    """Tests for the classic_settings function."""

    @patch("pathlib.Path.exists", return_value=True)
    def test_classic_settings_existing_file(self, mock_exists: MagicMock) -> None:
        """Test classic_settings with existing settings file."""
        with patch("ClassicLib.YamlSettingsCache.yaml_settings", return_value="test_setting_value") as mock_yaml:
            result = classic_settings(str, "test_setting")

            assert result == "test_setting_value"
            mock_yaml.assert_called_once_with(str, YAML.Settings, "CLASSIC_Settings.test_setting")

    @patch("pathlib.Path.exists", return_value=False)
    @patch("pathlib.Path.write_text")
    @patch("ClassicLib.YamlSettingsCache.yaml_settings")
    def test_classic_settings_creates_missing_file(self, mock_yaml: MagicMock, mock_write: MagicMock, mock_exists: MagicMock) -> None:
        """Test classic_settings creates missing settings file."""
        # Setup mock responses
        mock_yaml.side_effect = [
            "# Default settings content",  # get default settings
            "retrieved_setting_value",  # get actual setting
        ]

        result = classic_settings(str, "test_setting")

        assert result == "retrieved_setting_value"
        # Should have written the default settings to file
        mock_write.assert_called_once_with("# Default settings content", encoding="utf-8")
        # Should have called yaml_settings twice
        assert mock_yaml.call_count == 2

    @patch("pathlib.Path.exists", return_value=False)
    @patch("ClassicLib.YamlSettingsCache.yaml_settings", return_value=None)
    def test_classic_settings_invalid_default_settings(self, mock_yaml: MagicMock, mock_exists: MagicMock) -> None:
        """Test classic_settings raises ValueError for invalid default settings."""
        with pytest.raises(ValueError, match="Invalid Default Settings"):
            classic_settings(str, "test_setting")


class TestCachePerformance:
    """Tests for cache performance optimization."""

    def test_static_file_caching_optimization(self) -> None:
        """Test performance optimization for static files."""
        cache = YamlSettingsCache()

        # Test static file (should be cached in settings_cache)
        static_data = {"static": "value"}
        static_file = Path("static.yaml")

        with patch.object(cache, "get_path_for_store", return_value=static_file):
            with patch.object(cache, "load_yaml", return_value=static_data) as mock_load:
                # First call
                result1 = cache.get_setting(str, YAML.Main, "static")  # Main is static
                # Second call should use settings_cache
                result2 = cache.get_setting(str, YAML.Main, "static")

        # Both should return the same result
        assert result1 == "value"
        assert result2 == "value"

        # load_yaml should only be called once due to caching
        assert mock_load.call_count == 1


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_complex_nested_structures(self, tmp_path: Path) -> None:
        """Test handling of complex nested YAML structures."""
        cache = YamlSettingsCache()

        complex_data = {"level1": {"level2": {"level3": {"deep_list": [1, 2, {"nested_in_list": "value"}], "deep_string": "target"}}}}

        with patch.object(cache, "get_path_for_store", return_value=tmp_path / "complex.yaml"):
            with patch.object(cache, "load_yaml", return_value=complex_data):
                result = cache.get_setting(str, YAML.Settings, "level1.level2.level3.deep_string")

        assert result == "target"

    def test_invalid_path_structure_handling(self, tmp_path: Path) -> None:
        """Test handling of invalid path structures in YAML."""
        cache = YamlSettingsCache()

        # Data where intermediate path is not a dict
        invalid_data = {
            "level1": {
                "level2": "string_value"  # This should be a dict for further nesting
            }
        }

        with patch.object(cache, "get_path_for_store", return_value=tmp_path / "invalid.yaml"):
            with patch.object(cache, "load_yaml", return_value=invalid_data):
                result = cache.get_setting(str, YAML.Settings, "level1.level2.level3")

        # Should handle gracefully and return None
        assert result is None


if __name__ == "__main__":
    pytest.main()
