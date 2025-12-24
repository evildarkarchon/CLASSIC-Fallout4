"""ScanLog orchestrator and parser test fixtures.

This module provides fixtures specifically for testing the ScanLog orchestrator
and parser components. Crash log content fixtures are in crash_log_fixtures.py
and yamldata fixtures are in yamldata_fixtures.py.

Note: This module imports mock_yamldata from yamldata_fixtures.py.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
            "ClassicLib.ScanLog.scanloginfo.ClassicScanLogsInfo.create_async",
            new_callable=AsyncMock,
            return_value=mock_yamldata,
        ),
    }
    return patches
