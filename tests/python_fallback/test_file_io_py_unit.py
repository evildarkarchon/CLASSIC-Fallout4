"""Unit tests for ClassicLib.python.file_io_py module.

This module tests the PythonFileIO class, which provides the pure Python
fallback implementation for async file I/O operations when Rust acceleration
is not available.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

if TYPE_CHECKING:
    from ClassicLib.python.file_io_py import PythonFileIO

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def file_io() -> "PythonFileIO":
    """Create a PythonFileIO instance for testing.

    Returns:
        PythonFileIO instance with default settings.
    """
    from ClassicLib.python.file_io_py import PythonFileIO

    return PythonFileIO()


@pytest.fixture
def file_io_custom_encoding() -> "PythonFileIO":
    """Create a PythonFileIO instance with custom encoding.

    Returns:
        PythonFileIO instance with custom encoding settings.
    """
    from ClassicLib.python.file_io_py import PythonFileIO

    return PythonFileIO(encoding="latin-1", errors="replace")


@pytest.fixture
def temp_text_file(tmp_path: Path) -> Path:
    """Create a temporary text file for testing.

    Args:
        tmp_path: Pytest temporary path fixture.

    Returns:
        Path to temporary text file.
    """
    file_path = tmp_path / "test.txt"
    file_path.write_text("Line 1\nLine 2\nLine 3")
    return file_path


@pytest.fixture
def temp_binary_file(tmp_path: Path) -> Path:
    """Create a temporary binary file for testing.

    Args:
        tmp_path: Pytest temporary path fixture.

    Returns:
        Path to temporary binary file.
    """
    file_path = tmp_path / "test.bin"
    file_path.write_bytes(b"\x00\x01\x02\x03\x04")
    return file_path


@pytest.fixture
def temp_crash_log(tmp_path: Path) -> Path:
    """Create a temporary crash log file for testing.

    Args:
        tmp_path: Pytest temporary path fixture.

    Returns:
        Path to temporary crash log file.
    """
    file_path = tmp_path / "crash-test.log"
    content = "Header Line\nCall Stack:\n  Function1\n  Function2\n\n\n"
    file_path.write_text(content)
    return file_path


# ============================================================================
# PythonFileIO Initialization Tests
# ============================================================================


class TestPythonFileIOInit:
    """Tests for PythonFileIO initialization."""

    @pytest.mark.unit
    def test_init_default_encoding(self) -> None:
        """Test default encoding is UTF-8."""
        from ClassicLib.python.file_io_py import PythonFileIO

        io = PythonFileIO()

        assert io.default_encoding == "utf-8"
        assert io.default_errors == "ignore"

    @pytest.mark.unit
    def test_init_custom_encoding(self) -> None:
        """Test custom encoding can be specified."""
        from ClassicLib.python.file_io_py import PythonFileIO

        io = PythonFileIO(encoding="latin-1", errors="replace")

        assert io.default_encoding == "latin-1"
        assert io.default_errors == "replace"


# ============================================================================
# _ensure_path Tests
# ============================================================================


class TestEnsurePath:
    """Tests for PythonFileIO._ensure_path method."""

    @pytest.mark.unit
    def test_ensure_path_from_string(self, file_io: "PythonFileIO") -> None:
        """Test _ensure_path converts string to Path."""
        result = file_io._ensure_path("/some/path/file.txt")

        assert isinstance(result, Path)
        assert str(result) == "/some/path/file.txt" or str(result) == "\\some\\path\\file.txt"

    @pytest.mark.unit
    def test_ensure_path_from_path(self, file_io: "PythonFileIO") -> None:
        """Test _ensure_path returns Path unchanged."""
        original = Path("/some/path/file.txt")
        result = file_io._ensure_path(original)

        assert result is original


# ============================================================================
# read_file Tests
# ============================================================================


class TestReadFile:
    """Tests for PythonFileIO.read_file method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_file_returns_content(self, file_io: "PythonFileIO", temp_text_file: Path) -> None:
        """Test read_file returns file content."""
        content = await file_io.read_file(temp_text_file)

        assert content == "Line 1\nLine 2\nLine 3"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_file_with_string_path(self, file_io: "PythonFileIO", temp_text_file: Path) -> None:
        """Test read_file works with string path."""
        content = await file_io.read_file(str(temp_text_file))

        assert content == "Line 1\nLine 2\nLine 3"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_file_tries_encoding_detection(self, file_io: "PythonFileIO", temp_text_file: Path) -> None:
        """Test read_file attempts encoding detection first."""
        with patch("ClassicLib.python.file_io_py.AIOFILES_AVAILABLE", False):
            # Mock the encoding detection import to fail
            with patch.dict("sys.modules", {"ClassicLib.FileIO.Async": None}):
                content = await file_io.read_file(temp_text_file)

        assert "Line 1" in content


