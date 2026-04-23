"""Generate the app-notification ``manifest.json`` from the source YAML.

Run from ``.github/workflows/publish-app-notification.yml`` after
``validate.py`` passes. Produces the final JSON the workflow uploads as a
release asset and mirrors to GitHub Pages.

The generator consumes only fields that the validator has already approved,
but it re-checks required fields before emitting so a change to the source
format is caught even if the validator is skipped locally.

If ``published_at`` in the source is ``null``, the generator fills it with
``--published-at`` (typically the tag's UTC publication timestamp from
``gh release view``) so the manifest a client fetches carries a stable,
workflow-provided RFC 3339 timestamp rather than "now".

Output is written to ``--output`` as UTF-8 JSON without a BOM, sorted keys
disabled to preserve the field order the Rust decoder expects.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML, YAMLError

_YAML = YAML(typ="safe", pure=True)


def _load_source(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as err:
        raise SystemExit(f"FAIL: cannot read {path}: {err}") from err
    try:
        doc = _YAML.load(text)
    except YAMLError as err:
        raise SystemExit(f"FAIL: {path} does not parse as YAML: {err}") from err
    if not isinstance(doc, dict):
        raise SystemExit(f"FAIL: {path} top-level document must be a mapping")
    return doc


def build_manifest(
    source: dict[str, Any], fallback_published_at: str | None
) -> dict[str, Any]:
    """Project validated source fields into the final manifest dict.

    Raises ``SystemExit`` with a ``FAIL:`` message on missing required
    fields so the caller surfaces a clean single-line error in the job log.
    """
    required = ("manifest_version", "release_tag", "latest_version")
    for key in required:
        value = source.get(key)
        if not isinstance(value, str) or not value.strip():
            raise SystemExit(f"FAIL: source missing required string field `{key}`")

    manifest: dict[str, Any] = {
        "manifest_version": source["manifest_version"],
        "release_tag": source["release_tag"],
        "latest_version": source["latest_version"],
    }

    published_at = source.get("published_at")
    if published_at is None:
        if not fallback_published_at:
            raise SystemExit(
                "FAIL: source `published_at` is null and no --published-at fallback "
                "was supplied"
            )
        manifest["published_at"] = fallback_published_at
    else:
        if not isinstance(published_at, str) or not published_at.strip():
            raise SystemExit(
                "FAIL: source `published_at` must be a non-empty string or null"
            )
        manifest["published_at"] = published_at

    min_supported = source.get("min_supported_version")
    if min_supported is not None:
        if not isinstance(min_supported, str) or not min_supported.strip():
            raise SystemExit(
                "FAIL: source `min_supported_version` must be null or a non-empty string"
            )
        manifest["min_supported_version"] = min_supported

    display = source.get("display")
    if display is not None:
        if not isinstance(display, dict):
            raise SystemExit("FAIL: source `display` must be a mapping or null")
        payload: dict[str, Any] = {}
        for key in ("title", "body"):
            value = display.get(key)
            if not isinstance(value, str):
                raise SystemExit(
                    f"FAIL: source `display.{key}` must be a string when display is set"
                )
            payload[key] = value
        cta = display.get("cta_url")
        if cta is not None:
            if not isinstance(cta, str) or not cta.strip():
                raise SystemExit(
                    "FAIL: source `display.cta_url` must be null/omitted or a non-empty string"
                )
            payload["cta_url"] = cta
        manifest["display"] = payload

    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Path to the app-notification.yaml source artifact",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to write the generated manifest.json",
    )
    parser.add_argument(
        "--published-at",
        default=None,
        help=(
            "RFC 3339 timestamp to substitute when the source sets "
            "published_at to null (e.g. the tag's UTC publication time)"
        ),
    )
    args = parser.parse_args()

    source = _load_source(args.source)
    manifest = build_manifest(source, args.published_at)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    # `sort_keys=False` keeps the human-friendly order
    # (manifest_version, release_tag, latest_version, published_at, ...)
    # that also matches the Rust `AppNotificationManifest` field order.
    args.output.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"OK: wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
