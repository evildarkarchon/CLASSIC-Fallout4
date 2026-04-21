"""Smoke-test the Pages-hosted manifest after a `yaml-data-v*` publish.

GitHub Pages deployment is eventually consistent — the new content can take
a minute or two to propagate after the workflow pushes to the `gh-pages`
branch. This script polls
``https://<owner>.github.io/<repo>/yaml-data/manifest-latest.json`` with
exponential-ish backoff and asserts the returned JSON's ``release_tag``
matches the tag that just triggered the publish.

Exit non-zero on any final mismatch or on total timeout — callers in the
workflow treat the exit status as "release + Pages diverged", which the
spec scenario ``Pages deployment failure aborts the publish`` requires.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_POLL_INTERVAL_SECONDS = 10


def fetch_manifest_release_tag(url: str, socket_timeout: float) -> str | None:
    """Return the ``release_tag`` field, or ``None`` on any fetch/parse error."""
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            # Pages tends to cache aggressively; force a network hit.
            "Cache-Control": "no-cache",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=socket_timeout) as resp:
            body = resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError):
        return None
    try:
        doc = json.loads(body)
    except json.JSONDecodeError:
        return None
    tag = doc.get("release_tag") if isinstance(doc, dict) else None
    return str(tag) if isinstance(tag, str) else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--owner", required=True, help='The "<owner>" segment of the repo')
    parser.add_argument("--repo", required=True, help='The "<repo>" segment (no owner prefix)')
    parser.add_argument("--tag", required=True, help="The tag that was just published")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Total budget for retrying (default: 180)",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help="Seconds between polls (default: 10)",
    )
    parser.add_argument(
        "--pages-path",
        default="yaml-data/manifest-latest.json",
        help="Path under the Pages root (default: yaml-data/manifest-latest.json)",
    )
    args = parser.parse_args()

    url = f"https://{args.owner}.github.io/{args.repo}/{args.pages_path}"
    deadline = time.monotonic() + args.timeout_seconds

    attempt = 0
    last_seen: str | None = None
    while True:
        attempt += 1
        tag = fetch_manifest_release_tag(url, socket_timeout=15)
        if tag == args.tag:
            print(f"OK: {url} reports release_tag={tag!r} (attempt {attempt})")
            return 0
        last_seen = tag
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        print(
            f"retrying: attempt {attempt}, fetched {last_seen!r}, "
            f"expected {args.tag!r}, {int(remaining)}s remaining",
            file=sys.stderr,
        )
        time.sleep(min(args.poll_interval_seconds, max(1, int(remaining))))

    print(
        f"FAIL: {url} did not report release_tag={args.tag!r} within "
        f"{args.timeout_seconds}s (last saw {last_seen!r})",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
