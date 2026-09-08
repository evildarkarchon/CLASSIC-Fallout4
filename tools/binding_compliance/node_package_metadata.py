"""Narrow structural proof for the Node binding's compile-time Cargo version getter."""

import argparse
import json
import re
from pathlib import Path

import tomllib

_TOKEN = re.compile(
    r""""(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|[A-Za-z_]\w*|[^\s]"""
)
_RAW_STRING = re.compile(r'(?:br|r)(#*)"')


def _tokens(source: str) -> list[str]:
    """Tokenize code while keeping strings opaque and discarding nested comments."""
    result = []
    index = 0
    while index < len(source):
        if source[index].isspace():
            index += 1
            continue
        if source.startswith("//", index):
            end = source.find("\n", index)
            index = len(source) if end < 0 else end
            continue
        if source.startswith("/*", index):
            depth = 1
            index += 2
            while depth and index < len(source):
                if source.startswith("/*", index):
                    depth += 1
                    index += 2
                elif source.startswith("*/", index):
                    depth -= 1
                    index += 2
                else:
                    index += 1
            if depth:
                raise ValueError("unterminated source comment")
            continue
        raw = _RAW_STRING.match(source, index)
        if raw:
            terminator = '"' + raw[1]
            end = source.find(terminator, raw.end())
            if end < 0:
                raise ValueError("unterminated raw source string")
            result.append(source[index : end + len(terminator)])
            index = end + len(terminator)
            continue
        token = _TOKEN.match(source, index)
        if token is None:
            raise ValueError("unsupported source token")
        result.append(token[0])
        index = token.end()
    return result


def _require_export(
    source: str, expected: str, name: str, *, typescript: bool = False
) -> None:
    """Reject changed, nested, conditional, duplicate, or comment-only declarations."""
    tokens, wanted = _tokens(source), _tokens(expected)
    starts = [
        index
        for index in range(len(tokens))
        if tokens[index : index + len(wanted)] == wanted
    ]
    if len(starts) != 1 or tokens.count(name) != 1:
        raise ValueError(f"{name} is not the reviewed compile-time metadata export")
    index = starts[0]
    prefix = tokens[:index]
    if prefix.count("{") != prefix.count("}") or (
        not typescript and prefix and prefix[-1] not in {";", "}"}
    ):
        raise ValueError(f"{name} is not an unconditional top-level export")
    suffix = tokens[index + len(wanted) :]
    if typescript and suffix and suffix[0] not in {";", "export"}:
        raise ValueError(f"{name} declaration widens the metadata contract")


def validate_node_package_metadata(repo_root: Path) -> dict[str, str]:
    """Validate the exact Rust getter, TypeScript declaration, and resolved Cargo version.

    This proves one compile-time metadata disposition, never emitted runtime
    behavior. Any changed getter contract raises ``ValueError`` instead of
    extending structural ownership to arbitrary binding functions.
    """
    root = repo_root.resolve()
    package = root / "node-bindings/classic-node"
    source = (package / "src/lib.rs").read_text(encoding="utf-8")
    # A local/imported macro of the same name could change the apparent exact body.
    if _tokens(source).count("env") != 1:
        raise ValueError("metadata getter must use the unshadowed Cargo env macro")
    _require_export(
        source,
        '#[napi] pub fn get_version() -> String { env!("CARGO_PKG_VERSION").to_string() }',
        "get_version",
    )
    _require_export(
        (package / "index.d.ts").read_text(encoding="utf-8"),
        "export declare function getVersion(): string",
        "getVersion",
        typescript=True,
    )
    manifest = tomllib.loads((package / "Cargo.toml").read_text(encoding="utf-8"))
    if manifest.get("package", {}).get("name") != "classic-node":
        raise ValueError("metadata getter must belong to classic-node")
    version = manifest["package"].get("version")
    if (
        isinstance(version, dict)
        and set(version) == {"workspace"}
        and version["workspace"] is True
    ):
        workspace = tomllib.loads((root / "Cargo.toml").read_text(encoding="utf-8"))
        version = workspace.get("workspace", {}).get("package", {}).get("version")
    if not isinstance(version, str) or not re.fullmatch(
        r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", version
    ):
        raise ValueError(
            "Cargo package version must resolve to a semantic version string"
        )
    return {
        "binding": "node",
        "export": "getVersion",
        "rustPackageVersion": version,
        "evidenceKind": "structural",
    }


def main() -> int:
    """Run the blocking structural metadata check without certifying runtime coverage."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    args = parser.parse_args()
    try:
        print(
            json.dumps(validate_node_package_metadata(args.repo_root), sort_keys=True)
        )
    except (OSError, ValueError) as error:
        print(f"Node package metadata failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
