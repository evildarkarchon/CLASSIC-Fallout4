"""Web and network utilities."""

import asyncio
from urllib.parse import urlparse

import aiohttp
import requests

from ClassicLib import msg_error, msg_info


def pastebin_fetch(url: str) -> None:
    """
    Fetches and saves content from a pastebin URL to a file.

    Downloads raw content from various pastebin services and saves it
    to a crash log file. Handles URL conversion to raw format for supported services.

    Args:
        url: URL of the pastebin to fetch

    Returns:
        None
    """
    from pathlib import Path

    # Parse the URL
    parsed_url = urlparse(url)

    # Extract paste ID for filename
    paste_id = parsed_url.path.split("/")[-1]
    if paste_id.startswith("raw/"):
        paste_id = paste_id[4:]  # Remove "raw/" prefix

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

        # Save content to file
        content = response.text

        # Create directory structure
        crash_logs_dir = Path.cwd() / "Crash Logs" / "Pastebin"
        crash_logs_dir.mkdir(parents=True, exist_ok=True)

        # Save to file
        output_file = crash_logs_dir / f"crash-{paste_id}.log"
        output_file.write_text(content, encoding="utf-8")

        msg_info(f"Downloaded pastebin content to: {output_file}")

    except requests.RequestException as e:
        msg_error(f"Failed to fetch pastebin content: {e}")
        raise
    except Exception as e:  # noqa: BLE001
        msg_error(f"Unexpected error fetching pastebin: {e}")
        raise


async def async_pastebin_fetch(url: str) -> str | None:
    """
    Asynchronously fetches and saves content from a pastebin URL.

    Downloads raw content from various pastebin services and saves it to a file.
    Handles URL conversion to raw format for supported services.

    Args:
        url: URL of the pastebin to fetch

    Returns:
        Content string if successful, None if failed
    """
    from pathlib import Path

    # Parse the URL
    parsed_url = urlparse(url)

    # Extract paste ID for filename
    paste_id = parsed_url.path.split("/")[-1]
    if paste_id.startswith("raw/"):
        paste_id = paste_id[4:]  # Remove "raw/" prefix

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
                content = await response.text()

                # Save content to file
                crash_logs_dir = Path.cwd() / "Crash Logs" / "Pastebin"
                crash_logs_dir.mkdir(parents=True, exist_ok=True)

                # Save to file
                output_file = crash_logs_dir / f"crash-{paste_id}.log"
                output_file.write_text(content, encoding="utf-8")

                msg_info(f"Downloaded pastebin content to: {output_file}")
                return content
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        msg_error(f"Failed to fetch pastebin content: {e}")
        return None
    except Exception as e:  # noqa: BLE001
        msg_error(f"Unexpected error fetching pastebin: {e}")
        return None
