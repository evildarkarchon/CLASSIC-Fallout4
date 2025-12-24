"""YamlData and ScanLogInfo test fixtures.

This module provides all yamldata-related fixtures for testing.
Fixtures are designed to be Rust-compatible by default.

IMPORTANT: Use `mock_yamldata` for Rust integration tests.
Use `mock_yamldata_simple` for unit tests that don't call Rust.
Use `mock_yamldata_with_data` for mod detection tests.

Consolidated from:
- Original yamldata_fixtures.py
- tests/yaml/conftest.py (yaml_async_core, yaml_temp_file)
"""

import math
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock

import pytest
import ruamel.yaml


def _create_vr_methods(mock: MagicMock) -> None:
    """Add VR-aware methods to a yamldata mock."""

    def get_crashgen_name(is_vr: bool) -> str:
        return mock.crashgen_name_vr if is_vr else mock.crashgen_name

    def get_game_root_name(is_vr: bool) -> str:
        return mock.game_root_name_vr if is_vr else mock.game_root_name

    mock.get_crashgen_name = get_crashgen_name
    mock.get_game_root_name = get_game_root_name


@pytest.fixture
def mock_yamldata() -> MagicMock:
    """Create Rust-compatible yamldata mock with full attributes.

    All attributes are proper Python types (not Mock objects)
    to ensure PyO3 type conversion works correctly.

    Use for: Rust integration, parity tests, orchestrator tests

    Returns:
        MagicMock: Mock object with all required yamldata attributes.
    """
    mock = MagicMock(spec=False)

    # Basic game info
    mock.crashgen_name = "Buffout 4"
    mock.crashgen_name_vr = "Buffout 4 NG"
    mock.xse_acronym = "F4SE"
    mock.crashgen_latest_og = "1.28.6"
    mock.crashgen_latest_vr = "1.26.2"
    mock.game_root_name = "Fallout4"
    mock.game_root_name_vr = "Fallout4VR"

    # VR-aware methods
    _create_vr_methods(mock)

    # CRITICAL: These attributes are required by RustPluginAnalyzer
    # They must be proper Python types, not Mock objects
    mock.game_ignore_plugins = []
    mock.ignore_list = []
    mock.game_version = "1.10.163"
    mock.game_version_vr = "1.2.72"
    mock.game_version_new = "1.10.163"

    # Required for report generation
    mock.classic_version = "CLASSIC v1.0.0"

    # Required for suspect scanning
    mock.suspects_error_list = {}
    mock.suspects_stack_list = {}

    # Game mod data for detection (empty by default)
    mock.game_mods_conf = {}
    mock.game_mods_freq = {}
    mock.game_mods_solu = {}
    mock.game_mods_core = {}
    mock.game_mods_core_folon = {}
    mock.game_mods_opc2 = {}

    # Crash log error/stack checks
    mock.crashlog_error_check = {}
    mock.crashlog_stack_check = {}

    # Game hints
    mock.classic_game_hints = []
    mock.autoscan_text = ""

    # Path attributes (for stress tests)
    mock.game_path = "C:\\Games\\Fallout4"
    mock.docs_path = "C:\\Users\\Test\\Documents\\My Games\\Fallout4"
    mock.plugins = {}
    mock.settings = {}

    return mock


@pytest.fixture
def mock_yamldata_simple() -> MagicMock:
    """Create minimal yamldata mock for simple unit tests.

    Use for: Unit tests that don't call Rust FFI.

    Returns:
        MagicMock: Minimal mock with basic attributes.
    """
    mock = MagicMock()
    mock.scan_groups = {}
    mock.rules = []

    # Rust FFI compatibility - provide real string values
    mock.crashgen_name = "Buffout 4"
    mock.crashgen_name_vr = "Buffout 4 NG"
    mock.game_version = "1.10.163.0"
    mock.game_version_vr = "1.2.72.0"
    mock.game_version_new = "1.10.980.0"
    mock.game_ignore_plugins = []
    mock.ignore_list = []
    mock.game_root_name = "Fallout4"
    mock.game_root_name_vr = "Fallout4VR"

    # VR-aware methods
    _create_vr_methods(mock)

    # Additional common attributes
    mock.formid_analyzer_enabled = False
    mock.record_scanner_enabled = False
    mock.plugin_analyzer_enabled = True

    return mock


@pytest.fixture
def mock_yamldata_with_data() -> MagicMock:
    """Create yamldata mock with populated mod detection data.

    Use for: Mod detection, suspect scanning tests

    Returns:
        MagicMock: Mock with game_mods_* dictionaries populated.
    """
    mock = MagicMock(spec=False)

    # Basic game info
    mock.crashgen_name = "Buffout 4"
    mock.crashgen_name_vr = "Buffout 4 NG"
    mock.xse_acronym = "F4SE"
    mock.crashgen_latest_og = "1.28.6"
    mock.crashgen_latest_vr = "1.26.2"
    mock.game_root_name = "Fallout4"
    mock.game_root_name_vr = "Fallout4VR"

    # VR-aware methods
    _create_vr_methods(mock)

    # CRITICAL: Required by RustPluginAnalyzer
    mock.game_ignore_plugins = []
    mock.ignore_list = []
    mock.game_version = "1.10.163"
    mock.game_version_vr = "1.2.72"
    mock.game_version_new = "1.10.163"

    # Required for report generation
    mock.classic_version = "CLASSIC v1.0.0"

    # Required for suspect scanning
    mock.suspects_error_list = {}
    mock.suspects_stack_list = {}

    # Game mod data for detection - POPULATED
    mock.game_mods_conf = {"conflict_mod_1|conflict_mod_2": "These mods conflict together"}
    mock.game_mods_freq = {"problemplugin.esp": "This plugin causes frequent crashes"}
    mock.game_mods_solu = {"outdated.esp": "Update to latest version"}
    mock.game_mods_core = {
        "ufop4": {"warn": "Unofficial Patch not detected", "plugin": "Unofficial Fallout 4 Patch.esp", "required": True}
    }
    mock.game_mods_core_folon = {}
    mock.game_mods_opc2 = {"oldmod.esp": "This mod is outdated"}

    # Crash log error/stack checks - POPULATED
    mock.crashlog_error_check = {"HIGH | Test Error": "error_signal"}
    mock.crashlog_stack_check = {"MEDIUM | Stack Error": ["required:signal1", "optional:signal2"]}

    # Game hints
    mock.classic_game_hints = ["Test hint 1", "Test hint 2"]
    mock.autoscan_text = "Additional scan information"

    return mock


