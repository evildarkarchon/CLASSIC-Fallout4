"""
Shared fixtures for backup management tests.
"""

from pathlib import Path

import pytest

from ClassicLib.BackupManager import BackupManager


@pytest.fixture
def manager() -> BackupManager:
    """Create a BackupManager instance for testing."""
    return BackupManager()


@pytest.fixture
def mock_backup_config() -> dict[str, str | list[str]]:
    """Create mock backup configuration."""
    return {
        "backup_list": ["*.dll", "*.exe", "*.ini"],
        "game_path": "C:/Games/Fallout4",
        "xse_log_file": "C:/Documents/My Games/Fallout4/F4SE/f4se.log",
        "xse_ver_latest": "0.6.23",
    }


@pytest.fixture
def test_game_dir(tmp_path: Path) -> Path:
    """Create a test game directory with sample files."""
    game_dir = tmp_path / "Game"
    game_dir.mkdir()

    # Create test files
    (game_dir / "test.dll").write_text("dll content")
    (game_dir / "game.exe").write_text("exe content")
    (game_dir / "config.ini").write_text("ini content")
    (game_dir / "readme.txt").write_text("txt content")

    return game_dir