# ============================================================================
# read_lines Tests
# ============================================================================


class TestReadLines:
    """Tests for PythonFileIO.read_lines method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_lines_returns_list(self, file_io: "PythonFileIO", temp_text_file: Path) -> None:
        """Test read_lines returns list of lines."""
        lines = await file_io.read_lines(temp_text_file)

        assert isinstance(lines, list)
        assert lines == ["Line 1", "Line 2", "Line 3"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_lines_empty_file(self, file_io: "PythonFileIO", tmp_path: Path) -> None:
        """Test read_lines handles empty file."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        lines = await file_io.read_lines(empty_file)

        assert lines == []


# ============================================================================
# read_bytes Tests
# ============================================================================


class TestReadBytes:
    """Tests for PythonFileIO.read_bytes method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_bytes_returns_bytes(self, file_io: "PythonFileIO", temp_binary_file: Path) -> None:
        """Test read_bytes returns bytes."""
        data = await file_io.read_bytes(temp_binary_file)

        assert isinstance(data, bytes)
        assert data == b"\x00\x01\x02\x03\x04"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_bytes_with_string_path(self, file_io: "PythonFileIO", temp_binary_file: Path) -> None:
        """Test read_bytes works with string path."""
        data = await file_io.read_bytes(str(temp_binary_file))

        assert data == b"\x00\x01\x02\x03\x04"


# ============================================================================
# write_file Tests
# ============================================================================


class TestWriteFile:
    """Tests for PythonFileIO.write_file method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_write_file_creates_file(self, file_io: "PythonFileIO", tmp_path: Path) -> None:
        """Test write_file creates new file."""
        file_path = tmp_path / "new_file.txt"

        await file_io.write_file(file_path, "Test content")

        assert file_path.exists()
        assert file_path.read_text() == "Test content"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_write_file_overwrites_existing(self, file_io: "PythonFileIO", temp_text_file: Path) -> None:
        """Test write_file overwrites existing content."""
        await file_io.write_file(temp_text_file, "New content")

        assert temp_text_file.read_text() == "New content"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_write_file_creates_parent_dirs(self, file_io: "PythonFileIO", tmp_path: Path) -> None:
        """Test write_file creates parent directories."""
        file_path = tmp_path / "subdir1" / "subdir2" / "file.txt"

        await file_io.write_file(file_path, "Content")

        assert file_path.exists()
        assert file_path.read_text() == "Content"


# ============================================================================
# write_lines Tests
# ============================================================================


class TestWriteLines:
    """Tests for PythonFileIO.write_lines method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_write_lines_joins_with_newlines(self, file_io: "PythonFileIO", tmp_path: Path) -> None:
        """Test write_lines joins lines with newlines."""
        file_path = tmp_path / "lines.txt"

        await file_io.write_lines(file_path, ["Line 1", "Line 2", "Line 3"])

        content = file_path.read_text()
        assert content == "Line 1\nLine 2\nLine 3\n"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_write_lines_adds_trailing_newline(self, file_io: "PythonFileIO", tmp_path: Path) -> None:
        """Test write_lines adds trailing newline."""
        file_path = tmp_path / "lines.txt"

        await file_io.write_lines(file_path, ["Single line"])

        content = file_path.read_text()
        assert content.endswith("\n")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_write_lines_empty_list(self, file_io: "PythonFileIO", tmp_path: Path) -> None:
        """Test write_lines handles empty list."""
        file_path = tmp_path / "empty.txt"

        await file_io.write_lines(file_path, [])

        assert file_path.read_text() == "\n"


# ============================================================================
# write_bytes Tests
# ============================================================================


class TestWriteBytes:
    """Tests for PythonFileIO.write_bytes method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_write_bytes_creates_file(self, file_io: "PythonFileIO", tmp_path: Path) -> None:
        """Test write_bytes creates binary file."""
        file_path = tmp_path / "binary.bin"

        await file_io.write_bytes(file_path, b"\x00\x01\x02")

        assert file_path.exists()
        assert file_path.read_bytes() == b"\x00\x01\x02"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_write_bytes_creates_parent_dirs(self, file_io: "PythonFileIO", tmp_path: Path) -> None:
        """Test write_bytes creates parent directories."""
        file_path = tmp_path / "subdir" / "binary.bin"

        await file_io.write_bytes(file_path, b"\xff")

        assert file_path.exists()


