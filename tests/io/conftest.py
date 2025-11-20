"""Shared fixtures for file I/O tests."""

import tempfile
from pathlib import Path

import pytest

from ClassicLib.FileIOCore import FileIOCore


@pytest.fixture
def io_core() -> FileIOCore:
    """Create a FileIOCore instance for testing."""
    return FileIOCore()


@pytest.fixture
def temp_file() -> Path:
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        test_path = Path(f.name)
        f.write("Test content\nLine 2\nLine 3")
    yield test_path
    test_path.unlink(missing_ok=True)


@pytest.fixture
def temp_binary_file() -> Path:
    """Create a temporary binary file for testing."""
    test_bytes = b"Binary content \x00\x01\x02\x03"
    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
        test_path = Path(f.name)
        f.write(test_bytes)
    yield test_path
    test_path.unlink(missing_ok=True)


@pytest.fixture
def temp_crash_log() -> Path:
    """Create a temporary crash log file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
        test_path = Path(f.name)
        f.write("Crash log line 1\nCrash log line 2\n\n\n")
    yield test_path
    test_path.unlink(missing_ok=True)


@pytest.fixture
def temp_files_set(tmp_path: Path) -> list[Path]:
    """Create a set of temporary test files."""
    test_files = []
    for i in range(3):
        file_path = tmp_path / f"test_{i}.txt"
        file_path.write_text(f"Content of file {i}")
        test_files.append(file_path)
    return test_files
