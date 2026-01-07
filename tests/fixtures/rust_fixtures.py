"""Rust-specific test fixtures.

Fixtures for Rust integration testing including:
- YAML environment setup
- Rust extension availability checks
- Performance timing utilities
- Dataset fixtures for FormID and plugin testing
"""

import asyncio
import time
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ============================================================================
# YAML Content Constants for Rust YamlData Initialization
# ============================================================================

MINIMAL_MAIN_YAML = """
CLASSIC_Info:
  version: "7.31.0"
  version_date: "2024-01-01"
catch_log_records: []
CLASSIC_Interface:
  autoscan_text_Fallout4: "Autoscan report"
"""

MINIMAL_GAME_YAML = """
Game_Hints:
  - "Hint 1"
Game_Info:
  CRASHGEN_LogName: "Buffout 4"
  CRASHGEN_LatestVer: "1.28.6"
  XSE_Acronym: "F4SE"
  GameVersion: "1.10.163"
  GameVersionNEW: "1.10.984"
GameVR_Info:
  CRASHGEN_LogName: "Buffout 4 VR"
  CRASHGEN_LatestVer: "1.28.6"
  GameVersion: "1.2.72"
  CRASHGEN_Ignore: []
Warnings_CRASHGEN:
  Warn_NOPlugins: "No plugins warning"
  Warn_Outdated: "Outdated warning"
Crashlog_Plugins_Exclude: []
Crashlog_Records_Exclude: []
Crashlog_Error_Check:
  "Error Pattern": "Error Description"
Crashlog_Stack_Check: {}
Mods_CONF:
  "ConflictingMod.esp": "Reason"
Mods_CORE: {}
Mods_CORE_FOLON: {}
Mods_FREQ:
  "FrequentMod.esp": "Reason"
Mods_OPC2: {}
Mods_SOLU: {}
"""

MINIMAL_IGNORE_YAML = """
CLASSIC_Ignore_Fallout4: []
"""


# ============================================================================
# Performance Timer Classes
# ============================================================================


class PerformanceTimer:
    """Helper class for performance timing in tests."""

    def __init__(self) -> None:
        self.elapsed: float = 0.0
        self.start_time: float = 0.0

    def __enter__(self) -> "PerformanceTimer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        self.elapsed = time.perf_counter() - self.start_time

    def reset(self) -> None:
        """Reset the timer."""
        self.elapsed = 0.0
        self.start_time = 0.0


# ============================================================================
# YAML Environment Fixtures
# ============================================================================


@pytest.fixture
def rust_yaml_files(tmp_path: Path) -> dict[str, Path]:
    """Create minimal YAML files needed for Rust YamlData initialization.

    This fixture creates the directory structure and YAML files that the
    Rust classic_config::YamlData requires to initialize successfully.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        dict: Contains 'root_dir', 'data_dir', and 'tmp_path' paths.
    """
    # Create directory structure
    root_dir = tmp_path / "classic_root"
    data_dir = root_dir / "CLASSIC Data"
    databases_dir = data_dir / "databases"
    databases_dir.mkdir(parents=True)

    # Create YAML files
    (databases_dir / "CLASSIC Main.yaml").write_text(MINIMAL_MAIN_YAML, encoding="utf-8")
    (databases_dir / "CLASSIC Fallout4.yaml").write_text(MINIMAL_GAME_YAML, encoding="utf-8")
    (root_dir / "CLASSIC Ignore.yaml").write_text(MINIMAL_IGNORE_YAML, encoding="utf-8")

    return {
        "root_dir": root_dir,
        "data_dir": data_dir,
        "tmp_path": tmp_path,
    }


@pytest.fixture
def mock_rust_yaml_environment(rust_yaml_files: dict[str, Path]) -> Generator[dict[str, Path], None, None]:
    """Mock the environment for Rust YamlData initialization.

    This fixture patches ResourceLoader.get_data_directory() and GlobalRegistry
    to use the test YAML files, allowing Rust orchestrator to initialize in CI.

    Args:
        rust_yaml_files: The fixture providing YAML files.

    Yields:
        dict: The rust_yaml_files dictionary.

    Usage:
        def test_something(mock_rust_yaml_environment):
            # Rust orchestrator will now find the test YAML files
            orch = ClassicOrchestrator()
    """
    data_dir = rust_yaml_files["data_dir"]

    with (
        patch("ClassicLib.ResourceLoader.ResourceLoader.get_data_directory", return_value=data_dir),
        patch("ClassicLib.GlobalRegistry.get_game", return_value="Fallout4"),
        patch("ClassicLib.GlobalRegistry.get_vr", return_value=""),
    ):
        yield rust_yaml_files


