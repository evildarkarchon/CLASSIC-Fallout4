"""
Performance test fixtures and configuration.

This module provides fixtures for performance tests to ensure proper test isolation
by using test data instead of production directories.
"""

import shutil
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def sample_crash_logs_dir() -> Path:
    """
    Provide path to sample crash logs directory.

    Returns:
        Path to the test_data/sample_crash_logs directory
    """
    return Path(__file__).parent.parent / "test_data" / "sample_crash_logs"


@pytest.fixture
def performance_test_logs(tmp_path: Path, sample_crash_logs_dir: Path) -> list[Path]:
    """
    Create multiple copies of sample crash logs for performance testing.

    This fixture creates multiple crash log files in a temporary directory
    to simulate a realistic workload without depending on production data.

    Args:
        tmp_path: Pytest's temporary directory fixture
        sample_crash_logs_dir: Path to sample crash logs

    Returns:
        List of paths to crash log files for testing
    """
    # Get sample crash log files
    sample_files = list(sample_crash_logs_dir.glob("*.log"))
    if not sample_files:
        pytest.skip("No sample crash logs found in test_data")

    # Create a test directory with multiple copies for performance testing
    test_logs_dir = tmp_path / "performance_test_logs"
    test_logs_dir.mkdir()

    crash_log_files = []

    # Create 50 crash log files by duplicating and modifying samples
    for i in range(50):
        sample_file = sample_files[i % len(sample_files)]

        # Create unique filename
        dest_file = test_logs_dir / f"crash_{i:03d}_{sample_file.name}"

        # Copy the file
        shutil.copy2(sample_file, dest_file)

        # Optionally modify the content slightly to simulate variation
        content = dest_file.read_text(encoding="utf-8", errors="ignore")
        # Add a unique identifier to make each file slightly different
        modified_content = f"# Test Log {i:03d}\n" + content
        dest_file.write_text(modified_content, encoding="utf-8")

        crash_log_files.append(dest_file)

    return crash_log_files


@pytest.fixture
def small_performance_test_logs(tmp_path: Path, sample_crash_logs_dir: Path) -> list[Path]:
    """
    Create a smaller set of crash logs for quick performance tests.

    Args:
        tmp_path: Pytest's temporary directory fixture
        sample_crash_logs_dir: Path to sample crash logs

    Returns:
        List of 20 crash log files for testing
    """
    # Get sample crash log files
    sample_files = list(sample_crash_logs_dir.glob("*.log"))
    if not sample_files:
        pytest.skip("No sample crash logs found in test_data")

    # Create a test directory with multiple copies for performance testing
    test_logs_dir = tmp_path / "small_performance_test_logs"
    test_logs_dir.mkdir()

    crash_log_files = []

    # Create 20 crash log files
    for i in range(20):
        sample_file = sample_files[i % len(sample_files)]
        dest_file = test_logs_dir / f"crash_{i:03d}_{sample_file.name}"
        shutil.copy2(sample_file, dest_file)

        # Add unique content
        content = dest_file.read_text(encoding="utf-8", errors="ignore")
        modified_content = f"# Small Test Log {i:03d}\n" + content
        dest_file.write_text(modified_content, encoding="utf-8")

        crash_log_files.append(dest_file)

    return crash_log_files


@pytest.fixture
def minimal_performance_test_logs(sample_crash_logs_dir: Path) -> list[Path]:
    """
    Provide minimal set of crash logs (just the samples themselves).

    This is useful for tests that need at least some crash logs
    but don't need many files.

    Args:
        sample_crash_logs_dir: Path to sample crash logs

    Returns:
        List of sample crash log files
    """
    sample_files = list(sample_crash_logs_dir.glob("*.log"))
    if len(sample_files) < 2:
        pytest.skip("Not enough sample crash logs for testing")
    return sample_files
