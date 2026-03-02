"""Pytest configuration and fixtures for parity tests.

This module provides fixtures and configuration specific to parity validation
tests between Rust and Python implementations.

Fixtures:
    rust_parser: Rust parser instance from factory
    sample_logs_dir: Path to sample crash logs directory
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from ClassicLib.integration.factory import get_parser

if TYPE_CHECKING:
    from ClassicLib.integration.types import LogParserProtocol


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