# ============================================================================
# Performance Timer Fixtures
# ============================================================================


@pytest.fixture
def performance_timer() -> type[PerformanceTimer]:
    """Context manager for timing operations.

    Returns:
        type[PerformanceTimer]: The PerformanceTimer class for instantiation.

    Usage:
        def test_performance(performance_timer):
            timer = performance_timer()
            with timer:
                do_operation()
            assert timer.elapsed < 1.0
    """
    return PerformanceTimer


@pytest.fixture
def performance_timer_instance() -> PerformanceTimer:
    """Get a ready-to-use PerformanceTimer instance.

    Returns:
        PerformanceTimer: A fresh timer instance.
    """
    return PerformanceTimer()


# ============================================================================
# Dataset Fixtures
# ============================================================================


@pytest.fixture
def mock_formid_dataset() -> dict[str, list[str]]:
    """Create a comprehensive FormID test dataset.

    Returns:
        dict[str, list[str]]: Dictionary of FormID categories.
    """
    return {
        "simple": ["00012345", "00023456", "00034567"],
        "mixed_case": ["00AbCdEf", "00FEDCBA", "00aAbBcC"],
        "with_prefixes": ["0x00012345", "0X00023456", "00034567"],
        "edge_cases": ["00000001", "FFFFFFFF", "00000000"],
        "invalid": ["GGGGGGGG", "12345", "not_a_formid", ""],
    }


@pytest.fixture
def mock_plugin_dataset() -> dict[str, list[str | None]]:
    """Create a comprehensive plugin test dataset.

    Returns:
        dict[str, list]: Dictionary of plugin categories.
    """
    return {
        "vanilla": ["Fallout4.esm", "DLCRobot.esm", "DLCworkshop01.esm", "DLCCoast.esm", "DLCNukaWorld.esm"],
        "creation_club": ["ccBGSFO4001-PipBoy(Camo01).esl", "ccBGSFO4003-PipBoy(Camo02).esl", "ccBGSFO4016-Prey.esl"],
        "mods": ["TestMod.esp", "AnotherMod.esp", "BigOverhaul.esm", "Patch.esp"],
        "invalid": ["NotAPlugin.txt", "BadExtension.esz", "", None],
    }


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture
async def initialized_database_pool(tmp_path: Path):
    """Create and initialize a database pool for testing.

    Handles both Rust and Python implementations appropriately.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Yields:
        The initialized database pool.
    """
    import sqlite3

    from ClassicLib.integration.factory import get_database_pool
    from ClassicLib.integration.status import is_rust_accelerated

    db_path = tmp_path / "test.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Fallout4 (
            formid TEXT NOT NULL,
            plugin TEXT NOT NULL,
            entry TEXT NOT NULL,
            PRIMARY KEY (formid, plugin)
        )
    """)

    # Insert test data
    test_data = [
        ("00012345", "Fallout4.esm", "Power Armor Frame"),
        ("00023456", "DLCCoast.esm", "Fog Condenser"),
        ("00034567", "DLCNukaWorld.esm", "Nuka Cola Quantum"),
        ("00045678", "TestMod.esp", "Custom Weapon"),
    ]

    cursor.executemany("INSERT OR REPLACE INTO Fallout4 (formid, plugin, entry) VALUES (?, ?, ?)", test_data)

    conn.commit()
    conn.close()

    # Create pool via factory
    pool = get_database_pool(max_connections=5, cache_ttl_seconds=60)

    # Initialize appropriately
    if hasattr(pool, "initialize"):
        if is_rust_accelerated("database_pool") and hasattr(pool, "_rust_pool"):
            # Rust version can take paths
            await pool.initialize([str(db_path)])
        else:
            # Python version uses global DB_PATHS
            with patch("ClassicLib.Constants.get_db_paths", return_value=(db_path,)):
                await pool.initialize()

    yield pool

    # Cleanup
    if hasattr(pool, "close"):
        await pool.close()


# ============================================================================
# Mock Orchestrator Fixtures
# ============================================================================


@pytest.fixture
def mock_orchestrator() -> MagicMock:
    """Create a mock orchestrator for testing.

    Returns:
        MagicMock: Mock orchestrator with async process method.
    """
    orchestrator = MagicMock()
    orchestrator.process_crash_log_async = MagicMock(return_value=asyncio.Future())
    orchestrator.process_crash_log_async.return_value.set_result({"segments": {}, "formids": [], "plugins": [], "records": []})
    return orchestrator
