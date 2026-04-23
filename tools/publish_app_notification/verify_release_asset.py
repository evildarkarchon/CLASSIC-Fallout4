"""Probe that the single app-notification release asset is anonymously reachable.

The yaml-data workflow walks every ``download_url`` in its ``manifest.json``
and probes each one. The app-notification manifest has no nested download
URLs — the only release asset is ``manifest.json`` itself. This helper
fetches it anonymously (no token) with a retry budget so the workflow can
clear the prerelease flag once the GitHub CDN has warmed the asset URL.

Strict-body mode
----------------
Reachability alone is NOT sufficient. The workflow supports operator
delete-and-rerun on the same tag; the `releases/download/<tag>/manifest.json`
URL reuses the same path. If GitHub's CDN happens to serve a stale copy
of the asset from a previous release recreation, a reachability-only
probe would pass while the Releases fallback clients later read the
previous tag's manifest — splitting Pages-first clients (on the new
Pages payload) from Releases-fallback clients (on the stale asset).

To close that gap, the probe accepts ``--expected-body-path`` pointing
at the staged manifest bytes. When provided, the probe computes the
SHA-256 of the fetched body and compares it to the SHA-256 of the
staged manifest. Any mismatch is treated as "not ready yet" and the
retry budget keeps ticking — the probe only reports success when the
bytes on the release asset URL are exactly the bytes the workflow
staged in this run. This mirrors ``tools/publish_yaml_data/smoke_test_pages.py``'s
strict-body behavior for the Pages channel.

Usage::

    python tools/publish_app_notification/verify_release_asset.py \\
        --url https://github.com/<owner>/<repo>/releases/download/<tag>/manifest.json \\
        --expected-body-path "$RUNNER_TEMP/staging/manifest.json"

Exit status 0 on a successful anonymous fetch that parses as JSON with a
non-empty ``release_tag`` **and** (when ``--expected-body-path`` is
supplied) whose SHA-256 matches the staged manifest bytes; non-zero on
any transport, status, parse, or digest-mismatch failure within the
retry budget.
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

DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_POLL_INTERVAL_SECONDS = 5


def _fetch(url: str, socket_timeout: float) -> tuple[int, bytes | None, str | None]:
    """Return ``(status_code, body_bytes, error_message)``.

    ``status_code`` is 0 if the transport failed before we got an HTTP
    response (DNS, socket, timeout). In that case ``error_message`` carries
    the transport diagnostic.
    """
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "classic-app-notification-publish-probe",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=socket_timeout) as resp:
            return int(resp.status), resp.read(), None
    except urllib.error.HTTPError as err:
        try:
            body = err.read()
        except Exception:
            body = None
        return int(err.code), body, f"HTTP {err.code}: {err.reason}"
    except (urllib.error.URLError, TimeoutError) as err:
        return 0, None, str(err)


def probe_once(url: str, expected_sha256: str | None = None) -> str | None:
    """Single-shot probe; return ``None`` on success, an error string otherwise.

    When ``expected_sha256`` is non-None, the SHA-256 of the fetched body
    is compared against it. A mismatch is returned as an error string so
    the retry loop keeps polling — on a same-tag rerun this is exactly
    the window during which a stale CDN copy can be served, and we want
    to keep retrying until the CDN replaces it with the bytes this run
    staged.
    """
    status, body, transport_err = _fetch(url, socket_timeout=15)
    if status == 0:
        return f"transport error: {transport_err}"
    if status != 200:
        return f"unexpected status {status}"
    if body is None:
        return "empty body"
    try:
        doc = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        return f"body is not JSON: {err}"
    tag = doc.get("release_tag") if isinstance(doc, dict) else None
    if not isinstance(tag, str) or not tag.strip():
        return "manifest is missing a non-empty release_tag"
    if expected_sha256 is not None:
        actual_sha256 = hashlib.sha256(body).hexdigest()
        if actual_sha256 != expected_sha256:
            return (
                "body SHA-256 mismatch: expected "
                f"{expected_sha256}, got {actual_sha256} "
                "(CDN likely still serving the previous same-tag asset)"
            )
    return None


def _compute_expected_sha256(expected_body_path: Path) -> str:
    """Read ``expected_body_path`` once and return its SHA-256 hex digest."""
    bytes_staged = expected_body_path.read_bytes()
    return hashlib.sha256(bytes_staged).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--url",
        required=True,
        help="HTTPS URL of the release asset manifest.json",
    )
    parser.add_argument(
        "--expected-body-path",
        type=Path,
        default=None,
        help=(
            "Optional path to the staged manifest.json bytes. When "
            "provided, the probe only reports success if the SHA-256 of "
            "the anonymously fetched body matches the SHA-256 of this "
            "file. Closes the same-tag CDN-stale window described in "
            "the module docstring."
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Total retry budget in seconds (default: 120)",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
        help="Seconds between retries (default: 5)",
    )
    args = parser.parse_args()

    expected_sha256: str | None = None
    if args.expected_body_path is not None:
        if not args.expected_body_path.is_file():
            print(
                f"FAIL: --expected-body-path `{args.expected_body_path}` "
                "does not exist or is not a regular file",
                file=sys.stderr,
            )
            return 1
        expected_sha256 = _compute_expected_sha256(args.expected_body_path)
        print(
            f"expecting body SHA-256 {expected_sha256} "
            f"(computed from {args.expected_body_path})"
        )

    deadline = time.monotonic() + args.timeout_seconds
    attempt = 0
    last_error = "not attempted"
    while True:
        attempt += 1
        err = probe_once(args.url, expected_sha256=expected_sha256)
        if err is None:
            suffix = " (body matches staged manifest)" if expected_sha256 else ""
            print(
                f"OK: {args.url} is anonymously reachable (attempt {attempt})"
                f"{suffix}"
            )
            return 0
        last_error = err
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        print(
            f"retrying: attempt {attempt}: {err}; {int(remaining)}s remaining",
            file=sys.stderr,
        )
        time.sleep(min(args.poll_interval_seconds, max(1, int(remaining))))

    print(
        f"FAIL: {args.url} did not become reachable within "
        f"{args.timeout_seconds}s (last error: {last_error})",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
