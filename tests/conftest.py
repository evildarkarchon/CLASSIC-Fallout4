"""
Pytest configuration file for CLASSIC-Fallout4 test suite.

This file contains shared fixtures and configuration that are available to all test modules.
"""

import sys
from collections.abc import Callable, Generator
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Ensure the parent directory is in sys.path so imports work correctly
sys.path.insert(0, str(Path(__file__).parent.parent))

from ClassicLib import GlobalRegistry
from ClassicLib.Constants import YAML


@pytest.fixture
def sample_crash_logs_dir() -> Callable[[Path], Path]:
    """Fixture to create a temporary crash logs directory with sample files."""
    # Create a temporary directory with pytest's tmp_path
    def _create_sample_logs(tmp_path: Path) -> Path:
        crash_logs_dir: Path = tmp_path / "Crash Logs"
        crash_logs_dir.mkdir(exist_ok=True)

        # Create a simple crash log file
        simple_log: Path = crash_logs_dir / "crash-2023-01-01-00-00-00.log"
        simple_log.write_text("""Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512

SYSTEM SPECS:
\tOS: Microsoft Windows 11 Pro v10.0.22621
\tCPU: AMD Ryzen 7 7800X3D 8-Core Processor
\tGPU #1: Nvidia AD104 [GeForce RTX 4070]

PLUGINS:
\t[00] Fallout4.esm
\t[01] DLCRobot.esm
\t[02] ProblemPlugin.esp
""")

        return crash_logs_dir

    return _create_sample_logs

@pytest.fixture
def mock_global_registry() -> Generator[ModuleType, None, None]:
    """Mock the GlobalRegistry to return test values."""
    """Mock the GlobalRegistry to return test values."""
    original_values = {}

    # Save original values
    for key in GlobalRegistry._registry:
        original_values[key] = GlobalRegistry.get(key)

    # Set test values
    GlobalRegistry.register(GlobalRegistry.Keys.GAME, "Fallout4")
    GlobalRegistry.register(GlobalRegistry.Keys.VR, "")

    yield GlobalRegistry

    # Restore original values
    for key, value in original_values.items():
        GlobalRegistry.register(key, value)


@pytest.fixture
def mock_yaml_settings() -> Generator[MagicMock, None, None]:
    """Mock YAML settings for testing."""
    with patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml:

        def side_effect(_type_arg: Any, yaml_store: Any, key_path: str, new_value: Any = None) -> Any:  # noqa: ARG001
            if key_path == "catch_log_records":
                return ["Record1", "Record2"]
            if key_path == "Game_Info.CRASHGEN_LogName":
                return "Buffout 4"
            if key_path == "Game_Info.XSE_Acronym":
                return "F4SE"
            if key_path == "Crashlog_Error_Check":
                return {"HIGH | Test Error": "error_signal"}
            if key_path == "Crashlog_Stack_Check":
                return {"MEDIUM | Stack Error": ["required:signal1", "optional:signal2"]}
            if isinstance(yaml_store, YAML) and yaml_store == YAML.Game and "Mods_" in key_path:
                return {"test_mod": "Test mod warning message"}
            return None

        mock_yaml.side_effect = side_effect
        yield mock_yaml
