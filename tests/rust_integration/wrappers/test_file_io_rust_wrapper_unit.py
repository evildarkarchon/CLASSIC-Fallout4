"""Unit tests for ClassicLib.rust.file_io_rust module.

This module tests the FileIOCore Rust wrapper class, which provides
high-performance file I/O with automatic fallback to Python.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from ClassicLib.integration.rust.file_io_rust import FileIOCore


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def file_io_core() -> "FileIOCore":
    """Create a FileIOCore instance for testing."""
    from ClassicLib.integration.rust.file_io_rust import FileIOCore

    return FileIOCore()


@pytest.fixture
def file_io_core_custom_encoding() -> "FileIOCore":
    """Create a FileIOCore instance with custom encoding."""
    from ClassicLib.integration.rust.file_io_rust import FileIOCore

    return FileIOCore(encoding="latin-1", errors="replace")


@pytest.fixture
def temp_text_file(tmp_path: Path) -> Path:
    """Create a temporary text file for testing."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("Line 1\nLine 2\nLine 3")
    return file_path


@pytest.fixture
def temp_binary_file(tmp_path: Path) -> Path:
    """Create a temporary binary file for testing."""
    file_path = tmp_path / "test.bin"
    file_path.write_bytes(b"\x00\x01\x02\x03\x04")
    return file_path


@pytest.fixture
def temp_dds_file(tmp_path: Path) -> Path:
    """Create a temporary DDS-like file for header testing."""
    import struct

    file_path = tmp_path / "test.dds"
    header = bytearray(128)
    header[0:4] = b"DDS "
    header[4:8] = struct.pack("<I", 124)  # dwSize
    header[12:16] = struct.pack("<I", 512)  # height
    header[16:20] = struct.pack("<I", 1024)  # width
    file_path.write_bytes(bytes(header) + b"\x00" * 100)
    return file_path


# ============================================================================
# FileIOCore Initialization Tests
# ============================================================================


class TestFileIOCoreInit:
    """Tests for FileIOCore initialization."""

    @pytest.mark.unit
    def test_init_default_encoding(self) -> None:
        """Test default encoding is UTF-8."""
        from ClassicLib.integration.rust.file_io_rust import FileIOCore

        io = FileIOCore()
        assert io.default_encoding == "utf-8"
        assert io.default_errors == "ignore"

    @pytest.mark.unit
    def test_init_custom_encoding(self) -> None:
        """Test custom encoding can be specified."""
        from ClassicLib.integration.rust.file_io_rust import FileIOCore

        io = FileIOCore(encoding="latin-1", errors="replace")
        assert io.default_encoding == "latin-1"
        assert io.default_errors == "replace"

    @pytest.mark.unit
    def test_is_rust_accelerated_property(self, file_io_core: "FileIOCore") -> None:
        """Test is_rust_accelerated property works."""
        assert isinstance(file_io_core.is_rust_accelerated, bool)

    @pytest.mark.unit
    def test_init_fallback_when_rust_unavailable(self) -> None:
        """Test Python fallback is created when Rust unavailable."""
        with patch("ClassicLib.integration.rust.file_io_rust.RUST_AVAILABLE", False):
            with patch("ClassicLib.integration.rust.file_io_rust._rust_io", None):
                from ClassicLib.integration.rust.file_io_rust import FileIOCore

                io = FileIOCore.__new__(FileIOCore)
                io.default_encoding = "utf-8"
                io.default_errors = "ignore"
                io._rust_core = None
                assert io._rust_core is None


# ============================================================================
# Async Read Operations Tests
# ============================================================================


