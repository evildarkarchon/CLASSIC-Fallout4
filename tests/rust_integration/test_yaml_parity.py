"""
Python integration tests for Rust YAML operations.

This module provides Python-side integration tests that mirror the comprehensive
Rust tests in classic-rust/tests/test_yaml.rs to ensure Python-Rust parity.

Tests cover:
- Basic YAML parsing and dumping
- Python type conversions (null, bool, number, string, list, dict)
- File operations with caching
- Settings navigation (get/set with dot notation)
- Cache management
- Error handling
"""

import math
import tempfile
import time
from pathlib import Path

import pytest

try:
    import classic_yaml

    YamlOperations = classic_yaml.YamlOperations
    RUST_AVAILABLE = True
except (ImportError, AttributeError):
    RUST_AVAILABLE = False


# ============================================================================
# Basic Parsing Tests
# ============================================================================


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust YAML operations not available")
class TestParseYaml:
    """Test YAML parsing functionality."""

    def test_parse_yaml_simple_types(self):
        """Test parsing simple YAML types."""
        yaml_ops = YamlOperations()

        # Null
        result = yaml_ops.parse_yaml("null")
        assert result is None

        # Boolean
        result = yaml_ops.parse_yaml("true")
        assert result is True

        result = yaml_ops.parse_yaml("false")
        assert result is False

        # Integer
        result = yaml_ops.parse_yaml("42")
        assert result == 42

        # Float
        result = yaml_ops.parse_yaml("3.14")
        assert abs(result - math.pi) < 0.002

        # String
        result = yaml_ops.parse_yaml('"hello world"')
        assert result == "hello world"

    def test_parse_yaml_list(self):
        """Test parsing YAML lists."""
        yaml_ops = YamlOperations()

        list_yaml = """
- item1
- item2
- item3
"""
        result = yaml_ops.parse_yaml(list_yaml)

        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0] == "item1"
        assert result[1] == "item2"
        assert result[2] == "item3"

    def test_parse_yaml_dict(self):
        """Test parsing YAML dictionaries."""
        yaml_ops = YamlOperations()

        dict_yaml = """
key1: value1
key2: 42
key3: true
"""
        result = yaml_ops.parse_yaml(dict_yaml)

        assert isinstance(result, dict)
        assert len(result) == 3
        assert result["key1"] == "value1"
        assert result["key2"] == 42
        assert result["key3"] is True

    def test_parse_yaml_nested_structure(self):
        """Test parsing nested YAML structures."""
        yaml_ops = YamlOperations()

        nested_yaml = """
database:
  host: localhost
  port: 5432
  credentials:
    username: admin
    password: secret
servers:
  - name: server1
    ip: 192.168.1.1
  - name: server2
    ip: 192.168.1.2
"""
        result = yaml_ops.parse_yaml(nested_yaml)

        assert isinstance(result, dict)

        # Test nested dict
        assert result["database"]["host"] == "localhost"
        assert result["database"]["port"] == 5432
        assert result["database"]["credentials"]["username"] == "admin"

        # Test list of dicts
        assert len(result["servers"]) == 2
        assert result["servers"][0]["name"] == "server1"
        assert result["servers"][1]["ip"] == "192.168.1.2"

    def test_parse_yaml_invalid(self):
        """Test error handling for invalid YAML."""
        yaml_ops = YamlOperations()

        # Invalid YAML syntax
        invalid_yaml = "{ invalid: yaml: content"

        with pytest.raises(Exception) as exc_info:
            yaml_ops.parse_yaml(invalid_yaml)

        assert "Failed to parse YAML" in str(exc_info.value)


