"""Stress test configuration with autouse cleanup.

This conftest.py applies the cleanup_after_stress_test fixture as autouse
only for tests in this directory, preventing the cleanup overhead from
affecting the entire test suite.
"""

import pytest

from tests.fixtures.stress_fixtures import cleanup_after_stress_test


@pytest.fixture(autouse=True)
def _autouse_cleanup_after_stress_test(cleanup_after_stress_test):
    """Automatic cleanup after each stress test to prevent pollution.

    This autouse fixture ensures the shared cleanup_after_stress_test fixture
    is applied to all tests in tests/stress/.
    """
    pass
