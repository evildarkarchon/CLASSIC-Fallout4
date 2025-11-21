"""
Shared fixtures for Rust integration tests.

This module provides common fixtures used across rust integration tests
to ensure consistent test environments and reduce duplication.
"""

import asyncio
import time
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def crash_log_samples(tmp_path):
    """Create sample crash logs for testing."""
    samples = {}

    # Small sample - basic crash with FormID
    small_log = tmp_path / "small.log"
    small_log.write_text("""
Buffout 4 Crash Log
EXCEPTION_ACCESS_VIOLATION (0xc0000005)
Unhandled exception at 0x7FF6DEADBEEF

PROBABLE CALL STACK:
[0] 0x7FF6DEADBEEF    FormID: 0x00012345    TestMod.esp
[1] 0x7FF6CAFEBABE    FormID: 0x00023456    Fallout4.esm
[2] 0x7FF6BADF00D5    FormID: 0x00034567    DLCCoast.esm

PLUGINS:
[FE:000] ccBGSFO4001-PipBoy(Camo01).esl
[FE:001] ccBGSFO4003-PipBoy(Camo02).esl
[00] Fallout4.esm
[01] DLCRobot.esm
[02] DLCworkshop01.esm
[03] DLCCoast.esm
[04] TestMod.esp
""")
    samples["small"] = small_log

    # Medium sample - more complex crash
    medium_log = tmp_path / "medium.log"
    medium_content = """
Buffout 4 Crash Log

EXCEPTION_ACCESS_VIOLATION (0xc0000005)

SYSTEM SPECS:
OS: Windows 10
GPU: NVIDIA RTX 3080
RAM: 32GB

PROBABLE CALL STACK:
"""
    # Add many stack frames
    for i in range(100):
        medium_content += f"[{i}] 0x7FF6{i:08X}    FormID: 0x{i:08X}    TestMod{i % 5}.esp\n"

    medium_content += "\nPLUGINS:\n"
    for i in range(50):
        medium_content += f"[{i:02X}] Plugin_{i}.esm\n"

    medium_log.write_text(medium_content)
    samples["medium"] = medium_log

    # Large sample - stress test
    large_log = tmp_path / "large.log"
    large_content = "Buffout 4 Crash Log\n" + ("Line of log data\n" * 10000)
    large_log.write_text(large_content)
    samples["large"] = large_log

    return samples


@pytest.fixture
def mock_scanlog_info():
    """Create mock ScanLogInfo for testing."""

    class MockScanLogInfo:
        def __init__(self):
            self.crashgen_name = "Buffout"
            self.xse_acronym = "F4SE"
            self.game_root_name = "Fallout4"
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

            # Ignore lists
            self.game_ignore_plugins = []
            self.game_ignore_records = []
            self.ignore_list = []

        def get(self, key, default=None):
            """Allow dict-like access."""
            return getattr(self, key, default)

    return MockScanLogInfo()


@pytest.fixture
def mock_yamldata():
    """Alias for mock_scanlog_info for compatibility."""
    return mock_scanlog_info()


@pytest.fixture
def performance_timer():
    """Context manager for timing operations."""

    class Timer:
        def __init__(self):
            self.elapsed = 0
            self.start_time = 0

        def __enter__(self):
            self.start_time = time.perf_counter()
            return self

        def __exit__(self, *args):
            self.elapsed = time.perf_counter() - self.start_time

        def reset(self):
            self.elapsed = 0
            self.start_time = 0

    return Timer


@pytest.fixture
async def initialized_database_pool(tmp_path):
    """
    Create and initialize a database pool for testing.

    Handles both Rust and Python implementations appropriately.
    """
    # Create test database
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
            from ClassicLib.Constants import DB_PATHS

            # Temporarily add our test database to DB_PATHS
            original_paths = DB_PATHS.copy()
            DB_PATHS.clear()
            DB_PATHS.append(db_path)

            try:
                await pool.initialize()
            finally:
                # Restore original paths
                DB_PATHS.clear()
                DB_PATHS.extend(original_paths)

    yield pool

    # Cleanup
    if hasattr(pool, "close"):
        await pool.close()


@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator for testing."""
    orchestrator = MagicMock()
    orchestrator.process_crash_log_async = MagicMock(return_value=asyncio.Future())
    orchestrator.process_crash_log_async.return_value.set_result({"segments": {}, "formids": [], "plugins": [], "records": []})
    return orchestrator


class PerformanceTimer:
    """Helper class for performance timing in tests."""

    def __init__(self):
        self.elapsed = 0.0
        self.start_time = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed = time.perf_counter() - self.start_time


@pytest.fixture
def mock_formid_dataset():
    """Create a comprehensive FormID test dataset."""
    return {
        "simple": ["00012345", "00023456", "00034567"],
        "mixed_case": ["00AbCdEf", "00FEDCBA", "00aAbBcC"],
        "with_prefixes": ["0x00012345", "0X00023456", "00034567"],
        "edge_cases": ["00000001", "FFFFFFFF", "00000000"],
        "invalid": ["GGGGGGGG", "12345", "not_a_formid", ""],
    }


@pytest.fixture
def mock_plugin_dataset():
    """Create a comprehensive plugin test dataset."""
    return {
        "vanilla": ["Fallout4.esm", "DLCRobot.esm", "DLCworkshop01.esm", "DLCCoast.esm", "DLCNukaWorld.esm"],
        "creation_club": ["ccBGSFO4001-PipBoy(Camo01).esl", "ccBGSFO4003-PipBoy(Camo02).esl", "ccBGSFO4016-Prey.esl"],
        "mods": ["TestMod.esp", "AnotherMod.esp", "BigOverhaul.esm", "Patch.esp"],
        "invalid": ["NotAPlugin.txt", "BadExtension.esz", "", None],
    }
