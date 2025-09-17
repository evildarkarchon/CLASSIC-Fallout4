"""
Pytest configuration file for CLASSIC-Fallout4 test suite.

This minimal configuration file imports organized fixtures from subdirectories
and defines test type markers for selective test execution.
"""

import sys
from pathlib import Path

import pytest

# Ensure the parent directory is in sys.path so imports work correctly
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all fixtures from the organized modules
# This makes them available to all test files
from tests.fixtures.async_fixtures import *  # noqa: F403, F401
from tests.fixtures.data_fixtures import *  # noqa: F403, F401
from tests.fixtures.database_pool_fixtures import *  # noqa: F403, F401
from tests.fixtures.mock_fixtures import *  # noqa: F403, F401
from tests.fixtures.qt_fixtures import *  # noqa: F403, F401
from tests.fixtures.registry_fixtures import *  # noqa: F403, F401
from tests.fixtures.version_cache_fixtures import *  # noqa: F403, F401


def pytest_configure(config):
    """Register custom markers for test types."""
    # Test type markers for selective execution
    config.addinivalue_line(
        "markers",
        "unit: Fast unit tests with mocked dependencies (< 100ms)"
    )
    config.addinivalue_line(
        "markers",
        "integration: Tests with real I/O and multiple components"
    )
    config.addinivalue_line(
        "markers",
        "e2e: Full workflow tests from entry point to output"
    )

    # Component-specific markers
    config.addinivalue_line(
        "markers",
        "async_test: Tests that use async/await patterns"
    )
    config.addinivalue_line(
        "markers",
        "gui: Tests that require Qt/PySide6 GUI components"
    )
    config.addinivalue_line(
        "markers",
        "tui: Tests for the Textual Terminal UI"
    )
    config.addinivalue_line(
        "markers",
        "performance: Performance benchmarks and regression tests"
    )
    config.addinivalue_line(
        "markers",
        "slow: Tests that take > 1 second to run"
    )
    config.addinivalue_line(
        "markers",
        "network: Tests that require network access"
    )
    config.addinivalue_line(
        "markers",
        "database: Tests that interact with databases"
    )


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

        # Auto-mark TUI tests
        if "tui" in item.nodeid.lower() or "textual" in item.nodeid.lower():
            item.add_marker(pytest.mark.tui)

        # Auto-mark performance tests
        if "performance" in item.nodeid.lower() or "benchmark" in item.nodeid.lower():
            item.add_marker(pytest.mark.performance)


# Pytest configuration options
def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests"
    )
    parser.addoption(
        "--run-network",
        action="store_true",
        default=False,
        help="Run tests that require network access"
    )


def pytest_runtest_setup(item):
    """Skip tests based on markers and command line options."""
    # Skip slow tests unless --run-slow is specified
    if "slow" in item.keywords and not item.config.getoption("--run-slow"):
        pytest.skip("Need --run-slow option to run slow tests")

    # Skip network tests unless --run-network is specified
    if "network" in item.keywords and not item.config.getoption("--run-network"):
        pytest.skip("Need --run-network option to run network tests")
