"""Regression tests for the app-notification release-asset publish probe.

These tests pin the strict-body contract that closes the same-tag
CDN-stale window called out by the Codex adversarial review: a
reachability-only probe could bless a previous release recreation's
cached bytes, which would then split Pages-first and Releases-fallback
clients onto different manifests. The probe must refuse success unless
the bytes actually served match the bytes this workflow run staged.

``probe_once`` talks to the network via ``urllib.request.urlopen``, so
the tests replace that symbol inside the module under test with a
fake that returns caller-supplied bytes. No real HTTP happens; the
test exercises the response-handling logic directly.
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
from pathlib import Path
from typing import Iterator

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from tools.publish_app_notification import verify_release_asset  # noqa: E402


_STAGED_MANIFEST = json.dumps(
    {
        "manifest_version": "1.0",
        "release_tag": "v9.1.0",
        "latest_version": "9.1.0",
        "published_at": "2026-04-22T12:00:00Z",
    },
    separators=(",", ":"),
).encode("utf-8")


class _FakeResponse:
    """Minimal context manager matching the ``urllib`` response surface."""

    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._buf = io.BytesIO(body)

    def read(self) -> bytes:
        return self._buf.read()

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_exc: object) -> None:
        self._buf.close()


@pytest.fixture
def patch_urlopen(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[list[bytes]]:
    """Swap ``urllib.request.urlopen`` inside the module for a queue.

    Yields a mutable ``bodies`` list that callers extend with the bytes
    the fake should return on each successive call. Each call to
    ``urlopen`` pops from the front and returns a 200 response carrying
    those bytes.
    """
    bodies: list[bytes] = []

    def _fake_urlopen(_req: object, timeout: float) -> _FakeResponse:
        if not bodies:
            raise AssertionError(
                "urlopen called without a queued body — test bug"
            )
        return _FakeResponse(status=200, body=bodies.pop(0))

    monkeypatch.setattr(
        verify_release_asset.urllib.request,
        "urlopen",
        _fake_urlopen,
    )
    yield bodies


def test_probe_once_accepts_matching_body(patch_urlopen: list[bytes]) -> None:
    patch_urlopen.append(_STAGED_MANIFEST)
    expected = hashlib.sha256(_STAGED_MANIFEST).hexdigest()

    err = verify_release_asset.probe_once(
        "https://example.test/manifest.json", expected_sha256=expected
    )

    assert err is None


def test_probe_once_rejects_mismatched_body(patch_urlopen: list[bytes]) -> None:
    # Served body is well-formed manifest JSON (so the legacy reachability
    # checks pass) but its bytes differ from the staged manifest. Without
    # the strict-body guard this probe would have returned None; with
    # the guard, it must surface a SHA-256 mismatch.
    stale_bytes = json.dumps(
        {
            "manifest_version": "1.0",
            "release_tag": "v9.0.0",
            "latest_version": "9.0.0",
            "published_at": "2026-01-01T00:00:00Z",
        },
        separators=(",", ":"),
    ).encode("utf-8")
    assert stale_bytes != _STAGED_MANIFEST

    patch_urlopen.append(stale_bytes)
    expected = hashlib.sha256(_STAGED_MANIFEST).hexdigest()

    err = verify_release_asset.probe_once(
        "https://example.test/manifest.json", expected_sha256=expected
    )

    assert err is not None
    assert "SHA-256 mismatch" in err
    assert expected in err


def test_probe_once_without_expected_accepts_reachable_body(
    patch_urlopen: list[bytes],
) -> None:
    # Backwards-compatible path: when no ``expected_sha256`` is passed,
    # the probe still performs the reachability + JSON + release_tag
    # checks. Defensive so ad-hoc callers don't break.
    patch_urlopen.append(_STAGED_MANIFEST)

    err = verify_release_asset.probe_once(
        "https://example.test/manifest.json", expected_sha256=None
    )

    assert err is None


def test_probe_once_rejects_missing_release_tag(
    patch_urlopen: list[bytes],
) -> None:
    bad_body = json.dumps({"manifest_version": "1.0"}).encode("utf-8")
    patch_urlopen.append(bad_body)

    err = verify_release_asset.probe_once(
        "https://example.test/manifest.json", expected_sha256=None
    )

    assert err is not None
    assert "release_tag" in err


def test_compute_expected_sha256(tmp_path: Path) -> None:
    staged = tmp_path / "manifest.json"
    staged.write_bytes(_STAGED_MANIFEST)

    digest = verify_release_asset._compute_expected_sha256(staged)

    assert digest == hashlib.sha256(_STAGED_MANIFEST).hexdigest()
