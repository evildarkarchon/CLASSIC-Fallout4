"""
Unit tests for async_util - unit logic testing.

This file contains unit tests that test individual functions with mocked dependencies.
"""

import asyncio
import tempfile
from pathlib import Path
import pytest
from ClassicLib.AsyncUtil import detect_encoding_async, get_encoding_detection_available, open_file_with_encoding_async, read_file_with_encoding_async, read_lines_with_encoding_async

pytestmark = pytest.mark.unit

class TestAsyncEncodingDetection:
    """Test cases for async encoding detection utilities."""

    def test_encoding_detection_available(self) -> None:
        """Test checking if async encoding detection is available."""
        assert get_encoding_detection_available() is True
