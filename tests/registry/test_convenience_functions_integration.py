"""
Integration tests for convenience_functions - integration logic testing.

This file contains integration tests that test interactions between components.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ClassicLib import GlobalRegistry

pytestmark = pytest.mark.integration


class TestConvenienceFunctions:
    """Tests for GlobalRegistry convenience functions."""

    def test_open_file_with_encoding_function_registered(self, tmp_path: Path) -> None:
        """Test open_file_with_encoding when function is registered."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")
        mock_func = MagicMock()
        mock_func.return_value.__enter__ = MagicMock(return_value=MagicMock(read=lambda: "mocked content"))
        mock_func.return_value.__exit__ = MagicMock(return_value=None)
        GlobalRegistry.register(GlobalRegistry.Keys.OPEN_FILE_FUNC, mock_func)
        with GlobalRegistry.open_file_with_encoding(test_file) as f:
            f.read()
        mock_func.assert_called_once_with(test_file, "utf-8", "ignore")
