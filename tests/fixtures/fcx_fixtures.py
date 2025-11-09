"""
Test fixtures for FCX mode testing.

This module provides test fixtures for creating test configuration files,
verifying no file modifications occur, and generating sample ConfigIssue objects.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import pytest

from ClassicLib.ScanGame.Config import ConfigFileCache
from ClassicLib.ScanGame.models.fcx_issue import ConfigIssue


@pytest.fixture
def fcx_test_config(tmp_path: Path) -> ConfigFileCache:
    """
    Create test configuration files with known issues for FCX mode testing.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        ConfigFileCache instance with test configuration files loaded
    """
    # Create espexplorer.ini with commented hotkey
    espexplorer_ini = tmp_path / "espexplorer.ini"
    espexplorer_ini.write_text("[Main]\n; Hotkey to open ESPExplorer\nHotKey = ; F10\n", encoding="utf-8")

    # Create epo.ini with high particle count
    epo_ini = tmp_path / "epo.ini"
    epo_ini.write_text("[Particles]\niMaxDesired = 7500\niMaxActive = 7500\n", encoding="utf-8")

    # Create f4ee.ini with locked settings
    f4ee_ini = tmp_path / "f4ee.ini"
    f4ee_ini.write_text("[HeadParts]\nbUnlockHeadParts = 0\nbUnlockTints = 0\n", encoding="utf-8")

    # Create highfpsphysicsfix.ini with low loading screen FPS
    highfps_ini = tmp_path / "highfpsphysicsfix.ini"
    highfps_ini.write_text("[Limiter]\nLoadingScreenFPS = 60.0\nGameFPS = 0.0\n", encoding="utf-8")

    # Create enblocal.ini with VSync enabled
    enblocal_ini = tmp_path / "enblocal.ini"
    enblocal_ini.write_text("[ENGINE]\nForceVSync = 1\niPresentInterval = 1\n", encoding="utf-8")

    # Create ConfigFileCache with test files
    cache = ConfigFileCache()
    cache._config_files = {
        "espexplorer.ini": espexplorer_ini,
        "epo.ini": epo_ini,
        "f4ee.ini": f4ee_ini,
        "highfpsphysicsfix.ini": highfps_ini,
        "enblocal.ini": enblocal_ini,
    }

    return cache


@pytest.fixture
def assert_no_file_modifications(tmp_path: Path) -> Generator[dict[Path, float], None, None]:
    """
    Context manager fixture to verify files are not modified during test.

    Tracks file modification times before test and verifies they remain
    unchanged after test execution.

    Args:
        tmp_path: Pytest temporary directory fixture

    Yields:
        Dictionary mapping file paths to their initial modification times

    Example:
        def test_fcx_no_writes(assert_no_file_modifications, tmp_path):
            test_file = tmp_path / "test.ini"
            test_file.write_text("[Main]\\nKey=Value\\n")

            with assert_no_file_modifications:
                # Perform operations that should not modify files
                run_fcx_checks()

            # Fixture verifies file was not modified
    """
    file_mtimes: dict[Path, float] = {}

    # Track modification times for all files in tmp_path
    for file_path in tmp_path.rglob("*"):
        if file_path.is_file():
            file_mtimes[file_path] = file_path.stat().st_mtime

    yield file_mtimes

    # Verify no files were modified
    for file_path, initial_mtime in file_mtimes.items():
        if not file_path.exists():
            continue  # File was deleted (which is also a modification, but handle separately)

        current_mtime = file_path.stat().st_mtime
        assert current_mtime == initial_mtime, f"File {file_path} was modified (mtime changed from {initial_mtime} to {current_mtime})"


@pytest.fixture
def sample_config_issues(tmp_path: Path) -> list[ConfigIssue]:
    """
    Generate sample ConfigIssue objects for testing.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        List of ConfigIssue objects representing common FCX mode detections
    """
    return [
        # ESPExplorer hotkey issue
        ConfigIssue(
            file_path=tmp_path / "espexplorer.ini",
            section="Main",
            setting="HotKey",
            current_value="; F10",
            recommended_value="0x79",
            description="Hotkey is commented out and won't work. Change to hex code 0x79 for F10.",
            severity="warning",
        ),
        # EPO particle count issue
        ConfigIssue(
            file_path=tmp_path / "epo.ini",
            section="Particles",
            setting="iMaxDesired",
            current_value="7500",
            recommended_value="5000",
            description="High particle count can cause performance issues and crashes.",
            severity="warning",
        ),
        # F4EE head parts issue
        ConfigIssue(
            file_path=tmp_path / "f4ee.ini",
            section="HeadParts",
            setting="bUnlockHeadParts",
            current_value="0",
            recommended_value="1",
            description="Head parts are locked. Set to 1 to unlock all head parts.",
            severity="warning",
        ),
        # F4EE face tints issue
        ConfigIssue(
            file_path=tmp_path / "f4ee.ini",
            section="HeadParts",
            setting="bUnlockTints",
            current_value="0",
            recommended_value="1",
            description="Face tints are locked. Set to 1 to unlock all face tints.",
            severity="warning",
        ),
        # High FPS Physics Fix loading screen FPS issue
        ConfigIssue(
            file_path=tmp_path / "highfpsphysicsfix.ini",
            section="Limiter",
            setting="LoadingScreenFPS",
            current_value="60.0",
            recommended_value="600.0",
            description="Loading screen FPS is too low. Increase to 600.0 to prevent physics issues.",
            severity="warning",
        ),
        # VSync enabled issue
        ConfigIssue(
            file_path=tmp_path / "enblocal.ini",
            section="ENGINE",
            setting="iPresentInterval",
            current_value="1",
            recommended_value="0",
            description="VSync is enabled. Disable iPresentInterval for better performance with high FPS mods.",
            severity="info",
        ),
        # Critical issue example
        ConfigIssue(
            file_path=tmp_path / "critical.ini",
            section="Critical",
            setting="ImportantSetting",
            current_value="bad_value",
            recommended_value="good_value",
            description="Critical configuration error that may cause crashes.",
            severity="error",
        ),
    ]


@contextmanager
def track_file_modifications(file_paths: list[Path]) -> Generator[dict[Path, tuple[float, str]], None, None]:
    """
    Context manager to track file modifications during operations.

    Args:
        file_paths: List of file paths to track

    Yields:
        Dictionary mapping file paths to (mtime, content_hash) tuples

    Example:
        files = [Path("test1.ini"), Path("test2.ini")]
        with track_file_modifications(files) as tracker:
            # Perform operations
            run_fcx_checks()

        # Check if specific file was modified
        if tracker[Path("test1.ini")][0] != Path("test1.ini").stat().st_mtime:
            print("test1.ini was modified!")
    """
    import hashlib

    def get_file_hash(path: Path) -> str:
        """Calculate SHA256 hash of file content."""
        if not path.exists():
            return ""
        return hashlib.sha256(path.read_bytes()).hexdigest()

    # Record initial state
    initial_state: dict[Path, tuple[float, str]] = {}
    for path in file_paths:
        if path.exists() and path.is_file():
            initial_state[path] = (path.stat().st_mtime, get_file_hash(path))

    yield initial_state

    # Verify no modifications
    for path, (initial_mtime, initial_hash) in initial_state.items():
        if not path.exists():
            raise AssertionError(f"File {path} was deleted during operation")

        current_mtime = path.stat().st_mtime
        current_hash = get_file_hash(path)

        if current_mtime != initial_mtime:
            raise AssertionError(f"File {path} modification time changed: {initial_mtime} -> {current_mtime}")

        if current_hash != initial_hash:
            raise AssertionError(f"File {path} content changed (hash mismatch): {initial_hash[:8]}... -> {current_hash[:8]}...")
