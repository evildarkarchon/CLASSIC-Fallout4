"""Pastebin Service for CLASSIC TUI.

Async fetch of Pastebin content using existing backend.
"""

from pathlib import Path

from ClassicLib.Utils.web_utils import async_pastebin_fetch


class PastebinService:
    """Service for fetching Pastebin content.

    Wraps existing pastebin functionality from ClassicLib for TUI use.
    Provides async methods compatible with Textual's Worker API.
    """

    @staticmethod
    async def fetch(url_or_id: str) -> Path | None:
        """Fetch content from a Pastebin URL or ID.

        Downloads raw content from various pastebin services and saves it
        to the Crash Logs/Pastebin directory.

        Args:
            url_or_id: Full URL or paste ID to fetch.

        Returns:
            Path to downloaded file if successful, None otherwise.

        """
        # Normalize input - if it's just an ID, construct the URL
        url = f"https://pastebin.com/{url_or_id}" if not url_or_id.startswith(("http://", "https://")) else url_or_id

        # Call the existing async implementation
        result = await async_pastebin_fetch(url)

        if result is not None:
            # async_pastebin_fetch returns the content, but it also
            # saves to file. We need to return the file path.
            # Extract paste ID to construct the file path
            from urllib.parse import urlparse

            parsed = urlparse(url)
            paste_id = parsed.path.split("/")[-1]
            paste_id = paste_id.removeprefix("raw/")

            output_file = Path.cwd() / "Crash Logs" / "Pastebin" / f"crash-{paste_id}.log"
            if output_file.exists():
                return output_file

        return None