# ============================================================================
# Dumping Tests
# ============================================================================


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust YAML operations not available")
class TestDumpYaml:
    """Test YAML dumping functionality."""

    def test_dump_yaml_simple_types(self):
        """Test dumping simple Python types to YAML."""
        yaml_ops = YamlOperations()

        # Boolean
        yaml_str = yaml_ops.dump_yaml(True)
        assert "true" in yaml_str

        # Integer
        yaml_str = yaml_ops.dump_yaml(42)
        assert "42" in yaml_str

        # String
        yaml_str = yaml_ops.dump_yaml("hello")
        assert "hello" in yaml_str

    def test_dump_yaml_complex(self):
        """Test dumping complex Python structures to YAML."""
        yaml_ops = YamlOperations()

        # Create a complex structure
        data = {
            "name": "test",
            "count": 42,
            "items": [1, 2, 3],
        }

        yaml_str = yaml_ops.dump_yaml(data)

        # Verify it can be parsed back
        reparsed = yaml_ops.parse_yaml(yaml_str)

        assert reparsed["name"] == "test"
        assert reparsed["count"] == 42
        assert reparsed["items"] == [1, 2, 3]

    def test_roundtrip_yaml(self):
        """Test YAML roundtrip (parse → dump → parse)."""
        yaml_ops = YamlOperations()

        original_yaml = """
settings:
  enabled: true
  timeout: 30
  servers:
    - localhost
    - 127.0.0.1
"""

        # Parse, dump, and parse again
        parsed1 = yaml_ops.parse_yaml(original_yaml)
        dumped = yaml_ops.dump_yaml(parsed1)
        parsed2 = yaml_ops.parse_yaml(dumped)

        # Verify structure is preserved
        assert parsed2["settings"]["enabled"] is True
        assert parsed2["settings"]["timeout"] == 30
        assert parsed2["settings"]["servers"] == ["localhost", "127.0.0.1"]


# ============================================================================
# File Operations Tests
# ============================================================================


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust YAML operations not available")
class TestFileOperations:
    """Test file loading and saving."""

    def test_load_yaml_file(self):
        """Test loading YAML from file."""
        yaml_ops = YamlOperations()

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "test.yaml"

            yaml_content = """
name: test_file
version: 1.0
features:
  - feature1
  - feature2
"""
            yaml_file.write_text(yaml_content)

            # Load file
            result = yaml_ops.load_yaml_file(str(yaml_file))

            assert result["name"] == "test_file"
            assert result["version"] == 1.0
            assert len(result["features"]) == 2

    def test_load_yaml_file_nonexistent(self):
        """Test error handling for nonexistent files."""
        yaml_ops = YamlOperations()

        with pytest.raises(Exception) as exc_info:
            yaml_ops.load_yaml_file("/nonexistent/path/file.yaml")

        assert "Failed to read file" in str(exc_info.value)

    def test_load_yaml_file_invalid_content(self):
        """Test error handling for invalid YAML content."""
        yaml_ops = YamlOperations()

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "invalid.yaml"

            # Write invalid YAML
            yaml_file.write_text("{ invalid: yaml: syntax")

            with pytest.raises(Exception) as exc_info:
                yaml_ops.load_yaml_file(str(yaml_file))

            assert "Failed to parse YAML" in str(exc_info.value)

    def test_save_yaml_file(self):
        """Test saving YAML to file."""
        yaml_ops = YamlOperations()

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "output.yaml"

            # Create data to save
            data = {
                "title": "Saved YAML",
                "count": 100,
            }

            # Save file
            yaml_ops.save_yaml_file(str(yaml_file), data)

            # Verify file exists and content is correct
            assert yaml_file.exists()

            content = yaml_file.read_text()
            assert "title" in content
            assert "Saved YAML" in content
            assert "100" in content

    def test_save_yaml_file_cache_invalidation(self):
        """Test that saving invalidates cache."""
        yaml_ops = YamlOperations()

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "cache_test.yaml"

            # Create and load file (caches it)
            original_data = {"version": 1}
            yaml_ops.save_yaml_file(str(yaml_file), original_data)

            cached = yaml_ops.load_yaml_file(str(yaml_file))
            assert cached["version"] == 1

            # Save new data (should invalidate cache)
            new_data = {"version": 2}
            yaml_ops.save_yaml_file(str(yaml_file), new_data)

            # Load again - should get new data, not cached
            reloaded = yaml_ops.load_yaml_file(str(yaml_file))
            assert reloaded["version"] == 2


