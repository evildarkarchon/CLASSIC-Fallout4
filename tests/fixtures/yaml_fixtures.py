"""YAML test fixtures for CLASSIC-Fallout4 test suite.

This module provides consolidated YAML-related fixtures for testing,
including AsyncYamlSettingsCore instances and temporary YAML files.

All YAML fixtures should be defined here according to fixture consolidation standards.
"""

from pathlib import Path
from typing import Any

import pytest
import ruamel.yaml

from ClassicLib.core.constants import YAML
from ClassicLib.io.yaml.async_ import AsyncYamlSettingsCore


@pytest.fixture
async def yaml_async_core() -> AsyncYamlSettingsCore:
    """Create a fresh AsyncYamlSettingsCore instance for testing.

    This is the canonical YAML core fixture. All tests needing an
    AsyncYamlSettingsCore should use this fixture instead of defining
    their own.

    Yields:
        AsyncYamlSettingsCore instance with proper cleanup.
    """
    core = AsyncYamlSettingsCore()
    yield core
    # Cleanup - clear cache to prevent pollution
    await core.clear_cache()


# Alias for backward compatibility
@pytest.fixture
async def async_yaml_core() -> AsyncYamlSettingsCore:
    """Alias for yaml_async_core for backward compatibility.

    New tests should prefer yaml_async_core.

    Yields:
        AsyncYamlSettingsCore instance with proper cleanup.
    """
    core = AsyncYamlSettingsCore()
    yield core
    await core.clear_cache()


@pytest.fixture
def yaml_temp_file(tmp_path: Path) -> Path:
    """Create a temporary YAML file for testing.

    Creates a YAML file with standard test data structure including
    string, boolean, integer, and nested values.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        Path to the created YAML file.
    """
    yaml_file = tmp_path / "test.yaml"
    data: dict[str, Any] = {
        "test_settings": {
            "string_value": "test",
            "bool_value": True,
            "int_value": 42,
            "nested": {"deep_value": "deep"},
        }
    }

    yaml = ruamel.yaml.YAML()
    yaml.indent(offset=2)
    with Path(yaml_file).open("w") as f:
        yaml.dump(data, f)

    return yaml_file


# Alias for backward compatibility
@pytest.fixture
def temp_yaml_file(tmp_path: Path) -> Path:
    """Alias for yaml_temp_file for backward compatibility.

    New tests should prefer yaml_temp_file.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        Path to the created YAML file.
    """
    yaml_file = tmp_path / "test.yaml"
    data: dict[str, Any] = {
        "test_settings": {
            "string_value": "test",
            "bool_value": True,
            "int_value": 42,
            "nested": {"deep_value": "deep"},
        }
    }

    yaml = ruamel.yaml.YAML()
    yaml.indent(offset=2)
    with Path(yaml_file).open("w") as f:
        yaml.dump(data, f)

    return yaml_file


@pytest.fixture
def create_yaml_files(tmp_path: Path) -> Path:
    """Create temporary YAML files for integration testing.

    Creates a directory with full CLASSIC-style YAML files including
    settings, mods alerts, crashlog checks, and local settings.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        Path to the directory containing YAML files.
    """
    yaml_dir: Path = tmp_path / "yaml"
    yaml_dir.mkdir(exist_ok=True)

    # Create main settings file with proper structure
    settings_file: Path = yaml_dir / "CLASSIC Settings.yaml"
    settings_file.write_text("""
CLASSIC_Settings:
  Managed Game: "Fallout 4"

Game_Info:
  CRASHGEN_LogName: "Buffout 4"
  XSE_Acronym: "F4SE"

Mods_Alert_Single:
  problematic_mod: "This mod causes crashes."
  another_problem: "Another problematic mod."

Mods_Alert_Double:
  mod_conflict | mod_conflict2: "These mods conflict with each other."

Mods_Alert_Important:
  critical_mod | Critical Mod: "This mod is critical and incompatible with your GPU."

Crashlog_Error_Check:
  "HIGH | Access violation": "Access violation detected"
  "MEDIUM | Null pointer": "Null pointer detected"

Crashlog_Stack_Check:
  "MEDIUM | Problematic stack":
    - "required:BadFunction"
    - "optional:OtherFunction"
    """)

    # Create local settings file
    local_file: Path = yaml_dir / "CLASSIC Fallout4 Local.yaml"
    local_file.write_text("""
catch_log_records:
  - "Record1"
  - "Record2"
    """)

    return yaml_dir


@pytest.fixture
def yaml_with_complex_data(tmp_path: Path) -> Path:
    """Create a YAML file with complex nested data structures.

    Useful for testing deep nesting, lists, and mixed types.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        Path to the created YAML file.
    """
    yaml_file = tmp_path / "complex.yaml"
    data: dict[str, Any] = {
        "level1": {
            "level2": {
                "level3": {
                    "deep_string": "very_deep_value",
                    "deep_list": [1, 2, 3],
                    "deep_bool": True,
                }
            },
            "list_of_dicts": [
                {"name": "item1", "value": 10},
                {"name": "item2", "value": 20},
            ],
        },
        "top_level_list": ["a", "b", "c"],
        "mixed_types": {
            "string": "hello",
            "number": 123,
            "float": 3.14,
            "boolean": False,
            "null_value": None,
        },
    }

    yaml = ruamel.yaml.YAML()
    yaml.indent(offset=2)
    with Path(yaml_file).open("w") as f:
        yaml.dump(data, f)

    return yaml_file


@pytest.fixture
def yaml_simple_file(tmp_path: Path) -> Path:
    """Create a simple YAML file with comments for testing.

    Creates a minimal YAML file with key-value pairs and a comment,
    useful for testing Rust YAML operations that need to handle
    comment preservation.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        Path to the created YAML file.
    """
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(
        "test_key: test_value\n# This is a comment\ntest_int: 42\n",
        encoding="utf-8",
    )
    return yaml_file


@pytest.fixture
def yaml_file_ops():
    """Create YamlFileOperations instance for testing.

    Returns:
        YamlFileOperations instance.
    """
    from ClassicLib.io.yaml.async_ import YamlFileOperations

    return YamlFileOperations()


@pytest.fixture
def yaml_cache_instance():
    """Create YamlSettingsCache instance for testing.

    Returns:
        YamlSettingsCache instance.
    """
    from ClassicLib.io.yaml import YamlSettingsCache

    return YamlSettingsCache()


@pytest.fixture
def mock_yaml_store_path(tmp_path: Path) -> callable:
    """Create a mock function for YAML store path resolution.

    Returns a factory that creates mock get_path_for_store functions
    pointing to a specific YAML file.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        Factory function that takes a yaml_file Path and returns
        a mock get_path_for_store function.
    """

    def create_mock_get_path(yaml_file: Path) -> callable:
        """Create a mock get_path_for_store function.

        Args:
            yaml_file: Path to return for all store lookups.

        Returns:
            Mock function returning the specified path.
        """

        def mock_get_path(store: YAML) -> Path:
            return yaml_file

        return mock_get_path

    return create_mock_get_path
