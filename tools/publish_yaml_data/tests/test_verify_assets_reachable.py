"""Regression tests for the YAML-data release-asset publish probe.

These tests pin the strict-byte contract that closes the same-tag
CDN-stale window: a reachability-only probe could bless a previous
release recreation's cached bytes, which would then cause every client
install to fail checksum validation against the new manifest.
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

from tools.publish_yaml_data import verify_assets_reachable  # noqa: E402

_STAGED_YAML = b"schema_version: 1.0\nfoo: bar\n"
_STAGED_DIGEST = hashlib.sha256(_STAGED_YAML).hexdigest()
_STALE_YAML = b"schema_version: 0.9\nfoo: old\n"


class _FakeResponse:
    """Minimal context manager matching the ``urllib`` response surface."""

    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._buf = io.BytesIO(body)

    def read(self, size: int = -1) -> bytes:
        return self._buf.read(size)

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_exc: object) -> None:
        self._buf.close()


@pytest.fixture
def patch_urlopen(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[list[tuple[int, bytes]]]:
    """Swap ``urllib.request.urlopen`` inside the module for a queue.

    Yields a mutable list of ``(status, body)`` tuples. Each call to
    ``urlopen`` pops from the front and returns a response carrying those
    values.
    """
    responses: list[tuple[int, bytes]] = []

    def _fake_urlopen(_req: object, timeout: float) -> _FakeResponse:
        if not responses:
            raise AssertionError(
                "urlopen called without a queued response — test bug"
            )
        status, body = responses.pop(0)
        if status >= 400:
            raise verify_assets_reachable.urllib.error.HTTPError(
                "https://example.test", status, "Error", {}, None
            )
        return _FakeResponse(status=status, body=body)

    monkeypatch.setattr(
        verify_assets_reachable.urllib.request,
        "urlopen",
        _fake_urlopen,
    )
    yield responses


def test_probe_asset_once_accepts_matching_body(
    patch_urlopen: list[tuple[int, bytes]],
) -> None:
    patch_urlopen.append((200, _STAGED_YAML))

    err = verify_assets_reachable.probe_asset_once(
        "https://example.test/CLASSIC%20Fallout4.yaml",
        _STAGED_DIGEST,
        socket_timeout=15,
    )

    assert err is None


def test_probe_asset_once_rejects_mismatched_body(
    patch_urlopen: list[tuple[int, bytes]],
) -> None:
    patch_urlopen.append((200, _STALE_YAML))

    err = verify_assets_reachable.probe_asset_once(
        "https://example.test/CLASSIC%20Fallout4.yaml",
        _STAGED_DIGEST,
        socket_timeout=15,
    )

    assert err is not None
    assert "SHA-256 mismatch" in err
    assert _STAGED_DIGEST in err


def test_probe_asset_once_rejects_non_200_status(
    patch_urlopen: list[tuple[int, bytes]],
) -> None:
    patch_urlopen.append((404, b""))

    err = verify_assets_reachable.probe_asset_once(
        "https://example.test/missing.yaml",
        _STAGED_DIGEST,
        socket_timeout=15,
    )

    assert err is not None
    assert "HTTP 404" in err


def test_load_manifest_assets_rejects_non_object_root(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

    with pytest.raises(SystemExit, match="root is not a JSON object"):
        verify_assets_reachable._load_manifest_assets(manifest)


def test_load_manifest_assets_requires_sha256(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "name": "CLASSIC Fallout4.yaml",
                        "download_url": "https://example.test/file.yaml",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="sha256"):
        verify_assets_reachable._load_manifest_assets(manifest)


@pytest.mark.parametrize(
    "digest",
    [
        "",
        "   ",
        "not-a-digest",
        _STAGED_DIGEST[:32],
        f"{_STAGED_DIGEST}deadbeef",
    ],
)
def test_load_manifest_assets_rejects_malformed_sha256(
    tmp_path: Path, digest: str
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "name": "CLASSIC Fallout4.yaml",
                        "download_url": "https://example.test/file.yaml",
                        "sha256": digest,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="64-character hex digest"):
        verify_assets_reachable._load_manifest_assets(manifest)


def test_load_manifest_assets_trims_sha256_whitespace(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "name": "CLASSIC Fallout4.yaml",
                        "download_url": "https://example.test/file.yaml",
                        "sha256": f"  {_STAGED_DIGEST.upper()}  ",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    expected_manifest_digest = hashlib.sha256(manifest.read_bytes()).hexdigest()

    assets = verify_assets_reachable._load_manifest_assets(manifest)

    assert assets == [
        ("CLASSIC Fallout4.yaml", "https://example.test/file.yaml", _STAGED_DIGEST),
        (
            "manifest.json",
            "https://example.test/manifest.json",
            expected_manifest_digest,
        ),
    ]


def test_load_manifest_assets_returns_triples(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "name": "CLASSIC Fallout4.yaml",
                        "download_url": "https://example.test/file.yaml",
                        "sha256": _STAGED_DIGEST,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    expected_manifest_digest = hashlib.sha256(manifest.read_bytes()).hexdigest()

    assets = verify_assets_reachable._load_manifest_assets(manifest)

    assert assets == [
        ("CLASSIC Fallout4.yaml", "https://example.test/file.yaml", _STAGED_DIGEST),
        (
            "manifest.json",
            "https://example.test/manifest.json",
            expected_manifest_digest,
        ),
    ]


def test_load_manifest_assets_includes_release_manifest_asset(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "name": "CLASSIC Fallout4.yaml",
                        "download_url": (
                            "https://github.com/example/repo/releases/download/"
                            "yaml-data-v2026.06.12/CLASSIC%20Fallout4.yaml"
                        ),
                        "sha256": _STAGED_DIGEST,
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    expected_manifest_digest = hashlib.sha256(manifest.read_bytes()).hexdigest()

    assets = verify_assets_reachable._load_manifest_assets(manifest)

    assert (
        "manifest.json",
        "https://github.com/example/repo/releases/download/"
        "yaml-data-v2026.06.12/manifest.json",
        expected_manifest_digest,
    ) in assets
