"""Shared fixtures for file I/O tests."""

from pathlib import Path

import pytest

from ClassicLib.FileIO import FileIOCore


@pytest.fixture
def io_core() -> FileIOCore:
    """Create a FileIOCore instance for testing."""
    return FileIOCore()


@pytest.fixture
def temp_file(tmp_path: Path) -> Path:
    """Create a temporary file for testing."""
    test_path = tmp_path / "test_file.txt"
    test_path.write_text("Test content\nLine 2\nLine 3")
    return test_path


@pytest.fixture
def temp_binary_file(tmp_path: Path) -> Path:
    """Create a temporary binary file for testing."""
    test_path = tmp_path / "test_binary.bin"
    test_bytes = b"Binary content \x00\x01\x02\x03"
    test_path.write_bytes(test_bytes)
    return test_path


@pytest.fixture
def temp_crash_log(tmp_path: Path) -> Path:
    """Create a temporary crash log file for testing."""
    test_path = tmp_path / "test_crash.log"
    test_path.write_text("Crash log line 1\nCrash log line 2\n\n\n")
    return test_path


@pytest.fixture
def temp_files_set(tmp_path: Path) -> list[Path]:
    """Create a set of temporary test files."""
    test_files = []
    for i in range(3):
        file_path = tmp_path / f"test_{i}.txt"
        file_path.write_text(f"Content of file {i}")
        test_files.append(file_path)
    return test_files
