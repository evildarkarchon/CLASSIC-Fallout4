"""Shared fixtures for registry tests."""
# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001

import pytest

from ClassicLib import GlobalRegistry


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear the registry before and after each test."""
    # Clear before test
    GlobalRegistry._registry.clear()
    yield
    # Clear after test
    GlobalRegistry._registry.clear()
