"""Validate the app-notification source artifact before publish.

Run from ``.github/workflows/publish-app-notification.yml``. Parses
``CLASSIC Data/app-notification.yaml`` and asserts:

- The file parses as a YAML mapping.
- ``manifest_version`` is a quoted string matching ``^\\d+\\.\\d+$`` (same
  contract the Rust decoder enforces in
  ``classic_update_core::notification::validate_notification_manifest``).
- ``release_tag`` is a ``v<SEMVER>`` string (mirrors the Rust ``is_release_tag``
  check; bare semver without the ``v`` prefix is rejected because the publish
  workflow always emits the prefixed form and the Rust client requires it).
- ``latest_version`` parses as strict SemVer (MAJOR.MINOR.PATCH where each
  numeric identifier has no leading zero, plus optional prerelease/build).
  Mirrors what the ``semver`` crate accepts in the Rust runtime.
- ``published_at`` is either ``null`` (the workflow fills it from the tag
  publication timestamp) or a valid RFC 3339 UTC timestamp with an explicit
  ``Z`` or ``±HH:MM`` offset. Naive timestamps are rejected; the Rust
  runtime validator (``is_rfc3339``) requires the offset, so accepting it
  here would let unreadable manifests through.
- ``min_supported_version`` is either absent / ``null`` or a strict SemVer
  string.
- ``display`` is either absent / ``null`` or a mapping with a ``title`` and
  ``body`` string plus optional ``cta_url`` string.

The rule set deliberately matches the Rust runtime exactly. Drift in either
direction is a no-ship: a Python-only laxity lets unreadable manifests
publish (the original Codex adversarial-review finding), and a Python-only
strictness blocks otherwise valid manifests from publishing.

Non-zero exit on any violation, with one ``FAIL:`` line per failure on
stderr so the job log surfaces it cleanly.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from ruamel.yaml import YAML, YAMLError # type: ignore

# Mirror the `^\d+\.\d+$` contract in
# `classic_update_core::notification::is_major_minor`. Two numeric segments.
MANIFEST_VERSION_RE = re.compile(r"^\d+\.\d+$")

# Strict SemVer per https://semver.org and what the `semver` crate parses.
# Numeric identifiers (MAJOR/MINOR/PATCH and any all-digit prerelease ident)
# must NOT have a leading zero, otherwise `Version::parse` rejects them and
# the Rust client rejects the manifest at validate-time.
_NUMERIC_IDENT = r"(?:0|[1-9]\d*)"
_ALNUM_HYPHEN_IDENT = r"\d*[a-zA-Z-][0-9a-zA-Z-]*"
_PRE_IDENT = rf"(?:{_NUMERIC_IDENT}|{_ALNUM_HYPHEN_IDENT})"
_PRERELEASE = rf"{_PRE_IDENT}(?:\.{_PRE_IDENT})*"
_BUILD_IDENT = r"[0-9a-zA-Z-]+"
_BUILD = rf"{_BUILD_IDENT}(?:\.{_BUILD_IDENT})*"
_SEMVER_BODY = (
    rf"{_NUMERIC_IDENT}\.{_NUMERIC_IDENT}\.{_NUMERIC_IDENT}"
    rf"(?:-{_PRERELEASE})?(?:\+{_BUILD})?"
)
SEMVER_RE = re.compile(rf"^{_SEMVER_BODY}$")

# `v<SEMVER>` — mirrors `is_release_tag` in
# `business-logic/classic-update-core/src/notification.rs`. The publish
# workflow always emits the lowercase `v` prefix; bare semver is not the
# tag the Rust client expects.
RELEASE_TAG_RE = re.compile(rf"^v{_SEMVER_BODY}$")

# Shape-only RFC 3339 mirroring the Rust `is_rfc3339` byte-walker. The
# explicit `[Zz]|[+-]\d{2}:\d{2}` tail is the load-bearing part: naive
# timestamps (e.g. `2026-05-01T12:00:00`) are rejected here exactly because
# they are rejected by the Rust runtime, even though Python's
# `datetime.fromisoformat` would otherwise accept them.
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})$"
)

_YAML = YAML(typ="safe", pure=True)


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def _semver_precedence_key(s: str) -> tuple:
    """Return a sort key that orders SemVer strings per semver.org rule 11.

    Assumes ``s`` has already matched :data:`SEMVER_RE`. Build metadata
    (everything after ``+``) is ignored per the spec. Mirrors the
    precedence the Rust ``semver`` crate applies at runtime.

    Encoding:
      * Slot 3 = 1 if no prerelease, 0 if a prerelease is present — so a
        core-only version outranks the same core with any prerelease.
      * Slot 4 = tuple of ``(kind, value)`` per prerelease identifier,
        where numeric identifiers sort below non-numeric ones (kind 0 vs
        kind 1) and numeric identifiers compare numerically. Python's
        tuple comparison is short-circuiting, so the mixed int/str
        values inside the identifier slot are only ever compared when
        the kind tag already matches.
    """
    body = s.split("+", 1)[0]
    if "-" in body:
        core, pre = body.split("-", 1)
    else:
        core, pre = body, ""
    major, minor, patch = (int(x) for x in core.split("."))
    if not pre:
        return (major, minor, patch, 1, ())
    idents: list[tuple[int, int | str]] = []
    for part in pre.split("."):
        if part.isdigit():
            idents.append((0, int(part)))
        else:
            idents.append((1, part))
    return (major, minor, patch, 0, tuple(idents))


def _is_mapping(value: Any) -> bool:
    return isinstance(value, dict)


def _validate_published_at(value: Any) -> str | None:
    """Return an error message, or ``None`` if ``value`` is acceptable.

    ``None`` is acceptable — the workflow fills it from the tag timestamp.
    Otherwise must be a string matching RFC 3339 with an explicit ``Z``
    or ``±HH:MM`` offset. Naive timestamps are rejected because the Rust
    runtime ``is_rfc3339`` requires the offset; accepting them here would
    let manifests through that all clients then refuse to parse.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        return "published_at must be null or an RFC 3339 string"
    if not RFC3339_RE.match(value):
        return (
            "published_at is not RFC 3339 with an explicit Z or "
            f"±HH:MM offset: {value!r}"
        )
    return None


