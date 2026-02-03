"""Pytest configuration and fixtures for parity tests.

This module provides fixtures and configuration specific to parity validation
tests between Rust and Python implementations.

Fixtures:
    parity_golden_dir: Path to golden files directory
    rust_parser: Rust parser instance from factory
    sample_logs_dir: Path to sample crash logs directory
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from ClassicLib.integration.factory import get_parser
from tests.fixtures.golden_fixtures import GOLDEN_DIR

if TYPE_CHECKING:
    from ClassicLib.integration.types import LogParserProtocol


@pytest.fixture
def parity_golden_dir() -> Path:
    """Path to golden files directory.

    Returns:
        Path to tests/golden/captured/ directory.
    """
    return GOLDEN_DIR


@pytest.fixture
def rust_parser() -> LogParserProtocol:
    """Get Rust parser from factory.

    Returns:
        Rust-accelerated log parser instance.
    """
    return get_parser()


@pytest.fixture
def sample_logs_dir() -> Path:
    """Path to sample crash logs directory.

    Returns:
        Path to sample_logs/FO4/ directory.
    """
    return Path(__file__).parent.parent.parent / "sample_logs" / "FO4"