# ============================================================================
# append_file Tests
# ============================================================================


class TestAppendFile:
    """Tests for PythonFileIO.append_file method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_append_file_adds_content(self, file_io: "PythonFileIO", temp_text_file: Path) -> None:
        """Test append_file adds to existing content."""
        await file_io.append_file(temp_text_file, "\nLine 4")

        content = temp_text_file.read_text()
        assert content == "Line 1\nLine 2\nLine 3\nLine 4"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_append_file_creates_if_missing(self, file_io: "PythonFileIO", tmp_path: Path) -> None:
        """Test append_file creates file if missing."""
        file_path = tmp_path / "new.txt"

        await file_io.append_file(file_path, "First content")

        assert file_path.exists()
        assert file_path.read_text() == "First content"


# ============================================================================
# read_crash_log Tests
# ============================================================================


class TestReadCrashLog:
    """Tests for PythonFileIO.read_crash_log method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_crash_log_strips_trailing_empty(self, file_io: "PythonFileIO", temp_crash_log: Path) -> None:
        """Test read_crash_log strips trailing empty lines."""
        lines = await file_io.read_crash_log(temp_crash_log)

        # Should not have trailing empty lines
        assert lines[-1].strip() != ""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_crash_log_returns_list(self, file_io: "PythonFileIO", temp_crash_log: Path) -> None:
        """Test read_crash_log returns list of lines."""
        lines = await file_io.read_crash_log(temp_crash_log)

        assert isinstance(lines, list)
        assert len(lines) > 0
        assert "Header Line" in lines[0]


# ============================================================================
# write_crash_report Tests
# ============================================================================


class TestWriteCrashReport:
    """Tests for PythonFileIO.write_crash_report method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_write_crash_report_creates_md_file(self, file_io: "PythonFileIO", tmp_path: Path) -> None:
        """Test write_crash_report creates .md file."""
        log_path = tmp_path / "crash.log"

        await file_io.write_crash_report(log_path, ["# Report\n", "Content\n"])

        md_path = tmp_path / "crash.md"
        assert md_path.exists()
        assert md_path.read_text() == "# Report\nContent\n"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_write_crash_report_joins_lines(self, file_io: "PythonFileIO", tmp_path: Path) -> None:
        """Test write_crash_report joins lines directly."""
        log_path = tmp_path / "test.log"

        await file_io.write_crash_report(log_path, ["Line 1\n", "Line 2\n"])

        md_path = tmp_path / "test.md"
        assert md_path.read_text() == "Line 1\nLine 2\n"


# ============================================================================
# read_multiple_files Tests
# ============================================================================


class TestReadMultipleFiles:
    """Tests for PythonFileIO.read_multiple_files method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_multiple_files_returns_dict(self, file_io: "PythonFileIO", tmp_path: Path) -> None:
        """Test read_multiple_files returns dictionary."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("Content 1")
        file2.write_text("Content 2")

        result = await file_io.read_multiple_files([file1, file2])

        assert isinstance(result, dict)
        assert result["file1.txt"] == "Content 1"
        assert result["file2.txt"] == "Content 2"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_multiple_files_handles_errors(self, file_io: "PythonFileIO", tmp_path: Path) -> None:
        """Test read_multiple_files handles missing files gracefully."""
        existing = tmp_path / "exists.txt"
        missing = tmp_path / "missing.txt"
        existing.write_text("Content")

        result = await file_io.read_multiple_files([existing, missing])

        assert result["exists.txt"] == "Content"
        assert result["missing.txt"] == ""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_multiple_files_empty_list(self, file_io: "PythonFileIO") -> None:
        """Test read_multiple_files handles empty list."""
        result = await file_io.read_multiple_files([])

        assert result == {}


# ============================================================================
# write_multiple_files Tests
# ============================================================================


class TestWriteMultipleFiles:
    """Tests for PythonFileIO.write_multiple_files method."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_write_multiple_files_creates_files(self, file_io: "PythonFileIO", tmp_path: Path) -> None:
        """Test write_multiple_files creates all files."""
        files = {
            tmp_path / "file1.txt": "Content 1",
            tmp_path / "file2.txt": "Content 2",
        }

        await file_io.write_multiple_files(files)

        assert (tmp_path / "file1.txt").read_text() == "Content 1"
        assert (tmp_path / "file2.txt").read_text() == "Content 2"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_write_multiple_files_empty_dict(self, file_io: "PythonFileIO") -> None:
        """Test write_multiple_files handles empty dict."""
        # Should not raise
        await file_io.write_multiple_files({})


