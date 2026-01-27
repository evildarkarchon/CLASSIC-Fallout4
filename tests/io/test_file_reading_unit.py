"""Tests for file reading operations."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from pathlib import Path

import pytest

from ClassicLib.io.files import FileIOCore, read_bytes_sync, read_crash_log_sync, read_file_sync, read_lines_sync


class TestAsyncFileReading:
    """Test cases for async file reading operations."""

    @pytest.mark.asyncio
    async def test_read_file(self, io_core: FileIOCore, temp_file: Path):
        """Test reading text files."""
        content = await io_core.read_file(temp_file)
        assert "Test content" in content
        assert "Line 2" in content

    @pytest.mark.asyncio
    async def test_read_lines(self, io_core: FileIOCore, temp_file: Path):
        """Test reading file lines."""
        lines = await io_core.read_lines(temp_file)
        assert len(lines) == 3
        assert lines[0] == "Test content"
        assert lines[1] == "Line 2"
        assert lines[2] == "Line 3"

    @pytest.mark.asyncio
    async def test_read_bytes(self, io_core: FileIOCore, temp_binary_file: Path):
        """Test reading binary files."""
        content = await io_core.read_bytes(temp_binary_file)
        assert b"Binary content" in content
        assert b"\x00\x01\x02\x03" in content

    @pytest.mark.asyncio
    async def test_read_crash_log(self, io_core: FileIOCore, temp_crash_log: Path):
        """Test crash log specific operations (strips trailing empty lines)."""
        lines = await io_core.read_crash_log(temp_crash_log)
        assert len(lines) == 2
        assert lines[0] == "Crash log line 1"
        assert lines[1] == "Crash log line 2"

    @pytest.mark.asyncio
    async def test_read_multiple_files(self, io_core: FileIOCore, temp_files_set: list[Path]):
        """Test reading multiple files concurrently."""
        # Read all files
        contents = await io_core.read_multiple_files(temp_files_set)  # pyright: ignore[reportArgumentType, reportOptionalMemberAccess, reportAttributeAccessIssue]

        # Verify contents
        assert len(contents) == 3
        for i, path in enumerate(temp_files_set):
            assert path.name in contents
            assert f"Content of file {i}" in contents[path.name]

    @pytest.mark.asyncio
    async def test_file_exists(self, io_core: FileIOCore, temp_file: Path):
        """Test file existence check.

        Note: file_exists is now a synchronous method that returns bool directly,
        not a coroutine. This was optimized for performance since Path.exists()
        is a fast non-blocking operation.
        """
        # Test existing file - no await needed
        assert io_core.file_exists(temp_file) is True

        # Delete and test non-existing
        temp_file.unlink()
        assert io_core.file_exists(temp_file) is False

    @pytest.mark.asyncio
    async def test_get_file_size(self, io_core: FileIOCore, temp_file: Path):
        """Test getting file size.

        Note: get_file_size is now a synchronous method that returns int directly,
        not a coroutine. This was optimized for performance since Path.stat()
        is a fast non-blocking operation.
        """
        # Test existing file - no await needed
        size = io_core.get_file_size(temp_file)
        # Use stat to get actual file size (handles line endings correctly)
        expected_size = temp_file.stat().st_size
        assert size == expected_size

        # Test non-existing file
        temp_file.unlink()
        size = io_core.get_file_size(temp_file)
        assert size == -1


class TestSyncFileReading:
    """Test cases for sync adapter file reading functions."""

    def test_read_file_sync(self, temp_file: Path):
        """Test sync adapter for reading files."""
        content = read_file_sync(temp_file)
        assert "Test content" in content
        assert "Line 2" in content

    def test_read_lines_sync(self, temp_file: Path):
        """Test sync adapter for reading lines."""
        lines = read_lines_sync(temp_file)
        assert len(lines) == 3
        assert lines[0] == "Test content"

    def test_read_bytes_sync(self, temp_binary_file: Path):
        """Test sync adapter for reading bytes."""
        content = read_bytes_sync(temp_binary_file)
        assert b"Binary content" in content

    def test_read_crash_log_sync(self, temp_crash_log: Path):
        """Test sync adapter for reading crash logs."""
        lines = read_crash_log_sync(temp_crash_log)
        assert len(lines) == 2
        assert lines[0] == "Crash log line 1"
        assert lines[1] == "Crash log line 2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
