"""
Unit tests for async_util - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

import pytest

from ClassicLib.AsyncUtil import get_encoding_detection_available

pytestmark = pytest.mark.unit

class TestAsyncEncodingDetection:
    """Test cases for async encoding detection utilities."""

    def test_encoding_detection_available(self) -> None:
        """Test checking if async encoding detection is available."""
        assert get_encoding_detection_available() is True
