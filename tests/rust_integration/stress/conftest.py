"""Rust integration stress test configuration with autouse cleanup.

This conftest.py applies the cleanup_after_stress_test fixture as autouse
only for tests in this directory, preventing the cleanup overhead from
affecting the entire test suite.
"""

import pytest

from tests.fixtures.stress_fixtures import cleanup_after_stress_test as _cleanup_impl


@pytest.fixture(autouse=True)
def cleanup_after_stress_test():
    """Automatic cleanup after each stress test to prevent pollution.

    This autouse fixture wraps the shared cleanup implementation and
    applies it only to tests in tests/rust_integration/stress/.
    """
    yield from _cleanup_impl()
