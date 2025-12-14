"""ScanLog test fixtures for crash log parsing and analysis testing.

This module provides fixtures specifically for testing the ScanLog package,
including crash log samples, mock YAML data, and orchestrator components.
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================================
# Crash Log Sample Fixtures
# ============================================================================


@pytest.fixture
def sample_crash_log_content() -> str:
    """Provide a realistic crash log content string for testing.

    Returns:
        str: Complete crash log content with all standard sections.
    """
    return """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512|nvwgf2umx.dll+00FF1234

\t[Compatibility]
\tAchievements: true
\tMemoryManager: false
\tF4EE: false
\tActorIsHostileToActor: true
\tBSTextureStreamerLocalHeap: true
\tHavokMemorySystem: true
\tSmallBlockAllocator: false
\tScaleformAllocator: true
\tMaxStdIO: 8192
\tWorkshopMenu: true
\tLoadScreenFix: true

SYSTEM SPECS:
\tOS: Microsoft Windows 11 Pro v10.0.22621
\tCPU: AMD Ryzen 7 7800X3D 8-Core Processor
\tGPU #1: Nvidia AD104 [GeForce RTX 4070]
\tGPU #2: AMD RX 6800
\tPHYSICAL MEMORY: 32.0 GB

PROBABLE CALL STACK:
\t[ 0] 0x7FF6EF4C3512 Fallout4.exe+0733512 -> TESForm::SetReference+0x12
\t[ 1] 0x7FF6EF4C3600 Fallout4.exe+0733600 -> BGSInventoryItem::GetOwner+0x30
\t[ 2] 0x7FFB12340000 nvwgf2umx.dll+00FF1234 -> ?
\t[ 3] 0x7FF6EF500000 Fallout4.exe+0800000 -> BSResource::LoaderThread::Run+0x100
\t[ 4] 0x7FFB23450000 kernel32.dll+0001000 -> BaseThreadInitThunk
\t[ 5] 0x7FFB34560000 ntdll.dll+00023000 -> RtlUserThreadStart

MODULES:
\tFallout4.exe v1.10.163.0
\tnvwgf2umx.dll v31.0.15.3713
\tkernel32.dll v10.0.22621.1
\tntdll.dll v10.0.22621.1
\tbuffer_allocator.dll v1.28.6
\tAchievements.dll v2.3.0
\tBakaScrapHeap.dll v1.1.0
\tLooksMenu.dll v1.6.23

F4SE PLUGINS:
\tAchievements.dll v2.3.0
\tBakaScrapHeap.dll v1.1.0
\tLooksMenu.dll v1.6.23
\tbuffer_allocator.dll v1.28.6
\tHighFPSPhysicsFix.dll v0.8.6
\tTestPlugin.dll v1.0.0

PLUGINS:
\t[00] Fallout4.esm
\t[01] DLCRobot.esm
\t[02] DLCworkshop01.esm
\t[03] DLCCoast.esm
\t[04] DLCworkshop02.esm
\t[05] DLCworkshop03.esm
\t[06] DLCNukaWorld.esm
\t[FE:000] ccBGSFO4001-PipBoy(Black).esl
\t[FE:001] TestMod.esl
\t[07] Unofficial Fallout 4 Patch.esp
\t[08] ArmorKeywords.esm
\t[09] ProblemPlugin.esp
\t[0A] AnotherMod.esp
"""


@pytest.fixture
def sample_crash_log_lines(sample_crash_log_content: str) -> list[str]:
    """Provide crash log content as list of lines.

    Args:
        sample_crash_log_content: The full crash log content string.

    Returns:
        list[str]: List of individual lines from the crash log.
    """
    return sample_crash_log_content.splitlines()


@pytest.fixture
def malformed_crash_log_content() -> str:
    """Provide a malformed/incomplete crash log for error handling tests.

    Returns:
        str: Incomplete crash log content missing standard sections.
    """
    return """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512

SYSTEM SPECS:
\tOS: Microsoft Windows 11 Pro

"""


@pytest.fixture
def minimal_crash_log_content() -> str:
    """Provide a minimal valid crash log for edge case testing.

    Returns:
        str: Minimal crash log with only essential sections.
    """
    return """Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF6EF4C3512 Fallout4.exe+0733512

