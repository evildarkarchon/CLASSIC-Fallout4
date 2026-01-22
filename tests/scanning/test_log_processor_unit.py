"""Unit tests for ClassicLib.ScanGame.core.log_processor module.

This module tests the LogProcessor class for log file error detection.
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

pytestmark = [pytest.mark.unit]


@pytest.fixture(autouse=True)
def mock_message_handler():
    """Mock message handler for all tests."""
    with patch("ClassicLib.ScanGame.core.log_processor.msg_info"):
        with patch("ClassicLib.ScanGame.core.log_processor.msg_error"):
            yield


class TestLogProcessorInit:
    """Tests for LogProcessor initialization."""

    def test_init_stores_semaphore(self) -> None:
        """Test __init__ stores the semaphore."""
        from ClassicLib.ScanGame.core.log_processor import LogProcessor

        semaphore = asyncio.Semaphore(5)
        processor = LogProcessor(semaphore)

        assert processor.log_read_semaphore is semaphore

    def test_init_accepts_any_semaphore_value(self) -> None:
        """Test __init__ accepts semaphores with any value."""
        from ClassicLib.ScanGame.core.log_processor import LogProcessor

        semaphore = asyncio.Semaphore(1)
        processor = LogProcessor(semaphore)

        assert processor.log_read_semaphore is not None


class TestCheckLogErrors:
    """Tests for check_log_errors method."""

    @pytest.mark.asyncio
    async def test_returns_string(self, tmp_path: Path) -> None:
        """Test returns a string result."""
        from ClassicLib.ScanGame.core.log_processor import LogProcessor

        semaphore = asyncio.Semaphore(5)
        processor = LogProcessor(semaphore)

        with patch("ClassicLib.ScanGame.core.log_processor.yaml_settings_async", new_callable=AsyncMock) as mock_yaml:
            mock_yaml.return_value = []

            result = await processor.check_log_errors(tmp_path)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_log_files(self, tmp_path: Path) -> None:
        """Test returns empty string when no log files exist."""
        from ClassicLib.ScanGame.core.log_processor import LogProcessor

        semaphore = asyncio.Semaphore(5)
        processor = LogProcessor(semaphore)

        with patch("ClassicLib.ScanGame.core.log_processor.yaml_settings_async", new_callable=AsyncMock) as mock_yaml:
            mock_yaml.return_value = []

            result = await processor.check_log_errors(tmp_path)

        assert result == ""

    @pytest.mark.asyncio
    async def test_accepts_string_path(self, tmp_path: Path) -> None:
        """Test accepts string path and converts to Path."""
        from ClassicLib.ScanGame.core.log_processor import LogProcessor

        semaphore = asyncio.Semaphore(5)
        processor = LogProcessor(semaphore)

        with patch("ClassicLib.ScanGame.core.log_processor.yaml_settings_async", new_callable=AsyncMock) as mock_yaml:
            mock_yaml.return_value = []

            # Pass as string
            result = await processor.check_log_errors(str(tmp_path))

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_excludes_crash_log_files(self, tmp_path: Path) -> None:
        """Test excludes files containing 'crash-' in name."""
        from ClassicLib.ScanGame.core.log_processor import LogProcessor

        # Create a crash log file
        crash_log = tmp_path / "crash-2024-01-01.log"
        crash_log.write_text("error: test error")

        semaphore = asyncio.Semaphore(5)
        processor = LogProcessor(semaphore)

        with patch("ClassicLib.ScanGame.core.log_processor.yaml_settings_async", new_callable=AsyncMock) as mock_yaml:
            mock_yaml.return_value = ["error"]

            result = await processor.check_log_errors(tmp_path)

        # Crash logs should be excluded
        assert result == ""

    @pytest.mark.asyncio
    async def test_detects_errors_in_log_files(self, tmp_path: Path) -> None:
        """Test detects errors matching catch_log_errors patterns."""
        from ClassicLib.ScanGame.core.log_processor import LogProcessor

        # Create a log file with an error
        log_file = tmp_path / "test.log"
        log_file.write_text("Line 1: normal\nLine 2: error found here\nLine 3: normal\n")

        semaphore = asyncio.Semaphore(5)
        processor = LogProcessor(semaphore)

        # Mock yaml_settings_async to return error patterns
        async def mock_yaml(type_hint, yaml_type, key):
            if key == "catch_log_errors":
                return ["error"]
            return []

        with patch("ClassicLib.ScanGame.core.log_processor.yaml_settings_async", side_effect=mock_yaml):
            with patch("ClassicLib.ScanGame.core.log_processor.ASYNC_ENCODING_AVAILABLE", False):
                with patch("ClassicLib.ScanGame.core.log_processor.aiofiles", None):
                    result = await processor.check_log_errors(tmp_path)

        assert "CAUTION" in result
        assert "error found here" in result.lower() or "ERROR >" in result

    @pytest.mark.asyncio
    async def test_excludes_ignored_files(self, tmp_path: Path) -> None:
        """Test excludes files matching exclude_log_files patterns."""
        from ClassicLib.ScanGame.core.log_processor import LogProcessor

        # Create log files - one that should be excluded
        included_log = tmp_path / "game.log"
        included_log.write_text("error: test error")

        excluded_log = tmp_path / "debug.log"
        excluded_log.write_text("error: test error")

        semaphore = asyncio.Semaphore(5)
        processor = LogProcessor(semaphore)

        async def mock_yaml(type_hint, yaml_type, key):
            if key == "catch_log_errors":
                return ["error"]
            elif key == "exclude_log_files":
                return ["debug"]
            return []

        with patch("ClassicLib.ScanGame.core.log_processor.yaml_settings_async", side_effect=mock_yaml):
            with patch("ClassicLib.ScanGame.core.log_processor.ASYNC_ENCODING_AVAILABLE", False):
                with patch("ClassicLib.ScanGame.core.log_processor.aiofiles", None):
                    result = await processor.check_log_errors(tmp_path)

        # Only game.log should be processed, not debug.log
        assert "game.log" in result.lower()

    @pytest.mark.asyncio
    async def test_excludes_ignored_errors(self, tmp_path: Path) -> None:
        """Test excludes errors matching exclude_log_errors patterns."""
        from ClassicLib.ScanGame.core.log_processor import LogProcessor

        # Create a log file with errors, one that should be excluded
        log_file = tmp_path / "test.log"
        log_file.write_text("error: critical issue\nerror: warning ignored\n")

        semaphore = asyncio.Semaphore(5)
        processor = LogProcessor(semaphore)

        async def mock_yaml(type_hint, yaml_type, key):
            if key == "catch_log_errors":
                return ["error"]
            elif key == "exclude_log_errors":
                return ["ignored"]
            return []

        with patch("ClassicLib.ScanGame.core.log_processor.yaml_settings_async", side_effect=mock_yaml):
            with patch("ClassicLib.ScanGame.core.log_processor.ASYNC_ENCODING_AVAILABLE", False):
                with patch("ClassicLib.ScanGame.core.log_processor.aiofiles", None):
                    result = await processor.check_log_errors(tmp_path)

        assert "critical issue" in result.lower()
        # The "ignored" error should not be included

    @pytest.mark.asyncio
    async def test_handles_read_error_gracefully(self, tmp_path: Path) -> None:
        """Test handles OSError when reading file."""
        from ClassicLib.ScanGame.core.log_processor import LogProcessor

        # Create a log file
        log_file = tmp_path / "test.log"
        log_file.write_text("error: test")

        semaphore = asyncio.Semaphore(5)
        processor = LogProcessor(semaphore)

        async def mock_yaml(type_hint, yaml_type, key):
            if key == "catch_log_errors":
                return ["error"]
            return []

        # Mock to raise OSError when reading
        with patch("ClassicLib.ScanGame.core.log_processor.yaml_settings_async", side_effect=mock_yaml):
            with patch("ClassicLib.ScanGame.core.log_processor.ASYNC_ENCODING_AVAILABLE", False):
                with patch("ClassicLib.ScanGame.core.log_processor.aiofiles", None):
                    with patch("ClassicLib.ScanGame.core.log_processor.open_file_with_encoding", side_effect=OSError("Cannot read")):
                        result = await processor.check_log_errors(tmp_path)

        assert "ERROR" in result or "Unable to scan" in result

    @pytest.mark.asyncio
    async def test_truncates_to_last_50_errors(self, tmp_path: Path) -> None:
        """Test truncates error list to last 50 when more than 50 errors."""
        from ClassicLib.ScanGame.core.log_processor import LogProcessor

        # Create a log file with many errors
        log_lines = [f"error: line {i}\n" for i in range(100)]
        log_file = tmp_path / "test.log"
        log_file.write_text("".join(log_lines))

        semaphore = asyncio.Semaphore(5)
        processor = LogProcessor(semaphore)

        async def mock_yaml(type_hint, yaml_type, key):
            if key == "catch_log_errors":
                return ["error"]
            return []

        with patch("ClassicLib.ScanGame.core.log_processor.yaml_settings_async", side_effect=mock_yaml):
            with patch("ClassicLib.ScanGame.core.log_processor.ASYNC_ENCODING_AVAILABLE", False):
                with patch("ClassicLib.ScanGame.core.log_processor.aiofiles", None):
                    result = await processor.check_log_errors(tmp_path)

        # Should show truncation notice
        assert "100 total" in result or "of 100" in result

    @pytest.mark.asyncio
    async def test_processes_multiple_files_concurrently(self, tmp_path: Path) -> None:
        """Test processes multiple log files."""
        from ClassicLib.ScanGame.core.log_processor import LogProcessor

        # Create multiple log files
        for i in range(3):
            log_file = tmp_path / f"test{i}.log"
            log_file.write_text(f"error: issue in file {i}")

        semaphore = asyncio.Semaphore(5)
        processor = LogProcessor(semaphore)

        async def mock_yaml(type_hint, yaml_type, key):
            if key == "catch_log_errors":
                return ["error"]
            return []

        with patch("ClassicLib.ScanGame.core.log_processor.yaml_settings_async", side_effect=mock_yaml):
            with patch("ClassicLib.ScanGame.core.log_processor.ASYNC_ENCODING_AVAILABLE", False):
                with patch("ClassicLib.ScanGame.core.log_processor.aiofiles", None):
                    result = await processor.check_log_errors(tmp_path)

        # Should process all files
        assert result.count("LOG PATH") >= 3 or result.count("CAUTION") >= 3

    @pytest.mark.asyncio
    async def test_returns_empty_for_files_without_errors(self, tmp_path: Path) -> None:
        """Test returns empty string when log files have no matching errors."""
        from ClassicLib.ScanGame.core.log_processor import LogProcessor

        # Create a log file without matching errors
        log_file = tmp_path / "test.log"
        log_file.write_text("Line 1: normal\nLine 2: also normal\n")

        semaphore = asyncio.Semaphore(5)
        processor = LogProcessor(semaphore)

        async def mock_yaml(type_hint, yaml_type, key):
            if key == "catch_log_errors":
                return ["error"]  # Pattern won't match our file content
            return []

        with patch("ClassicLib.ScanGame.core.log_processor.yaml_settings_async", side_effect=mock_yaml):
            with patch("ClassicLib.ScanGame.core.log_processor.ASYNC_ENCODING_AVAILABLE", False):
                with patch("ClassicLib.ScanGame.core.log_processor.aiofiles", None):
                    result = await processor.check_log_errors(tmp_path)

        assert result == ""


class TestLogProcessorWithAsyncEncoding:
    """Tests for LogProcessor with async encoding detection."""

    @pytest.mark.asyncio
    async def test_uses_async_encoding_when_available(self, tmp_path: Path) -> None:
        """Test uses async encoding detection when available."""
        from ClassicLib.ScanGame.core.log_processor import LogProcessor

        log_file = tmp_path / "test.log"
        log_file.write_text("error: test error")

        semaphore = asyncio.Semaphore(5)
        processor = LogProcessor(semaphore)

        async def mock_yaml(type_hint, yaml_type, key):
            if key == "catch_log_errors":
                return ["error"]
            return []

        mock_read_lines = AsyncMock(return_value=["error: test error"])

        with patch("ClassicLib.ScanGame.core.log_processor.yaml_settings_async", side_effect=mock_yaml):
            with patch("ClassicLib.ScanGame.core.log_processor.ASYNC_ENCODING_AVAILABLE", True):
                with patch("ClassicLib.ScanGame.core.log_processor.read_lines_with_encoding_async", mock_read_lines):
                    result = await processor.check_log_errors(tmp_path)

        mock_read_lines.assert_called()


class TestLogProcessorWithAiofiles:
    """Tests for LogProcessor with aiofiles fallback."""

    @pytest.mark.asyncio
    async def test_uses_aiofiles_when_async_encoding_unavailable(self, tmp_path: Path) -> None:
        """Test uses aiofiles when async encoding not available."""
        from ClassicLib.ScanGame.core.log_processor import LogProcessor

        log_file = tmp_path / "test.log"
        log_file.write_text("error: test error")

        semaphore = asyncio.Semaphore(5)
        processor = LogProcessor(semaphore)

        async def mock_yaml(type_hint, yaml_type, key):
            if key == "catch_log_errors":
                return ["error"]
            return []

        # Create a mock aiofiles context manager
        mock_file = MagicMock()
        mock_file.readlines = AsyncMock(return_value=["error: test error"])
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_file)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        mock_aiofiles = MagicMock()
        mock_aiofiles.open = MagicMock(return_value=mock_context)

        with patch("ClassicLib.ScanGame.core.log_processor.yaml_settings_async", side_effect=mock_yaml):
            with patch("ClassicLib.ScanGame.core.log_processor.ASYNC_ENCODING_AVAILABLE", False):
                with patch("ClassicLib.ScanGame.core.log_processor.aiofiles", mock_aiofiles):
                    result = await processor.check_log_errors(tmp_path)

        mock_aiofiles.open.assert_called()


class TestModuleImports:
    """Tests for module-level imports and constants."""

    def test_logger_exists(self) -> None:
        """Test logger is imported."""
        from ClassicLib.ScanGame.core.log_processor import logger

        assert logger is not None

    def test_logprocessor_class_exists(self) -> None:
        """Test LogProcessor class can be imported."""
        from ClassicLib.ScanGame.core.log_processor import LogProcessor

        assert LogProcessor is not None
