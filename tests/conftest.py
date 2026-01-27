"""
Pytest configuration file for CLASSIC-Fallout4 test suite.

This minimal configuration file imports organized fixtures from subdirectories
and defines test type markers for selective test execution.
"""

# Python 3.13 compatibility patch for pyffi
# pyffi uses time.clock() which was removed in Python 3.8+
import time

if not hasattr(time, "clock"):
    # Monkey-patch time.clock for compatibility with old libraries
    time.clock = time.perf_counter  # pyright: ignore[reportAttributeAccessIssue]

import sys
from pathlib import Path

import pytest

# Ensure the parent directory is in sys.path so imports work correctly
sys.path.insert(0, str(Path(__file__).parent.parent))

# Force offscreen Qt platform for headless testing
import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Import all fixtures from the organized modules
# This makes them available to all test files

# Core fixtures
from tests.fixtures.async_fixtures import *  # noqa: F403

# Phase 2 consolidated fixtures (fixture consolidation task)
from tests.fixtures.backup_fixtures import *  # noqa: F403
from tests.fixtures.concurrency_fixtures import *  # noqa: F403

# Consolidated fixture modules (Phase 1 consolidation)
from tests.fixtures.crash_log_fixtures import *  # noqa: F403
from tests.fixtures.data_fixtures import *  # noqa: F403
from tests.fixtures.database_pool_fixtures import *  # noqa: F403
from tests.fixtures.fcx_fixtures import *  # noqa: F403
from tests.fixtures.game_fixtures import *  # noqa: F403
from tests.fixtures.gui_settings_fixtures import *  # noqa: F403
from tests.fixtures.io_fixtures import *  # noqa: F403
from tests.fixtures.mock_fixtures import *  # noqa: F403
from tests.fixtures.mods_fixtures import *  # noqa: F403
from tests.fixtures.parity_fixtures import *  # noqa: F403
from tests.fixtures.performance_fixtures import *  # noqa: F403
from tests.fixtures.qt_fixtures import *  # noqa: F403
from tests.fixtures.registry_fixtures import *  # noqa: F403
from tests.fixtures.rust_fixtures import *  # noqa: F403

# Scanlog fixtures (orchestrator, parser fixtures)
from tests.fixtures.scanlog_fixtures import *  # noqa: F403
from tests.fixtures.stress_fixtures import *  # noqa: F403
from tests.fixtures.version_cache_fixtures import *  # noqa: F403
from tests.fixtures.yaml_fixtures import *  # noqa: F403
from tests.fixtures.yamldata_fixtures import *  # noqa: F403


def pytest_configure(config):
    """Register custom markers for test types."""
    # Test type markers for selective execution
    config.addinivalue_line("markers", "unit: Fast unit tests with mocked dependencies (< 100ms)")
    config.addinivalue_line("markers", "integration: Tests with real I/O and multiple components")
    config.addinivalue_line("markers", "e2e: Full workflow tests from entry point to output")

    # Component-specific markers
    config.addinivalue_line("markers", "async_test: Tests that use async/await patterns")
    config.addinivalue_line("markers", "gui: Tests that require Qt/PySide6 GUI components")
    config.addinivalue_line("markers", "performance: Performance benchmarks and regression tests")
    config.addinivalue_line("markers", "timing: Tests that are sensitive to execution time")
    config.addinivalue_line("markers", "slow: Tests that take > 1 second to run")
    config.addinivalue_line("markers", "network: Tests that require network access")
    config.addinivalue_line("markers", "database: Tests that interact with databases")

    # Stress testing markers
    config.addinivalue_line("markers", "stress: Comprehensive stress tests for production validation")
    config.addinivalue_line("markers", "memory: Memory usage, leak detection, and pressure tests")
    config.addinivalue_line("markers", "concurrency: Thread safety and race condition tests")
    config.addinivalue_line("markers", "error_recovery: Error handling and recovery tests")
    config.addinivalue_line("markers", "data_volume: Large dataset and scalability tests")


# Test collection configuration
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test characteristics."""
    for item in items:
        # Auto-mark async tests
        if "async" in item.nodeid.lower():
            item.add_marker(pytest.mark.async_test)

        # Auto-mark GUI tests
        if any(x in item.nodeid.lower() for x in ["gui", "qt", "pyside", "widget", "dialog"]):
            item.add_marker(pytest.mark.gui)

        # Auto-mark performance tests
        if "performance" in item.nodeid.lower() or "benchmark" in item.nodeid.lower() or "perf" in item.nodeid.lower():
            item.add_marker(pytest.mark.performance)

        # Auto-mark stress tests
        if "stress" in item.nodeid.lower():
            item.add_marker(pytest.mark.stress)

            # Auto-mark specific stress test types
            if "memory" in item.nodeid.lower():
                item.add_marker(pytest.mark.memory)
            if "concurrency" in item.nodeid.lower():
                item.add_marker(pytest.mark.concurrency)
            if "error_recovery" in item.nodeid.lower():
                item.add_marker(pytest.mark.error_recovery)
            if "data_volume" in item.nodeid.lower():
                item.add_marker(pytest.mark.data_volume)


# Pytest configuration options
def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption("--skip-slow", action="store_true", default=False, help="Skip slow tests")
    parser.addoption("--skip-network", action="store_true", default=False, help="Skip tests that require network access")
    parser.addoption("--skip-performance", action="store_true", default=False, help="Skip performance and benchmark tests")
    parser.addoption("--skip-stress", action="store_true", default=False, help="Skip stress tests")


def pytest_runtest_setup(item):
    """Skip tests based on markers and command line options."""
    # Skip timing-sensitive tests in CI environment
    if os.environ.get("CI", "false").lower() == "true":
        for marker in ["performance", "stress", "benchmark", "timing"]:
            if marker in item.keywords:
                pytest.skip(f"Skipping {marker} test in CI environment")

    # Skip slow tests if --skip-slow is specified
    if "slow" in item.keywords and item.config.getoption("--skip-slow"):
        pytest.skip("Skipping slow test (--skip-slow specified)")

    # Skip network tests if --skip-network is specified
    if "network" in item.keywords and item.config.getoption("--skip-network"):
        pytest.skip("Skipping network test (--skip-network specified)")

    # Skip performance tests if --skip-performance is specified
    if item.config.getoption("--skip-performance"):
        if any(marker in item.keywords for marker in ["performance", "benchmark", "timing"]):
            pytest.skip("Skipping performance test (--skip-performance specified)")

    # Skip stress tests if --skip-stress is specified
    if item.config.getoption("--skip-stress"):
        if any(marker in item.keywords for marker in ["stress", "memory", "concurrency", "error_recovery", "data_volume"]):
            pytest.skip("Skipping stress test (--skip-stress specified)")