# ============================================================================
# Caching Tests
# ============================================================================


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust YAML operations not available")
class TestCaching:
    """Test file caching functionality."""

    def test_yaml_file_caching(self):
        """Test that files are cached."""
        yaml_ops = YamlOperations()

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "cached.yaml"

            # Create file
            yaml_file.write_text("cached: true")

            # First load - cache miss
            result1 = yaml_ops.load_yaml_file(str(yaml_file))
            assert result1["cached"] is True

            stats1 = yaml_ops.get_cache_stats()
            assert stats1["cached_files"] >= 1

            # Second load - cache hit (no file modification)
            result2 = yaml_ops.load_yaml_file(str(yaml_file))
            assert result2["cached"] is True

            # Cache stats should be same or higher
            stats2 = yaml_ops.get_cache_stats()
            assert stats2["cached_files"] >= 1

    def test_cache_modification_detection(self):
        """Test that cache detects file modifications."""
        yaml_ops = YamlOperations()

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "modified.yaml"

            # Create and load file
            yaml_file.write_text("version: 1")
            result1 = yaml_ops.load_yaml_file(str(yaml_file))
            assert result1["version"] == 1

            # Wait a bit and modify file
            time.sleep(0.02)
            yaml_file.write_text("version: 2")

            # Load again - should detect modification and reload
            result2 = yaml_ops.load_yaml_file(str(yaml_file))
            assert result2["version"] == 2

    def test_clear_cache(self):
        """Test cache clearing."""
        yaml_ops = YamlOperations()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Load multiple files to populate cache
            for i in range(3):
                yaml_file = Path(tmpdir) / f"file{i}.yaml"
                yaml_file.write_text(f"index: {i}")
                yaml_ops.load_yaml_file(str(yaml_file))

            stats_before = yaml_ops.get_cache_stats()
            assert stats_before["cached_files"] >= 3

            # Clear cache
            yaml_ops.clear_cache()

            stats_after = yaml_ops.get_cache_stats()
            assert stats_after["cached_files"] == 0
            assert stats_after["total_bytes"] == 0

    def test_cache_stats(self):
        """Test cache statistics."""
        yaml_ops = YamlOperations()

        # Clear cache first
        yaml_ops.clear_cache()

        stats_empty = yaml_ops.get_cache_stats()
        assert stats_empty["cached_files"] == 0
        assert stats_empty["total_bytes"] == 0

        with tempfile.TemporaryDirectory() as tmpdir:
            # Add file to cache
            content = "test: data\nmore: content"
            yaml_file = Path(tmpdir) / "stats_test.yaml"
            yaml_file.write_text(content)

            yaml_ops.load_yaml_file(str(yaml_file))

            stats_filled = yaml_ops.get_cache_stats()
            assert stats_filled["cached_files"] == 1
            assert stats_filled["total_bytes"] > 0


# ============================================================================
# Settings Navigation Tests
# ============================================================================


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust YAML operations not available")
class TestSettingsNavigation:
    """Test dot notation settings navigation."""

    def test_get_setting_simple(self):
        """Test getting simple settings."""
        yaml_ops = YamlOperations()

        data = {
            "key1": "value1",
            "key2": 42,
        }

        # Get existing key
        result = yaml_ops.get_setting(data, "key1")
        assert result is not None
        assert result == "value1"

        # Get non-existent key
        result = yaml_ops.get_setting(data, "missing")
        assert result is None

    def test_get_setting_nested(self):
        """Test getting nested settings with dot notation."""
        yaml_ops = YamlOperations()

        yaml_content = """
database:
  connection:
    host: localhost
    port: 5432
  pool:
    size: 10
"""
        data = yaml_ops.parse_yaml(yaml_content)

        # Navigate nested path
        result = yaml_ops.get_setting(data, "database.connection.host")
        assert result is not None
        assert result == "localhost"

        # Navigate to integer value
        result = yaml_ops.get_setting(data, "database.pool.size")
        assert result is not None
        assert result == 10

        # Non-existent nested path
        result = yaml_ops.get_setting(data, "database.connection.timeout")
        assert result is None

    def test_get_setting_non_mapping(self):
        """Test navigation through non-mapping values."""
        yaml_ops = YamlOperations()

        yaml_content = """
settings:
  value: 42
"""
        data = yaml_ops.parse_yaml(yaml_content)

        # Try to navigate through non-mapping value
        result = yaml_ops.get_setting(data, "settings.value.nested")
        assert result is None

    def test_set_setting_simple(self):
        """Test setting simple values."""
        yaml_ops = YamlOperations()

        data = {
            "existing": "old",
        }

        # Set new value
        updated = yaml_ops.set_setting(data, "existing", "updated")

        assert updated["existing"] == "updated"

    def test_set_setting_create_nested(self):
        """Test creating nested paths."""
        yaml_ops = YamlOperations()

        # Start with empty dict
        data = {}

        # Create nested path
        updated = yaml_ops.set_setting(data, "database.connection.port", 42)

        # Verify nested structure was created
        result = yaml_ops.get_setting(updated, "database.connection.port")
        assert result is not None
        assert result == 42

    def test_set_setting_overwrite_non_mapping(self):
        """Test overwriting non-mapping values."""
        yaml_ops = YamlOperations()

        yaml_content = """
settings: 42
"""
        data = yaml_ops.parse_yaml(yaml_content)

        # Try to create nested path where intermediate value is not a mapping
        updated = yaml_ops.set_setting(data, "settings.nested.value", "test")

        # Should convert settings to mapping and create nested structure
        result = yaml_ops.get_setting(updated, "settings.nested.value")
        assert result is not None
        assert result == "test"

    def test_set_setting_empty_key_path(self):
        """Test error handling for empty key path."""
        yaml_ops = YamlOperations()

        data = {}

        # Empty key path should error
        with pytest.raises(Exception) as exc_info:
            yaml_ops.set_setting(data, "", "test")

        assert "Empty key path" in str(exc_info.value)

    def test_set_setting_update_existing_nested(self):
        """Test updating existing nested values."""
        yaml_ops = YamlOperations()

        yaml_content = """
server:
  host: localhost
  port: 8080
  ssl: false
"""
        data = yaml_ops.parse_yaml(yaml_content)

        # Update existing nested value
        updated = yaml_ops.set_setting(data, "server.port", 9000)

        # Verify update
        result = yaml_ops.get_setting(updated, "server.port")
        assert result == 9000

        # Verify other values unchanged
        host_result = yaml_ops.get_setting(updated, "server.host")
        assert host_result == "localhost"


