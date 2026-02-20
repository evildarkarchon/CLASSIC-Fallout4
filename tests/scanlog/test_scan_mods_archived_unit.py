"""
Test suite for scanning archived BA2 mod files.

This module contains tests for BA2 archive format validation,
BSArch subprocess handling, and concurrent archive processing.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

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
    # Create test directories
    mods_path = tmp_path / "Mods"
    mods_path.mkdir()

    logs_path = tmp_path / "Logs"
    logs_path.mkdir()

    bsarch_path = tmp_path / "CLASSIC Data"
    bsarch_path.mkdir()
    (bsarch_path / "BSArch.exe").touch()

    return {"mods": mods_path, "logs": logs_path, "bsarch": bsarch_path / "BSArch.exe", "tmp": tmp_path}


@pytest.fixture
def mock_scan_settings(mock_paths):
    """Mock get_scan_settings function."""
    with (
        patch("classic_scan_game.get_scan_settings") as mock_get,
        patch("ClassicLib.scanning.game.core.ScanGameCore.get_scan_settings") as mock_core_get,
    ):
        return_val = (
            "F4SE",  # xse_acronym
            {"f4se_loader": "hash123"},  # xse_scriptfiles
            mock_paths["mods"],  # mod_path
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


class TestScanModsArchived:
    """Test cases for ScanGameCore.scan_mods_archived method."""

    @pytest.mark.asyncio
    async def test_scan_mods_archived_with_valid_ba2(
        self, mock_settings, mock_paths, mock_scan_settings, mock_issue_messages, mock_global_registry, message_handler
    ):
        """Test scanning valid BA2 archives."""
        # Create test BA2 files
        ba2_file1 = mock_paths["mods"] / "test1.ba2"
        ba2_file2 = mock_paths["mods"] / "test2.ba2"

        # Write valid BA2 headers
        async with aiofiles.open(ba2_file1, "wb") as f:
            await f.write(b"BTDX\x00\x00\x00\x00DX10")  # Texture BA2
        async with aiofiles.open(ba2_file2, "wb") as f:
            await f.write(b"BTDX\x00\x00\x00\x00GNRL")  # General BA2

        # Mock subprocess for BSArch
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=("Header\n\n\n\n\nFile: test.dds\nExt: dds\nWidth: 1024 Height: 1024", ""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            core = ScanGameCore()
            result = await core.scan_mods_archived()

        assert "RESULTS FROM ARCHIVED / BA2 FILES" in result
        assert mock_proc.communicate.called

    @pytest.mark.asyncio
    async def test_scan_mods_archived_with_invalid_ba2(
        self, mock_settings, mock_paths, mock_scan_settings, mock_issue_messages, mock_global_registry, message_handler
    ):
        """Test scanning invalid BA2 archives."""
        # Create test BA2 file with invalid header
        ba2_file = mock_paths["mods"] / "invalid.ba2"
        async with aiofiles.open(ba2_file, "wb") as f:
            await f.write(b"INVALID_HEADER")

        core = ScanGameCore()
        result = await core.scan_mods_archived()

        assert "BA2 ARCHIVES HAVE INCORRECT FORMAT" in result
        assert "invalid.ba2" in result

    @pytest.mark.asyncio
    async def test_scan_mods_archived_concurrency_limit(
        self, mock_settings, mock_paths, mock_scan_settings, mock_issue_messages, mock_global_registry, message_handler
    ):
        """Test that concurrency is limited by semaphore."""
        # Create multiple BA2 files
        ba2_files = []
        for i in range(10):
            ba2_file = mock_paths["mods"] / f"test{i}.ba2"
            async with aiofiles.open(ba2_file, "wb") as f:
                await f.write(b"BTDX\x00\x00\x00\x00DX10")
            ba2_files.append(ba2_file)

        # Track concurrent processes
        concurrent_count = 0
        max_concurrent = 0

        async def mock_subprocess(*args, **kwargs):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)

            mock_proc = AsyncMock()
            mock_proc.returncode = 0

            async def simulate_communicate():
                await asyncio.sleep(0.1)
                return ("output", "")

            mock_proc.communicate = AsyncMock(side_effect=simulate_communicate)

            # Simulate process completion
            await asyncio.sleep(0.1)
            concurrent_count -= 1

            return mock_proc

        with patch("asyncio.create_subprocess_exec", side_effect=mock_subprocess):
            core = ScanGameCore()
            await core.scan_mods_archived()

        # Verify concurrency was limited
        from ClassicLib.scanning.game.checks.utils import get_optimal_limits

        ACTUAL_LIMIT = get_optimal_limits()["subprocesses"]
        assert max_concurrent <= ACTUAL_LIMIT

    @pytest.mark.asyncio
    async def test_scan_mods_archived_timeout_handling(
        self, mock_settings, mock_paths, mock_scan_settings, mock_issue_messages, mock_global_registry, message_handler
    ):
        """Test timeout handling for BSArch subprocess."""
        # Create test BA2 file
        ba2_file = mock_paths["mods"] / "timeout.ba2"
        async with aiofiles.open(ba2_file, "wb") as f:
            await f.write(b"BTDX\x00\x00\x00\x00DX10")

        # Mock subprocess that times out
        mock_proc = AsyncMock()
        # Ensure kill is a standard Mock (sync), not AsyncMock, because asyncio.subprocess.Process.kill() is sync
        mock_proc.kill = MagicMock()
        mock_proc.communicate = AsyncMock(side_effect=TimeoutError())

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
            patch("ClassicLib.scanning.game.checks.ba2_scanner.msg_error") as mock_error,
        ):
            core = ScanGameCore()
            _result = await core.scan_mods_archived()

            # Verify timeout was handled
            mock_error.assert_called_with("BSArch command timed out processing timeout.ba2")
            # Verify kill was called
            mock_proc.kill.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
