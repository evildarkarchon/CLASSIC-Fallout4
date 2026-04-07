#!/usr/bin/env python3
"""Generate Rust->CXX bridge parity baseline artifacts.

This module contains the shared parser used by both generate_baseline.py
(standalone bootstrap) and check_parity_gate.py (read-only diff).

Architecture:
    parse_cxx_bridge_surface(repo_root, bridge_crate_rel)
      -> build.rs text -> parse_build_rs_file_list() -> file list
      -> for each file: source -> extract_ffi_block() -> ffi body
      -> parse items from ffi body:
            * opaque types      (type Foo;)
            * shared structs    (struct Foo { ... })
            * shared enums      (enum Foo { ... })      + strip #[derive] + strip discriminants
            * extern "Rust"     functions                (blockOrigin="Rust")
            * extern "C++"      items                    (blockOrigin="C++", ignore include!())
      -> sort rows by (bridgeModule, kind, rustSymbol)
      -> return { "generated_at_utc": ..., "entries": [...] }

All output is deterministic (Pitfall 8 / Parser Determinism Guarantees):
    - Entry order: sorted by (bridgeModule, kind, rustSymbol)
    - id field: sha256(f"{rustSymbol}:{kind}:{bridgeModule}")[:16]
    - Signature whitespace normalized via re.sub(r'\\s+', ' ', s).strip()
    - Struct field / enum variant lists preserve source order (NOT sorted)
    - JSON key insertion order fixed by constructing dicts the same way every time
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---- JSON helper (mirrors tools/python_api_parity/generate_baseline.write_json) ----


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON with stable formatting: indent=2, sort_keys=False, trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


# ---- build.rs parser (D-07) ----

_BRIDGES_RE = re.compile(r'cxx_build::bridges\s*\(\s*\[(.*?)\]\s*\)', re.DOTALL)
_QUOTED_STR_RE = re.compile(r'"([^"]+)"')


def parse_build_rs_file_list(build_rs_source: str) -> list[str]:
    """Extract the file list from `cxx_build::bridges([...])`.

    Raises ValueError if the bridges() call is missing (D-07: no hardcoded fallback).
    """
    match = _BRIDGES_RE.search(build_rs_source)
    if match is None:
        raise ValueError(
            "build.rs does not contain a cxx_build::bridges([...]) call; "
            "gate cannot enumerate bridge files (no hardcoded fallback -- D-07)."
        )
    return _QUOTED_STR_RE.findall(match.group(1))


# ---- ffi block extraction (Pitfall 1) ----

_BRIDGE_ATTR_RE = re.compile(
    r'#\[cxx::bridge(?:\(\s*namespace\s*=\s*"([^"]+)"\s*\))?\]'
)


def extract_ffi_block(source: str) -> tuple[str | None, str]:
    """Find the #[cxx::bridge] attribute and extract the balanced `mod ffi { ... }` block.

    Uses a brace-depth counter (NOT regex) to find the outer closing brace so
    nested struct field blocks do not terminate the extraction early.

    Returns (ffi_body_without_braces_or_None, namespace_or_empty_string).
    The caller receives the INNER content of mod ffi { ... } -- outer braces stripped.
    """
    attr_match = _BRIDGE_ATTR_RE.search(source)
    if attr_match is None:
        return None, ""
    namespace = attr_match.group(1) or ""
    # Find `mod ffi {` after the attribute.
    mod_idx = source.find("mod ffi", attr_match.end())
    if mod_idx == -1:
        return None, namespace
    open_brace = source.find("{", mod_idx)
    if open_brace == -1:
        return None, namespace
    depth = 0
    for i, ch in enumerate(source[open_brace:], open_brace):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[open_brace + 1:i], namespace
    return None, namespace


# ---- item parsers ----

# Strip #[...] attribute lines (Pitfall 5) before regex-scanning for struct/enum names.
_ATTR_LINE_RE = re.compile(r'^[ \t]*#\[[^\]]*\][ \t]*\r?\n', re.MULTILINE)

# Inline comment stripping helpers (used before struct/enum body scans)
_LINE_COMMENT_RE = re.compile(r'//[^\n]*')
_BLOCK_COMMENT_RE = re.compile(r'/\*.*?\*/', re.DOTALL)

_OPAQUE_TYPE_RE = re.compile(r'\btype\s+([A-Za-z_][A-Za-z0-9_]*)\s*;')

# extern blocks -- track positions for block-origin attribution
_EXTERN_RUST_RE = re.compile(r'extern\s+"Rust"\s*\{')
_EXTERN_CPP_RE = re.compile(r'unsafe\s+extern\s+"C\+\+"\s*\{')

# Inside an extern block, parse functions. Multi-line signatures supported via DOTALL.
# Function form: `fn name(args) -> RetType;` or `fn name(args);`
_FUNCTION_RE = re.compile(
    r'\bfn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)\s*(?:->\s*([^;{]+?))?\s*;',
    re.DOTALL,
)
_INCLUDE_MACRO_RE = re.compile(r'include!\s*\(\s*"[^"]*"\s*\)\s*;')


def _normalize_ws(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


def _make_id(rust_symbol: str, kind: str, bridge_module: str) -> str:
    return hashlib.sha256(
        f"{rust_symbol}:{kind}:{bridge_module}".encode("utf-8")
    ).hexdigest()[:16]


def _split_top_level_commas(text: str) -> list[str]:
    """Split on commas that are NOT inside angle brackets / parens / square brackets."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in text:
        if ch in "<([":
            depth += 1
            current.append(ch)
        elif ch in ">)]":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    tail = "".join(current)
    if tail.strip():
        parts.append(tail)
    return parts


