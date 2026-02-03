"""Pytest configuration for golden file tests.

Imports golden_file fixture and adds --update-golden option.
"""

from tests.fixtures.golden_fixtures import golden_file, pytest_addoption

__all__ = ["golden_file", "pytest_addoption"]
