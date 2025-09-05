"""
Tests for character encoding detection and handling.
"""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import tempfile
from pathlib import Path

import pytest

from ClassicLib.FileIOCore import FileIOCore


class TestEncodingSupport:
    """Test encoding detection integration."""

    @pytest.mark.asyncio
    async def test_utf8_encoding(self, io_core: FileIOCore):
        """Test reading UTF-8 files with special characters."""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, suffix=".txt") as f:
            test_path = Path(f.name)
            f.write("UTF-8: 世界 🌍 Café")

        try:
            content = await io_core.read_file(test_path)
            assert "世界" in content
            assert "🌍" in content
            assert "Café" in content
        finally:
            test_path.unlink()

    @pytest.mark.asyncio
    async def test_latin1_encoding(self, io_core: FileIOCore):
        """Test reading Latin-1 encoded files."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".txt") as f:
            test_path = Path(f.name)
            # Write Latin-1 content
            f.write("Café Münchën".encode("latin-1"))

        try:
            content = await io_core.read_file(test_path)
            # Should handle the content gracefully
            assert len(content) > 0
        finally:
            test_path.unlink()

    @pytest.mark.asyncio
    async def test_mixed_encoding_resilience(self, io_core: FileIOCore):
        """Test handling files with mixed or unknown encodings."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".txt") as f:
            test_path = Path(f.name)
            # Write some potentially problematic bytes
            f.write(b"Normal text\n")
            f.write(b"\x80\x81\x82\x83\x84\x85\x86\x87\n")  # Non-standard bytes
            f.write(b"More normal text\n")

        try:
            # Should not raise an exception
            content = await io_core.read_file(test_path)
            assert "Normal text" in content
            assert "More normal text" in content
        finally:
            test_path.unlink()

    @pytest.mark.asyncio
    async def test_windows_1252_encoding(self, io_core: FileIOCore):
        """Test reading Windows-1252 encoded files."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".txt") as f:
            test_path = Path(f.name)
            # Write Windows-1252 content (common on Windows)
            f.write('Smart quotes: "Hello"'.encode("windows-1252"))

        try:
            content = await io_core.read_file(test_path)
            # Should handle the content
            assert len(content) > 0
            assert "Hello" in content or "quotes" in content
        finally:
            test_path.unlink()

    @pytest.mark.asyncio
    async def test_bom_utf8_encoding(self, io_core: FileIOCore):
        """Test reading UTF-8 files with BOM."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".txt") as f:
            test_path = Path(f.name)
            # Write UTF-8 BOM followed by content
            f.write(b"\xef\xbb\xbf")  # UTF-8 BOM
            f.write("UTF-8 with BOM: Hello 世界".encode("utf-8"))

        try:
            content = await io_core.read_file(test_path)
            assert "Hello" in content
            assert "世界" in content
        finally:
            test_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
