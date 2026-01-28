"""ScanLog orchestrator and parser test fixtures.

This module provides fixtures specifically for testing the ScanLog orchestrator
and parser components. Crash log content fixtures are in crash_log_fixtures.py
and yamldata fixtures are in yamldata_fixtures.py.

Note: This module imports mock_yamldata from yamldata_fixtures.py.

Consolidated Fixtures:
- mock_scan_yaml_settings: Basic mock for YAML settings in scan tests
- mock_orchestrator_settings: Mock for orchestrator async settings
- mock_paths: Common paths fixture for scan game tests
- mock_scan_settings: Common scan settings mock
- mock_issue_messages: Common issue messages mock
"""

import struct
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ClassicLib.scanning.game.checks.dds_analyzer import (
    DDSFlags,
    DDSPixelFlags,
    EnhancedDDSAnalyzer,
)

# ============================================================================
# Mock Database Pool Fixtures
# ============================================================================


@pytest.fixture
def mock_database_pool() -> MagicMock:
    """Create a mock AsyncDatabasePool for FormID testing.

    Returns:
        MagicMock: Mock database pool with common async methods.
    """
    pool = AsyncMock()

    # Mock common database methods
    pool.get_entry = AsyncMock(return_value=None)
    pool.get_entries_batch = AsyncMock(return_value={})
    pool.initialize = AsyncMock()
    pool.close = AsyncMock()

    # Mock FormID lookup returning sample data
    pool.lookup_formid = AsyncMock(return_value="TestItem")

    return pool


@pytest.fixture
def mock_database_pool_with_data() -> MagicMock:
    """Create a mock database pool with sample FormID data.

    Returns:
        MagicMock: Mock pool returning realistic FormID lookups.
    """
    pool = AsyncMock()

    # Sample FormID to name mappings
    formid_data = {
        "00000014": "Gold001",
        "0001F66A": "ArmorPowerT51",
        "00033A81": "BoS_M_Uniform",
    }

    async def get_entry_mock(formid: str) -> str | None:
        return formid_data.get(formid)

    async def get_entries_batch_mock(formids: list[str]) -> dict[str, str]:
        return {fid: name for fid, name in formid_data.items() if fid in formids}

    pool.get_entry = AsyncMock(side_effect=get_entry_mock)
    pool.get_entries_batch = AsyncMock(side_effect=get_entries_batch_mock)
    pool.initialize = AsyncMock()
    pool.close = AsyncMock()

    return pool


# ============================================================================
# Orchestrator Test Fixtures
# ============================================================================


@pytest.fixture
def mock_orchestrator_dependencies(mock_yamldata: MagicMock, mock_database_pool: MagicMock) -> dict[str, Any]:
    """Bundle common mock dependencies for OrchestratorCore testing.

    Args:
        mock_yamldata: Mock YAML data fixture (from yamldata_fixtures).
        mock_database_pool: Mock database pool fixture.

    Returns:
        dict[str, Any]: Dictionary of all mock dependencies.
    """
    return {
        "yamldata": mock_yamldata,
        "database_pool": mock_database_pool,
        "fcx_mode": False,
        "show_formid_values": False,
        "formid_db_exists": False,
    }


@pytest.fixture
def mock_file_io() -> MagicMock:
    """Create a mock FileIOCore for testing file operations.

    Returns:
        MagicMock: Mock file I/O with async read/write methods.
    """
    file_io = MagicMock()

    # Mock async read
    file_io.read_file = AsyncMock(return_value="Test file content")

    # Mock async write
    file_io.write_file = AsyncMock(return_value=None)

    return file_io


@pytest.fixture
def mock_parser() -> MagicMock:
    """Create a mock crash log parser for testing.

    Returns:
        MagicMock: Mock parser with find_segments method.
    """
    parser = MagicMock()

    # Default return value for find_segments
    parser.find_segments = MagicMock(
        return_value=(
            "Fallout 4 v1.10.163",  # game_version
            "Buffout 4 v1.28.6",  # crashgen_version
            'Unhandled exception "EXCEPTION_ACCESS_VIOLATION"',  # main_error
            [  # segments
                ["Achievements: true"],  # segment_crashgen
                ["OS: Microsoft Windows 11"],  # segment_system
                ["[ 0] 0x7FF6EF4C3512 Fallout4.exe"],  # segment_callstack
                ["Fallout4.exe v1.10.163.0"],  # segment_allmodules
                ["Achievements.dll v2.3.0"],  # segment_xsemodules
                ["[00] Fallout4.esm"],  # segment_plugins
            ],
        )
    )

    return parser


# ============================================================================
# Integration Test Fixtures
# ============================================================================