# ============================================================================
# file_exists Tests
# ============================================================================


class TestFileExists:
    """Tests for PythonFileIO.file_exists method."""

    @pytest.mark.unit
    def test_file_exists_returns_true(self, file_io: "PythonFileIO", temp_text_file: Path) -> None:
        """Test file_exists returns True for existing file."""
        assert file_io.file_exists(temp_text_file) is True

    @pytest.mark.unit
    def test_file_exists_returns_false(self, file_io: "PythonFileIO", tmp_path: Path) -> None:
        """Test file_exists returns False for missing file."""
        assert file_io.file_exists(tmp_path / "nonexistent.txt") is False

    @pytest.mark.unit
    def test_file_exists_with_string_path(self, file_io: "PythonFileIO", temp_text_file: Path) -> None:
        """Test file_exists works with string path."""
        assert file_io.file_exists(str(temp_text_file)) is True


# ============================================================================
# get_file_size Tests
# ============================================================================


class TestGetFileSize:
    """Tests for PythonFileIO.get_file_size method."""

    @pytest.mark.unit
    def test_get_file_size_returns_size(self, file_io: "PythonFileIO", temp_binary_file: Path) -> None:
        """Test get_file_size returns correct size."""
        size = file_io.get_file_size(temp_binary_file)

        assert size == 5  # 5 bytes

    @pytest.mark.unit
    def test_get_file_size_returns_negative_for_missing(self, file_io: "PythonFileIO", tmp_path: Path) -> None:
        """Test get_file_size returns -1 for missing file."""
        size = file_io.get_file_size(tmp_path / "nonexistent.txt")

        assert size == -1

    @pytest.mark.unit
    def test_get_file_size_with_string_path(self, file_io: "PythonFileIO", temp_binary_file: Path) -> None:
        """Test get_file_size works with string path."""
        size = file_io.get_file_size(str(temp_binary_file))

        assert size == 5


# ============================================================================
# Alias Tests
# ============================================================================


class TestFileIOCoreAlias:
    """Tests for FileIOCore alias."""

    @pytest.mark.unit
    def test_file_io_core_alias_exists(self) -> None:
        """Test FileIOCore is an alias for PythonFileIO."""
        from ClassicLib.python.file_io_py import FileIOCore, PythonFileIO

        assert FileIOCore is PythonFileIO


# ============================================================================
# aiofiles Fallback Tests
# ============================================================================


class TestAiofilesFallback:
    """Tests for aiofiles availability handling."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_file_without_aiofiles(self, file_io: "PythonFileIO", temp_text_file: Path) -> None:
        """Test read_file works without aiofiles."""
        with patch("ClassicLib.python.file_io_py.AIOFILES_AVAILABLE", False):
            content = await file_io.read_file(temp_text_file)

        assert "Line 1" in content

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_write_file_without_aiofiles(self, file_io: "PythonFileIO", tmp_path: Path) -> None:
        """Test write_file works without aiofiles."""
        file_path = tmp_path / "test.txt"

        with patch("ClassicLib.python.file_io_py.AIOFILES_AVAILABLE", False):
            await file_io.write_file(file_path, "Test content")

        assert file_path.read_text() == "Test content"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_read_bytes_without_aiofiles(self, file_io: "PythonFileIO", temp_binary_file: Path) -> None:
        """Test read_bytes works without aiofiles."""
        with patch("ClassicLib.python.file_io_py.AIOFILES_AVAILABLE", False):
            data = await file_io.read_bytes(temp_binary_file)

        assert data == b"\x00\x01\x02\x03\x04"
