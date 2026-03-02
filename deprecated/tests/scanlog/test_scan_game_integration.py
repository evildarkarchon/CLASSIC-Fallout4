"""
Test suite for ScanGameCore integration and performance tests.

This module contains integration tests that verify the complete
async functionality and performance improvements.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import asyncio
import time
from unittest.mock import AsyncMock, patch

import aiofiles
import pytest

from ClassicLib.scanning.game.core import ScanGameCore

# Note: MessageHandler initialization is now handled by standardized
# fixtures in tests/fixtures/registry_fixtures.py which provide:
# - message_handler: For non-GUI tests
# - gui_message_handler: For GUI tests (from qt_fixtures.py)
# - Automatic cleanup via ensure_message_handler_cleanup


@pytest.fixture
def mock_settings():
    """Mock YAML settings for tests.

    Note: ScanGameCore doesn't have a yaml_settings attribute - it uses
    validators.get_scan_settings() async method. We mock the YamlSettingsCache
    module-level function instead.
    """
    with patch("ClassicLib.io.yaml.yaml_settings") as mock_yaml_cache:

        def yaml_side_effect(type_, yaml_key, setting_path, default=None):
            settings_map = {
                "catch_log_errors": ["error", "warning", "critical"],
                "exclude_log_files": ["ignore.log"],
                "exclude_log_errors": ["ignorable error"],
                "Mods_Warn.Mods_Path_Missing": "Mods path not configured",
                "Mods_Warn.Mods_Path_Invalid": "Mods path does not exist",
                "Mods_Warn.Mods_BSArch_Missing": "BSArch.exe not found",
            }
            return settings_map.get(setting_path, default)

        mock_yaml_cache.side_effect = yaml_side_effect
        yield mock_yaml_cache


@pytest.fixture
def mock_paths(tmp_path):
    """Create mock paths for testing."""
    mods_path = tmp_path / "Mods"
    mods_path.mkdir()

    bsarch_path = tmp_path / "CLASSIC Data"
    bsarch_path.mkdir()
    (bsarch_path / "BSArch.exe").touch()

    return {"mods": mods_path, "bsarch": bsarch_path / "BSArch.exe", "tmp": tmp_path}


@pytest.fixture
def mock_scan_settings(mock_paths):
    """Mock get_scan_settings function."""
    with (
        patch("classic_scan_game.get_scan_settings") as mock_get,
        patch("ClassicLib.scanning.game.core.ScanGameCore.get_scan_settings") as mock_core_get,
    ):
        return_val = (
            "F4SE",
            {"f4se_loader": "hash123"},
            mock_paths["mods"],
        )
        mock_get.return_value = return_val
        mock_core_get.return_value = return_val
        yield mock_get


@pytest.fixture
def mock_issue_messages():
    """Mock get_issue_messages function."""
    with (
        patch("classic_scan_game.get_issue_messages") as mock_get,
        patch("ClassicLib.scanning.game.core.ScanGameCore.get_issue_messages") as mock_core_get,
    ):
        return_val = {
            "ba2_frmt": ["[!] BA2 FORMAT ERRORS FOUND:\n"],
            "tex_dims": ["[!] TEXTURE DIMENSION ERRORS:\n"],
            "tex_frmt": ["[!] TEXTURE FORMAT ERRORS:\n"],
            "snd_frmt": ["[!] SOUND FORMAT ERRORS:\n"],
            "animdata": ["[!] ANIMATION DATA FOUND:\n"],
            "xse_file": ["[!] F4SE FILES FOUND:\n"],
            "previs": ["[!] PREVIS FILES FOUND:\n"],
            "cleanup": ["[!] CLEANUP FILES:\n"],
        }
        mock_get.return_value = return_val
        mock_core_get.return_value = return_val
        yield mock_get


@pytest.fixture
def mock_global_registry(mock_paths):
    """Mock GlobalRegistry."""
    with patch("ClassicLib.scanning.game.core.GlobalRegistry") as mock_gr_core:
        mock_gr_core.get_local_dir.return_value = mock_paths["tmp"]
        mock_gr_core.get_vr.return_value = ""
        yield mock_gr_core


class TestScanGameCoreIntegration:
    """Integration tests for ScanGameCore async functionality."""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_scan_game_core_performance_improvement(
        self, mock_settings, mock_paths, mock_scan_settings, mock_issue_messages, mock_global_registry, message_handler
    ):
        """Test that ScanGameCore async methods are faster than sequential processing."""
        # Create multiple BA2 files
        for i in range(5):
            ba2_file = mock_paths["mods"] / f"test{i}.ba2"
            async with aiofiles.open(ba2_file, "wb") as f:
                await f.write(b"BTDX\x00\x00\x00\x00DX10")

        # Mock subprocess with delay
        async def slow_subprocess(*args, **kwargs):
            mock_proc = AsyncMock()
            mock_proc.returncode = 0

            async def simulate_communicate():
                await asyncio.sleep(0.2)
                return ("output", "")

            mock_proc.communicate = AsyncMock(side_effect=simulate_communicate)
            return mock_proc

        with patch("asyncio.create_subprocess_exec", side_effect=slow_subprocess):
            start_time = time.time()
            core = ScanGameCore()
            await core.scan_mods_archived()
            async_time = time.time() - start_time

        # With semaphore limit of 4, 5 files should take ~0.4s (2 batches)
        # Sequential would take ~1.0s (5 * 0.2s)
        assert async_time < 0.8  # Allow some overhead


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