@pytest.fixture
def patch_scanlog_dependencies(
    mock_yamldata: MagicMock,
    mock_file_io: MagicMock,
    mock_parser: MagicMock,
) -> dict[str, Any]:
    """Set up patches for all ScanLog external dependencies.

    Args:
        mock_yamldata: Mock YAML data (from yamldata_fixtures).
        mock_file_io: Mock file I/O operations.
        mock_parser: Mock crash log parser.

    Returns:
        dict[str, Any]: Dictionary of patch context managers.
    """
    patches = {
        "file_io": patch("ClassicLib.integration.factory.get_file_io", return_value=mock_file_io),
        "parser": patch("ClassicLib.integration.factory.get_parser", return_value=mock_parser),
        "yamldata": patch(
            "ClassicLib.scanning.logs.scanloginfo.ClassicScanLogsInfo.create_async",
            new_callable=AsyncMock,
            return_value=mock_yamldata,
        ),
    }
    return patches


# ============================================================================
# Mock Settings Fixtures (Consolidated from test files)
# ============================================================================


# Default settings map for ScanGame tests
DEFAULT_SCAN_SETTINGS_MAP: dict[str, Any] = {
    "catch_log_errors": ["error", "warning", "critical"],
    "exclude_log_files": ["ignore.log"],
    "exclude_log_errors": ["ignorable error"],
    "Mods_Warn.Mods_Path_Missing": "Mods path not configured",
    "Mods_Warn.Mods_Path_Invalid": "Mods path does not exist",
    "Mods_Warn.BA2_Invalid": "Invalid BA2 archive",
    "Mods_Warn.DDS_Invalid_Dimensions": "DDS file has invalid dimensions",
}


@pytest.fixture
def mock_scan_yaml_settings() -> Generator[MagicMock, None, None]:
    """Mock YAML settings for ScanGame tests.

    Patches ClassicLib.io.yaml.yaml_settings with a function that
    returns values from a default settings map for common scan operations.

    Yields:
        MagicMock: The mock yaml_settings function.
    """
    with patch("ClassicLib.io.yaml.yaml_settings") as mock_yaml_cache:

        def yaml_side_effect(type_: type, yaml_key: Any, setting_path: str, default: Any = None) -> Any:
            return DEFAULT_SCAN_SETTINGS_MAP.get(setting_path, default)

        mock_yaml_cache.side_effect = yaml_side_effect
        yield mock_yaml_cache


@pytest.fixture
def mock_orchestrator_settings() -> Generator[tuple[MagicMock, MagicMock], None, None]:
    """Mock async settings for OrchestratorCore tests.

    Patches both yaml_settings_async and classic_settings_async
    for orchestrator testing.

    Yields:
        Tuple of (mock_yaml_settings_async, mock_classic_settings_async).
    """
    with (
        patch("ClassicLib.scanning.logs.orchestrator_core.yaml_settings_async") as mock_yaml,
        patch("ClassicLib.scanning.logs.orchestrator_core.classic_settings_async") as mock_classic,
    ):
        mock_yaml.return_value = None
        mock_classic.return_value = None
        yield (mock_yaml, mock_classic)


@pytest.fixture
def mock_orchestrator_settings_with_concurrency() -> Generator[tuple[MagicMock, MagicMock, Any], None, None]:
    """Mock async settings for OrchestratorCore with HybridOrchestrator classic_settings.

    This variant also mocks HybridOrchestrator.classic_settings for
    tests that need to configure concurrency settings.

    Yields:
        Tuple of (mock_yaml_settings_async, mock_classic_settings_async, hybrid_patch).
    """
    with (
        patch("ClassicLib.scanning.logs.orchestrator_core.yaml_settings_async") as mock_yaml,
        patch("ClassicLib.scanning.logs.orchestrator_core.classic_settings_async") as mock_classic,
        patch("ClassicLib.scanning.logs.hybrid_orchestrator.classic_settings", return_value=0) as hybrid_mock,
    ):
        mock_yaml.return_value = None
        mock_classic.return_value = None
        yield (mock_yaml, mock_classic, hybrid_mock)


@pytest.fixture
def mock_paths(tmp_path: Path) -> dict[str, Path]:
    """Create a temporary directory structure for ScanGame tests.

    Creates common directories needed for scan tests including
    mods, data, logs, docs, and game directories.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        dict[str, Path]: Dictionary mapping directory names to paths.
    """
    paths = {
        "game": tmp_path / "game",
        "data": tmp_path / "game" / "Data",
        "mods": tmp_path / "mods",
        "logs": tmp_path / "logs",
        "docs": tmp_path / "docs",
        "backup": tmp_path / "backup",
    }

    # Create all directories
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)

    return paths


@pytest.fixture
def mock_scan_settings() -> MagicMock:
    """Create a mock ScanSettings object for tests.

    Returns:
        MagicMock: Mock with common scan settings attributes.
    """
    settings = MagicMock()
    settings.mods_path = Path("/mock/mods")
    settings.data_path = Path("/mock/data")
    settings.docs_path = Path("/mock/docs")
    settings.game_path = Path("/mock/game")
    settings.backup_path = Path("/mock/backup")
    settings.check_dds = True
    settings.check_ba2 = True
    settings.check_xse = True
    settings.check_previs = True
    settings.cleanup_mode = False
    return settings