@pytest.fixture
def mock_yamldata_python_only() -> Any:
    """Mock yamldata that DISABLES Rust acceleration (forces Python fallback).

    Use this fixture ONLY for stress tests or unit tests that use complex
    mocking patterns that don't work with PyO3 type conversion.

    For Rust integration tests, DO NOT use this fixture - use proper test data.

    Yields:
        Mock: Simple mock object for Python-only testing.
    """
    # Disable Rust to avoid PyO3 type conversion issues with Mock objects
    original_value = os.environ.get("CLASSIC_DISABLE_RUST")
    os.environ["CLASSIC_DISABLE_RUST"] = "1"

    # Create a simple mock that works with Python fallback
    mock = Mock()
    mock.game_path = "C:\\Games\\Fallout4"
    mock.docs_path = "C:\\Users\\Test\\Documents\\My Games\\Fallout4"
    mock.plugins = {}
    mock.settings = {}

    yield mock

    # Restore original environment variable state
    if original_value is None:
        os.environ.pop("CLASSIC_DISABLE_RUST", None)
    else:
        os.environ["CLASSIC_DISABLE_RUST"] = original_value


@pytest.fixture
def mock_scanlog_info() -> Any:
    """Create mock ScanLogInfo for testing (class-based mock).

    This provides a more realistic mock with proper class structure.
    Use for: Tests that need dict-like access or class methods.

    Returns:
        MockScanLogInfo: Class instance with all scanlog info attributes.
    """

    class MockScanLogInfo:
        def __init__(self) -> None:
            self.crashgen_name = "Buffout"
            self.crashgen_name_vr = "Buffout 4 NG"
            self.xse_acronym = "F4SE"
            self.game_root_name = "Fallout4"
            self.game_root_name_vr = "Fallout4VR"
            self.game = "Fallout4"
            self.yamldata_segments = {}
            self.crashgen_2_name = "Crash"
            self.crashgen_2_has_stacktrace = True
            self.xse_name = "F4SE"
            self.game_runtime = "Fallout4.exe"

            # Plugin configuration
            self.plugins_always_ignore = []
            self.plugins_always_valid = ["Fallout4.esm", "DLCRobot.esm"]
            self.plugins_mods_to_check = {}
            self.plugins_too_many = 255

            # FormID configuration
            self.formid_plugins_always_scan = ["Fallout4.esm"]
            self.formid_plugins_all_scan = False

            # Version info
            self.game_version = "1.10.163"
            self.game_version_vr = "1.2.72"
            self.game_version_new = "1.10.984"
            self.classic_version = "7.31.0"
            self.crashgen_latest_og = "1.28.6"
            self.crashgen_latest_vr = "1.28.6"

            # Suspects
            self.suspects_error_list = {}
            self.suspects_stack_list = {}

            # Ignore lists
            self.game_ignore_plugins = []
            self.game_ignore_records = []
            self.ignore_list = []
            self.classic_records_list = []

            # Problematic plugins
            self.problematic_plugins = {
                "MoreSpawns.esp": "Causes CTD due to spawning conflicts",
                "Arbitration.esp": "Combat overhaul with script conflicts",
                "ChildrenofAtom.esp": "Known faction conflicts",
                "CompanionsGoneWild.esp": "Companion script issues",
            }

        def get(self, key: str, default: Any = None) -> Any:
            """Allow dict-like access."""
            return getattr(self, key, default)

        def get_crashgen_name(self, is_vr: bool) -> str:
            """Get crash generator name based on VR mode."""
            return self.crashgen_name_vr if is_vr else self.crashgen_name

        def get_game_root_name(self, is_vr: bool) -> str:
            """Get game root name based on VR mode."""
            return self.game_root_name_vr if is_vr else self.game_root_name

    return MockScanLogInfo()


# ============================================================================
# YAML Settings Fixtures (from tests/yaml/conftest.py)
# ============================================================================


@pytest.fixture
async def yaml_async_core():
    """Get the AsyncYamlSettingsCore singleton instance for testing.

    This fixture provides access to the async YAML settings core for
    testing async YAML operations.

    Returns:
        The AsyncYamlSettingsCore singleton instance.

    Note:
        Since it's a singleton, the instance is not disposed after the test.
    """
    from ClassicLib.YamlSettings.async_ import get_async_yaml_core

    core = await get_async_yaml_core()
    return core


@pytest.fixture
def yaml_temp_file(tmp_path: Path) -> Path:
    """Create a temporary YAML file with test data.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        Path to the temporary YAML file containing test settings.
    """
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


# Backward compatibility aliases (deprecated - use prefixed names)
async_yaml_core = yaml_async_core
temp_yaml_file = yaml_temp_file
