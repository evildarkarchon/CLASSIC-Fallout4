"""
Integration tests for path_validator - integration logic testing.

This file contains integration tests that test interactions between components.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from ClassicLib.PathValidator import PathValidator

pytestmark = pytest.mark.integration

class TestPathValidator:
    """Tests for the PathValidator class."""

    def test_is_valid_path_relative(self, tmp_path: Path, monkeypatch) -> None:
        """Test is_valid_path with relative paths."""
        monkeypatch.chdir(tmp_path)
        test_file = Path('test.txt')
        test_file.write_text('content')
        assert PathValidator.is_valid_path('test.txt') is True
        assert PathValidator.is_valid_path('./test.txt') is True
        assert PathValidator.is_valid_path(test_file) is True
        assert PathValidator.is_valid_path('nonexistent.txt') is False
