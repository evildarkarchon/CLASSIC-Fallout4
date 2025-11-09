"""
Shared fixtures for utility function tests.

This module provides common fixtures used across the utils test suite.
"""

from pathlib import Path

import pytest


@pytest.fixture
def sample_text_file(tmp_path: Path) -> Path:
    """Create a sample text file for testing."""
    file_path = tmp_path / "sample.txt"
    file_path.write_text("Sample content for testing")
    return file_path


@pytest.fixture
def sample_binary_file(tmp_path: Path) -> Path:
    """Create a sample binary file for testing."""
    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"\x00\x01\x02\x03\xff\xfe\xfd")
    return file_path


@pytest.fixture
def empty_file(tmp_path: Path) -> Path:
    """Create an empty file for testing."""
    file_path = tmp_path / "empty.txt"
    file_path.touch()
    return file_path
