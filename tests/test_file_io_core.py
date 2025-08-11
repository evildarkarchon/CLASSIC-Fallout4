"""
Test suite for FileIOCore unified async file I/O operations.
"""

import tempfile
from pathlib import Path

import pytest

from ClassicLib.FileIOCore import (
    FileIOCore,
    read_bytes_sync,
    read_crash_log_sync,
    read_file_sync,
    read_lines_sync,
    write_bytes_sync,
    write_crash_report_sync,
    write_file_sync,
    write_lines_sync,
)


class TestFileIOCoreAsync:
    """Test cases for async FileIOCore operations."""

    @pytest.mark.asyncio
    async def test_read_write_file(self):
        """Test reading and writing text files."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            test_path = Path(f.name)
            f.write("Test content\nLine 2\nLine 3")

        try:
            io_core = FileIOCore()

            # Test read_file
            content = await io_core.read_file(test_path)
            assert "Test content" in content
            assert "Line 2" in content

            # Test write_file
            new_content = "New content\nNew line 2"
            await io_core.write_file(test_path, new_content)

            # Verify write
            content = await io_core.read_file(test_path)
            assert content == new_content
        finally:
            test_path.unlink()

    @pytest.mark.asyncio
    async def test_read_write_lines(self):
        """Test reading and writing file lines."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            test_path = Path(f.name)
            f.write("Line 1\nLine 2\nLine 3\n")

        try:
            io_core = FileIOCore()

            # Test read_lines
            lines = await io_core.read_lines(test_path)
            assert len(lines) == 3
            assert lines[0] == "Line 1"
            assert lines[1] == "Line 2"
            assert lines[2] == "Line 3"

            # Test write_lines
            new_lines = ["New line 1", "New line 2", "New line 3"]
            await io_core.write_lines(test_path, new_lines)

            # Verify write
            lines = await io_core.read_lines(test_path)
            assert len(lines) == 3
            assert lines == new_lines
        finally:
            test_path.unlink()

    @pytest.mark.asyncio
    async def test_read_write_bytes(self):
        """Test reading and writing binary files."""
        test_bytes = b"Binary content \x00\x01\x02\x03"

        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            test_path = Path(f.name)
            f.write(test_bytes)

        try:
            io_core = FileIOCore()

            # Test read_bytes
            content = await io_core.read_bytes(test_path)
            assert content == test_bytes

            # Test write_bytes
            new_bytes = b"New binary \xff\xfe\xfd"
            await io_core.write_bytes(test_path, new_bytes)

            # Verify write
            content = await io_core.read_bytes(test_path)
            assert content == new_bytes
        finally:
            test_path.unlink()

    @pytest.mark.asyncio
    async def test_crash_log_operations(self):
        """Test crash log specific operations."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            test_path = Path(f.name)
            f.write("Crash log line 1\nCrash log line 2\n\n\n")

        try:
            io_core = FileIOCore()

            # Test read_crash_log (should strip trailing empty lines)
            lines = await io_core.read_crash_log(test_path)
            assert len(lines) == 2
            assert lines[0] == "Crash log line 1"
            assert lines[1] == "Crash log line 2"

            # Test write_crash_report
            report_lines = ["# Crash Report\n", "## Analysis\n", "Error found\n"]
            await io_core.write_crash_report(test_path, report_lines)

            # Verify report was written
            report_path = test_path.with_suffix(".md")
            assert report_path.exists()
            content = await io_core.read_file(report_path)
            assert "# Crash Report" in content
            assert "Error found" in content

            # Clean up report file
            report_path.unlink()
        finally:
            test_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_read_multiple_files(self):
        """Test reading multiple files concurrently."""
        # Create test files
        test_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
                test_path = Path(f.name)
                f.write(f"Content of file {i}")
                test_files.append(test_path)

        try:
            io_core = FileIOCore()

            # Read all files
            contents = await io_core.read_multiple_files(test_files)

            # Verify contents
            assert len(contents) == 3
            for i, path in enumerate(test_files):
                assert path.name in contents
                assert f"Content of file {i}" in contents[path.name]
        finally:
            for path in test_files:
                path.unlink()

    @pytest.mark.asyncio
    async def test_write_multiple_files(self):
        """Test writing multiple files concurrently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Prepare files to write
            files_to_write = {
                tmpdir_path / "file1.txt": "Content 1",
                tmpdir_path / "file2.txt": "Content 2",
                tmpdir_path / "file3.txt": "Content 3",
            }

            io_core = FileIOCore()

            # Write all files
            await io_core.write_multiple_files(files_to_write)

            # Verify all files were written
            for path, expected_content in files_to_write.items():
                assert path.exists()
                content = await io_core.read_file(path)
                assert content == expected_content

    @pytest.mark.asyncio
    async def test_file_exists(self):
        """Test file existence check."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_path = Path(f.name)

        try:
            io_core = FileIOCore()

            # Test existing file
            assert await io_core.file_exists(test_path) is True

            # Delete and test non-existing
            test_path.unlink()
            assert await io_core.file_exists(test_path) is False
        finally:
            test_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_get_file_size(self):
        """Test getting file size."""
        test_content = "Test content" * 100  # Make it reasonably sized

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            test_path = Path(f.name)
            f.write(test_content)

        try:
            io_core = FileIOCore()

            # Test existing file
            size = await io_core.get_file_size(test_path)
            assert size == len(test_content)

            # Test non-existing file
            test_path.unlink()
            size = await io_core.get_file_size(test_path)
            assert size == -1
        finally:
            test_path.unlink(missing_ok=True)


class TestFileIOCoreSyncAdapters:
    """Test cases for sync adapter functions."""

    def test_read_file_sync(self):
        """Test sync adapter for reading files."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            test_path = Path(f.name)
            f.write("Sync test content")

        try:
            content = read_file_sync(test_path)
            assert content == "Sync test content"
        finally:
            test_path.unlink()

    def test_read_lines_sync(self):
        """Test sync adapter for reading lines."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            test_path = Path(f.name)
            f.write("Line 1\nLine 2\nLine 3")

        try:
            lines = read_lines_sync(test_path)
            assert len(lines) == 3
            assert lines[0] == "Line 1"
        finally:
            test_path.unlink()

    def test_read_bytes_sync(self):
        """Test sync adapter for reading bytes."""
        test_bytes = b"Binary \x00\x01"

        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            test_path = Path(f.name)
            f.write(test_bytes)

        try:
            content = read_bytes_sync(test_path)
            assert content == test_bytes
        finally:
            test_path.unlink()

    def test_write_file_sync(self):
        """Test sync adapter for writing files."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            test_path = Path(f.name)

        try:
            write_file_sync(test_path, "Sync write test")
            content = test_path.read_text()
            assert content == "Sync write test"
        finally:
            test_path.unlink()

    def test_write_lines_sync(self):
        """Test sync adapter for writing lines."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            test_path = Path(f.name)

        try:
            lines = ["Line A", "Line B", "Line C"]
            write_lines_sync(test_path, lines)
            content = test_path.read_text()
            assert content == "Line A\nLine B\nLine C\n"
        finally:
            test_path.unlink()

    def test_write_bytes_sync(self):
        """Test sync adapter for writing bytes."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_path = Path(f.name)

        try:
            test_bytes = b"Binary sync \xff\xfe"
            write_bytes_sync(test_path, test_bytes)
            content = test_path.read_bytes()
            assert content == test_bytes
        finally:
            test_path.unlink()

    def test_read_crash_log_sync(self):
        """Test sync adapter for reading crash logs."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            test_path = Path(f.name)
            f.write("Log 1\nLog 2\n\n")

        try:
            lines = read_crash_log_sync(test_path)
            assert len(lines) == 2
            assert lines[0] == "Log 1"
            assert lines[1] == "Log 2"
        finally:
            test_path.unlink()

    def test_write_crash_report_sync(self):
        """Test sync adapter for writing crash reports."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as f:
            test_path = Path(f.name)

        try:
            report_lines = ["# Report\n", "Error\n"]
            write_crash_report_sync(test_path, report_lines)

            report_path = test_path.with_suffix(".md")
            assert report_path.exists()
            content = report_path.read_text()
            assert "# Report" in content

            report_path.unlink()
        finally:
            test_path.unlink(missing_ok=True)


class TestFileIOCoreEncodingSupport:
    """Test encoding detection integration."""

    @pytest.mark.asyncio
    async def test_utf8_encoding(self):
        """Test reading UTF-8 files with special characters."""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, suffix=".txt") as f:
            test_path = Path(f.name)
            f.write("UTF-8: 世界 🌍 Café")

        try:
            io_core = FileIOCore()
            content = await io_core.read_file(test_path)
            assert "世界" in content
            assert "🌍" in content
            assert "Café" in content
        finally:
            test_path.unlink()

    @pytest.mark.asyncio
    async def test_latin1_encoding(self):
        """Test reading Latin-1 encoded files."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".txt") as f:
            test_path = Path(f.name)
            # Write Latin-1 content
            f.write("Café Münchën".encode("latin-1"))

        try:
            io_core = FileIOCore()
            content = await io_core.read_file(test_path)
            # Should handle the content gracefully
            assert len(content) > 0
        finally:
            test_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
