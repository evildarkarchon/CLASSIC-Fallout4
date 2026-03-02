"""Unit tests for web_utils module.

This module tests the pastebin fetching utilities:
- pastebin_fetch (synchronous)
- async_pastebin_fetch (asynchronous)
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]

from ClassicLib.Utils.web_utils import async_pastebin_fetch, pastebin_fetch


class TestPastebinFetchURLParsing:
    """Test URL parsing logic for pastebin_fetch."""

    @patch("ClassicLib.Utils.web_utils.requests.get")
    @patch("ClassicLib.Utils.web_utils.msg_info")
    def test_pastebin_com_url_converts_to_raw(
        self, mock_info: MagicMock, mock_get: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that pastebin.com URLs are converted to raw format."""
        mock_response = MagicMock()
        mock_response.text = "Test content"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        monkeypatch.chdir(tmp_path)
        pastebin_fetch("https://pastebin.com/abc123")

        # Check that raw URL was called
        call_args = mock_get.call_args
        assert "raw" in call_args[0][0]

    @patch("ClassicLib.Utils.web_utils.requests.get")
    @patch("ClassicLib.Utils.web_utils.msg_info")
    def test_paste_ee_url_converts_to_raw(
        self, mock_info: MagicMock, mock_get: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that paste.ee URLs are converted to raw format."""
        mock_response = MagicMock()
        mock_response.text = "Test content"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        monkeypatch.chdir(tmp_path)
        pastebin_fetch("https://paste.ee/p/xyz789")

        # Check that /r/ was added
        call_args = mock_get.call_args
        assert "/r/" in call_args[0][0]

    @patch("ClassicLib.Utils.web_utils.requests.get")
    @patch("ClassicLib.Utils.web_utils.msg_info")
    def test_hastebin_url_converts_to_raw(
        self, mock_info: MagicMock, mock_get: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that hastebin.com URLs are converted to raw format."""
        mock_response = MagicMock()
        mock_response.text = "Test content"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        monkeypatch.chdir(tmp_path)
        pastebin_fetch("https://hastebin.com/abcdef")

        call_args = mock_get.call_args
        assert "raw" in call_args[0][0]

    @patch("ClassicLib.Utils.web_utils.requests.get")
    @patch("ClassicLib.Utils.web_utils.msg_info")
    def test_haste_zneix_url_converts_to_raw(
        self, mock_info: MagicMock, mock_get: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that haste.zneix.eu URLs are converted to raw format."""
        mock_response = MagicMock()
        mock_response.text = "Test content"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        monkeypatch.chdir(tmp_path)
        pastebin_fetch("https://haste.zneix.eu/testpaste")

        call_args = mock_get.call_args
        assert "raw" in call_args[0][0]


class TestPastebinFetchFileSaving:
    """Test file saving logic for pastebin_fetch."""

    @patch("ClassicLib.Utils.web_utils.requests.get")
    @patch("ClassicLib.Utils.web_utils.msg_info")
    def test_creates_directory_structure(
        self, mock_info: MagicMock, mock_get: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that Crash Logs/Pastebin directory is created."""
        mock_response = MagicMock()
        mock_response.text = "Test content"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        monkeypatch.chdir(tmp_path)
        pastebin_fetch("https://pastebin.com/raw/test123")

        expected_dir = tmp_path / "Crash Logs" / "Pastebin"
        assert expected_dir.exists()

    @patch("ClassicLib.Utils.web_utils.requests.get")
    @patch("ClassicLib.Utils.web_utils.msg_info")
    def test_saves_content_to_file(
        self, mock_info: MagicMock, mock_get: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that fetched content is saved to file."""
        mock_response = MagicMock()
        mock_response.text = "Crash log content here"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        monkeypatch.chdir(tmp_path)
        pastebin_fetch("https://pastebin.com/raw/myPaste")

        # Check file was created with content
        saved_file = tmp_path / "Crash Logs" / "Pastebin" / "crash-myPaste.log"
        assert saved_file.exists()
        assert saved_file.read_text(encoding="utf-8") == "Crash log content here"


class TestPastebinFetchErrorHandling:
    """Test error handling for pastebin_fetch."""

    @patch("ClassicLib.Utils.web_utils.requests.get")
    @patch("ClassicLib.Utils.web_utils.msg_error")
    def test_raises_on_request_exception(self, mock_error: MagicMock, mock_get: MagicMock) -> None:
        """Test that request exceptions are raised and logged."""
        import requests

        mock_get.side_effect = requests.RequestException("Network error")

        with pytest.raises(requests.RequestException):
            pastebin_fetch("https://pastebin.com/abc123")

        mock_error.assert_called_once()

    @patch("ClassicLib.Utils.web_utils.requests.get")
    @patch("ClassicLib.Utils.web_utils.msg_error")
    def test_raises_on_general_exception(self, mock_error: MagicMock, mock_get: MagicMock) -> None:
        """Test that general exceptions are raised and logged."""
        mock_response = MagicMock()
        mock_response.text = "content"
        mock_response.raise_for_status.side_effect = Exception("Unexpected error")
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Unexpected error"):
            pastebin_fetch("https://pastebin.com/abc123")


class TestAsyncPastebinFetch:
    """Test async_pastebin_fetch function."""

    @pytest.mark.asyncio
    async def test_returns_content_on_success(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that async fetch returns content on success."""
        monkeypatch.chdir(tmp_path)

        with (
            patch("ClassicLib.Utils.web_utils.aiohttp.ClientSession") as mock_client,
            patch("ClassicLib.Utils.web_utils.msg_info"),
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None

            mock_resp = AsyncMock()
            mock_resp.text = AsyncMock(return_value="Async content")
            mock_resp.raise_for_status = MagicMock()

            mock_get_ctx = AsyncMock()
            mock_get_ctx.__aenter__.return_value = mock_resp
            mock_get_ctx.__aexit__.return_value = None

            mock_ctx.get = MagicMock(return_value=mock_get_ctx)
            mock_client.return_value = mock_ctx

            result = await async_pastebin_fetch("https://pastebin.com/raw/test123")

            assert result == "Async content"

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self) -> None:
        """Test that async fetch returns None on timeout."""
        with patch("ClassicLib.Utils.web_utils.aiohttp.ClientSession") as mock_client:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_ctx.get = MagicMock(side_effect=TimeoutError("Timeout"))
            mock_client.return_value = mock_ctx

            with patch("ClassicLib.Utils.web_utils.msg_error"):
                result = await async_pastebin_fetch("https://pastebin.com/test")

                assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_client_error(self) -> None:
        """Test that async fetch returns None on aiohttp client error."""
        import aiohttp

        with patch("ClassicLib.Utils.web_utils.aiohttp.ClientSession") as mock_client:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_ctx.get = MagicMock(side_effect=aiohttp.ClientError("Connection failed"))
            mock_client.return_value = mock_ctx

            with patch("ClassicLib.Utils.web_utils.msg_error"):
                result = await async_pastebin_fetch("https://pastebin.com/test")

                assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_unexpected_exception(self) -> None:
        """Test that async fetch returns None on unexpected exception."""
        with patch("ClassicLib.Utils.web_utils.aiohttp.ClientSession") as mock_client:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_ctx.get = MagicMock(side_effect=RuntimeError("Unexpected"))
            mock_client.return_value = mock_ctx

            with patch("ClassicLib.Utils.web_utils.msg_error"):
                result = await async_pastebin_fetch("https://pastebin.com/test")

                assert result is None


class TestAsyncPastebinFetchURLParsing:
    """Test URL parsing in async_pastebin_fetch."""

    @pytest.mark.asyncio
    async def test_pastebin_com_url_parsed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test pastebin.com URL is correctly parsed."""
        monkeypatch.chdir(tmp_path)

        with (
            patch("ClassicLib.Utils.web_utils.aiohttp.ClientSession") as mock_client,
            patch("ClassicLib.Utils.web_utils.msg_info"),
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None

            mock_resp = AsyncMock()
            mock_resp.text = AsyncMock(return_value="content")
            mock_resp.raise_for_status = MagicMock()

            mock_get_ctx = AsyncMock()
            mock_get_ctx.__aenter__.return_value = mock_resp
            mock_get_ctx.__aexit__.return_value = None

            mock_ctx.get = MagicMock(return_value=mock_get_ctx)
            mock_client.return_value = mock_ctx

            await async_pastebin_fetch("https://pastebin.com/abc123")

            # Check get was called with raw URL
            call_args = mock_ctx.get.call_args
            assert "raw" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_paste_ee_url_parsed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test paste.ee URL is correctly parsed."""
        monkeypatch.chdir(tmp_path)

        with (
            patch("ClassicLib.Utils.web_utils.aiohttp.ClientSession") as mock_client,
            patch("ClassicLib.Utils.web_utils.msg_info"),
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None

            mock_resp = AsyncMock()
            mock_resp.text = AsyncMock(return_value="content")
            mock_resp.raise_for_status = MagicMock()

            mock_get_ctx = AsyncMock()
            mock_get_ctx.__aenter__.return_value = mock_resp
            mock_get_ctx.__aexit__.return_value = None

            mock_ctx.get = MagicMock(return_value=mock_get_ctx)
            mock_client.return_value = mock_ctx

            await async_pastebin_fetch("https://paste.ee/p/xyz123")

            # Check get was called with /r/ URL
            call_args = mock_ctx.get.call_args
            assert "/r/" in call_args[0][0]