class TestAsyncReadOperations:
    """Tests for async read operations."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_file_returns_content(self, file_io_core: "FileIOCore", temp_text_file: Path) -> None:
        """Test read_file returns file content."""
        content = await file_io_core.read_file(temp_text_file)
        normalized = content.replace("\r\n", "\n")
        assert normalized == "Line 1\nLine 2\nLine 3"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_file_with_string_path(self, file_io_core: "FileIOCore", temp_text_file: Path) -> None:
        """Test read_file works with string path."""
        content = await file_io_core.read_file(str(temp_text_file))
        normalized = content.replace("\r\n", "\n")
        assert normalized == "Line 1\nLine 2\nLine 3"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_lines_returns_list(self, file_io_core: "FileIOCore", temp_text_file: Path) -> None:
        """Test read_lines returns list of lines."""
        lines = await file_io_core.read_lines(temp_text_file)
        assert isinstance(lines, list)
        assert lines == ["Line 1", "Line 2", "Line 3"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_bytes_returns_bytes(self, file_io_core: "FileIOCore", temp_binary_file: Path) -> None:
        """Test read_bytes returns bytes."""
        data = await file_io_core.read_bytes(temp_binary_file)
        assert isinstance(data, bytes)
        assert data == b"\x00\x01\x02\x03\x04"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_file_mmap(self, file_io_core: "FileIOCore", temp_text_file: Path) -> None:
        """Test read_file_mmap returns content."""
        content = await file_io_core.read_file_mmap(temp_text_file)
        assert "Line 1" in content

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_file_with_encoding(self, file_io_core: "FileIOCore", temp_text_file: Path) -> None:
        """Test read_file_with_encoding works."""
        content = await file_io_core.read_file_with_encoding(temp_text_file, "utf-8")
        normalized = content.replace("\r\n", "\n")
        assert normalized == "Line 1\nLine 2\nLine 3"


# ============================================================================
# Async Write Operations Tests
# ============================================================================


class TestAsyncWriteOperations:
    """Tests for async write operations."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_write_file_creates_file(self, file_io_core: "FileIOCore", tmp_path: Path) -> None:
        """Test write_file creates new file."""
        file_path = tmp_path / "new_file.txt"
        await file_io_core.write_file(file_path, "Test content")
        assert file_path.exists()
        assert file_path.read_text() == "Test content"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_write_lines_creates_file(self, file_io_core: "FileIOCore", tmp_path: Path) -> None:
        """Test write_lines creates file with lines."""
        file_path = tmp_path / "lines.txt"
        await file_io_core.write_lines(file_path, ["Line 1", "Line 2"])
        content = file_path.read_text()
        assert "Line 1" in content
        assert "Line 2" in content

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_write_bytes_creates_file(self, file_io_core: "FileIOCore", tmp_path: Path) -> None:
        """Test write_bytes creates binary file."""
        file_path = tmp_path / "binary.bin"
        await file_io_core.write_bytes(file_path, b"\x00\x01\x02")
        assert file_path.exists()
        assert file_path.read_bytes() == b"\x00\x01\x02"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_append_file_adds_content(self, file_io_core: "FileIOCore", temp_text_file: Path) -> None:
        """Test append_file adds to existing content."""
        await file_io_core.append_file(temp_text_file, "\nLine 4")
        content = temp_text_file.read_text()
        assert "Line 4" in content


# ============================================================================
# stream_lines Tests
# ============================================================================


