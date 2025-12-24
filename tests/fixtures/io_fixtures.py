"""
File I/O and utility fixtures for CLASSIC-Fallout4 test suite.

This module provides fixtures for file operations testing, including
temporary file creation, binary files, crash logs, and utility files.

Consolidated from:
- tests/io/conftest.py
- tests/utils/conftest.py
"""

from pathlib import Path

import pytest

from ClassicLib.FileIO import FileIOCore


# ============================================================================
# FileIOCore Fixtures (from tests/io/conftest.py)
# ============================================================================


@pytest.fixture
def io_file_core() -> FileIOCore:
    """Create a FileIOCore instance for testing.

    Returns:
        A fresh FileIOCore instance for file operations testing.
    """
    return FileIOCore()


@pytest.fixture
def io_temp_file(tmp_path: Path) -> Path:
    """Create a temporary text file for testing.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        Path to a temporary text file with sample content.
    """
    test_path = tmp_path / "test_file.txt"
    test_path.write_text("Test content\nLine 2\nLine 3")
    return test_path


@pytest.fixture
def io_temp_binary_file(tmp_path: Path) -> Path:
    """Create a temporary binary file for testing.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        Path to a temporary binary file with sample binary content.
    """
    test_path = tmp_path / "test_binary.bin"
    test_bytes = b"Binary content \x00\x01\x02\x03"
    test_path.write_bytes(test_bytes)
    return test_path


@pytest.fixture
def io_temp_crash_log(tmp_path: Path) -> Path:
    """Create a temporary crash log file for testing.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        Path to a temporary crash log file with sample content.
    """
    test_path = tmp_path / "test_crash.log"
    test_path.write_text("Crash log line 1\nCrash log line 2\n\n\n")
    return test_path


@pytest.fixture
def io_temp_files_set(tmp_path: Path) -> list[Path]:
    """Create a set of temporary test files.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        List of paths to temporary test files.
    """
    test_files = []
    for i in range(3):
        file_path = tmp_path / f"test_{i}.txt"
        file_path.write_text(f"Content of file {i}")
        test_files.append(file_path)
    return test_files


# ============================================================================
# Utility File Fixtures (from tests/utils/conftest.py)
# ============================================================================


@pytest.fixture
def io_sample_text_file(tmp_path: Path) -> Path:
    """Create a sample text file for testing.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        Path to a sample text file with testing content.
    """
    file_path = tmp_path / "sample.txt"
    file_path.write_text("Sample content for testing")
    return file_path


@pytest.fixture
def io_sample_binary_file(tmp_path: Path) -> Path:
    """Create a sample binary file for testing.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        Path to a sample binary file with test bytes.
    """
    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"\x00\x01\x02\x03\xff\xfe\xfd")
    return file_path


@pytest.fixture
def io_empty_file(tmp_path: Path) -> Path:
    """Create an empty file for testing.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        Path to an empty file.
    """
    file_path = tmp_path / "empty.txt"
    file_path.touch()
    return file_path


# Backward compatibility aliases (deprecated - use prefixed names)
# These will be removed in a future version
io_core = io_file_core
temp_file = io_temp_file
temp_binary_file = io_temp_binary_file
temp_crash_log = io_temp_crash_log
temp_files_set = io_temp_files_set
sample_text_file = io_sample_text_file
sample_binary_file = io_sample_binary_file
empty_file = io_empty_file
