"""
Game integrity fixtures for CLASSIC-Fallout4 test suite.

This module provides fixtures for testing game integrity checking,
including GameIntegrityChecker instances and mock configurations.

Consolidated from:
- tests/game/integrity/conftest.py
"""

from pathlib import Path

import pytest

from ClassicLib.GameIntegrity import GameIntegrityChecker


@pytest.fixture
def game_integrity_checker() -> GameIntegrityChecker:
    """Create a GameIntegrityChecker instance for testing.

    Returns:
        A fresh GameIntegrityChecker instance.
    """
    return GameIntegrityChecker()


@pytest.fixture
def game_mock_config() -> dict[str, str | set[str]]:
    """Create mock configuration for game integrity testing.

    Returns:
        A dictionary containing mock game configuration settings.
    """
    return {
        "steam_ini_path": "C:/Games/Fallout4/steam_api.ini",
        "valid_exe_hashes": {"hash_old_version", "hash_new_version"},
        "game_exe_path": "C:/Games/Fallout4/Fallout4.exe",
        "root_name": "Fallout4",
        "root_warn": "WARNING: Game installed in Program Files!",
    }


@pytest.fixture
def game_test_exe(tmp_path: Path) -> Path:
    """Create a test game executable file.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        Path to the test game executable.
    """
    exe_path = tmp_path / "Fallout4.exe"
    exe_path.write_text("fake exe content")
    return exe_path


@pytest.fixture
def game_test_steam_ini(tmp_path: Path) -> Path:
    """Create a test Steam INI file.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        Path to the test Steam INI file.
    """
    steam_ini = tmp_path / "steam_api.ini"
    steam_ini.write_text("steam config")
    return steam_ini


# Backward compatibility aliases (deprecated - use prefixed names)
checker = game_integrity_checker
mock_config = game_mock_config
test_game_exe = game_test_exe
test_steam_ini = game_test_steam_ini
