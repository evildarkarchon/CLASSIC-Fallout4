"""Verify every manifest ``download_url`` serves the advertised bytes anonymously.

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

Strict-byte mode
----------------

Reachability alone is NOT sufficient. The workflow supports operator
delete-and-rerun on the same tag; ``releases/download/<tag>/<name>`` URLs
reuse the same path. If GitHub's CDN happens to serve a stale copy of an
asset from a previous release recreation, a reachability-only probe would
pass while clients later download bytes that do not match the manifest's
``sha256`` — every install fails with a checksum mismatch.

Each URL is probed with an unauthenticated full GET (no ``Range`` header).
The response body is streamed through SHA-256 and compared to the manifest
entry's ``sha256`` field. Any mismatch is treated as "not ready yet" and
the retry budget keeps ticking until the CDN serves the bytes this run
staged.

The request is deliberately unauthenticated: no ``Authorization`` header
is attached even when ``$GITHUB_TOKEN`` is present in the environment.
Clients consuming the published manifest will not authenticate either.

Exit status
-----------

- 0 on first attempt where every URL returns HTTP 200 and the body SHA-256
  matches the manifest entry.
- Non-zero after the retry budget is exhausted, with a per-URL diagnostic
  printed to stderr so the workflow log names the offending asset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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

_READ_CHUNK_SIZE = 65536
_SHA256_HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _parse_manifest_sha256(raw: str) -> str:
    """Return a normalized lowercase SHA-256 hex digest from a manifest field."""
    normalized = raw.strip()
    if not _SHA256_HEX_RE.fullmatch(normalized):
        raise SystemExit(
            "FAIL: manifest entry sha256 must be a 64-character hex digest "
            f"(got {raw!r})"
        )
    return normalized.lower()


def probe_asset_once(
    url: str, expected_sha256: str, socket_timeout: float
) -> str | None:
    """Single-shot probe; return ``None`` on success, an error string otherwise.

    When ``expected_sha256`` is non-empty, the SHA-256 of the fetched body
    is compared against it. A mismatch is returned as an error string so
    the retry loop keeps polling — on a same-tag rerun this is exactly
    the window during which a stale CDN copy can be served.
    """
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "*/*",
            "User-Agent": "classic-publish-yaml-data/verify-assets",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=socket_timeout) as resp:
            status = resp.status
            if status != 200:
                return f"HTTP {status}"
            hasher = hashlib.sha256()
            while True:
                chunk = resp.read(_READ_CHUNK_SIZE)
                if not chunk:
                    break
                hasher.update(chunk)
            actual_sha256 = hasher.hexdigest()
            if actual_sha256 != expected_sha256:
                return (
                    "SHA-256 mismatch: expected "
                    f"{expected_sha256}, got {actual_sha256} "
                    "(CDN likely still serving the previous same-tag asset)"
                )
            return None
    except urllib.error.HTTPError as exc:
        return f"HTTP {exc.code}"
    except OSError as exc:
        return f"network error: {exc!r}"


def _load_manifest_assets(
    manifest_path: Path,
) -> list[tuple[str, str, str]]:
    """Return ``[(name, download_url, expected_sha256), ...]`` from manifest.json."""
    with manifest_path.open("r", encoding="utf-8") as f:
        doc = json.load(f)
    if not isinstance(doc, dict):
        raise SystemExit(f"FAIL: {manifest_path} root is not a JSON object")
    files = doc.get("files")
    if not isinstance(files, list) or not files:
        raise SystemExit(
            f"FAIL: {manifest_path} has no non-empty 'files' array"
        )
    assets: list[tuple[str, str, str]] = []
    for entry in files:
        if not isinstance(entry, dict):
            raise SystemExit(f"FAIL: manifest entry is not a mapping: {entry!r}")
        name = entry.get("name")
        url = entry.get("download_url")
        digest = entry.get("sha256")
        if not isinstance(name, str) or not isinstance(url, str):
            raise SystemExit(
                f"FAIL: manifest entry missing string name/download_url: {entry!r}"
            )
        if not isinstance(digest, str):
            raise SystemExit(
                f"FAIL: manifest entry missing string sha256: {entry!r}"
            )
        assets.append((name, url, _parse_manifest_sha256(digest)))
    return assets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
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

    assets = _load_manifest_assets(args.manifest)
    deadline = time.monotonic() + args.timeout_seconds

    # Sweep all URLs each attempt rather than failing on the first one; a
    # single offender on an N-file manifest should surface clearly instead
    # of hiding behind a generic "one of these failed" message.
    attempt = 0
    while True:
        attempt += 1
        failures: list[tuple[str, str, str]] = []
        for name, url, expected_sha256 in assets:
            err = probe_asset_once(
                url, expected_sha256, args.socket_timeout_seconds
            )
            if err is not None:
                failures.append((name, url, err))

        if not failures:
            print(
                f"OK: all {len(assets)} asset URL(s) serve manifest bytes "
                f"anonymously (attempt {attempt})"
            )
            return 0

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break

        print(
            f"retrying: attempt {attempt}, {len(failures)}/{len(assets)} asset(s) "
            f"not ready, {int(remaining)}s remaining",
            file=sys.stderr,
        )
        for name, url, diag in failures:
            print(f"  - {name}: {diag} ({url})", file=sys.stderr)
        time.sleep(min(args.poll_interval_seconds, max(1, int(remaining))))

    print(
        f"FAIL: {len(failures)} of {len(assets)} asset URL(s) still not serving "
        f"expected bytes after {args.timeout_seconds}s:",
        file=sys.stderr,
    )
    for name, url, diag in failures:
        print(f"  - {name}: {diag} ({url})", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
