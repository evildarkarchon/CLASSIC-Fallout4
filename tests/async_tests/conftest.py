"""
Shared fixtures for async tests.

This file contains fixtures that are used across multiple async test files.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Import AsyncBridge fixtures for proper test isolation


@pytest.fixture
def mock_yamldata() -> MagicMock:
    """Create mock YAML data for testing."""
    mock = MagicMock()
    mock.scan_groups = {}
    mock.rules = []
    return mock


@pytest.fixture
def sample_crash_logs(tmp_path: Path) -> list[Path]:
    """Create sample crash log files for testing with realistic content."""
    crash_logs = []

    # Sample content based on actual Buffout 4 crash logs
    sample_content = b"""Fallout 4 v1.10.163
Buffout 4 v1.28.6

Unhandled exception "EXCEPTION_ACCESS_VIOLATION" at 0x7FF7D5058F6A Fallout4.exe+1AF8F6A

SYSTEM SPECS:
	OS: Microsoft Windows 11 Pro v10.0.22621
	CPU: AuthenticAMD AMD Ryzen 7 7800X3D 8-Core Processor
	GPU #1: Nvidia AD104 [GeForce RTX 4070]
	PHYSICAL MEMORY: 15.62 GB/63.15 GB

PROBABLE CALL STACK:
	[0] 0x7FF7D5058F6A Fallout4.exe+1AF8F6A
	[1] 0x7FF7D4058F6B Fallout4.exe+0AF8F6B

REGISTERS:
	RAX 0x0
	RCX 0x0
"""

    for i in range(5):
        log_file = tmp_path / f"crash-2023-09-15-0{i}.log"
        log_file.write_bytes(sample_content)
        crash_logs.append(log_file)
    return crash_logs


@pytest.fixture
def crash_log_files(tmp_path: Path) -> list[Path]:
    """Create test crash log files for batch processing tests."""
    crash_logs = []
    for i in range(3):
        log_file = tmp_path / f"crash_{i}.log"
        log_file.write_text("Test crash log content")
        crash_logs.append(log_file)
    return crash_logs
