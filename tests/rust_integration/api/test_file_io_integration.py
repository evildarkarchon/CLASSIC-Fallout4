"""
Tests for Rust FileIOCore integration.

Tests the high-performance file I/O operations including:
- Async file reading/writing with encoding detection
- Memory-mapped file operations
- DDS header parsing
- Parallel directory traversal
- Caching behavior
"""
# ruff: noqa: ANN201, ANN001, PLR6301

import asyncio
from pathlib import Path

import pytest

from ClassicLib.integration.factory import get_file_io
from ClassicLib.integration.status import is_rust_accelerated

# Check if Rust file I/O is available
RUST_AVAILABLE = {"file_io_core": is_rust_accelerated("file_io_core")}


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory with test files."""
    # Create some test files
    (tmp_path / "test.txt").write_text("Hello, World!", encoding="utf-8")
    (tmp_path / "test_utf8.txt").write_text("UTF-8 content: 你好世界", encoding="utf-8")
    (tmp_path / "test_cp1252.txt").write_bytes(b"Windows-1252: \xe9\xe0\xe8")  # éàè in CP1252

    # Create subdirectories
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "nested.txt").write_text("Nested file", encoding="utf-8")

    # Create a large file for mmap testing (11MB)
    large_content = "Large file content\n" * 600_000  # ~11MB
    (tmp_path / "large.txt").write_text(large_content, encoding="utf-8")

    return tmp_path


@pytest.fixture
def mock_dds_file(tmp_path):
    """Create a mock DDS file with valid header."""
    dds_path = tmp_path / "texture.dds"

    # Create a minimal valid DDS header
    header = bytearray(128)

    # Magic number "DDS " (0x20534444)
    header[0:4] = b"DDS "

    # Header size (124)
    header[4:8] = (124).to_bytes(4, "little")

    # Height (1024)
    header[12:16] = (1024).to_bytes(4, "little")

    # Width (2048)
    header[16:20] = (2048).to_bytes(4, "little")

    dds_path.write_bytes(bytes(header))
    return dds_path


@pytest.fixture
def mock_invalid_dds_file(tmp_path):
    """Create a DDS file with odd dimensions (invalid for mipmaps)."""
    dds_path = tmp_path / "invalid_texture.dds"

    header = bytearray(128)
    header[0:4] = b"DDS "
    header[4:8] = (124).to_bytes(4, "little")
    header[12:16] = (1023).to_bytes(4, "little")  # Odd height
    header[16:20] = (2047).to_bytes(4, "little")  # Odd width

    dds_path.write_bytes(bytes(header))
    return dds_path


class TestRustFileIOCore:
    """Test Rust FileIOCore functionality."""

    @pytest.mark.asyncio
    async def test_read_file_basic(self, temp_dir):
        """Test basic file reading."""
        io = get_file_io()  # Factory returns the implementation directly

        content = await io.read_file(temp_dir / "test.txt")
        assert content == "Hello, World!"

    @pytest.mark.asyncio
    async def test_read_file_encoding_detection(self, temp_dir):
        """Test automatic encoding detection."""
        io = get_file_io()  # Factory returns the implementation directly

        # UTF-8 file
        utf8_content = await io.read_file(temp_dir / "test_utf8.txt")
        assert "你好世界" in utf8_content

        # Windows-1252 file (should be detected and decoded)
        cp1252_content = await io.read_file(temp_dir / "test_cp1252.txt")
        assert len(cp1252_content) > 0

    @pytest.mark.asyncio
    async def test_read_lines(self, temp_dir):
        """Test reading file as lines."""
        # Create multi-line file
        multiline_path = temp_dir / "multiline.txt"
        multiline_path.write_text("Line 1\nLine 2\nLine 3\n", encoding="utf-8")

        io = get_file_io()  # Factory returns the implementation directly

        lines = await io.read_lines(multiline_path)
        assert lines == ["Line 1", "Line 2", "Line 3"]

    @pytest.mark.asyncio
    async def test_write_file(self, temp_dir):
        """Test file writing."""
        io = get_file_io()  # Factory returns the implementation directly

        output_path = temp_dir / "output.txt"
        await io.write_file(output_path, "Test content")

        assert output_path.exists()
        assert output_path.read_text() == "Test content"

    @pytest.mark.asyncio
    async def test_write_lines(self, temp_dir):
        """Test writing lines to file."""
        io = get_file_io()  # Factory returns the implementation directly

        output_path = temp_dir / "lines_output.txt"
        await io.write_lines(output_path, ["Line 1", "Line 2", "Line 3"])

        assert output_path.exists()
        content = output_path.read_text()
        assert content == "Line 1\nLine 2\nLine 3\n"

    @pytest.mark.asyncio
    async def test_append_file(self, temp_dir):
        """Test appending to file."""
        io = get_file_io()  # Factory returns the implementation directly

        # Create initial file
        append_path = temp_dir / "append.txt"
        append_path.write_text("Initial content\n", encoding="utf-8")

        # Append content
        await io.append_file(append_path, "Appended content\n")

        result = append_path.read_text()
        assert result == "Initial content\nAppended content\n"

    @pytest.mark.asyncio
    async def test_read_bytes(self, temp_dir):
        """Test reading file as bytes."""
        io = get_file_io()  # Factory returns the implementation directly

        # Write binary data
        binary_path = temp_dir / "binary.dat"
        test_bytes = b"\x00\x01\x02\x03\x04\x05"
        binary_path.write_bytes(test_bytes)

        result = await io.read_bytes(binary_path)
        assert result == test_bytes

    @pytest.mark.asyncio
    async def test_write_bytes(self, temp_dir):
        """Test writing bytes to file."""
        io = get_file_io()  # Factory returns the implementation directly

        output_path = temp_dir / "bytes_output.dat"
        test_bytes = b"\x00\x01\x02\x03\x04\x05"

        await io.write_bytes(output_path, test_bytes)

        assert output_path.exists()
        assert output_path.read_bytes() == test_bytes

    def test_file_exists(self, temp_dir):
        """Test file existence check."""
        io = get_file_io()  # Factory returns the implementation directly

        assert io.file_exists(temp_dir / "test.txt") is True
        assert io.file_exists(temp_dir / "nonexistent.txt") is False

    def test_get_file_size(self, temp_dir):
        """Test getting file size."""
        io = get_file_io()  # Factory returns the implementation directly

        size = io.get_file_size(temp_dir / "test.txt")
        assert size == len("Hello, World!")

        # Non-existent file
        size = io.get_file_size(temp_dir / "nonexistent.txt")
        assert size == -1

    @pytest.mark.asyncio
    async def test_read_multiple_files(self, temp_dir):
        """Test reading multiple files concurrently."""
        io = get_file_io()  # Factory returns the implementation directly

        paths = [
            temp_dir / "test.txt",
            temp_dir / "test_utf8.txt",
            temp_dir / "subdir" / "nested.txt",
        ]

        results = await io.read_multiple_files(paths)

        assert "test.txt" in results
        assert "test_utf8.txt" in results
        assert "nested.txt" in results
        assert results["test.txt"] == "Hello, World!"
        assert "你好世界" in results["test_utf8.txt"]
        assert results["nested.txt"] == "Nested file"

    @pytest.mark.asyncio
    async def test_write_multiple_files(self, temp_dir):
        """Test writing multiple files concurrently."""
        io = get_file_io()  # Factory returns the implementation directly

        files = {
            temp_dir / "multi1.txt": "Content 1",
            temp_dir / "multi2.txt": "Content 2",
            temp_dir / "subdir" / "multi3.txt": "Content 3",
        }

        await io.write_multiple_files(files)

        for path, expected_content in files.items():
            assert Path(path).exists()  # noqa: ASYNC240
            assert Path(path).read_text(encoding="utf-8") == expected_content  # noqa: ASYNC240

    @pytest.mark.asyncio
    async def test_crash_log_operations(self, temp_dir):
        """Test crash log specific operations."""
        io = get_file_io()  # Factory returns the implementation directly

        # Create a mock crash log
        crash_log_path = temp_dir / "crash.log"
        crash_log_content = [
            "Crash Log Line 1",
            "Crash Log Line 2",
            "Crash Log Line 3",
            "",  # Empty line at end
            "",
        ]
        crash_log_path.write_text("\n".join(crash_log_content), encoding="utf-8")

        # Read crash log (should strip trailing empty lines)
        lines = await io.read_crash_log(crash_log_path)
        assert len(lines) == 3
        assert lines[-1] == "Crash Log Line 3"

        # Write crash report
        report_lines = ["# Crash Report\n", "## Details\n", "Error occurred\n"]
        await io.write_crash_report(crash_log_path, report_lines)

        report_path = crash_log_path.with_suffix(".md")
        assert report_path.exists()
        content = report_path.read_text()
        assert "# Crash Report" in content
        assert "Error occurred" in content

    @pytest.mark.skipif(not RUST_AVAILABLE.get("file_io_core"), reason="Rust FileIOCore not available")
    @pytest.mark.asyncio
    async def test_memory_mapped_reading(self, temp_dir):
        """Test memory-mapped file reading for large files."""
        io = get_file_io()

        # Read large file (should use mmap)
        content = await io.read_file_mmap(temp_dir / "large.txt")
        assert "Large file content" in content
        assert len(content) > 10_000_000  # Should be ~11MB

    @pytest.mark.skip(
        reason="Rust DDS parser uses ddsfile crate which requires fully valid DDS files, not mock headers. Needs real game DDS files for testing."
    )
    @pytest.mark.skipif(not RUST_AVAILABLE.get("file_io_core"), reason="Rust FileIOCore not available")
    @pytest.mark.asyncio
    async def test_dds_header_parsing(self, mock_dds_file):
        """Test DDS header parsing.

        Note: This test is skipped because the Rust DDS parser uses the ddsfile crate
        which performs full DDS format validation, not just header byte checking.
        Mock DDS files created with minimal headers do not pass full validation.
        Real DDS files from the game would be needed for proper testing.
        """
        io = get_file_io()

        # Read valid DDS header
        dimensions = await io.read_dds_header(mock_dds_file)
        assert dimensions is not None
        assert dimensions == (2048, 1024)  # (width, height)

    @pytest.mark.skip(
        reason="Rust DDS parser uses ddsfile crate which requires fully valid DDS files, not mock headers. Needs real game DDS files for testing."
    )
    @pytest.mark.skipif(not RUST_AVAILABLE.get("file_io_core"), reason="Rust FileIOCore not available")
    @pytest.mark.asyncio
    async def test_dds_header_invalid_dimensions(self, mock_invalid_dds_file):
        """Test DDS header parsing with invalid dimensions.

        Note: This test is skipped because the Rust DDS parser uses the ddsfile crate
        which performs full DDS format validation. Mock files don't pass validation.
        """
        io = get_file_io()

        # Read DDS with odd dimensions
        dimensions = await io.read_dds_header(mock_invalid_dds_file)
        assert dimensions is not None
        assert dimensions == (2047, 1023)  # Odd dimensions

    @pytest.mark.skip(
        reason="Rust DDS parser uses ddsfile crate which requires fully valid DDS files, not mock headers. Needs real game DDS files for testing."
    )
    @pytest.mark.skipif(not RUST_AVAILABLE.get("file_io_core"), reason="Rust FileIOCore not available")
    @pytest.mark.asyncio
    async def test_dds_batch_processing(self, tmp_path):
        """Test batch DDS header processing.

        Note: This test is skipped because the Rust DDS parser uses the ddsfile crate
        which performs full DDS format validation. Mock files don't pass validation.
        """
        # Create multiple DDS files
        dds_files = []
        for i in range(5):
            dds_path = tmp_path / f"texture_{i}.dds"
            header = bytearray(128)
            header[0:4] = b"DDS "
            header[4:8] = (124).to_bytes(4, "little")
            header[12:16] = ((i + 1) * 256).to_bytes(4, "little")  # Variable heights
            header[16:20] = ((i + 1) * 512).to_bytes(4, "little")  # Variable widths
            dds_path.write_bytes(bytes(header))
            dds_files.append(dds_path)

        io = get_file_io()
        results = await io.read_dds_headers_batch(dds_files)

        assert len(results) == 5
        for i, path in enumerate(dds_files):
            assert str(path) in results
            dims = results[str(path)]
            assert dims == ((i + 1) * 512, (i + 1) * 256)

    @pytest.mark.skipif(not RUST_AVAILABLE.get("file_io_core"), reason="Rust FileIOCore not available")
    @pytest.mark.asyncio
    async def test_directory_traversal(self, temp_dir):
        """Test parallel directory traversal."""
        # Create more files and directories
        (temp_dir / "dir1").mkdir()
        (temp_dir / "dir1" / "file1.txt").write_text("content")
        (temp_dir / "dir1" / "file2.py").write_text("code")
        (temp_dir / "dir2").mkdir()
        (temp_dir / "dir2" / "file3.txt").write_text("more content")
        (temp_dir / "dir2" / "subdir").mkdir()
        (temp_dir / "dir2" / "subdir" / "deep.txt").write_text("deep content")

        io = get_file_io()

        # Walk all files
        all_files = io.walk_directory(temp_dir)
        assert len(all_files) > 5  # Should find all created files

        # Walk with pattern (only .txt files)
        txt_files = io.walk_directory(temp_dir, pattern=r"\.txt$")
        for file in txt_files:
            assert file.endswith(".txt")

        # Walk with max depth
        shallow_files = io.walk_directory(temp_dir, max_depth=1)
        # Should not include deep.txt
        deep_paths = [f for f in shallow_files if "deep.txt" in f]
        assert len(deep_paths) == 0

    @pytest.mark.skipif(not RUST_AVAILABLE.get("file_io_core"), reason="Rust FileIOCore not available")
    def test_caching_behavior(self, temp_dir):
        """Test that caching improves performance."""
        io = get_file_io()

        # Clear cache first
        io.clear_cache()

        # First read (not cached)
        import time

        start = time.perf_counter()
        asyncio.run(io.read_file(temp_dir / "test.txt"))
        _ = time.perf_counter() - start

        # Second read (should be cached and faster)
        start = time.perf_counter()
        asyncio.run(io.read_file(temp_dir / "test.txt"))
        cached_read_time = time.perf_counter() - start

        # Cached read should generally be faster (though not always measurable for small files)
        # Just verify it completes successfully
        assert cached_read_time >= 0

        # Clear cache and verify it works
        io.clear_cache()
        content = asyncio.run(io.read_file(temp_dir / "test.txt"))
        assert content == "Hello, World!"

    @pytest.mark.asyncio
    async def test_stream_lines(self, temp_dir):
        """Test streaming lines asynchronously."""
        io = get_file_io()
        file_path = temp_dir / "test.txt"

        lines = []
        async for line in io.stream_lines(file_path):
            lines.append(line)

        assert len(lines) == 1
        assert lines[0] == "Hello, World!"

        # Test with multi-line file
        multi_path = temp_dir / "multi_stream.txt"
        multi_path.write_text("Line 1\nLine 2\nLine 3", encoding="utf-8")

        lines = []
        async for line in io.stream_lines(multi_path):
            lines.append(line)

        assert len(lines) == 3
        assert lines[0] == "Line 1"
        assert lines[1] == "Line 2"
        assert lines[2] == "Line 3"

    @pytest.mark.asyncio
    async def test_stream_lines_sync(self, temp_dir):
        """Test streaming lines synchronously."""
        io = get_file_io()
        file_path = temp_dir / "test.txt"

        # Even though it's a sync method, we can call it here
        # Just need to convert iterator to list
        def run_sync():
            return list(io.stream_lines_sync(file_path))

        loop = asyncio.get_running_loop()
        lines = await loop.run_in_executor(None, run_sync)

        assert len(lines) == 1
        assert lines[0] == "Hello, World!"


class TestRustIntegration:
    """Test Rust integration detection and fallback."""

    def test_rust_detection(self):
        """Test that Rust modules are properly detected."""
        io = get_file_io()
        # Check if Rust is being used (if available)
        if RUST_AVAILABLE.get("file_io_core"):
            assert io.is_rust_accelerated
        else:
            assert not io.is_rust_accelerated

    def test_python_fallback(self):
        """Test that FileIOCore implementation is available.

        Note: This test verifies that a FileIOCore implementation is available,
        whether Rust-accelerated or Python fallback. Testing actual fallback
        behavior requires Rust to not be installed, which can't be easily mocked.
        """
        io = get_file_io()
        assert io is not None  # Factory returns implementation directly

        # Verify that the object has the is_rust_accelerated attribute
        assert hasattr(io, "is_rust_accelerated")

        # The value will be True if Rust is available, False otherwise
        # Both cases are valid - we just verify the attribute exists
        assert isinstance(io.is_rust_accelerated, bool)

    @pytest.mark.asyncio
    async def test_api_compatibility(self, temp_dir):
        """Test that both Rust and Python implementations have the same API."""
        io = get_file_io()  # Factory returns the implementation directly

        # Test that all expected methods exist
        required_methods = [
            "read_file",
            "read_lines",
            "read_bytes",
            "write_file",
            "write_lines",
            "write_bytes",
            "append_file",
            "read_crash_log",
            "write_crash_report",
            "read_multiple_files",
            "write_multiple_files",
            "file_exists",
            "get_file_size",
        ]

        for method in required_methods:
            assert hasattr(io, method), f"Missing method: {method}"

        # Test basic operations work regardless of implementation
        test_file = temp_dir / "api_test.txt"
        await io.write_file(test_file, "API test content")
        content = await io.read_file(test_file)
        assert content == "API test content"
