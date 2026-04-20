"""Verify every manifest `download_url` is reachable anonymously.

Runs after the GitHub release is promoted out of draft but before the
``manifest-latest.json`` pointer is pushed to ``gh-pages``. Anonymous
download of release assets only becomes possible once the release is
non-draft, so this step is the gate that tells the workflow "assets are
genuinely fetchable" before any client-visible Pages update fires.

Without this check the publish flow is split-brain-prone: if
``gh release edit --draft=false`` succeeds but the client-facing URL is
still propagating (or GitHub Releases is having a bad minute), Pages
clients seeing the new ``release_tag`` will 404 on every asset download.
That failure mode is exactly the one the yaml-update-delivery change's
Codex adversarial review flagged as ``high`` severity.

Anonymous probing
-----------------

The request is deliberately unauthenticated: no ``Authorization`` header
is attached even when ``$GITHUB_TOKEN`` is present in the environment.
Clients consuming the published manifest will not authenticate either —
the whole point is to catch the case where the operator happened to have
auth available locally but a real client would not.

Each URL is probed with a ranged 1-byte GET (``Range: bytes=0-0``) rather
than HEAD. Some GitHub CDN redirects do not support HEAD reliably, but a
ranged GET is cheap (one byte + redirect overhead) and exercises the
exact code path clients use.

Exit status
-----------

- 0 on first attempt where every URL returns 200 or 206.
- Non-zero after the retry budget is exhausted, with a per-URL diagnostic
  printed to stderr so the workflow log names the offending asset.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_POLL_INTERVAL_SECONDS = 8
# Per-request socket timeout. Short enough to iterate through several URLs
# without burning the whole retry budget on one stuck connection.
DEFAULT_SOCKET_TIMEOUT_SECONDS = 15

# Ranged GET for a single byte — smallest request that still exercises the
# same redirect chain clients use. 200 is the non-redirected response (rare
# on GitHub release assets), 206 is the expected partial-content response
# after the CDN redirect.
_OK_STATUS = {200, 206}


def _anonymous_reachable(url: str, socket_timeout: float) -> tuple[bool, str]:
    """Return ``(ok, diagnostic)`` for one URL.

    ``ok`` is True iff the URL is reachable without credentials. ``diagnostic``
    is a short human-readable reason for workflow logs — empty on success.
    """
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Range": "bytes=0-0",
            "Accept": "*/*",
            "User-Agent": "classic-publish-yaml-data/verify-assets",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=socket_timeout) as resp:
            status = resp.status
            if status in _OK_STATUS:
                return True, ""
            return False, f"HTTP {status}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError) as exc:
        return False, f"network error: {exc!r}"


def _load_download_urls(manifest_path: Path) -> list[tuple[str, str]]:
    """Return ``[(name, download_url), ...]`` from a manifest.json file."""
    with manifest_path.open("r", encoding="utf-8") as f:
        doc = json.load(f)
    files = doc.get("files")
    if not isinstance(files, list) or not files:
        raise SystemExit(
            f"FAIL: {manifest_path} has no non-empty 'files' array"
        )
    pairs: list[tuple[str, str]] = []
    for entry in files:
        if not isinstance(entry, dict):
            raise SystemExit(f"FAIL: manifest entry is not a mapping: {entry!r}")
        name = entry.get("name")
        url = entry.get("download_url")
        if not isinstance(name, str) or not isinstance(url, str):
            raise SystemExit(
                f"FAIL: manifest entry missing string name/download_url: {entry!r}"
            )
        pairs.append((name, url))
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to the generated manifest.json",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Total retry budget across all URLs (default: 120)",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help="Wait between full-sweep retries (default: 8)",
    )
    parser.add_argument(
        "--socket-timeout-seconds",
        type=int,
        default=DEFAULT_SOCKET_TIMEOUT_SECONDS,
        help="Per-request socket timeout (default: 15)",
    )
    args = parser.parse_args()

    urls = _load_download_urls(args.manifest)
    deadline = time.monotonic() + args.timeout_seconds

    # Sweep all URLs each attempt rather than failing on the first one; a
    # single offender on an N-file manifest should surface clearly instead
    # of hiding behind a generic "one of these failed" message.
    attempt = 0
    while True:
        attempt += 1
        failures: list[tuple[str, str, str]] = []
        for name, url in urls:
            ok, diag = _anonymous_reachable(url, args.socket_timeout_seconds)
            if not ok:
                failures.append((name, url, diag))

        if not failures:
            print(
                f"OK: all {len(urls)} asset URL(s) reachable anonymously "
                f"(attempt {attempt})"
            )
            return 0

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break

        print(
            f"retrying: attempt {attempt}, {len(failures)}/{len(urls)} asset(s) "
            f"not yet reachable, {int(remaining)}s remaining",
            file=sys.stderr,
        )
        for name, url, diag in failures:
            print(f"  - {name}: {diag} ({url})", file=sys.stderr)
        time.sleep(min(args.poll_interval_seconds, max(1, int(remaining))))

    print(
        f"FAIL: {len(failures)} of {len(urls)} asset URL(s) still unreachable "
        f"after {args.timeout_seconds}s:",
        file=sys.stderr,
    )
    for name, url, diag in failures:
        print(f"  - {name}: {diag} ({url})", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
