"""Smoke-test the Pages-hosted manifest after a publish.

GitHub Pages deployment is eventually consistent — the new content can take
a minute or two to propagate after the workflow pushes to the `gh-pages`
branch. This script polls the Pages URL with fixed-interval backoff until the
remote body matches what the workflow staged, then exits 0. Workflow callers
use ``https://<owner>.github.io/<repo>/<pages-path>``; local dry-run harnesses
can pass ``--base-url`` to point the same smoke-test logic at a temporary
server.

Two match modes are supported:

- ``--tag <T>`` (legacy): assert that the response JSON's ``release_tag``
  field equals ``T``. Intended for the ``yaml-data-v*`` channel, whose
  workflow tag IS its manifest's ``release_tag``.
- ``--expected-body-path <PATH>`` (strict): assert that the full response
  bytes exactly equal the staged manifest bytes at ``PATH``, compared via
  SHA-256. Required for the ``app-notification-v*`` channel, where
  notification-only republishes MAY keep the same binary ``release_tag``
  while changing ``min_supported_version`` / ``display``. Comparing only
  ``release_tag`` in that case can pass against the PREVIOUS Pages payload
  and open a split-brain window between Pages-first and Releases-fallback
  consumers.

Exactly one of ``--tag`` / ``--expected-body-path`` MUST be provided.

Exit non-zero on any final mismatch or on total timeout — callers in the
workflow treat the exit status as "release + Pages diverged", which the
spec scenario ``Pages deployment failure aborts the publish`` requires.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_POLL_INTERVAL_SECONDS = 10


def build_pages_url(
    owner: str | None,
    repo: str | None,
    pages_path: str,
    base_url: str | None = None,
) -> str:
    """Return the URL that the Pages smoke test should poll.

    ``base_url`` is for local dry-runs that serve a staged Pages tree from a
    temporary localhost HTTP server. Without it, ``owner`` and ``repo`` are
    required and the live GitHub Pages URL shape is preserved.
    """
    normalized_path = pages_path.lstrip("/")
    if base_url:
        return f"{base_url.rstrip('/')}/{normalized_path}"
    if not owner or not repo:
        raise ValueError("--owner and --repo are required unless --base-url is provided")
    return f"https://{owner}.github.io/{repo}/{normalized_path}"


def _fetch_bytes(url: str, socket_timeout: float) -> bytes | None:
    """Return the raw response bytes, or ``None`` on any fetch error."""
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
            return resp.read()
    except (urllib.error.URLError, TimeoutError):
        return None


def fetch_manifest_release_tag(url: str, socket_timeout: float) -> str | None:
    """Return the ``release_tag`` field, or ``None`` on any fetch/parse error."""
    body = _fetch_bytes(url, socket_timeout)
    if body is None:
        return None
    try:
        doc = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    tag = doc.get("release_tag") if isinstance(doc, dict) else None
    return str(tag) if isinstance(tag, str) else None


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument(
        "--owner",
        help='The "<owner>" segment of the repo. Required unless --base-url is provided.',
    )
    parser.add_argument(
        "--repo",
        help='The "<repo>" segment (no owner prefix). Required unless --base-url is provided.',
    )
    match_group = parser.add_mutually_exclusive_group(required=True)
    match_group.add_argument(
        "--tag",
        help="Legacy yaml-data match mode: compare the response JSON's release_tag to this value",
    )
    match_group.add_argument(
        "--expected-body-path",
        help=(
            "Strict match mode: require the response bytes to equal the bytes at this path "
            "(SHA-256 compared). Use for notification-channel smoke tests where two different "
            "manifests can share the same release_tag."
        ),
    )
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
    parser.add_argument(
        "--base-url",
        default=None,
        help=(
            "Override the Pages root URL, for example a localhost server used "
            "by dry-run tooling. When omitted, owner/repo build the live "
            "GitHub Pages URL."
        ),
    )
    args = parser.parse_args()

    try:
        url = build_pages_url(args.owner, args.repo, args.pages_path, args.base_url)
    except ValueError as err:
        parser.error(str(err))

    deadline = time.monotonic() + args.timeout_seconds

    expected_digest: str | None = None
    if args.expected_body_path:
        staged = Path(args.expected_body_path).read_bytes()
        expected_digest = _sha256(staged)
        print(
            f"strict-body smoke test: expecting sha256={expected_digest} "
            f"({len(staged)} bytes from {args.expected_body_path})"
        )

    attempt = 0
    last_seen: str | None = None
    while True:
        attempt += 1

        if expected_digest is not None:
            body = _fetch_bytes(url, socket_timeout=15)
            if body is not None:
                digest = _sha256(body)
                if digest == expected_digest:
                    print(f"OK: {url} serves staged manifest (sha256={digest}, attempt {attempt})")
                    return 0
                last_seen = f"sha256={digest}"
            else:
                last_seen = "fetch-failed"
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            print(
                f"retrying: attempt {attempt}, remote {last_seen}, "
                f"expected sha256={expected_digest}, {int(remaining)}s remaining",
                file=sys.stderr,
            )
            time.sleep(min(args.poll_interval_seconds, max(1, int(remaining))))
            continue

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

    if expected_digest is not None:
        print(
            f"FAIL: {url} did not serve expected bytes (sha256={expected_digest}) within "
            f"{args.timeout_seconds}s (last saw {last_seen})",
            file=sys.stderr,
        )
    else:
        print(
            f"FAIL: {url} did not report release_tag={args.tag!r} within "
            f"{args.timeout_seconds}s (last saw {last_seen!r})",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
