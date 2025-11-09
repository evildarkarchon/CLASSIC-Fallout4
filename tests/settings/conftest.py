"""
Shared fixtures for settings tests.

This file contains fixtures that are used across multiple settings test files.
"""

import math
from pathlib import Path

import pytest
import ruamel.yaml

from ClassicLib.AsyncYamlSettings.core import get_async_yaml_core


@pytest.fixture
async def async_yaml_core():
    """Get the AsyncYamlSettingsCore singleton instance for testing."""
    core = await get_async_yaml_core()
    return core
    # Note: Since it's a singleton, we don't dispose of it


@pytest.fixture
def temp_yaml_file(tmp_path: Path) -> Path:
    """Create a temporary YAML file with test data."""
    yaml_file = tmp_path / "test_settings.yaml"
    data = {
        "test_settings": {
            "string_value": "test",
            "bool_value": True,
            "int_value": 42,
            "float_value": math.pi,
            "list_value": [1, 2, 3],
            "dict_value": {"nested": "value"},
        }
    }

    yaml = ruamel.yaml.YAML()
    with Path(yaml_file).open("w") as f:
        yaml.dump(data, f)

    return yaml_file
