"""Tests for file writing and atomic write operations."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

from pathlib import Path

import pytest

from ClassicLib.core.async_bridge import AsyncBridge
from ClassicLib.io.files import FileIOCore


class TestAsyncFileWriting:
    """Test cases for async file writing operations."""

    @pytest.mark.asyncio
    async def test_write_file(self, io_core: FileIOCore, tmp_path: Path):
        """Test writing text files."""
        test_path = tmp_path / "test_write.txt"

        # Write content
        new_content = "New content\nNew line 2"
        await io_core.write_file(test_path, new_content)

        # Verify write
        content = await io_core.read_file(test_path)
        assert content == new_content

    @pytest.mark.asyncio
    async def test_write_lines(self, io_core: FileIOCore, tmp_path: Path):
        """Test writing file lines."""
        test_path = tmp_path / "test_lines.txt"

        # Write lines
        new_lines = ["New line 1", "New line 2", "New line 3"]
        await io_core.write_lines(test_path, new_lines)

        # Verify write
        lines = await io_core.read_lines(test_path)
        assert len(lines) == 3
        assert lines == new_lines

    @pytest.mark.asyncio
    async def test_write_bytes(self, io_core: FileIOCore, tmp_path: Path):
        """Test writing binary files."""
        test_path = tmp_path / "test_bytes.bin"

        # Write bytes
        new_bytes = b"New binary \xff\xfe\xfd"
        await io_core.write_bytes(test_path, new_bytes)

        # Verify write
        content = await io_core.read_bytes(test_path)
        assert content == new_bytes

    @pytest.mark.asyncio
    async def test_write_crash_report(self, io_core: FileIOCore, tmp_path: Path):
        """Test writing crash reports."""
        test_path = tmp_path / "test_crash.log"

        # Write crash report
        report_lines = ["# Crash Report\n", "## Analysis\n", "Error found\n"]
        await io_core.write_crash_report(test_path, report_lines)

        # Verify report was written
        report_path = test_path.with_suffix(".md")
        assert report_path.exists()
        content = await io_core.read_file(report_path)
        assert "# Crash Report" in content
        assert "Error found" in content

    @pytest.mark.asyncio
    async def test_write_multiple_files(self, io_core: FileIOCore, tmp_path: Path):
        """Test writing multiple files concurrently."""
        # Prepare files to write
        files_to_write = {
            tmp_path / "file1.txt": "Content 1",
            tmp_path / "file2.txt": "Content 2",
            tmp_path / "file3.txt": "Content 3",
        }

        # Write all files
        await io_core.write_multiple_files(files_to_write)  # pyright: ignore[reportArgumentType, reportOptionalMemberAccess, reportAttributeAccessIssue]

        # Verify all files were written
        for path, expected_content in files_to_write.items():
            assert path.exists()
            content = await io_core.read_file(path)
            assert content == expected_content


class TestSyncFileWriting:
    """Test cases for sync file writing via AsyncBridge."""

    def test_write_file_via_bridge(self, io_core: FileIOCore, tmp_path: Path):
        """Test writing files via AsyncBridge.run_async()."""
        bridge = AsyncBridge.get_instance()
        test_path = tmp_path / "sync_write.txt"
        bridge.run_async(io_core.write_file(test_path, "Sync write test"))
        content = test_path.read_text()
        assert content == "Sync write test"

    def test_write_lines_via_bridge(self, io_core: FileIOCore, tmp_path: Path):
        """Test writing lines via AsyncBridge.run_async()."""
        bridge = AsyncBridge.get_instance()
        test_path = tmp_path / "sync_lines.txt"
        lines = ["Line A", "Line B", "Line C"]
        bridge.run_async(io_core.write_lines(test_path, lines))
        content = test_path.read_text()
        assert content == "Line A\nLine B\nLine C\n"

    def test_write_bytes_via_bridge(self, io_core: FileIOCore, tmp_path: Path):
        """Test writing bytes via AsyncBridge.run_async()."""
        bridge = AsyncBridge.get_instance()
        test_path = tmp_path / "sync_bytes.bin"
        test_bytes = b"Binary sync \xff\xfe"
        bridge.run_async(io_core.write_bytes(test_path, test_bytes))
        content = test_path.read_bytes()
        assert content == test_bytes

    def test_write_crash_report_via_bridge(self, io_core: FileIOCore, tmp_path: Path):
        """Test writing crash reports via AsyncBridge.run_async()."""
        bridge = AsyncBridge.get_instance()
        test_path = tmp_path / "sync_crash.log"
        report_lines = ["# Report\n", "Error\n"]
        bridge.run_async(io_core.write_crash_report(test_path, report_lines))

        report_path = test_path.with_suffix(".md")
        assert report_path.exists()
        content = report_path.read_text()
        assert "# Report" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
