"""
Integration tests for async_util - integration logic testing.

This file contains integration tests that test interactions between components.
"""

import asyncio
from pathlib import Path

import pytest

from ClassicLib.io.files.async_files import (
    detect_encoding_async,
    open_file_with_encoding_async,
    read_file_with_encoding_async,
    read_lines_with_encoding_async,
)

pytestmark = pytest.mark.integration


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncEncodingDetection:
    """Test cases for async encoding detection utilities."""

    @pytest.mark.asyncio
    async def test_detect_encoding_utf8(self, tmp_path) -> None:
        """Test detection of UTF-8 encoded files."""
        test_path = tmp_path / "utf8_test.txt"
        test_path.write_bytes(b"\xef\xbb\xbf" + "Hello, 世界! 🌍".encode())
        encoding = await detect_encoding_async(test_path)
        assert encoding.lower() in ["utf-8", "utf-8-sig"]

    @pytest.mark.asyncio
    async def test_detect_encoding_latin1(self, tmp_path) -> None:
        """Test detection of Latin-1 encoded files."""
        test_path = tmp_path / "latin1_test.txt"
        test_path.write_bytes("Héllö Wörld! àèìòù".encode("latin-1"))
        encoding = await detect_encoding_async(test_path)
        assert encoding.lower() in ["iso-8859-1", "windows-1252", "latin-1", "utf-8"]

    @pytest.mark.asyncio
    async def test_detect_encoding_with_small_sample(self, tmp_path) -> None:
        """Test encoding detection with custom sample size."""
        test_path = tmp_path / "sample_test.txt"
        content = ("A" * 1000 + "世界" + "B" * 1000).encode("utf-8")
        test_path.write_bytes(content)
        encoding = await detect_encoding_async(test_path, sample_size=500)
        assert encoding.lower() in ["utf-8", "ascii"]

    @pytest.mark.asyncio
    async def test_open_file_with_encoding_async(self, tmp_path) -> None:
        """Test opening file with automatic encoding detection."""
        test_path = tmp_path / "open_test.txt"
        test_path.write_text("Hello\n世界\n🌍", encoding="utf-8")
        async with open_file_with_encoding_async(test_path) as f:
            contents = await f.read()
            assert "Hello" in contents
            assert "世界" in contents
            assert "🌍" in contents

    @pytest.mark.asyncio
    async def test_read_file_with_encoding_async(self, tmp_path) -> None:
        """Test reading entire file with automatic encoding detection."""
        test_path = tmp_path / "utf16_test.txt"
        test_path.write_text("UTF-16 encoded content: 世界", encoding="utf-16")
        contents = await read_file_with_encoding_async(test_path)
        assert "UTF-16" in contents
        assert "世界" in contents

    @pytest.mark.asyncio
    async def test_read_lines_with_encoding_async(self, tmp_path) -> None:
        """Test reading file lines with automatic encoding detection."""
        test_path = tmp_path / "lines_test.txt"
        test_path.write_text("Line 1\nLine 2 with 世界\nLine 3", encoding="utf-8")
        lines = await read_lines_with_encoding_async(test_path)
        assert len(lines) == 3
        assert "Line 1" in lines[0]
        assert "世界" in lines[1]
        assert "Line 3" in lines[2]

    @pytest.mark.asyncio
    async def test_nonexistent_file(self) -> None:
        """Test handling of nonexistent files."""
        nonexistent_path = Path("/tmp/nonexistent_file_12345.txt")
        with pytest.raises(FileNotFoundError):
            await detect_encoding_async(nonexistent_path)
        with pytest.raises(FileNotFoundError):
            await read_file_with_encoding_async(nonexistent_path)

    @pytest.mark.asyncio
    async def test_concurrent_encoding_detection(self, tmp_path) -> None:
        """Test concurrent encoding detection on multiple files."""
        test_files = []
        utf8_file = tmp_path / "utf8.txt"
        utf8_file.write_text("UTF-8: 世界", encoding="utf-8")
        test_files.append(utf8_file)
        ascii_file = tmp_path / "ascii.txt"
        ascii_file.write_text("Pure ASCII content")
        test_files.append(ascii_file)
        latin1_file = tmp_path / "latin1.txt"
        latin1_file.write_bytes("Café Münchën".encode("latin-1"))
        test_files.append(latin1_file)
        tasks = [detect_encoding_async(f) for f in test_files]
        encodings = await asyncio.gather(*tasks)
        assert len(encodings) == 3
        for encoding in encodings:
            assert encoding is not None
            assert len(encoding) > 0