# ============================================================================
# Python Type Conversion Tests
# ============================================================================


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust YAML operations not available")
class TestPythonTypeConversion:
    """Test Python ↔ YAML type conversion."""

    def test_python_to_yaml_all_types(self):
        """Test conversion of all Python types to YAML."""
        yaml_ops = YamlOperations()

        # Create complex Python structure
        root = {
            # Null
            "null_value": None,
            # Bool
            "bool_true": True,
            "bool_false": False,
            # Numbers
            "int_value": 42,
            "float_value": math.pi,
            # String
            "string_value": "hello",
            # List
            "list_value": [1, 2, 3],
            # Nested dict
            "dict_value": {
                "nested_key": "nested_value",
            },
        }

        # Convert to YAML and back
        yaml_str = yaml_ops.dump_yaml(root)
        reparsed = yaml_ops.parse_yaml(yaml_str)

        # Verify all types preserved
        assert reparsed["null_value"] is None
        assert reparsed["bool_true"] is True
        assert reparsed["bool_false"] is False
        assert reparsed["int_value"] == 42
        assert abs(reparsed["float_value"] - math.pi) < 0.001
        assert reparsed["string_value"] == "hello"
        assert reparsed["list_value"] == [1, 2, 3]
        assert reparsed["dict_value"]["nested_key"] == "nested_value"


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.rust
@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust YAML operations not available")
class TestIntegration:
    """Test full workflow integration."""

    def test_full_workflow(self):
        """Test complete workflow: create → save → load → update → save → load."""
        yaml_ops = YamlOperations()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"

            # Create initial config
            config = {
                "app_name": "TestApp",
                "version": "1.0.0",
                "database": {
                    "host": "localhost",
                    "port": 5432,
                },
            }

            # Save config
            yaml_ops.save_yaml_file(str(config_file), config)

            # Load config
            loaded = yaml_ops.load_yaml_file(str(config_file))

            # Get nested setting
            port = yaml_ops.get_setting(loaded, "database.port")
            assert port == 5432

            # Update setting
            updated = yaml_ops.set_setting(loaded, "database.port", 6543)

            # Save updated config
            yaml_ops.save_yaml_file(str(config_file), updated)

            # Load again and verify
            final_config = yaml_ops.load_yaml_file(str(config_file))
            final_port = yaml_ops.get_setting(final_config, "database.port")
            assert final_port == 6543

            # Check cache stats
            stats = yaml_ops.get_cache_stats()
            assert stats["cached_files"] >= 1

    def test_concurrent_file_loads(self):
        """Test loading multiple files (cache should handle concurrent access)."""
        yaml_ops = YamlOperations()

        # Clear cache from previous tests
        yaml_ops.clear_cache()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple YAML files
            files = []
            for i in range(5):
                file = Path(tmpdir) / f"config{i}.yaml"
                file.write_text(f"index: {i}")
                files.append(file)

            # Load all files (cache should handle concurrent access)
            for i, file in enumerate(files):
                loaded = yaml_ops.load_yaml_file(str(file))
                assert loaded["index"] == i

            # Verify cache stats
            stats = yaml_ops.get_cache_stats()
            assert stats["cached_files"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
