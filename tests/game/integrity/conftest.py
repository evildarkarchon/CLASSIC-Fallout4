"""
Shared fixtures for game integrity tests.
"""

from pathlib import Path

import pytest

from ClassicLib.GameIntegrity import GameIntegrityChecker


@pytest.fixture
def checker() -> GameIntegrityChecker:
    """Create a GameIntegrityChecker instance for testing."""
    return GameIntegrityChecker()


@pytest.fixture
def mock_config() -> dict[str, str]:
    """Create mock configuration for testing."""
    return {
        "steam_ini_path": "C:/Games/Fallout4/steam_api.ini",
        "exe_hash_old": "hash_old_version",
        "exe_hash_new": "hash_new_version",
        "game_exe_path": "C:/Games/Fallout4/Fallout4.exe",
        "root_name": "Fallout4",
        "root_warn": "WARNING: Game installed in Program Files!",
    }


@pytest.fixture
def test_game_exe(tmp_path: Path) -> Path:
    """Create a test game executable file."""
    exe_path = tmp_path / "Fallout4.exe"
    exe_path.write_text("fake exe content")
    return exe_path


@pytest.fixture
def test_steam_ini(tmp_path: Path) -> Path:
    """Create a test Steam INI file."""
    steam_ini = tmp_path / "steam_api.ini"
    steam_ini.write_text("steam config")
    return steam_ini
