"""Drift guard: checked-in YAML headers vs client_schemas::* constants.

For every entry in ``CLASSIC Data/databases/client-schema-ranges.yaml``
that declares ``client_schemas_const: <NAME>``, this tool:

1. Parses ``pub const <NAME>: SchemaCompat = SchemaCompat::new(<MAJOR>, <MINOR>);``
   out of ``business-logic/classic-config-core/src/client_schemas.rs``.
2. Reads the root-level ``schema_version: "X.Y"`` from the actual bundled
   YAML file.
3. Fails if ``file.major != accepted_major`` OR ``file.minor < minimum_minor``.

The intent is catching the failure mode where a contributor bumps a shipped
YAML's ``schema_version`` without also raising the client constant (silent
refusal at load time) — or vice-versa.

Run via ``python tools/schema_version_gate.py`` from the repo root.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML # type: ignore

_YAML = YAML(typ="safe", pure=True)

# Matches `pub const IDENT: SchemaCompat = SchemaCompat::new(1, 2);` with
# permissive whitespace. The Rust source is machine-stable — if the declaration
# style ever changes, update both the source and this regex in the same PR.
CONST_RE = re.compile(
    r"pub\s+const\s+(?P<name>[A-Z][A-Z0-9_]*)\s*:\s*SchemaCompat\s*="
    r"\s*SchemaCompat::new\(\s*(?P<major>\d+)\s*,\s*(?P<minor>\d+)\s*\)",
)

SCHEMA_VERSION_RE = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)$")


@dataclass(frozen=True)
class ClientSchema:
    accepted_major: int
    minimum_minor: int


def parse_client_schemas(rs_path: Path) -> dict[str, ClientSchema]:
    """Return ``{const_name: ClientSchema(...)}`` by reading client_schemas.rs."""
    text = rs_path.read_text(encoding="utf-8")
    out: dict[str, ClientSchema] = {}
    for match in CONST_RE.finditer(text):
        out[match["name"]] = ClientSchema(
            accepted_major=int(match["major"]),
            minimum_minor=int(match["minor"]),
        )
    if not out:
        raise SystemExit(
            f"FAIL: {rs_path} contained no `pub const … SchemaCompat::new(…)` "
            "declarations — has the declaration style changed?"
        )
    return out


def load_ranges_entries(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8") as f:
        doc = _YAML.load(f)
    if not isinstance(doc, dict) or not isinstance(doc.get("files"), list):
        raise SystemExit(f"FAIL: {path} has no top-level `files` list")
    return list(doc["files"])


def read_file_schema(yaml_path: Path) -> tuple[int, int] | None:
    """Return ``(major, minor)`` from the file's root ``schema_version`` or
    ``None`` if absent/malformed (caller decides the failure message)."""
    with yaml_path.open("r", encoding="utf-8") as f:
        doc = _YAML.load(f)
    if not isinstance(doc, dict):
        return None
    value = doc.get("schema_version")
    if not isinstance(value, str):
        return None
    match = SCHEMA_VERSION_RE.match(value)
    if match is None:
        return None
    return int(match["major"]), int(match["minor"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current directory)",
    )
    args = parser.parse_args()

    repo_root: Path = args.repo_root.resolve()
    client_schemas_rs = (
        repo_root
        / "business-logic"
        / "classic-config-core"
        / "src"
        / "client_schemas.rs"
    )
    databases_dir = repo_root / "CLASSIC Data" / "databases"
    ranges_path = databases_dir / "client-schema-ranges.yaml"

    for path, label in (
        (client_schemas_rs, "client_schemas.rs"),
        (databases_dir, "databases directory"),
        (ranges_path, "client-schema-ranges.yaml"),
    ):
        if not path.exists():
            print(f"FAIL: {label} not found at {path}", file=sys.stderr)
            return 1

    client = parse_client_schemas(client_schemas_rs)
    entries = load_ranges_entries(ranges_path)

    all_errors: list[str] = []
    checked = 0
    for entry in entries:
        if not isinstance(entry, dict):
            all_errors.append(f"FAIL: ranges entry is not a mapping: {entry!r}")
            continue
        const_name = entry.get("client_schemas_const")
        file_name = entry.get("name")
        if not isinstance(file_name, str):
            all_errors.append(f"FAIL: ranges entry missing `name`: {entry!r}")
            continue
        if const_name is None:
            # An entry without a client_schemas_const is shippable but isn't
            # gated by a client-side constant yet. That's allowed — drift
            # guard only applies once the two sides are intentionally linked.
            continue
        if not isinstance(const_name, str):
            all_errors.append(
                f"FAIL: {file_name}: `client_schemas_const` must be a string"
            )
            continue
        if const_name not in client:
            all_errors.append(
                f"FAIL: {file_name}: client_schemas_const={const_name!r} "
                f"not found in {client_schemas_rs.name} — "
                "declare the constant or remove the binding"
            )
            continue

        yaml_path = databases_dir / file_name
        if not yaml_path.is_file():
            all_errors.append(
                f"FAIL: {file_name}: listed in client-schema-ranges.yaml "
                f"but missing from {databases_dir}"
            )
            continue

        file_version = read_file_schema(yaml_path)
        if file_version is None:
            all_errors.append(
                f"FAIL: {file_name}: root schema_version missing or not "
                "MAJOR.MINOR"
            )
            continue

        file_major, file_minor = file_version
        client_range = client[const_name]
        if file_major != client_range.accepted_major:
            all_errors.append(
                f"FAIL: {file_name}: schema_version MAJOR {file_major} != "
                f"client {const_name}.accepted_major {client_range.accepted_major} "
                "— either bump the client constant or revert the file header"
            )
            continue
        if file_minor < client_range.minimum_minor:
            all_errors.append(
                f"FAIL: {file_name}: schema_version MINOR {file_minor} < "
                f"client {const_name}.minimum_minor {client_range.minimum_minor} "
                "— lower the client constant or bump the file's schema_version"
            )
            continue

        checked += 1
        print(
            f"OK: {file_name} schema_version={file_major}.{file_minor} "
            f"accepted by {const_name} "
            f"(major={client_range.accepted_major}, "
            f"minor>={client_range.minimum_minor})"
        )

    if all_errors:
        for line in all_errors:
            print(line, file=sys.stderr)
        return 1

    if checked == 0:
        print(
            "WARN: no entries linked a client_schemas_const — drift guard "
            "checked nothing",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
