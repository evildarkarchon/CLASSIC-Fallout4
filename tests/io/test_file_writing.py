"""Tests for file writing and atomic write operations."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002

import tempfile
from pathlib import Path

import pytest

from ClassicLib.FileIO import FileIOCore, write_bytes_sync, write_crash_report_sync, write_file_sync, write_lines_sync


class TestAsyncFileWriting:
    """Test cases for async file writing operations."""

    @pytest.mark.asyncio
    async def test_write_file(self, io_core: FileIOCore):
        """Test writing text files."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            test_path = Path(f.name)

        try:
            # Write content
            new_content = "New content\nNew line 2"
            await io_core.write_file(test_path, new_content)

            # Verify write
            content = await io_core.read_file(test_path)
            assert content == new_content
        finally:
            test_path.unlink()

    @pytest.mark.asyncio
    async def test_write_lines(self, io_core: FileIOCore):
        """Test writing file lines."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            test_path = Path(f.name)

        try:
            # Write lines
            new_lines = ["New line 1", "New line 2", "New line 3"]
            await io_core.write_lines(test_path, new_lines)

            # Verify write
            lines = await io_core.read_lines(test_path)
            assert len(lines) == 3
            assert lines == new_lines
        finally:
            test_path.unlink()

    @pytest.mark.asyncio
    async def test_write_bytes(self, io_core: FileIOCore):
        """Test writing binary files."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_path = Path(f.name)

        try:
            # Write bytes
            new_bytes = b"New binary \xff\xfe\xfd"
            await io_core.write_bytes(test_path, new_bytes)

            # Verify write
            content = await io_core.read_bytes(test_path)
            assert content == new_bytes
        finally:
            test_path.unlink()

    @pytest.mark.asyncio
    async def test_write_crash_report(self, io_core: FileIOCore):
        """Test writing crash reports."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as f:
            test_path = Path(f.name)

        try:
            # Write crash report
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
    async def test_write_multiple_files(self, io_core: FileIOCore, tmp_path: Path):
        """Test writing multiple files concurrently."""
        # Prepare files to write
        files_to_write = {
            tmp_path / "file1.txt": "Content 1",
            tmp_path / "file2.txt": "Content 2",
            tmp_path / "file3.txt": "Content 3",
        }

        # Write all files
        await io_core.write_multiple_files(files_to_write)

        # Verify all files were written
        for path, expected_content in files_to_write.items():
            assert path.exists()
            content = await io_core.read_file(path)
            assert content == expected_content


class TestSyncFileWriting:
    """Test cases for sync adapter file writing functions."""

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
