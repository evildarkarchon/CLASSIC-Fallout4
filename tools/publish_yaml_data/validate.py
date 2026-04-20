"""Validate every shippable YAML file before a `yaml-data-v*` publish.

Run from the publish workflow (`.github/workflows/publish-yaml-data.yml`).
Parses every ``*.yaml`` file under ``CLASSIC Data/databases/`` and asserts:

- The file parses as a single YAML mapping document.
- The document has a root-level ``schema_version`` field.
- ``schema_version`` is a quoted string matching ``^\\d+\\.\\d+$`` — the
  same regex the client-side `SchemaVersion::from_str` implementation uses.
- The file's base name is listed in the client-schema-ranges metadata file
  (``CLASSIC Data/databases/client-schema-ranges.yaml``) so only curated
  shippable files reach a release.

Exit status is non-zero on any violation, with a one-line ``FAIL:`` message
per offending file to stderr. The workflow surfaces those lines in the job
log without any additional formatting.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from ruamel.yaml import YAML, YAMLError

# `pure=True` forces the pure-Python parser; the libyaml-backed C parser
# rejects the `foo::bar` bare-scalar pattern used by several
# `stack_contains_any` flow sequences in `CLASSIC Fallout4.yaml`, which the
# runtime Rust parser (`yaml-rust2`) accepts. Staying with the pure parser
# lets the workflow validate the file as-authored without requiring a
# repo-wide YAML rewrite.
_YAML = YAML(typ="safe", pure=True)

SCHEMA_VERSION_RE = re.compile(r"^\d+\.\d+$")


def _parse_schema_point(value: str) -> tuple[int, int]:
    """Convert a MAJOR.MINOR string to a comparable tuple.

    Caller is responsible for pre-matching `SCHEMA_VERSION_RE`; this helper
    only splits and integer-casts so the ordering comparison is numeric
    (``"1.10" > "1.9"`` must be true, which lexical comparison gets wrong).
    """
    major_str, minor_str = value.split(".", 1)
    return (int(major_str), int(minor_str))


def _validate_range_field(
    schema_ranges_path: Path, entry: dict[str, object], field: str
) -> str:
    """Extract and format-validate one schema-range field. Returns the raw
    string on success; raises ``SystemExit`` with a ``FAIL:`` diagnostic on
    any shape violation.

    Fails on the same surfaces the client-side ``SchemaVersion`` parser
    rejects: missing key, non-string value (unquoted `1.0` parses as a
    float), or anything that does not match ``^\\d+\\.\\d+$``. Catching these
    at publish time prevents a silent mis-edit from turning into a
    channel-wide outage where every client rejects the manifest at runtime
    with no CI signal ever firing.
    """
    if field not in entry:
        raise SystemExit(
            f"FAIL: {schema_ranges_path} entry {entry!r} missing '{field}'"
        )
    value = entry[field]
    if not isinstance(value, str):
        raise SystemExit(
            f"FAIL: {schema_ranges_path} entry {entry.get('name', entry)!r}: "
            f"{field} must be a quoted string, got {type(value).__name__} ({value!r})"
        )
    if not SCHEMA_VERSION_RE.match(value):
        raise SystemExit(
            f"FAIL: {schema_ranges_path} entry {entry.get('name', entry)!r}: "
            f"{field}={value!r} does not match regex ^\\d+\\.\\d+$"
        )
    return value


def load_shippable_names(schema_ranges_path: Path) -> set[str]:
    """Return the set of shippable file base names from the ranges metadata.

    Also validates each entry's ``min_client_schema`` / ``max_client_schema``
    format and ordering so a typo like ``"1.x"`` or an inverted range
    (``min > max``) fails here rather than reaching ``generate_manifest.py``
    or — worse — producing a manifest.json that every client rejects at
    runtime.
    """
    with schema_ranges_path.open("r", encoding="utf-8") as f:
        doc = _YAML.load(f)
    if not isinstance(doc, dict) or "files" not in doc:
        raise SystemExit(
            f"FAIL: {schema_ranges_path} has no top-level 'files' list"
        )
    # Reject duplicate `files[].name` entries here so the published manifest
    # can never list two rows for the same target. Client-side
    # `validate_manifest` rejects the same shape, but guarding at publish time
    # keeps a mis-edited ranges file from reaching a release at all.
    names: set[str] = set()
    for entry in doc["files"]:
        if not isinstance(entry, dict) or "name" not in entry:
            raise SystemExit(
                f"FAIL: {schema_ranges_path} entry missing 'name': {entry!r}"
            )
        name = str(entry["name"])
        if name in names:
            raise SystemExit(
                f"FAIL: {schema_ranges_path} contains duplicate entry for "
                f"{name!r}; each file must appear at most once"
            )
        names.add(name)

        min_raw = _validate_range_field(schema_ranges_path, entry, "min_client_schema")
        max_raw = _validate_range_field(schema_ranges_path, entry, "max_client_schema")
        # Compare as (major, minor) tuples so "1.10" > "1.9" evaluates
        # numerically; string comparison would mis-rank two-digit minors.
        if _parse_schema_point(min_raw) > _parse_schema_point(max_raw):
            raise SystemExit(
                f"FAIL: {schema_ranges_path} entry {name!r}: "
                f"min_client_schema={min_raw!r} > max_client_schema={max_raw!r} "
                "(declared range is empty; no client could ever accept it)"
            )

    if not names:
        raise SystemExit(f"FAIL: {schema_ranges_path} contains no files")
    return names


def validate_file(path: Path) -> list[str]:
    """Return a list of violation messages for one YAML file (empty = pass)."""
    errors: list[str] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            doc = _YAML.load(f)
    except YAMLError as exc:
        return [f"FAIL: {path}: unparseable YAML: {exc}"]

    if not isinstance(doc, dict):
        return [f"FAIL: {path}: root document is not a mapping"]

    if "schema_version" not in doc:
        errors.append(f"FAIL: {path}: missing root-level schema_version")
        return errors

    value = doc["schema_version"]
    # Explicit type check rejects unquoted numbers (e.g., `schema_version: 1.0`
    # parses as a float) — those are malformed per the spec.
    if not isinstance(value, str):
        errors.append(
            f"FAIL: {path}: schema_version must be a quoted string, "
            f"got {type(value).__name__} ({value!r})"
        )
        return errors

    if not SCHEMA_VERSION_RE.match(value):
        errors.append(
            f"FAIL: {path}: schema_version {value!r} does not match "
            r"regex ^\d+\.\d+$"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--databases-dir",
        type=Path,
        required=True,
        help="Path to CLASSIC Data/databases/",
    )
    parser.add_argument(
        "--schema-ranges",
        type=Path,
        default=None,
        help=(
            "Path to client-schema-ranges.yaml "
            "(defaults to <databases-dir>/client-schema-ranges.yaml)"
        ),
    )
    args = parser.parse_args()

    databases_dir: Path = args.databases_dir
    if not databases_dir.is_dir():
        print(f"FAIL: {databases_dir} is not a directory", file=sys.stderr)
        return 1

    schema_ranges_path: Path = (
        args.schema_ranges
        if args.schema_ranges is not None
        else databases_dir / "client-schema-ranges.yaml"
    )
    if not schema_ranges_path.is_file():
        print(
            f"FAIL: client-schema-ranges file {schema_ranges_path} is missing",
            file=sys.stderr,
        )
        return 1

    shippable = load_shippable_names(schema_ranges_path)

    # Scan every *.yaml, skipping the ranges file itself — it has no
    # schema_version field and is validated structurally above.
    all_errors: list[str] = []
    seen_shippable: set[str] = set()
    yaml_files = sorted(databases_dir.glob("*.yaml"))
    if not yaml_files:
        print(f"FAIL: {databases_dir} contains no *.yaml files", file=sys.stderr)
        return 1

    for path in yaml_files:
        if path.resolve() == schema_ranges_path.resolve():
            continue
        errors = validate_file(path)
        if path.name in shippable:
            seen_shippable.add(path.name)
        elif not errors:
            # A *.yaml file with a valid schema_version but not listed in the
            # ranges metadata would still ship today because we upload *.yaml
            # below; flag that as a missing ranges entry instead of a silent
            # drift.
            errors.append(
                f"FAIL: {path}: shippable YAML not listed in {schema_ranges_path.name}"
            )
        all_errors.extend(errors)

    missing_shippable = shippable - seen_shippable
    for name in sorted(missing_shippable):
        all_errors.append(
            f"FAIL: {name} listed in {schema_ranges_path.name} "
            f"but not found in {databases_dir}"
        )

    if all_errors:
        for line in all_errors:
            print(line, file=sys.stderr)
        return 1

    print(f"OK: validated {len(seen_shippable)} shippable YAML files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
