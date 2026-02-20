"""Unit tests for ClassicLib.io.files.async_files module.

This module tests the async file I/O utilities including encoding detection
and async file reading functions.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


class TestDetectEncodingAsync:
    """Tests for detect_encoding_async function."""

    @pytest.mark.asyncio
    async def test_raises_import_error_when_dependencies_unavailable(self, tmp_path: Path) -> None:
        """Test raises ImportError when aiofiles/chardet unavailable."""
        from ClassicLib.io.files.async_files import detect_encoding_async

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with patch("ClassicLib.io.files.async_files.AIOFILES_AVAILABLE", False):
            with pytest.raises(ImportError):
                await detect_encoding_async(test_file)

    @pytest.mark.asyncio
    async def test_raises_file_not_found_for_missing_file(self, tmp_path: Path) -> None:
        """Test raises FileNotFoundError for non-existent file."""
        from ClassicLib.io.files.async_files import detect_encoding_async

        nonexistent = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            await detect_encoding_async(nonexistent)

    @pytest.mark.asyncio
    async def test_converts_string_path_to_path_object(self, tmp_path: Path) -> None:
        """Test accepts string paths and converts to Path."""
        from ClassicLib.io.files.async_files import detect_encoding_async

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        # Should not raise - string path should work
        result = await detect_encoding_async(str(test_file))

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_returns_encoding_string(self, tmp_path: Path) -> None:
        """Test returns encoding as a string."""
        from ClassicLib.io.files.async_files import detect_encoding_async

        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World", encoding="utf-8")

        result = await detect_encoding_async(test_file)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_detects_utf8_encoding(self, tmp_path: Path) -> None:
        """Test detects UTF-8 encoding correctly."""
        from ClassicLib.io.files.async_files import detect_encoding_async

        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World with Unicode: café", encoding="utf-8")

        result = await detect_encoding_async(test_file)

        # Should be utf-8 or a compatible encoding
        assert result.lower() in ["utf-8", "ascii", "utf8"]


class TestGetEncodingDetectionAvailable:
    """Tests for get_encoding_detection_available function."""

    def test_returns_boolean(self) -> None:
        """Test returns a boolean value."""
        from ClassicLib.io.files.async_files import get_encoding_detection_available

        result = get_encoding_detection_available()

        assert isinstance(result, bool)

    def test_returns_true_when_aiofiles_available(self) -> None:
        """Test returns True when aiofiles is available."""
        from ClassicLib.io.files.async_files import get_encoding_detection_available

        with patch("ClassicLib.io.files.async_files.AIOFILES_AVAILABLE", True):
            # Import the function fresh to get the patched value
            result = get_encoding_detection_available()

        # Should be True in the test environment where aiofiles is installed
        assert result is True


class TestFallbackToSyncEncodingDetection:
    """Tests for fallback_to_sync_encoding_detection function."""

    @pytest.mark.asyncio
    async def test_returns_encoding_string(self, tmp_path: Path) -> None:
        """Test returns encoding as string."""
        from ClassicLib.io.files.async_files import fallback_to_sync_encoding_detection

        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content", encoding="utf-8")

        result = await fallback_to_sync_encoding_detection(test_file)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_accepts_string_path(self, tmp_path: Path) -> None:
        """Test accepts string paths."""
        from ClassicLib.io.files.async_files import fallback_to_sync_encoding_detection

        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content", encoding="utf-8")

        # Should not raise
        result = await fallback_to_sync_encoding_detection(str(test_file))

        assert isinstance(result, str)


class TestReadFileWithEncodingAsync:
    """Tests for read_file_with_encoding_async function."""

    @pytest.mark.asyncio
    async def test_reads_file_content(self, tmp_path: Path) -> None:
        """Test reads complete file content."""
        from ClassicLib.io.files.async_files import read_file_with_encoding_async

        test_file = tmp_path / "test.txt"
        expected_content = "Hello World\nLine 2"
        test_file.write_text(expected_content, encoding="utf-8")

        result = await read_file_with_encoding_async(test_file)

        assert result == expected_content


class TestReadLinesWithEncodingAsync:
    """Tests for read_lines_with_encoding_async function."""

    @pytest.mark.asyncio
    async def test_reads_file_lines(self, tmp_path: Path) -> None:
        """Test reads file as list of lines."""
        from ClassicLib.io.files.async_files import read_lines_with_encoding_async

        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3", encoding="utf-8")

        result = await read_lines_with_encoding_async(test_file)

        assert isinstance(result, list)
        assert len(result) == 3


class TestModuleConstants:
    """Tests for module-level constants."""

    def test_aiofiles_available_constant_exists(self) -> None:
        """Test AIOFILES_AVAILABLE constant exists."""
        from ClassicLib.io.files.async_files import AIOFILES_AVAILABLE

        assert isinstance(AIOFILES_AVAILABLE, bool)
