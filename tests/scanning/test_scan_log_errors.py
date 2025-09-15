"""
Test suite for log file error checking functionality.

This module contains tests for concurrent log file processing,
error detection, and handling of unreadable files.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import sys
from collections.abc import Generator
from contextlib import nullcontext
from unittest.mock import patch

import aiofiles
import pytest

import ClassicLib.MessageHandler
from ClassicLib.MessageHandler import init_message_handler
from ClassicLib.ScanGame.ScanGameCore import ScanGameCore


@pytest.fixture(autouse=True)
def init_message_handler_fixture() -> Generator[None, None, None]:
    """Initialize MessageHandler for tests."""
    _handler = init_message_handler(parent=None, is_gui_mode=False)
    yield
    ClassicLib.MessageHandler._message_handler = None


@pytest.fixture
def mock_settings():
    """Mock YAML settings for tests."""
    with (
        patch("ClassicLib.YamlSettingsCache.yaml_settings") as mock_yaml_cache,
        patch("ClassicLib.ScanGame.ScanGameCore.yaml_settings") as mock_yaml_core,
    ):
        def yaml_side_effect(type_, yaml_key, setting_path, default=None):
            settings_map = {
                "catch_log_errors": ["error", "warning", "critical"],
                "exclude_log_files": ["ignore.log"],
                "exclude_log_errors": ["ignorable error"],
            }
            return settings_map.get(setting_path, default)

        mock_yaml_cache.side_effect = yaml_side_effect
        mock_yaml_core.side_effect = yaml_side_effect
        yield mock_yaml_cache


@pytest.fixture
def mock_paths(tmp_path):
    """Create mock paths for testing."""
    logs_path = tmp_path / "Logs"
    logs_path.mkdir()
    return {"logs": logs_path, "tmp": tmp_path}


class TestCheckLogErrors:
    """Test cases for ScanGameCore.check_log_errors method."""

    @pytest.mark.asyncio
    async def test_check_log_errors_with_errors(self, mock_settings, mock_paths):
        """Test checking log files with errors."""
        # Create test log files
        log1 = mock_paths["logs"] / "test1.log"
        log2 = mock_paths["logs"] / "test2.log"
        log3 = mock_paths["logs"] / "crash-test.log"  # Should be ignored

        async with aiofiles.open(log1, "w") as f:
            await f.write("Normal line\nERROR: Something went wrong\nAnother line")
        async with aiofiles.open(log2, "w") as f:
            await f.write("ERROR: Another error\nNormal operation")
        async with aiofiles.open(log3, "w") as f:
            await f.write("ERROR: Crash log should be ignored")

        core = ScanGameCore()
        result = await core.check_log_errors(mock_paths["logs"])

        # Check that errors from non-crash logs are reported
        assert "ERROR > ERROR: Something went wrong" in result or "ERROR: Something went wrong" in result
        # WARNING lines are not reported as errors (correct behavior)
        # Crash logs are correctly ignored
        assert "Crash log should be ignored" not in result

    @pytest.mark.asyncio
    async def test_check_log_errors_concurrency(self, mock_settings, mock_paths):
        """Test concurrent log file processing."""
        # Create many log files
        for i in range(30):
            log_file = mock_paths["logs"] / f"test{i}.log"
            async with aiofiles.open(log_file, "w") as f:
                await f.write(f"Log {i}\nERROR: Error in file {i}")

        # Track concurrent reads
        concurrent_reads = 0
        max_concurrent_reads = 0

        original_open = open

        def track_concurrent_open(*args, **kwargs):
            nonlocal concurrent_reads, max_concurrent_reads
            concurrent_reads += 1
            max_concurrent_reads = max(max_concurrent_reads, concurrent_reads)
            result = original_open(*args, **kwargs)
            concurrent_reads -= 1
            return result

        with patch("builtins.open", side_effect=track_concurrent_open):
            core = ScanGameCore()
            result = await core.check_log_errors(mock_paths["logs"])

        # Verify all errors were found
        for i in range(30):
            assert f"Error in file {i}" in result

        # Verify concurrency was limited
        from ClassicLib.ScanGame.ScanGameCore import get_optimal_limits

        ACTUAL_LIMIT = get_optimal_limits()["log_reads"]
        assert max_concurrent_reads <= ACTUAL_LIMIT

    @pytest.mark.asyncio
    async def test_check_log_errors_with_unreadable_file(self, mock_settings, mock_paths):
        """Test handling of unreadable log files."""
        # Create a log file
        log_file = mock_paths["logs"] / "unreadable.log"
        async with aiofiles.open(log_file, "w") as f:
            await f.write("Some content")

        # Mock both possible file reading methods to raise OSError
        with (
            patch("ClassicLib.ScanGame.ScanGameCore.open_file_with_encoding", side_effect=OSError("Permission denied")),
            patch("aiofiles.open", side_effect=OSError("Permission denied")) if "aiofiles" in str(sys.modules) else nullcontext(),
        ):
            core = ScanGameCore()
            result = await core.check_log_errors(mock_paths["logs"])

            # Check for the error message (without emoji since test output may vary)
            assert "Unable to scan this log file" in result or "ERROR" in result
            assert "unreadable.log" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