\t[Compatibility]
\tAchievements: true

SYSTEM SPECS:
\tOS: Microsoft Windows 11 Pro

PROBABLE CALL STACK:
\t[ 0] 0x7FF6EF4C3512 Fallout4.exe+0733512

MODULES:
\tFallout4.exe v1.10.163.0

F4SE PLUGINS:
\tAchievements.dll v2.3.0

PLUGINS:
\t[00] Fallout4.esm
"""


@pytest.fixture
def crash_log_file(tmp_path: Path, sample_crash_log_content: str) -> Path:
    """Create a temporary crash log file for testing.

    Args:
        tmp_path: Pytest temporary directory fixture.
        sample_crash_log_content: The crash log content to write.

    Returns:
        Path: Path to the created crash log file.
    """
    crash_log = tmp_path / "crash-2024-01-15-12-30-45.log"
    crash_log.write_text(sample_crash_log_content, encoding="utf-8")
    return crash_log


@pytest.fixture
def malformed_crash_log_file(tmp_path: Path, malformed_crash_log_content: str) -> Path:
    """Create a temporary malformed crash log file for error handling tests.

    Args:
        tmp_path: Pytest temporary directory fixture.
        malformed_crash_log_content: The malformed crash log content.

    Returns:
        Path: Path to the created malformed crash log file.
    """
    crash_log = tmp_path / "crash-malformed.log"
    crash_log.write_text(malformed_crash_log_content, encoding="utf-8")
    return crash_log


@pytest.fixture
def crash_logs_directory(tmp_path: Path, sample_crash_log_content: str) -> Path:
    """Create a temporary directory with multiple crash log files.

    Args:
        tmp_path: Pytest temporary directory fixture.
        sample_crash_log_content: Content to use for crash logs.

    Returns:
        Path: Path to the directory containing crash logs.
    """
    crash_dir = tmp_path / "Crash Logs"
    crash_dir.mkdir()

    # Create multiple crash logs with different timestamps
    for i, timestamp in enumerate(["2024-01-15-10-00-00", "2024-01-15-11-00-00", "2024-01-15-12-00-00"]):
        crash_file = crash_dir / f"crash-{timestamp}.log"
        # Vary content slightly for testing
        content = sample_crash_log_content.replace("0733512", f"073351{i}")
        crash_file.write_text(content, encoding="utf-8")

    return crash_dir


# ============================================================================
# Mock YamlData Fixtures
# ============================================================================


@pytest.fixture
def mock_yamldata() -> MagicMock:
    """Create a mock ClassicScanLogsInfo object for OrchestratorCore testing.

    Returns:
        MagicMock: Mock object with all required yamldata attributes.

    Note:
        This fixture sets spec=False to allow attribute assignment, but explicitly
        sets all required attributes to avoid Mock objects being passed to Rust.
    """
    yamldata = MagicMock(spec=False)

    # Basic game info
    yamldata.crashgen_name = "Buffout 4"
    yamldata.xse_acronym = "F4SE"
    yamldata.crashgen_latest_og = "1.28.6"
    yamldata.crashgen_latest_vr = "1.26.2"

    # CRITICAL: These attributes are required by RustPluginAnalyzer
    # They must be proper Python types, not Mock objects
    yamldata.game_ignore_plugins = []  # List of plugins to ignore
    yamldata.ignore_list = []  # Additional ignore list
    yamldata.game_version = "1.10.163"  # Game version string
    yamldata.game_version_vr = "1.2.72"  # VR game version
    yamldata.game_version_new = "1.10.163"  # New game version

    # Required for report generation
    yamldata.classic_version = "CLASSIC v1.0.0"

    # Required for suspect scanning
    yamldata.suspects_error_list = {}
    yamldata.suspects_stack_list = {}

    # Game mod data for detection
    yamldata.game_mods_conf = {
        "conflict_mod_1|conflict_mod_2": "These mods conflict together"
    }
    yamldata.game_mods_freq = {
        "problemplugin.esp": "This plugin causes frequent crashes"
    }
    yamldata.game_mods_solu = {
        "outdated.esp": "Update to latest version"
    }
    yamldata.game_mods_core = {
        "ufop4": {
            "warn": "Unofficial Patch not detected",
            "plugin": "Unofficial Fallout 4 Patch.esp",
            "required": True
        }
    }
    yamldata.game_mods_core_folon = {}
    yamldata.game_mods_opc2 = {
        "oldmod.esp": "This mod is outdated"
    }

    # Crash log error/stack checks
    yamldata.crashlog_error_check = {
        "HIGH | Test Error": "error_signal"
    }
    yamldata.crashlog_stack_check = {
        "MEDIUM | Stack Error": ["required:signal1", "optional:signal2"]
    }

    # Game hints
    yamldata.classic_game_hints = ["Test hint 1", "Test hint 2"]
    yamldata.autoscan_text = "Additional scan information"

    return yamldata


@pytest.fixture
def mock_yamldata_async() -> MagicMock:
    """Create a mock ClassicScanLogsInfo with async factory method.

    Returns:
        MagicMock: Mock yamldata with async create_async class method.

    Note:
        This fixture includes all required attributes for Rust compatibility.
    """
    yamldata = MagicMock(spec=False)

    # Basic game info
    yamldata.crashgen_name = "Buffout 4"
    yamldata.xse_acronym = "F4SE"
    yamldata.crashgen_latest_og = "1.28.6"
    yamldata.crashgen_latest_vr = "1.26.2"

    # CRITICAL: Required by RustPluginAnalyzer
    yamldata.game_ignore_plugins = []
    yamldata.ignore_list = []
    yamldata.game_version = "1.10.163"
    yamldata.game_version_vr = "1.2.72"
    yamldata.game_version_new = "1.10.163"

    # Required for report generation
    yamldata.classic_version = "CLASSIC v1.0.0"

    # Required for suspect scanning
    yamldata.suspects_error_list = {}
    yamldata.suspects_stack_list = {}

    # Game mod data
    yamldata.game_mods_conf = {}
    yamldata.game_mods_freq = {}
    yamldata.game_mods_solu = {}
    yamldata.game_mods_core = {}
    yamldata.game_mods_core_folon = {}
    yamldata.game_mods_opc2 = {}

    # Error checks
    yamldata.crashlog_error_check = {}
    yamldata.crashlog_stack_check = {}

    # Hints
    yamldata.classic_game_hints = []
    yamldata.autoscan_text = ""

    return yamldata


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
# Parser Test Fixtures
# ============================================================================


@pytest.fixture
def segment_boundaries() -> list[tuple[str, str]]:
    """Provide standard segment boundaries for crash log parsing.

    Returns:
        list[tuple[str, str]]: List of (start_marker, end_marker) tuples.
    """
    return [
        ("\t[Compatibility]", "SYSTEM SPECS:"),
        ("SYSTEM SPECS:", "PROBABLE CALL STACK:"),
        ("PROBABLE CALL STACK:", "MODULES:"),
        ("MODULES:", "F4SE PLUGINS:"),
        ("F4SE PLUGINS:", "PLUGINS:"),
        ("PLUGINS:", "EOF"),
    ]


@pytest.fixture
def expected_segments() -> dict[str, list[str]]:
    """Provide expected parsed segments from sample crash log.

    Returns:
        dict[str, list[str]]: Dictionary mapping segment names to expected content.
    """
    return {
        "crashgen": [
            "Achievements: true",
            "MemoryManager: false",
            "F4EE: false",
        ],
        "system": [
            "OS: Microsoft Windows 11 Pro v10.0.22621",
            "CPU: AMD Ryzen 7 7800X3D 8-Core Processor",
            "GPU #1: Nvidia AD104 [GeForce RTX 4070]",
        ],
        "callstack": [
            "[ 0] 0x7FF6EF4C3512 Fallout4.exe+0733512",
        ],
        "plugins": [
            "[00] Fallout4.esm",
            "[01] DLCRobot.esm",
        ],
    }


# ============================================================================
# Orchestrator Test Fixtures
# ============================================================================


@pytest.fixture
def mock_orchestrator_dependencies(mock_yamldata: MagicMock, mock_database_pool: MagicMock) -> dict[str, Any]:
    """Bundle common mock dependencies for OrchestratorCore testing.

    Args:
        mock_yamldata: Mock YAML data fixture.
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
        mock_yamldata: Mock YAML data.
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