def _is_https_cta_url(value: str) -> bool:
    """Return ``True`` only when ``value`` parses as an HTTPS URL."""
    try:
        parsed = urlsplit(value)
        # urlsplit defers invalid-port errors until the property is read.
        _ = parsed.port
    except ValueError:
        return False
    if parsed.scheme.lower() != "https":
        return False
    if not parsed.netloc or not parsed.hostname:
        return False
    # ``urllib.parse`` is a parser, not a full validator; it leaves spaces in
    # the authority untouched. The Rust runtime's url parser rejects those.
    return not any(ord(ch) <= 0x20 or ch == "\x7f" for ch in parsed.netloc)


def _validate_display(value: Any) -> list[str]:
    """Return a list of error messages (empty on success)."""
    if value is None:
        return []
    if not _is_mapping(value):
        return ["display must be a mapping or null"]
    errors: list[str] = []
    title = value.get("title")
    body = value.get("body")
    cta = value.get("cta_url")
    if not isinstance(title, str) or not title.strip():
        errors.append("display.title must be a non-empty string")
    if not isinstance(body, str):
        errors.append("display.body must be a string")
    if cta is not None:
        if not isinstance(cta, str):
            errors.append("display.cta_url must be a string or null/omitted")
        elif not _is_https_cta_url(cta):
            # Codex adversarial-review finding: the GUI opens this URL from
            # an update prompt, so a typo'd or compromised manifest could
            # downgrade users onto an unauthenticated destination at the
            # exact moment they are being asked to fetch an update. Mirror
            # the runtime validator (`is_https_cta_url` in
            # classic_update_core::notification) so non-HTTPS URLs never
            # publish in the first place.
            errors.append(
                f"display.cta_url must be an HTTPS URL (got {cta!r})"
            )
    # Reject unknown sub-keys so a typo is caught early rather than silently
    # lost. The Rust decoder ignores unknown fields deliberately, but source-
    # side strictness gives the maintainer a faster feedback loop.
    unknown = set(value.keys()) - {"title", "body", "cta_url"}
    if unknown:
        errors.append(f"display has unexpected keys: {sorted(unknown)!r}")
    return errors


