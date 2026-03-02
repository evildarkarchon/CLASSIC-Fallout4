"""
Test suite for network operation utility functions in ClassicLib/Util.py.

This module contains tests for network-related operations such as
fetching content from Pastebin.
"""

# ruff: noqa: ANN001, ANN002, ANN003, RUF100, ANN201, ANN204, ANN202, ARG001, PT011, ARG002, PLR0913, F841
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from ClassicLib.Utils.web_utils import pastebin_fetch

# Message handler fixture is imported via conftest automatically

pytestmark = [pytest.mark.unit]


class TestPastebinOperations:
    """Tests for Pastebin fetching operations."""

    @pytest.fixture(autouse=True)
    def setup_message_handler(self, init_message_handler_fixture):
        """Ensure MessageHandler is initialized for all tests."""

    @patch("requests.get")
    def test_pastebin_fetch_success(self, mock_get: MagicMock, tmp_path: Path, monkeypatch) -> None:
        """Test pastebin_fetch with successful request."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Sample crash log content"
        mock_get.return_value = mock_response

        # Change to temp directory for complete isolation
        monkeypatch.chdir(tmp_path)

        # Create the directory structure that pastebin_fetch expects
        crash_logs_dir = tmp_path / "Crash Logs" / "Pastebin"
        crash_logs_dir.mkdir(parents=True, exist_ok=True)

        url = "https://pastebin.com/abc123"
        pastebin_fetch(url)

        # Check if file was created
        expected_file = crash_logs_dir / "crash-abc123.log"
        assert expected_file.exists()
        assert expected_file.read_text() == "Sample crash log content"

    @patch("requests.get")
    def test_pastebin_fetch_raw_url_conversion(self, mock_get: MagicMock, tmp_path: Path, monkeypatch) -> None:
        """Test pastebin_fetch converts regular URL to raw URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "content"
        mock_get.return_value = mock_response

        # Use monkeypatch for proper isolation
        monkeypatch.chdir(tmp_path)

        # Create the directory structure that pastebin_fetch expects
        crash_logs_dir = tmp_path / "Crash Logs" / "Pastebin"
        crash_logs_dir.mkdir(parents=True, exist_ok=True)

        url = "https://pastebin.com/abc123"  # Not raw URL
        pastebin_fetch(url)

        # Should have called with raw URL
        expected_url = "https://pastebin.com/raw/abc123"
        mock_get.assert_called_once_with(expected_url, timeout=10)

    @patch("requests.get")
    def test_pastebin_fetch_http_error(self, mock_get: MagicMock) -> None:
        """Test pastebin_fetch with HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        url = "https://pastebin.com/nonexistent"

        with pytest.raises(requests.HTTPError):
            pastebin_fetch(url)

    @patch("requests.get")
    def test_pastebin_fetch_already_raw_url(self, mock_get: MagicMock, tmp_path: Path, monkeypatch) -> None:
        """Test pastebin_fetch with already raw URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "raw content"
        mock_get.return_value = mock_response

        monkeypatch.chdir(tmp_path)
        crash_logs_dir = tmp_path / "Crash Logs" / "Pastebin"
        crash_logs_dir.mkdir(parents=True, exist_ok=True)

        url = "https://pastebin.com/raw/abc123"
        pastebin_fetch(url)

        # Should use URL as-is
        mock_get.assert_called_once_with(url, timeout=10)

    @patch("requests.get")
    def test_pastebin_fetch_timeout(self, mock_get: MagicMock) -> None:
        """Test pastebin_fetch with timeout error."""
        mock_get.side_effect = requests.Timeout("Connection timeout")

        url = "https://pastebin.com/abc123"

        with pytest.raises(requests.Timeout):
            pastebin_fetch(url)

    @patch("requests.get")
    def test_pastebin_fetch_connection_error(self, mock_get: MagicMock) -> None:
        """Test pastebin_fetch with connection error."""
        mock_get.side_effect = requests.ConnectionError("Connection failed")

        url = "https://pastebin.com/abc123"

        with pytest.raises(requests.ConnectionError):
            pastebin_fetch(url)

    @patch("requests.get")
    def test_pastebin_fetch_empty_content(self, mock_get: MagicMock, tmp_path: Path, monkeypatch) -> None:
        """Test pastebin_fetch with empty response content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_get.return_value = mock_response

        monkeypatch.chdir(tmp_path)
        crash_logs_dir = tmp_path / "Crash Logs" / "Pastebin"
        crash_logs_dir.mkdir(parents=True, exist_ok=True)

        url = "https://pastebin.com/abc123"
        pastebin_fetch(url)

        expected_file = crash_logs_dir / "crash-abc123.log"
        assert expected_file.exists()
        assert expected_file.read_text() == ""

    @patch("requests.get")
    def test_pastebin_fetch_special_characters_in_id(self, mock_get: MagicMock, tmp_path: Path, monkeypatch) -> None:
        """Test pastebin_fetch with special characters in paste ID."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "content"
        mock_get.return_value = mock_response

        monkeypatch.chdir(tmp_path)
        crash_logs_dir = tmp_path / "Crash Logs" / "Pastebin"
        crash_logs_dir.mkdir(parents=True, exist_ok=True)

        url = "https://pastebin.com/ABC_123-xyz"
        pastebin_fetch(url)

        # Should handle special characters in filename
        expected_file = crash_logs_dir / "crash-ABC_123-xyz.log"
        assert expected_file.exists()


if __name__ == "__main__":
    pytest.main([__file__])
