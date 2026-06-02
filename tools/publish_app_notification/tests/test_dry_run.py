"""Regression tests for the app-notification local dry-run harness."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from tools.publish_app_notification import dry_run  # noqa: E402
from tools.publish_yaml_data.smoke_test_pages import build_pages_url  # noqa: E402

_VALID_SOURCE = """\
manifest_version: "1.0"
release_tag: "v9.2.0"
latest_version: "9.2.0"
published_at: null
min_supported_version: null
display: null
"""


def _write_source(tmp_path: Path, body: str = _VALID_SOURCE) -> Path:
    path = tmp_path / "app-notification.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_invalid_workflow_tag_fails_before_source_read(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    missing_source = tmp_path / "missing.yaml"
    work_dir = tmp_path / "work"

    exit_code = dry_run.main(
        [
            "--workflow-tag",
            "app-notification-vnext",
            "--source",
            str(missing_source),
            "--work-dir",
            str(work_dir),
        ]
    )

    captured = capfd.readouterr()
    assert exit_code == 1
    assert "workflow tag must match app-notification-v<SEMVER>" in captured.err
    assert "cannot read" not in captured.err
    assert not work_dir.exists()


def test_invalid_source_fails_before_staging(tmp_path: Path) -> None:
    source = _write_source(tmp_path, 'manifest_version: "1.0"\n')
    work_dir = tmp_path / "work"

    exit_code = dry_run.main(
        [
            "--workflow-tag",
            "app-notification-v9.2.0",
            "--source",
            str(source),
            "--work-dir",
            str(work_dir),
        ]
    )

    assert exit_code == 1
    assert not work_dir.exists()


def test_happy_path_generates_and_stages_manifest(tmp_path: Path) -> None:
    source = _write_source(tmp_path)
    work_dir = tmp_path / "work"

    exit_code = dry_run.main(
        [
            "--workflow-tag",
            "app-notification-v9.2.0",
            "--source",
            str(source),
            "--published-at",
            "2026-06-02T12:34:56Z",
            "--work-dir",
            str(work_dir),
        ]
    )

    manifest = work_dir / dry_run.STAGED_MANIFEST_REL
    latest = work_dir / dry_run.PAGES_LATEST_REL
    tagged = work_dir / "gh-pages" / "app-notification" / (
        "manifest-app-notification-v9.2.0.json"
    )
    release_asset = (
        work_dir
        / dry_run.RELEASE_ASSET_REL
        / "app-notification-v9.2.0"
        / "manifest.json"
    )

    assert exit_code == 0
    assert manifest.is_file()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["published_at"] == "2026-06-02T12:34:56Z"
    assert latest.read_bytes() == manifest.read_bytes()
    assert tagged.read_bytes() == manifest.read_bytes()
    assert release_asset.read_bytes() == manifest.read_bytes()


def test_release_asset_mismatch_fails_before_pages_staging(tmp_path: Path) -> None:
    source = _write_source(tmp_path)
    work_dir = tmp_path / "work"

    exit_code = dry_run.main(
        [
            "--workflow-tag",
            "app-notification-v9.2.0",
            "--source",
            str(source),
            "--published-at",
            "2026-06-02T12:34:56Z",
            "--work-dir",
            str(work_dir),
            "--timeout-seconds",
            "1",
            "--simulate-release-asset-mismatch",
        ]
    )

    assert exit_code == 1
    assert (work_dir / dry_run.STAGED_MANIFEST_REL).is_file()
    assert not (work_dir / dry_run.PAGES_LATEST_REL).exists()


def test_pages_mismatch_fails_after_pages_staging(tmp_path: Path) -> None:
    source = _write_source(tmp_path)
    work_dir = tmp_path / "work"

    exit_code = dry_run.main(
        [
            "--workflow-tag",
            "app-notification-v9.2.0",
            "--source",
            str(source),
            "--published-at",
            "2026-06-02T12:34:56Z",
            "--work-dir",
            str(work_dir),
            "--timeout-seconds",
            "1",
            "--simulate-pages-mismatch",
        ]
    )

    manifest = work_dir / dry_run.STAGED_MANIFEST_REL
    latest = work_dir / dry_run.PAGES_LATEST_REL

    assert exit_code == 1
    assert latest.is_file()
    assert latest.read_bytes() != manifest.read_bytes()


def test_pages_url_builder_supports_live_and_local_roots() -> None:
    assert (
        build_pages_url(
            "classic-owner",
            "classic-repo",
            "app-notification/manifest-latest.json",
        )
        == "https://classic-owner.github.io/classic-repo/app-notification/manifest-latest.json"
    )
    assert (
        build_pages_url(
            None,
            None,
            "/app-notification/manifest-latest.json",
            "http://127.0.0.1:12345/gh-pages/",
        )
        == "http://127.0.0.1:12345/gh-pages/app-notification/manifest-latest.json"
    )
    with pytest.raises(ValueError):
        build_pages_url(None, None, "app-notification/manifest-latest.json")
