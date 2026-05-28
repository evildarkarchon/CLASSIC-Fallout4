"""Regression tests for app-notification publish-side validation.

Each test below pairs a manifest shape with the Rust runtime contract in
``classic_update_core::notification::validate_notification_manifest``. The
publish-side validator MUST reject every shape the Rust runtime would
reject — anything else lets the publish workflow greenlight a manifest
that all clients then refuse to parse.

These cases also pin the specific bypasses the Codex adversarial review
called out (release_tag without ``v`` prefix, leading-zero semver,
naive RFC 3339 timestamp). They exist to fail loudly if any future
relaxation re-introduces the drift.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from tools.publish_app_notification.validate import (  # noqa: E402
    validate_path,
    validate_workflow_tag,
)

_BASE_VALID_MANIFEST = """\
manifest_version: "1.0"
release_tag: "v9.1.0"
latest_version: "9.1.0"
published_at: "2026-04-22T12:00:00Z"
"""


def _write_manifest(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "app-notification.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_happy_path_passes(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path, _BASE_VALID_MANIFEST)
    assert validate_path(path) == []


def test_release_tag_without_v_prefix_is_rejected(tmp_path: Path) -> None:
    body = _BASE_VALID_MANIFEST.replace(
        'release_tag: "v9.1.0"', 'release_tag: "9.1.0"'
    )
    path = _write_manifest(tmp_path, body)
    errors = validate_path(path)
    assert any("release_tag" in err for err in errors), errors


def test_latest_version_with_leading_zero_is_rejected(tmp_path: Path) -> None:
    body = _BASE_VALID_MANIFEST.replace(
        'latest_version: "9.1.0"', 'latest_version: "01.2.3"'
    )
    path = _write_manifest(tmp_path, body)
    errors = validate_path(path)
    assert any("latest_version" in err for err in errors), errors


def test_published_at_without_offset_is_rejected(tmp_path: Path) -> None:
    body = _BASE_VALID_MANIFEST.replace(
        'published_at: "2026-04-22T12:00:00Z"',
        'published_at: "2026-05-01T12:00:00"',
    )
    path = _write_manifest(tmp_path, body)
    errors = validate_path(path)
    assert any("published_at" in err for err in errors), errors


def test_published_at_with_explicit_offset_is_accepted(tmp_path: Path) -> None:
    body = _BASE_VALID_MANIFEST.replace(
        'published_at: "2026-04-22T12:00:00Z"',
        'published_at: "2026-04-22T12:00:00+00:00"',
    )
    path = _write_manifest(tmp_path, body)
    assert validate_path(path) == []


def test_release_tag_with_leading_zero_semver_is_rejected(tmp_path: Path) -> None:
    body = _BASE_VALID_MANIFEST.replace(
        'release_tag: "v9.1.0"', 'release_tag: "v01.2.3"'
    )
    path = _write_manifest(tmp_path, body)
    errors = validate_path(path)
    assert any("release_tag" in err for err in errors), errors


def test_min_supported_version_with_leading_zero_is_rejected(tmp_path: Path) -> None:
    body = _BASE_VALID_MANIFEST + 'min_supported_version: "01.0.0"\n'
    path = _write_manifest(tmp_path, body)
    errors = validate_path(path)
    assert any("min_supported_version" in err for err in errors), errors


def test_min_supported_version_strict_semver_is_accepted(tmp_path: Path) -> None:
    body = _BASE_VALID_MANIFEST + 'min_supported_version: "9.0.0"\n'
    path = _write_manifest(tmp_path, body)
    assert validate_path(path) == []


def test_prerelease_semver_is_accepted(tmp_path: Path) -> None:
    body = _BASE_VALID_MANIFEST.replace(
        'latest_version: "9.1.0"', 'latest_version: "9.1.0-rc.1"'
    ).replace(
        'release_tag: "v9.1.0"', 'release_tag: "v9.1.0-rc.1"'
    )
    path = _write_manifest(tmp_path, body)
    assert validate_path(path) == []


def test_workflow_tag_with_strict_semver_is_accepted() -> None:
    assert validate_workflow_tag("app-notification-v9.2.0") == []


def test_workflow_tag_with_prerelease_and_build_is_accepted() -> None:
    assert validate_workflow_tag("app-notification-v9.2.0-rc.1+build.5") == []


def test_workflow_tag_with_unparseable_suffix_is_rejected() -> None:
    errors = validate_workflow_tag("app-notification-vnext")
    assert any("app-notification-v<SEMVER>" in err for err in errors), errors


def test_workflow_tag_with_leading_zero_semver_is_rejected() -> None:
    errors = validate_workflow_tag("app-notification-v01.2.3")
    assert any("app-notification-v<SEMVER>" in err for err in errors), errors


def test_workflow_tag_requires_notification_prefix() -> None:
    errors = validate_workflow_tag("v9.2.0")
    assert any("app-notification-v<SEMVER>" in err for err in errors), errors


def test_min_supported_above_latest_is_rejected(tmp_path: Path) -> None:
    # Regression: Codex adversarial-review finding. A manifest that
    # names a higher min_supported_version than latest_version would
    # falsely deprecate even the advertised latest build because the
    # Rust `classify` gives min_supported_version precedence.
    # Base manifest has latest_version=9.1.0, so min=9.2.0 is strictly
    # greater and MUST be rejected.
    body = _BASE_VALID_MANIFEST + 'min_supported_version: "9.2.0"\n'
    path = _write_manifest(tmp_path, body)
    errors = validate_path(path)
    assert any(
        "min_supported_version" in err and "latest_version" in err
        for err in errors
    ), errors


def test_min_supported_equal_to_latest_is_accepted(tmp_path: Path) -> None:
    # Boundary: min == latest is a valid publisher stance ("only the
    # latest release is supported"). Must not be flagged by the
    # cross-field invariant.
    body = _BASE_VALID_MANIFEST + 'min_supported_version: "9.1.0"\n'
    path = _write_manifest(tmp_path, body)
    assert validate_path(path) == []


def test_min_supported_prerelease_above_latest_core_is_rejected(
    tmp_path: Path,
) -> None:
    # SemVer rule 11: 9.2.0 > 9.2.0-rc.1. So a `latest=9.2.0-rc.1` +
    # `min=9.2.0` pair is still "min > latest" and the precedence
    # comparator must catch it.
    body = (
        _BASE_VALID_MANIFEST
        .replace('latest_version: "9.1.0"', 'latest_version: "9.2.0-rc.1"')
        .replace('release_tag: "v9.1.0"', 'release_tag: "v9.2.0-rc.1"')
        + 'min_supported_version: "9.2.0"\n'
    )
    path = _write_manifest(tmp_path, body)
    errors = validate_path(path)
    assert any(
        "min_supported_version" in err and "latest_version" in err
        for err in errors
    ), errors


def test_min_supported_prerelease_at_latest_core_is_accepted(
    tmp_path: Path,
) -> None:
    # SemVer rule 11: 9.2.0-rc.1 < 9.2.0. So `latest=9.2.0` with
    # `min=9.2.0-rc.1` is a valid pair — the invariant must not flag it.
    body = (
        _BASE_VALID_MANIFEST
        .replace('latest_version: "9.1.0"', 'latest_version: "9.2.0"')
        .replace('release_tag: "v9.1.0"', 'release_tag: "v9.2.0"')
        + 'min_supported_version: "9.2.0-rc.1"\n'
    )
    path = _write_manifest(tmp_path, body)
    assert validate_path(path) == []


_DISPLAY_BLOCK = """\
display:
  title: "Update available"
  body: "Bug fixes and improvements."
  cta_url: {cta}
