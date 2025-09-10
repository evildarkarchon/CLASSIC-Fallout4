"""Web and network utilities."""

import asyncio
from urllib.parse import urlparse

import aiohttp
import requests

from ClassicLib import msg_error, msg_info


def pastebin_fetch(url: str) -> None:
    """
    Fetches and displays content from a pastebin URL.

    Downloads raw content from various pastebin services and displays it
    to the user. Handles URL conversion to raw format for supported services.

    Args:
        url: URL of the pastebin to fetch

    Returns:
        None
    """
    # Parse the URL
    parsed_url = urlparse(url)

    # Convert to raw URL if needed
    raw_url = url

    # Handle different pastebin services
    if "pastebin.com" in parsed_url.netloc:
        # Convert pastebin.com URLs to raw format
        if "/raw/" not in parsed_url.path:
            paste_id = parsed_url.path.split("/")[-1]
            raw_url = f"https://pastebin.com/raw/{paste_id}"
    elif "paste.ee" in parsed_url.netloc:
        # Convert paste.ee URLs to raw format
        if "/r/" not in parsed_url.path:
            paste_id = parsed_url.path.split("/")[-1]
            raw_url = f"https://paste.ee/r/{paste_id}"
    elif "hastebin.com" in parsed_url.netloc or "haste.zneix.eu" in parsed_url.netloc:
        # Convert hastebin URLs to raw format
        if "/raw/" not in parsed_url.path:
            paste_id = parsed_url.path.split("/")[-1].replace(".txt", "")
            raw_url = f"{parsed_url.scheme}://{parsed_url.netloc}/raw/{paste_id}"

    try:
        # Fetch the content
        response = requests.get(raw_url, timeout=10)
        response.raise_for_status()

        # Display the content
        content = response.text
        msg_info(f"Fetched content from {url}:\n\n{content}")

    except requests.RequestException as e:
        msg_error(f"Failed to fetch pastebin content: {e}")
    except Exception as e:  # noqa: BLE001
        msg_error(f"Unexpected error fetching pastebin: {e}")


async def async_pastebin_fetch(url: str) -> str | None:
    """
    Asynchronously fetches content from a pastebin URL.

    Downloads raw content from various pastebin services.
    Handles URL conversion to raw format for supported services.

    Args:
        url: URL of the pastebin to fetch

    Returns:
        Content string if successful, None if failed
    """
    # Parse the URL
    parsed_url = urlparse(url)

    # Convert to raw URL if needed
    raw_url = url

    # Handle different pastebin services
    if "pastebin.com" in parsed_url.netloc:
        if "/raw/" not in parsed_url.path:
            paste_id = parsed_url.path.split("/")[-1]
            raw_url = f"https://pastebin.com/raw/{paste_id}"
    elif "paste.ee" in parsed_url.netloc:
        if "/r/" not in parsed_url.path:
            paste_id = parsed_url.path.split("/")[-1]
            raw_url = f"https://paste.ee/r/{paste_id}"
    elif "hastebin.com" in parsed_url.netloc or "haste.zneix.eu" in parsed_url.netloc:
        if "/raw/" not in parsed_url.path:
            paste_id = parsed_url.path.split("/")[-1].replace(".txt", "")
            raw_url = f"{parsed_url.scheme}://{parsed_url.netloc}/raw/{paste_id}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(raw_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                return await response.text()
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        msg_error(f"Failed to fetch pastebin content: {e}")
        return None
    except Exception as e:  # noqa: BLE001
        msg_error(f"Unexpected error fetching pastebin: {e}")
        return None
