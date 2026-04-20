"""Generate release-asset staging directory for a `yaml-data-v*` publish.

Reads the validated shippable YAML set from
``CLASSIC Data/databases/client-schema-ranges.yaml`` and, for every entry:

- Copies the source YAML to ``<staging>/<name>``.
- Computes sha256, writes ``<staging>/<name>.sha256`` in the conventional
  ``<hex>  <name>\\n`` format that matches the existing
  ``CLASSIC Fallout4.yaml.sha256`` sidecar.
- Assembles an entry in ``manifest.json`` with the fields defined by
  decision D-05 of the yaml-update-delivery proposal.

Every ``download_url`` is constructed from
``https://github.com/<owner>/<repo>/releases/download/<tag>/`` followed by
a URL-encoded asset name — the client rejects any other host, so the
construction happens in exactly one place.

The produced ``manifest.json`` has ``signatures: []``. Section 11a of the
yaml-update-delivery change adds a second post-processing step that fills in
the ``signatures`` array after cosign signs the manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from ruamel.yaml import YAML

# `pure=True` mirrors the parser choice in validate.py; see that module for
# the rationale around bare-scalar `foo::bar` patterns in flow sequences.
_YAML = YAML(typ="safe", pure=True)

CURRENT_MANIFEST_VERSION = 1

# Mirror of `validate.py::SCHEMA_VERSION_RE`. Duplicated here so a direct
# invocation of this script (outside the publish workflow) still catches
# malformed ranges rather than writing them verbatim into manifest.json,
# where they would turn every client into a runtime-rejection.
_SCHEMA_VERSION_RE = re.compile(r"^\d+\.\d+$")


def _parse_schema_point(value: str) -> tuple[int, int]:
    """Convert a MAJOR.MINOR string to a comparable (int, int) tuple."""
    major_str, minor_str = value.split(".", 1)
    return (int(major_str), int(minor_str))


def load_ranges(schema_ranges_path: Path) -> list[dict[str, str]]:
    """Return the validated ``files`` list from client-schema-ranges.yaml.

    Validates that each entry's ``min_client_schema`` and ``max_client_schema``
    are ``MAJOR.MINOR`` strings and that ``min <= max`` (tuple comparison, so
    ``"1.10"`` is correctly ordered above ``"1.9"``). The publish workflow
    normally runs ``validate.py`` first — this second pass exists so a direct
    ``python generate_manifest.py`` invocation cannot silently produce a
    manifest with a malformed or inverted range.
    """
    with schema_ranges_path.open("r", encoding="utf-8") as f:
        doc = _YAML.load(f)
    if not isinstance(doc, dict) or not isinstance(doc.get("files"), list):
        raise SystemExit(
            f"FAIL: {schema_ranges_path} has no top-level 'files' list"
        )
    required = {"name", "min_client_schema", "max_client_schema"}
    out: list[dict[str, str]] = []
    for entry in doc["files"]:
        if not isinstance(entry, dict):
            raise SystemExit(f"FAIL: ranges entry is not a mapping: {entry!r}")
        missing = required - entry.keys()
        if missing:
            raise SystemExit(
                f"FAIL: ranges entry {entry!r} missing keys: {sorted(missing)}"
            )

        name = str(entry["name"])
        for field in ("min_client_schema", "max_client_schema"):
            value = entry[field]
            if not isinstance(value, str):
                raise SystemExit(
                    f"FAIL: ranges entry {name!r}: {field} must be a quoted "
                    f"string, got {type(value).__name__} ({value!r})"
                )
            if not _SCHEMA_VERSION_RE.match(value):
                raise SystemExit(
                    f"FAIL: ranges entry {name!r}: {field}={value!r} does not "
                    r"match regex ^\d+\.\d+$"
                )

        if _parse_schema_point(str(entry["min_client_schema"])) > _parse_schema_point(
            str(entry["max_client_schema"])
        ):
            raise SystemExit(
                f"FAIL: ranges entry {name!r}: min_client_schema="
                f"{entry['min_client_schema']!r} > max_client_schema="
                f"{entry['max_client_schema']!r} (empty range)"
            )

        out.append({k: str(entry[k]) for k in required})
    return out


def read_schema_version(yaml_path: Path) -> str:
    """Pull the root ``schema_version`` string from a shippable YAML file."""
    with yaml_path.open("r", encoding="utf-8") as f:
        doc = _YAML.load(f)
    value = doc.get("schema_version") if isinstance(doc, dict) else None
    if not isinstance(value, str):
        raise SystemExit(
            f"FAIL: {yaml_path} has no string schema_version "
            "(run validate.py first)"
        )
    return value


def sha256_hex(path: Path) -> str:
    """Hex-encoded sha256 of a file, streaming to handle large YAML gracefully."""
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_sidecar(staging_path: Path, digest: str, _name: str) -> None:
    """Write a plain ``<hex>\\n`` sidecar matching the existing
    ``CLASSIC Fallout4.yaml.sha256`` format in the repo. The manifest already
    carries the filename, so the sidecar only needs the digest."""
    sidecar_path = staging_path.with_suffix(staging_path.suffix + ".sha256")
    sidecar_path.write_text(f"{digest}\n", encoding="utf-8")


def build_download_url(repo: str, tag: str, asset_name: str) -> str:
    """Return the canonical release-asset URL for one file."""
    # Use quote (not quote_plus) so spaces become %20, not '+'.
    encoded = urllib.parse.quote(asset_name, safe="")
    return f"https://github.com/{repo}/releases/download/{tag}/{encoded}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", required=True, help="Release tag, e.g. yaml-data-v2026.04.17")
    parser.add_argument("--repo", required=True, help='"<owner>/<repo>" (github.repository)')
    parser.add_argument("--databases-dir", type=Path, required=True)
    parser.add_argument(
        "--schema-ranges",
        type=Path,
        default=None,
        help="Defaults to <databases-dir>/client-schema-ranges.yaml",
    )
    parser.add_argument(
        "--staging",
        type=Path,
        required=True,
        help="Output directory to populate with release assets",
    )
    args = parser.parse_args()

    databases_dir: Path = args.databases_dir
    schema_ranges_path: Path = (
        args.schema_ranges
        if args.schema_ranges is not None
        else databases_dir / "client-schema-ranges.yaml"
    )
    staging: Path = args.staging
    staging.mkdir(parents=True, exist_ok=True)

    entries = load_ranges(schema_ranges_path)
    published_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )

    manifest_files: list[dict[str, object]] = []
    for entry in entries:
        name = entry["name"]
        source_path = databases_dir / name
        if not source_path.is_file():
            raise SystemExit(f"FAIL: shippable source missing: {source_path}")

        dest_path = staging / name
        shutil.copyfile(source_path, dest_path)

        digest = sha256_hex(dest_path)
        write_sidecar(dest_path, digest, name)

        manifest_files.append(
            {
                "name": name,
                "schema_version": read_schema_version(dest_path),
                "sha256": digest,
                "size_bytes": dest_path.stat().st_size,
                "min_client_schema": entry["min_client_schema"],
                "max_client_schema": entry["max_client_schema"],
                "download_url": build_download_url(args.repo, args.tag, name),
            }
        )

    manifest = {
        "manifest_version": CURRENT_MANIFEST_VERSION,
        "release_tag": args.tag,
        "published_at": published_at,
        "files": manifest_files,
        "signatures": [],
    }

    manifest_path = staging / "manifest.json"
    # Stable key order + trailing newline produces a clean diff if the
    # workflow is ever re-run deterministically; the only time-dependent
    # field is `published_at`.
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=False)
        f.write("\n")

    print(f"OK: staged {len(manifest_files)} files at {staging}")
    print(f"OK: wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
