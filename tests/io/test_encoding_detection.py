"""Tests for character encoding detection and handling."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from pathlib import Path

import pytest

from ClassicLib.FileIO import FileIOCore


class TestEncodingSupport:
    """Test encoding detection integration."""

    @pytest.mark.asyncio
    async def test_utf8_encoding(self, io_core: FileIOCore, tmp_path: Path):
        """Test reading UTF-8 files with special characters."""
        test_path = tmp_path / "utf8_test.txt"
        test_path.write_text("UTF-8: 世界 🌍 Café", encoding="utf-8")

        content = await io_core.read_file(test_path)
        assert "世界" in content
        assert "🌍" in content
        assert "Café" in content

    @pytest.mark.asyncio
    async def test_latin1_encoding(self, io_core: FileIOCore, tmp_path: Path):
        """Test reading Latin-1 encoded files."""
        test_path = tmp_path / "latin1_test.txt"
        # Write Latin-1 content
        test_path.write_bytes("Café Münchën".encode("latin-1"))

        content = await io_core.read_file(test_path)
        # Should handle the content gracefully
        assert len(content) > 0

    @pytest.mark.asyncio
    async def test_mixed_encoding_resilience(self, io_core: FileIOCore, tmp_path: Path):
        """Test handling files with mixed or unknown encodings."""
        test_path = tmp_path / "mixed_encoding.txt"
        # Write some potentially problematic bytes
        test_path.write_bytes(b"Normal text\n\x80\x81\x82\x83\x84\x85\x86\x87\nMore normal text\n")

        # Should not raise an exception
        content = await io_core.read_file(test_path)
        assert "Normal text" in content
        assert "More normal text" in content

    @pytest.mark.asyncio
    async def test_windows_1252_encoding(self, io_core: FileIOCore, tmp_path: Path):
        """Test reading Windows-1252 encoded files."""
        test_path = tmp_path / "windows1252_test.txt"
        # Write Windows-1252 content (common on Windows)
        test_path.write_bytes('Smart quotes: "Hello"'.encode("windows-1252"))

        content = await io_core.read_file(test_path)
        # Should handle the content
        assert len(content) > 0
        assert "Hello" in content or "quotes" in content

    @pytest.mark.asyncio
    async def test_bom_utf8_encoding(self, io_core: FileIOCore, tmp_path: Path):
        """Test reading UTF-8 files with BOM."""
        test_path = tmp_path / "bom_utf8_test.txt"
        # Write UTF-8 BOM followed by content
        test_path.write_bytes(b"\xef\xbb\xbf" + "UTF-8 with BOM: Hello 世界".encode())

        content = await io_core.read_file(test_path)
        assert "Hello" in content
        assert "世界" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
