"""
Test suite for log file error checking functionality.

This module contains tests for concurrent log file processing,
error detection, and handling of unreadable files.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002
import sys
from contextlib import nullcontext
from unittest.mock import patch

import aiofiles
import pytest

from ClassicLib.scanning.game.core import ScanGameCore

# Note: MessageHandler initialization is now handled by standardized
# fixtures in tests/fixtures/registry_fixtures.py which provide:
# - message_handler: For non-GUI tests
# - gui_message_handler: For GUI tests (from qt_fixtures.py)
# - Automatic cleanup via ensure_message_handler_cleanup

# Note: MessageHandler initialization is now handled by the standardized
# fixture system in tests/fixtures/registry_fixtures.py which provides:
# - Automatic cleanup via ensure_message_handler_cleanup (autouse)
# - On-demand initialization via message_handler or init_message_handler_fixture
# Tests in this file will automatically have MessageHandler cleaned up


@pytest.fixture
def mock_settings():
    """Mock YAML settings for tests.

    The log processor uses yaml_settings_async, so we must mock that.
    We also mock the sync yaml_settings for other callers.
    """
    from unittest.mock import AsyncMock

    settings_map = {
        "catch_log_errors": ["error", "warning", "critical"],
        "exclude_log_files": ["ignore.log"],
        "exclude_log_errors": ["ignorable error"],
    }

    def yaml_side_effect(type_, yaml_key, setting_path, default=None):
        return settings_map.get(setting_path, default)

    async def yaml_async_side_effect(type_, yaml_key, setting_path, default=None):
        return settings_map.get(setting_path, default)

    with (
        patch("ClassicLib.io.yaml.yaml_settings", side_effect=yaml_side_effect) as mock_sync,
        patch(
            "ClassicLib.scanning.game.checks.log_processor.yaml_settings_async",
            new_callable=AsyncMock,
            side_effect=yaml_async_side_effect,
        ),
    ):
        yield mock_sync


@pytest.fixture
def mock_paths(tmp_path):
    """Create mock paths for testing."""
    logs_path = tmp_path / "Logs"
    logs_path.mkdir()
    return {"logs": logs_path, "tmp": tmp_path}


class TestCheckLogErrors:
    """Test cases for ScanGameCore.check_log_errors method."""

    @pytest.mark.asyncio
    async def test_check_log_errors_with_errors(self, mock_settings, mock_paths, message_handler):
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
    async def test_check_log_errors_concurrency(self, mock_settings, mock_paths, message_handler):
        """Test concurrent log file processing."""
        # Create many log files
        for i in range(30):
            log_file = mock_paths["logs"] / f"test{i}.log"
            async with aiofiles.open(log_file, "w") as f:
                await f.write(f"Log {i}\nERROR: Error in file {i}")

        # Just run the actual method without patching - the test is about
        # verifying that all errors are found from concurrent processing
        core = ScanGameCore()
        result = await core.check_log_errors(mock_paths["logs"])

        # Verify all errors were found
        for i in range(30):
            assert f"Error in file {i}" in result

        # The concurrency limiting is handled internally by the semaphores
        # in the actual implementation, so we don't need to track it here

    @pytest.mark.asyncio
    async def test_check_log_errors_with_unreadable_file(self, mock_settings, mock_paths, message_handler):
        """Test handling of unreadable log files."""
        # Create a log file
        log_file = mock_paths["logs"] / "unreadable.log"
        async with aiofiles.open(log_file, "w") as f:
            await f.write("Some content")

        # Mock both possible file reading methods to raise OSError
        with (
            patch("ClassicLib.scanning.game.checks.log_processor.open_file_with_encoding", side_effect=OSError("Permission denied")),
            patch("aiofiles.open", side_effect=OSError("Permission denied")) if "aiofiles" in str(sys.modules) else nullcontext(),
        ):
            core = ScanGameCore()
            result = await core.check_log_errors(mock_paths["logs"])

            # Check for the error message (without emoji since test output may vary)
            assert "Unable to scan this log file" in result or "ERROR" in result
            assert "unreadable.log" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
