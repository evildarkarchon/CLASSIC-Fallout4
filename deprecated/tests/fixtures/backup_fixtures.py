"""
Backup management fixtures for CLASSIC-Fallout4 test suite.

This module provides fixtures for testing backup operations,
including BackupManager instances and mock configurations.

Consolidated from:
- tests/backup/conftest.py
"""

from pathlib import Path

import pytest

from ClassicLib.support.backup import BackupManager


@pytest.fixture
def backup_manager() -> BackupManager:
    """Create a BackupManager instance for testing.

    Returns:
        A fresh BackupManager instance.
    """
    return BackupManager()


@pytest.fixture
def backup_mock_config() -> dict[str, str | list[str]]:
    """Create mock backup configuration.

    Returns:
        A dictionary containing mock backup configuration settings.
    """
    return {
        "backup_list": ["*.dll", "*.exe", "*.ini"],
        "game_path": "C:/Games/Fallout4",
        "xse_log_file": "C:/Documents/My Games/Fallout4/F4SE/f4se.log",
        "xse_ver_latest": "0.6.23",
    }


@pytest.fixture
def backup_test_game_dir(tmp_path: Path) -> Path:
    """Create a test game directory with sample files.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        Path to the test game directory containing sample files.
    """
    game_dir = tmp_path / "Game"
    game_dir.mkdir()

    # Create test files
    (game_dir / "test.dll").write_text("dll content")
    (game_dir / "game.exe").write_text("exe content")
    (game_dir / "config.ini").write_text("ini content")
    (game_dir / "readme.txt").write_text("txt content")

    return game_dir


# Backward compatibility aliases (deprecated - use prefixed names)
manager = backup_manager
mock_backup_config = backup_mock_config
test_game_dir = backup_test_game_dir