def _validate_document(doc: Any) -> list[str]:
    if not _is_mapping(doc):
        return ["top-level document must be a YAML mapping"]

    errors: list[str] = []

    manifest_version = doc.get("manifest_version")
    if not isinstance(manifest_version, str) or not MANIFEST_VERSION_RE.match(
        manifest_version
    ):
        errors.append(
            "manifest_version must be a quoted MAJOR.MINOR string "
            f"(got {manifest_version!r})"
        )

    release_tag = doc.get("release_tag")
    if not isinstance(release_tag, str) or not RELEASE_TAG_RE.match(release_tag):
        errors.append(
            "release_tag must be a `v<SEMVER>` string "
            f"(got {release_tag!r})"
        )

    latest_version = doc.get("latest_version")
    if not isinstance(latest_version, str) or not SEMVER_RE.match(latest_version):
        errors.append(
            "latest_version must be a SemVer string "
            f"(got {latest_version!r})"
        )

    published_at_err = _validate_published_at(doc.get("published_at"))
    if published_at_err:
        errors.append(published_at_err)

    min_supported = doc.get("min_supported_version")
    if min_supported is not None:
        if not isinstance(min_supported, str) or not SEMVER_RE.match(min_supported):
            errors.append(
                "min_supported_version must be a SemVer string or null "
                f"(got {min_supported!r})"
            )

    # Cross-field invariant: min_supported_version MUST NOT exceed
    # latest_version. Mirrors the runtime check in
    # classic_update_core::notification::validate_notification_manifest.
    # A publisher typo like latest_version=9.1.0 with
    # min_supported_version=9.2.0 would otherwise ship and falsely
    # deprecate even the advertised latest build. Only compared when
    # both fields pass shape validation — otherwise the caller already
    # has a shape error to fix first.
    if (
        isinstance(latest_version, str)
        and SEMVER_RE.match(latest_version)
        and isinstance(min_supported, str)
        and SEMVER_RE.match(min_supported)
        and _semver_precedence_key(min_supported)
        > _semver_precedence_key(latest_version)
    ):
        errors.append(
            f"min_supported_version ({min_supported!r}) must not exceed "
            f"latest_version ({latest_version!r})"
        )

    errors.extend(_validate_display(doc.get("display")))

    # Unknown top-level keys: same rationale as for `display`. The Rust
    # decoder ignores unknown fields by design so newer manifests don't
    # break older clients, but source-side strictness prevents typos.
    known = {
        "manifest_version",
        "release_tag",
        "latest_version",
        "published_at",
        "min_supported_version",
        "display",
    }
    unknown = set(doc.keys()) - known
    if unknown:
        errors.append(f"top-level document has unexpected keys: {sorted(unknown)!r}")

    return errors


def validate_path(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as err:
        return [f"cannot read {path}: {err}"]
    try:
        doc = _YAML.load(text)
    except YAMLError as err:
        return [f"{path} does not parse as YAML: {err}"]
    return _validate_document(doc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Path to the app-notification.yaml source artifact",
    )
    args = parser.parse_args()

    errors = validate_path(args.source)
    if errors:
        for err in errors:
            _fail(err)
        return 1
    print(f"OK: {args.source} passes app-notification validation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