@pytest.fixture
def mock_issue_messages() -> MagicMock:
    """Create a mock issue messages dictionary.

    Returns:
        MagicMock: Mock with common issue message keys.
    """
    messages = MagicMock()
    messages.dds_invalid = "DDS file has invalid dimensions"
    messages.ba2_invalid = "Invalid BA2 archive"
    messages.xse_conflict = "XSE conflict detected"
    messages.previs_issue = "Previs file issue"
    return messages


@contextmanager
def scan_yaml_settings_context(settings_map: dict[str, Any] | None = None) -> Generator[MagicMock, None, None]:
    """Context manager for mocking YAML settings in scan tests.

    This is a helper for tests that need custom settings maps.

    Args:
        settings_map: Optional custom settings map. Uses DEFAULT_SCAN_SETTINGS_MAP if None.

    Yields:
        MagicMock: The mock yaml_settings function.
    """
    effective_map = settings_map if settings_map is not None else DEFAULT_SCAN_SETTINGS_MAP

    with patch("ClassicLib.io.yaml.yaml_settings") as mock_yaml_cache:

        def yaml_side_effect(type_: type, yaml_key: Any, setting_path: str, default: Any = None) -> Any:
            return effective_map.get(setting_path, default)

        mock_yaml_cache.side_effect = yaml_side_effect
        yield mock_yaml_cache


# ============================================================================
# DDS Analyzer Test Fixtures
# ============================================================================


@pytest.fixture
def dds_analyzer() -> EnhancedDDSAnalyzer:
    """Create DDS analyzer instance without library dependencies.

    Creates an EnhancedDDSAnalyzer with PyFFI and PIL_DDS libraries
    disabled for isolated testing.

    Returns:
        EnhancedDDSAnalyzer: Analyzer instance configured for testing.
    """
    with (
        patch("ClassicLib.scanning.game.checks.dds_analyzer.HAS_PYFFI", False),
        patch("ClassicLib.scanning.game.checks.dds_analyzer.HAS_PIL_DDS", False),
    ):
        return EnhancedDDSAnalyzer(use_libraries=False)


@pytest.fixture
def valid_dds_data() -> bytes:
    """Create valid DDS header data for testing.

    Creates a minimal valid DDS file header with:
    - Magic number "DDS "
    - Valid header size (124)
    - Dimensions: 1024x2048
    - Pixel format: DXT5
    - Single mipmap level

    Returns:
        bytes: Valid DDS header data (128 bytes).
    """
    header = bytearray(128)

    # Magic number "DDS "
    header[0:4] = b"DDS "

    # dwSize (124)
    header[4:8] = struct.pack("<I", 124)

    # dwFlags
    flags = DDSFlags.CAPS | DDSFlags.HEIGHT | DDSFlags.WIDTH | DDSFlags.PIXELFORMAT
    header[8:12] = struct.pack("<I", flags)

    # dwHeight
    header[12:16] = struct.pack("<I", 1024)

    # dwWidth
    header[16:20] = struct.pack("<I", 2048)

    # dwPitchOrLinearSize
    header[20:24] = struct.pack("<I", 0)

    # dwDepth
    header[24:28] = struct.pack("<I", 1)

    # dwMipMapCount
    header[28:32] = struct.pack("<I", 1)

    # Pixel format at offset 76
    pf_offset = 76
    header[pf_offset : pf_offset + 4] = struct.pack("<I", 32)  # Size
    header[pf_offset + 4 : pf_offset + 8] = struct.pack("<I", DDSPixelFlags.FOURCC)  # Flags
    header[pf_offset + 8 : pf_offset + 12] = b"DXT5"  # FourCC

    # Caps
    header[108:112] = struct.pack("<I", 0x1000)  # DDSCAPS_TEXTURE
    header[112:116] = struct.pack("<I", 0)  # Caps2

    return bytes(header)


@pytest.fixture
def bc7_dds_data(valid_dds_data: bytes) -> bytes:
    """Create DDS with BC7 format.

    Args:
        valid_dds_data: Base valid DDS header data.

    Returns:
        bytes: DDS header with DX10 FourCC (for BC7 format).
    """
    data = bytearray(valid_dds_data)
    # Change FourCC to DX10
    data[84:88] = b"DX10"
    return bytes(data)


@pytest.fixture
def odd_dimension_dds_data(valid_dds_data: bytes) -> bytes:
    """Create DDS with odd (non-power-of-2) dimensions.

    Args:
        valid_dds_data: Base valid DDS header data.

    Returns:
        bytes: DDS header with dimensions 1023x2047.
    """
    data = bytearray(valid_dds_data)
    # Set odd dimensions
    data[12:16] = struct.pack("<I", 1023)  # Height
    data[16:20] = struct.pack("<I", 2047)  # Width
    return bytes(data)