"""


def test_display_cta_url_https_is_accepted(tmp_path: Path) -> None:
    body = _BASE_VALID_MANIFEST + _DISPLAY_BLOCK.format(
        cta='"https://example.invalid/changelog"'
    )
    path = _write_manifest(tmp_path, body)
    assert validate_path(path) == []


def test_display_cta_url_must_parse_as_https_url(tmp_path: Path) -> None:
    # Regression: prefix checks alone accepted malformed values that the
    # Rust runtime rejects via url::Url::parse, causing published
    # manifests to fail at client fetch/validate time.
    for cta in (
        "https://",
        "https://example.com bad",
    ):
        body = _BASE_VALID_MANIFEST + _DISPLAY_BLOCK.format(cta=f'"{cta}"')
        path = _write_manifest(tmp_path, body)
        errors = validate_path(path)
        assert any("cta_url" in err and "HTTPS" in err for err in errors), (
            f"expected parse rejection for {cta!r}, got {errors!r}"
        )


def test_display_cta_url_http_is_rejected(tmp_path: Path) -> None:
    # Regression: Codex adversarial-review finding #3. The GUI opens
    # `display.cta_url` from an update prompt, so a typo'd or
    # compromised manifest could downgrade users onto an unauthenticated
    # destination at exactly the moment they are being asked to fetch
    # an update. Mirror the runtime validator and reject at publish
    # time so non-HTTPS URLs never publish in the first place.
    body = _BASE_VALID_MANIFEST + _DISPLAY_BLOCK.format(
        cta='"http://example.invalid/changelog"'
    )
    path = _write_manifest(tmp_path, body)
    errors = validate_path(path)
    assert any("cta_url" in err and "HTTPS" in err for err in errors), errors


def test_display_cta_url_other_schemes_are_rejected(tmp_path: Path) -> None:
    # Any non-HTTPS scheme — including ones with no useful semantics
    # for a CTA link — must be refused. This is the second line of
    # defense behind the workflow's HTTPS-only assumption.
    for cta in (
        "ftp://example.invalid/file",
        "file:///etc/passwd",
        "javascript:alert(1)",
    ):
        body = _BASE_VALID_MANIFEST + _DISPLAY_BLOCK.format(cta=f'"{cta}"')
        path = _write_manifest(tmp_path, body)
        errors = validate_path(path)
        assert any("cta_url" in err and "HTTPS" in err for err in errors), (
            f"expected HTTPS rejection for {cta!r}, got {errors!r}"
        )


def test_display_cta_url_omitted_is_accepted(tmp_path: Path) -> None:
    # cta_url is optional — a display block without one must still pass.
    body = (
        _BASE_VALID_MANIFEST
        + 'display:\n'
        + '  title: "Update available"\n'
        + '  body: "Notes"\n'
    )
    path = _write_manifest(tmp_path, body)
    assert validate_path(path) == []


def test_display_cta_url_https_case_insensitive(tmp_path: Path) -> None:
    # The Rust runtime validator uses url::Url::parse which normalizes
    # the scheme to lowercase, so `HTTPS://...` parses as scheme=https.
    # The publish-side check uses str.lower().startswith("https://")
    # to mirror that behavior — keep the two surfaces in lockstep.
    body = _BASE_VALID_MANIFEST + _DISPLAY_BLOCK.format(
        cta='"HTTPS://example.invalid/cased"'
    )
    path = _write_manifest(tmp_path, body)
    assert validate_path(path) == []