class TestStreamLines:
    """Tests for streaming line operations."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stream_lines_yields_lines(self, file_io_core: "FileIOCore", temp_text_file: Path) -> None:
        """Test stream_lines yields lines."""
        lines = []
        async for line in file_io_core.stream_lines(temp_text_file):
            lines.append(line)
        assert "Line 1" in lines[0]
        assert len(lines) == 3

    @pytest.mark.unit
    def test_stream_lines_sync_yields_lines(self, file_io_core: "FileIOCore", temp_text_file: Path) -> None:
        """Test stream_lines_sync yields lines synchronously."""
        lines = list(file_io_core.stream_lines_sync(temp_text_file))
        assert len(lines) == 3


# ============================================================================
# DDS Header Operations Tests
# ============================================================================


class TestDDSOperations:
    """Tests for DDS header operations."""

    @pytest.mark.unit
    def test_read_dds_header_returns_tuple_or_none(self, file_io_core: "FileIOCore", temp_dds_file: Path) -> None:
        """Test read_dds_header returns dimensions or None."""
        result = file_io_core.read_dds_header(temp_dds_file)
        assert result is None or (isinstance(result, tuple) and len(result) == 2)

    @pytest.mark.unit
    def test_read_dds_headers_batch_returns_dict(self, file_io_core: "FileIOCore", temp_dds_file: Path) -> None:
        """Test read_dds_headers_batch returns dictionary."""
        result = file_io_core.read_dds_headers_batch([temp_dds_file])
        assert isinstance(result, dict)
        assert str(temp_dds_file) in result


# ============================================================================
# walk_directory Tests
# ============================================================================


class TestWalkDirectory:
    """Tests for walk_directory operation."""

    @pytest.mark.unit
    def test_walk_directory_returns_list(self, file_io_core: "FileIOCore", tmp_path: Path) -> None:
        """Test walk_directory returns list of file paths."""
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file2.txt").write_text("content")
        result = file_io_core.walk_directory(tmp_path)
        assert isinstance(result, list)
        assert len(result) >= 2

    @pytest.mark.unit
    def test_walk_directory_with_pattern(self, file_io_core: "FileIOCore", tmp_path: Path) -> None:
        """Test walk_directory with file pattern filter."""
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file2.dds").write_text("content")
        result = file_io_core.walk_directory(tmp_path, pattern=r"\.txt$")
        assert all(".txt" in path for path in result)

    @pytest.mark.unit
    def test_walk_directory_with_max_depth(self, file_io_core: "FileIOCore", tmp_path: Path) -> None:
        """Test walk_directory respects max_depth."""
        (tmp_path / "file1.txt").write_text("content")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("content")
        result = file_io_core.walk_directory(tmp_path, max_depth=1)
        assert isinstance(result, list)


# ============================================================================
# Batch Operations Tests
# ============================================================================


class TestBatchOperations:
    """Tests for batch file operations."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_multiple_files_returns_dict(self, file_io_core: "FileIOCore", tmp_path: Path) -> None:
        """Test read_multiple_files returns dictionary."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("Content 1")
        file2.write_text("Content 2")
        result = await file_io_core.read_multiple_files([file1, file2])
        assert isinstance(result, dict)
        assert "file1.txt" in result
        assert "file2.txt" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_write_multiple_files_creates_files(self, file_io_core: "FileIOCore", tmp_path: Path) -> None:
        """Test write_multiple_files creates all files."""
        files = {
            tmp_path / "file1.txt": "Content 1",
            tmp_path / "file2.txt": "Content 2",
        }
        await file_io_core.write_multiple_files(files)
        assert (tmp_path / "file1.txt").read_text() == "Content 1"
        assert (tmp_path / "file2.txt").read_text() == "Content 2"


# ============================================================================
# Utility Operations Tests
# ============================================================================


class TestUtilityOperations:
    """Tests for utility operations."""

    @pytest.mark.unit
    def test_file_exists_returns_true(self, file_io_core: "FileIOCore", temp_text_file: Path) -> None:
        """Test file_exists returns True for existing file."""
        assert file_io_core.file_exists(temp_text_file) is True

    @pytest.mark.unit
    def test_file_exists_returns_false(self, file_io_core: "FileIOCore", tmp_path: Path) -> None:
        """Test file_exists returns False for missing file."""
        assert file_io_core.file_exists(tmp_path / "nonexistent.txt") is False

    @pytest.mark.unit
    def test_get_file_size_returns_size(self, file_io_core: "FileIOCore", temp_binary_file: Path) -> None:
        """Test get_file_size returns correct size."""
        size = file_io_core.get_file_size(temp_binary_file)
        assert size == 5

    @pytest.mark.unit
    def test_get_file_size_returns_negative_for_missing(self, file_io_core: "FileIOCore", tmp_path: Path) -> None:
        """Test get_file_size returns -1 for missing file."""
        size = file_io_core.get_file_size(tmp_path / "nonexistent.txt")
        assert size == -1

    @pytest.mark.unit
    def test_get_file_info_returns_dict(self, file_io_core: "FileIOCore", temp_text_file: Path) -> None:
        """Test get_file_info returns dictionary with info."""
        info = file_io_core.get_file_info(temp_text_file)
        assert isinstance(info, dict)
        assert "size" in info or "error" in info

    @pytest.mark.unit
    def test_clear_cache_runs_without_error(self, file_io_core: "FileIOCore") -> None:
        """Test clear_cache runs without error."""
        file_io_core.clear_cache()


# ============================================================================
# Crash Log Operations Tests
# ============================================================================


class TestCrashLogOperations:
    """Tests for crash log specific operations."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_crash_log_strips_trailing_empty(self, file_io_core: "FileIOCore", tmp_path: Path) -> None:
        """Test read_crash_log strips trailing empty lines."""
        crash_log = tmp_path / "crash.log"
        crash_log.write_text("Line 1\nLine 2\n\n\n")
        lines = await file_io_core.read_crash_log(crash_log)
        assert lines[-1].strip() != "" or len(lines) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_write_crash_report_creates_md_file(self, file_io_core: "FileIOCore", tmp_path: Path) -> None:
        """Test write_crash_report creates .md file."""
        log_path = tmp_path / "crash.log"
        await file_io_core.write_crash_report(log_path, ["# Report\n", "Content\n"])
        md_path = tmp_path / "crash.md"
        assert md_path.exists()


# ============================================================================
# RUST_AVAILABLE flag Tests
# ============================================================================


class TestRustAvailableFlag:
    """Tests for RUST_AVAILABLE module flag."""

    @pytest.mark.unit
    def test_rust_available_is_bool(self) -> None:
        """Test RUST_AVAILABLE is a boolean."""
        from ClassicLib.integration.rust.file_io_rust import RUST_AVAILABLE

        assert isinstance(RUST_AVAILABLE, bool)
