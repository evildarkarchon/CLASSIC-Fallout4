"""
Performance test fixtures for CLASSIC-Fallout4 test suite.

This module provides fixtures for performance tests, including crash log
generation and temporary file creation for benchmarking.

Consolidated from:
- tests/performance/conftest.py
"""

import shutil
from pathlib import Path

import pytest


@pytest.fixture
def perf_sample_crash_logs_dir() -> Path:
    """Provide path to sample crash logs directory.

    Returns:
        Path to the test_data/sample_crash_logs directory.
    """
    return Path(__file__).parent.parent / "test_data" / "sample_crash_logs"


@pytest.fixture
def perf_test_logs(tmp_path: Path, perf_sample_crash_logs_dir: Path) -> list[Path]:
    """Create multiple copies of sample crash logs for performance testing.

    This fixture creates 50 crash log files in a temporary directory
    to simulate a realistic workload without depending on production data.

    Args:
        tmp_path: Pytest's temporary directory fixture.
        perf_sample_crash_logs_dir: Path to sample crash logs.

    Returns:
        List of paths to crash log files for testing.
    """
    # Get sample crash log files
    sample_files = list(perf_sample_crash_logs_dir.glob("*.log"))
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
def perf_small_test_logs(tmp_path: Path, perf_sample_crash_logs_dir: Path) -> list[Path]:
    """Create a smaller set of crash logs for quick performance tests.

    Args:
        tmp_path: Pytest's temporary directory fixture.
        perf_sample_crash_logs_dir: Path to sample crash logs.

    Returns:
        List of 20 crash log files for testing.
    """
    # Get sample crash log files
    sample_files = list(perf_sample_crash_logs_dir.glob("*.log"))
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
def perf_minimal_test_logs(perf_sample_crash_logs_dir: Path) -> list[Path]:
    """Provide minimal set of crash logs (just the samples themselves).

    This is useful for tests that need at least some crash logs
    but don't need many files.

    Args:
        perf_sample_crash_logs_dir: Path to sample crash logs.

    Returns:
        List of sample crash log files.
    """
    sample_files = list(perf_sample_crash_logs_dir.glob("*.log"))
    if len(sample_files) < 2:
        pytest.skip("Not enough sample crash logs for testing")
    return sample_files


# Backward compatibility aliases (deprecated - use prefixed names)
sample_crash_logs_dir = perf_sample_crash_logs_dir
performance_test_logs = perf_test_logs
small_performance_test_logs = perf_small_test_logs
minimal_performance_test_logs = perf_minimal_test_logs


# ============================================================================
# Benchmark Fixtures (Consolidated from test_rust_ffi_performance.py)
# ============================================================================


@pytest.fixture
def complex_crash_log_path() -> Path:
    """Return path to complex crash log for benchmarking.

    Returns:
        Path to the complex crash log test file.
    """
    return Path("tests/test_data/sample_crash_logs/complex_crash.log")


@pytest.fixture
def complex_crash_log_lines(complex_crash_log_path: Path) -> list[str]:
    """Return lines of complex crash log for benchmarking.

    Includes a [Compatibility] header for default parser boundaries.

    Args:
        complex_crash_log_path: Path to the complex crash log.

    Returns:
        List of lines from the crash log with compatibility header.
    """
    if not complex_crash_log_path.exists():
        pytest.skip("Complex crash log not found")
    lines = complex_crash_log_path.read_text(encoding="utf-8").splitlines()
    # Ensure [Compatibility] exists for default parser boundaries
    return ["[Compatibility]"] + lines


@pytest.fixture
def test_settings_yaml_path() -> Path:
    """Return path to test settings yaml for benchmarking.

    Returns:
        Path to the test settings YAML file.
    """
    return Path("tests/test_data/sample_yaml/test_settings.yaml")