def _parse_function_signature(params_text: str, return_text: str | None) -> dict[str, Any]:
    """Build the signature dict from raw parameter and return-type text.

    Params are split on top-level commas (the simple split is safe because CXX bridge
    function signatures do not use default arguments or tuple destructuring).
    Each parameter is either "name: type" or a lone "self" / "&self" reference.
    """
    args: list[dict[str, str]] = []
    if params_text.strip():
        parts = _split_top_level_commas(params_text)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # `self: &Foo` style explicit-self parameters use the regular `name: type` form.
            if ":" in part:
                name, type_str = part.split(":", 1)
                args.append({"name": name.strip(), "type": _normalize_ws(type_str)})
            else:
                # bare "self" / "&self" / "&mut self" -- assign name="self".
                args.append({"name": "self", "type": _normalize_ws(part)})
    return_type = _normalize_ws(return_text) if return_text else None
    return {"args": args, "returnType": return_type}


def _strip_comments(text: str) -> str:
    """Strip line and block comments from a Rust source slice."""
    text = _BLOCK_COMMENT_RE.sub("", text)
    text = _LINE_COMMENT_RE.sub("", text)
    return text


def _parse_struct_fields(body: str) -> list[dict[str, str]]:
    """Extract ordered (name, type) pairs from a struct body.

    Field types may be compound (Vec<String>, nested struct references).
    Source order is preserved (Pitfall 3).
    """
    fields: list[dict[str, str]] = []
    body_clean = _strip_comments(body)
    for part in _split_top_level_commas(body_clean):
        part = part.strip()
        if not part or ":" not in part:
            continue
        # Skip attribute lines inside the struct body (defensive).
        if part.startswith("#"):
            continue
        name, type_str = part.split(":", 1)
        fields.append({"name": name.strip(), "type": _normalize_ws(type_str)})
    return fields


def _parse_enum_variants(body: str) -> list[str]:
    """Extract ordered variant names from an enum body.

    Handles `Variant = N,` discriminant form (Pitfall 4) by stripping everything
    from the `=` onward. Source order preserved.
    """
    variants: list[str] = []
    body_clean = _strip_comments(body)
    for part in _split_top_level_commas(body_clean):
        part = part.strip()
        if not part:
            continue
        # "Queued = 0" -> "Queued"
        name_part = part.split("=", 1)[0].strip()
        if name_part.startswith("#"):
            continue
        # Variant names are simple identifiers; reject anything with special chars.
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name_part):
            variants.append(name_part)
    return variants


