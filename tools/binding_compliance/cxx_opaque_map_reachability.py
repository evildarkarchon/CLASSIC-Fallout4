"""Negative reachability proof for CXX opaque maps with no exposed producer."""

import argparse
import json
import re
from pathlib import Path

# The source tokenizer moved here from the retired Node package-metadata proof
# (Retire, #304); this script is its last consumer until T1 deletes it.
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
            result.append(source[index: end + len(terminator)])
            index = end + len(terminator)
            continue
        token = _TOKEN.match(source, index)
        if token is None:
            raise ValueError("unsupported source token")
        result.append(token[0])
        index = token.end()
    return result


_DECLARATIONS = (
    "fn string_map_get(map: &StringMap, key: &str) -> String;",
    "fn string_map_contains(map: &StringMap, key: &str) -> bool;",
    "fn string_map_keys(map: &StringMap) -> Vec<String>;",
    "fn string_map_values(map: &StringMap) -> Vec<String>;",
    "fn string_map_len(map: &StringMap) -> usize;",
    "fn string_map_is_empty(map: &StringMap) -> bool;",
    "fn string_vec_map_get(map: &StringVecMap, key: &str) -> Vec<String>;",
    "fn string_vec_map_contains(map: &StringVecMap, key: &str) -> bool;",
    "fn string_vec_map_keys(map: &StringVecMap) -> Vec<String>;",
    "fn string_vec_map_len(map: &StringVecMap) -> usize;",
    "fn string_vec_map_is_empty(map: &StringVecMap) -> bool;",
)


def _rust_tokens(source: str) -> list[str]:
    """Keep lifetime-bound references visible instead of treating them as character strings."""
    return _tokens(re.sub(r"'([A-Za-z_][A-Za-z_0-9]*)\b(?!')", r"lifetime_\1", source))


def validate_cxx_opaque_map_reachability(repo_root: Path) -> frozenset[str]:
    """Require the closed read-only CXX surface and absence of any additional producer path.

    New aliases, callbacks, outputs, exported ABIs, or macro-generated exposure
    revoke this narrow disposition. Getter behavior is deliberately not proved;
    the retained Rust tests still own it. Raises ``ValueError`` for any expanded
    graph or missing source evidence and returns the unreachable export names.
    """
    crate = repo_root.resolve() / "cpp-bindings/classic-cpp-bridge"
    build = _tokens((crate / "build.rs").read_text(encoding="utf-8"))
    if build.count('"src/types.rs"') != 1 or '"src/types_tests.rs"' in build:
        raise ValueError(
            "opaque map module must remain the reviewed production bridge input"
        )
    source = _rust_tokens((crate / "src/types.rs").read_text(encoding="utf-8"))
    surface = _tokens(
        '#[cxx::bridge(namespace = "classic::types")] mod ffi { extern "Rust" { type StringMap; type StringVecMap; '
        + " ".join(_DECLARATIONS)
        + " } }"
    )
    starts = [
        index
        for index in range(len(source))
        if source[index: index + len(surface)] == surface
    ]
    if len(starts) != 1:
        raise ValueError(
            "opaque map CXX surface gained or changed an exposed reference"
        )
    start = starts[0]
    outside = source[:start] + source[start + len(surface):]
    if any(
            token in outside
            for token in ("extern", "type", "!", "no_mangle", "export_name", "bridge")
    ):
        raise ValueError(
            "opaque map module gained an alias, macro, or additional exported ABI"
        )
    guarded_tests = _tokens('#[cfg(test)] #[path = "types_tests.rs"] mod tests;')
    if not any(
            outside[index: index + len(guarded_tests)] == guarded_tests
            for index in range(len(outside))
    ):
        raise ValueError("opaque map construction tests must remain test-only")
    for path in (crate / "src").rglob("*.rs"):
        if path.name in {"types.rs", "types_tests.rs"} and path.parent == crate / "src":
            continue
        tokens = _rust_tokens(path.read_text(encoding="utf-8"))
        if {"StringMap", "StringVecMap"}.intersection(tokens):
            raise ValueError(
                f"additional opaque map reference outside closed module: {path.relative_to(crate)}"
            )
    return frozenset(
        declaration.split("(", 1)[0].removeprefix("fn ")
        for declaration in _DECLARATIONS
    )


def main() -> int:
    """Run the blocking negative proof without granting accessor runtime coverage."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    args = parser.parse_args()
    try:
        exports = validate_cxx_opaque_map_reachability(args.repo_root)
    except (OSError, ValueError) as error:
        print(f"CXX opaque map reachability failed: {error}")
        return 1
    print(
        json.dumps(
            {"evidenceKind": "negative", "unreachableExports": sorted(exports)},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