def _find_balanced_block(text: str, start_search: int) -> tuple[int, int] | None:
    """Find the next `{ ... }` block in `text` starting at or after `start_search`.

    Returns (open_brace_index, close_brace_index) or None.
    Uses a brace counter so nested blocks do not confuse the match.
    """
    open_brace = text.find("{", start_search)
    if open_brace == -1:
        return None
    depth = 0
    for i in range(open_brace, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return (open_brace, i)
    return None


def _find_top_level_blocks(
    ffi_body: str,
    keyword: str,
) -> list[tuple[str, int, int]]:
    """Find all `<keyword> Name { ... }` blocks at the top level of an ffi body.

    Returns list of (name, body_start, body_end) tuples where body_start is the
    position just after the opening `{` and body_end is the position of the
    matching closing `}`. Skips matches that occur inside extern blocks (because
    those are handled separately).
    """
    # Pre-compute the spans of extern blocks so we can skip names that fall inside them.
    extern_spans: list[tuple[int, int]] = []
    for pattern in (_EXTERN_RUST_RE, _EXTERN_CPP_RE):
        for m in pattern.finditer(ffi_body):
            block = _find_balanced_block(ffi_body, m.start())
            if block is not None:
                extern_spans.append(block)

    def _inside_extern(pos: int) -> bool:
        for start, end in extern_spans:
            if start <= pos <= end:
                return True
        return False

    keyword_re = re.compile(rf'\b{keyword}\s+([A-Za-z_][A-Za-z0-9_]*)\b')
    results: list[tuple[str, int, int]] = []
    for m in keyword_re.finditer(ffi_body):
        if _inside_extern(m.start()):
            continue
        name = m.group(1)
        block = _find_balanced_block(ffi_body, m.end())
        if block is None:
            continue
        open_brace, close_brace = block
        results.append((name, open_brace + 1, close_brace))
    return results


def _find_extern_blocks(ffi_body: str) -> list[tuple[str, int, int]]:
    """Locate all extern "Rust" and unsafe extern "C++" blocks in the ffi body.

    Returns list of (block_origin, body_start, body_end) tuples where body_start
    is the position just after the opening `{` and body_end is the position of
    the matching closing `}`.
    """
    blocks: list[tuple[str, int, int]] = []
    for origin, pattern in (("Rust", _EXTERN_RUST_RE), ("C++", _EXTERN_CPP_RE)):
        for match in pattern.finditer(ffi_body):
            block = _find_balanced_block(ffi_body, match.start())
            if block is None:
                continue
            open_brace, close_brace = block
            blocks.append((origin, open_brace + 1, close_brace))
    return blocks


def _parse_ffi_body(
    ffi_body: str,
    bridge_module: str,
    source_file: str,
) -> list[dict[str, Any]]:
    """Parse a single ffi body into a list of contract rows.

    Handles structs/enums (top-level in ffi body) and extern Rust / extern C++ blocks
    (function + opaque type items inside them).
    """
    rows: list[dict[str, Any]] = []

    # Strip attribute lines so `enum` / `struct` name regex isn't contaminated (Pitfall 5).
    ffi_clean = _ATTR_LINE_RE.sub("", ffi_body)

    # --- Structs (top-level in ffi body, NOT inside extern blocks) ---
    for name, body_start, body_end in _find_top_level_blocks(ffi_clean, "struct"):
        body = ffi_clean[body_start:body_end]
        fields = _parse_struct_fields(body)
        rows.append({
            "id": _make_id(name, "struct", bridge_module),
            "rustSymbol": name,
            "kind": "struct",
            "bridgeModule": bridge_module,
            "sourceFile": source_file,
            "blockOrigin": "Rust",
            "fields": fields,
        })

    # --- Enums (top-level in ffi body, NOT inside extern blocks) ---
    for name, body_start, body_end in _find_top_level_blocks(ffi_clean, "enum"):
        body = ffi_clean[body_start:body_end]
        variants = _parse_enum_variants(body)
        rows.append({
            "id": _make_id(name, "enum", bridge_module),
            "rustSymbol": name,
            "kind": "enum",
            "bridgeModule": bridge_module,
            "sourceFile": source_file,
            "blockOrigin": "Rust",
            "variants": variants,
        })

    # --- Extern blocks (opaque types + functions) ---
    # Use the ORIGINAL ffi_body for extern block extraction so positions stay accurate
    # (the attribute strip can shift offsets in nested cases). Extern block bodies do
    # not need attribute stripping because cxx forbids attributes inside them.
    for origin, start, end in _find_extern_blocks(ffi_body):
        block_text = ffi_body[start:end]
        block_text = _strip_comments(block_text)
        # Strip include!() macros (Pitfall 7) before scanning for items.
        block_text = _INCLUDE_MACRO_RE.sub("", block_text)

        # Opaque types (`type Foo;`)
        for match in _OPAQUE_TYPE_RE.finditer(block_text):
            name = match.group(1)
            rows.append({
                "id": _make_id(name, "opaque", bridge_module),
                "rustSymbol": name,
                "kind": "opaque",
                "bridgeModule": bridge_module,
                "sourceFile": source_file,
                "blockOrigin": origin,
            })

        # Functions
        # Remove opaque-type declarations before the function scan so the function regex
        # does not try to match `type Foo;` as a malformed fn.
        fn_text = _OPAQUE_TYPE_RE.sub("", block_text)
        for match in _FUNCTION_RE.finditer(fn_text):
            fn_name = match.group(1)
            params_text = match.group(2)
            return_text = match.group(3)
            signature = _parse_function_signature(params_text, return_text)
            rows.append({
                "id": _make_id(fn_name, "function", bridge_module),
                "rustSymbol": fn_name,
                "kind": "function",
                "bridgeModule": bridge_module,
                "sourceFile": source_file,
                "blockOrigin": origin,
                "signature": signature,
            })

    return rows


# ---- Top-level orchestrator ----


def parse_cxx_bridge_surface(
    repo_root: Path,
    bridge_crate_rel: str = "ClassicLib-rs/cpp-bindings/classic-cpp-bridge",
) -> dict[str, Any]:
    """Parse every bridge file listed in build.rs and return a deterministic payload."""
    repo_root = Path(repo_root)
    bridge_crate = repo_root / bridge_crate_rel
    build_rs = bridge_crate / "build.rs"
    if not build_rs.exists():
        raise FileNotFoundError(f"build.rs not found at {build_rs}")
    file_list = parse_build_rs_file_list(build_rs.read_text(encoding="utf-8"))

    all_rows: list[dict[str, Any]] = []
    for rel in file_list:
        source_path = bridge_crate / rel
        if not source_path.exists():
            raise FileNotFoundError(
                f"Bridge source file listed in build.rs not found: {source_path}"
            )
        source_text = source_path.read_text(encoding="utf-8")
        ffi_body, _ns = extract_ffi_block(source_text)
        if ffi_body is None:
            raise ValueError(
                f"No `#[cxx::bridge] mod ffi` block found in {source_path}"
            )
        # bridgeModule = filename stem (e.g. "scangame" from "src/scangame.rs")
        bridge_module = Path(rel).stem
        # Always emit forward slashes for sourceFile.
        source_file_fwd = f"{bridge_crate_rel}/{rel}".replace("\\", "/")
        rows = _parse_ffi_body(ffi_body, bridge_module, source_file_fwd)
        all_rows.extend(rows)

    # Sort for determinism (RESEARCH.md line 807).
    all_rows.sort(key=lambda r: (r["bridgeModule"], r["kind"], r["rustSymbol"]))

    return {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "entries": all_rows,
    }


# ---- CLI entrypoint (used by Plan 02's bootstrap run) ----


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate CXX bridge parity baseline artifacts."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Repository root path.",
    )
    parser.add_argument(
        "--output-dir",
        default="ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts",
        help="Directory for generated artifacts, relative to repo root.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_dir = repo_root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    surface = parse_cxx_bridge_surface(repo_root)
    write_json(output_dir / "rust_api_surface.json", surface)

    print(
        f"Wrote surface JSON with {len(surface['entries'])} entries to "
        f"{output_dir / 'rust_api_surface.json'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
