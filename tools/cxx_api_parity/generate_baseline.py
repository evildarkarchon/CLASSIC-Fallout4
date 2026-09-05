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

sys.path.append(str(Path(__file__).resolve().parents[1]))

from parity_artifact_io import preserve_baseline_generated_at, write_json
from parity_rust_surface import parse_rust_surface

CANONICAL_MAPPING_SCHEMA_VERSION = 1
CXX_CONTRACT_SCHEMA_VERSION = 2
DEFAULT_CANONICAL_MAPPINGS = "tools/cxx_api_parity/canonical_mappings.json"

_MAPPING_IDENTITY_FIELDS = frozenset({"id", "rustSymbol", "kind", "bridgeModule"})
_CANONICAL_MAPPING_FIELDS = frozenset({"ownerModule", "rustCrate", "coreRustSymbol"})
_BINDING_ONLY_MAPPING_FIELDS = frozenset({"unmappedReason"})
_ALL_MAPPING_FIELDS = _CANONICAL_MAPPING_FIELDS | _BINDING_ONLY_MAPPING_FIELDS


class CanonicalMappingError(ValueError):
    """Raised when canonical CXX mapping metadata is missing, stale, or invalid."""


# ---- JSON helper (mirrors tools/python_api_parity/generate_baseline.write_json) ----


# ---- build.rs parser (D-07) ----

_BRIDGES_RE = re.compile(r"cxx_build::bridges\s*\(\s*\[(.*?)\]\s*\)", re.DOTALL)
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
                return source[open_brace + 1 : i], namespace
    return None, namespace


# ---- item parsers ----

# Strip #[...] attribute lines (Pitfall 5) before regex-scanning for struct/enum names.
_ATTR_LINE_RE = re.compile(r"^[ \t]*#\[[^\]]*\][ \t]*\r?\n", re.MULTILINE)

# Inline comment stripping helpers (used before struct/enum body scans)
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)

_OPAQUE_TYPE_RE = re.compile(r"\btype\s+([A-Za-z_][A-Za-z0-9_]*)\s*;")

# extern blocks -- track positions for block-origin attribution
_EXTERN_RUST_RE = re.compile(r'extern\s+"Rust"\s*\{')
_EXTERN_CPP_RE = re.compile(r'unsafe\s+extern\s+"C\+\+"\s*\{')

# Inside an extern block, parse functions. Multi-line signatures supported via DOTALL.
# Function form: `fn name(args) -> RetType;` or `fn name(args);`
_FUNCTION_RE = re.compile(
    r"\bfn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)\s*(?:->\s*([^;{]+?))?\s*;",
    re.DOTALL,
)
_INCLUDE_MACRO_RE = re.compile(r'include!\s*\(\s*"[^"]*"\s*\)\s*;')


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


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


def _parse_function_signature(
    params_text: str, return_text: str | None
) -> dict[str, Any]:
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
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name_part):
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

    keyword_re = re.compile(rf"\b{keyword}\s+([A-Za-z_][A-Za-z0-9_]*)\b")
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

    # Strip comments for the same reason. The name scan below is a keyword regex over raw
    # text, so prose that merely *mentions* `enum Foo` or `struct Bar` -- which doc comments
    # explaining the bridge's own shape routinely do -- was being enumerated as a bridge item.
    # Three such phantoms sat in the committed baseline: `definitions` twice, from "cannot
    # share enum definitions", and `mirroring`. They were harmless as long as nobody edited
    # the sentence that produced them, and actively misleading the moment somebody did, since
    # a reworded comment surfaced as contract drift on a bridge that had not changed.
    #
    # Extern blocks are deliberately parsed from the ORIGINAL `ffi_body` below and strip their
    # own comments, so this affects only the struct/enum scan, whose offsets all live inside
    # `ffi_clean`.
    ffi_clean = _strip_comments(ffi_clean)

    # --- Structs (top-level in ffi body, NOT inside extern blocks) ---
    for name, body_start, body_end in _find_top_level_blocks(ffi_clean, "struct"):
        body = ffi_clean[body_start:body_end]
        fields = _parse_struct_fields(body)
        rows.append(
            {
                "id": _make_id(name, "struct", bridge_module),
                "rustSymbol": name,
                "kind": "struct",
                "bridgeModule": bridge_module,
                "sourceFile": source_file,
                "blockOrigin": "Rust",
                "fields": fields,
            }
        )

    # --- Enums (top-level in ffi body, NOT inside extern blocks) ---
    for name, body_start, body_end in _find_top_level_blocks(ffi_clean, "enum"):
        body = ffi_clean[body_start:body_end]
        variants = _parse_enum_variants(body)
        rows.append(
            {
                "id": _make_id(name, "enum", bridge_module),
                "rustSymbol": name,
                "kind": "enum",
                "bridgeModule": bridge_module,
                "sourceFile": source_file,
                "blockOrigin": "Rust",
                "variants": variants,
            }
        )

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
            rows.append(
                {
                    "id": _make_id(name, "opaque", bridge_module),
                    "rustSymbol": name,
                    "kind": "opaque",
                    "bridgeModule": bridge_module,
                    "sourceFile": source_file,
                    "blockOrigin": origin,
                }
            )

        # Functions
        # Remove opaque-type declarations before the function scan so the function regex
        # does not try to match `type Foo;` as a malformed fn.
        fn_text = _OPAQUE_TYPE_RE.sub("", block_text)
        for match in _FUNCTION_RE.finditer(fn_text):
            fn_name = match.group(1)
            params_text = match.group(2)
            return_text = match.group(3)
            signature = _parse_function_signature(params_text, return_text)
            rows.append(
                {
                    "id": _make_id(fn_name, "function", bridge_module),
                    "rustSymbol": fn_name,
                    "kind": "function",
                    "bridgeModule": bridge_module,
                    "sourceFile": source_file,
                    "blockOrigin": origin,
                    "signature": signature,
                }
            )

    return rows


# ---- Top-level orchestrator ----


def parse_cxx_bridge_surface(
    repo_root: Path,
    bridge_crate_rel: str = "cpp-bindings/classic-cpp-bridge",
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


def _nonempty_mapping_string(value: object, label: str) -> str:
    """Return one required mapping string or raise a field-specific error."""

    if not isinstance(value, str) or not value.strip():
        raise CanonicalMappingError(f"{label} must be a non-empty string")
    return value


def _index_rows_by_id(
    raw_rows: object,
    entries_label: str,
    duplicate_label: str,
) -> dict[str, dict[str, Any]]:
    """Validate an entry collection and index its object rows by unique string ID."""

    if not isinstance(raw_rows, list):
        raise CanonicalMappingError(f"{entries_label} must be a list")
    indexed: dict[str, dict[str, Any]] = {}
    for index, raw_row in enumerate(raw_rows):
        if not isinstance(raw_row, dict):
            raise CanonicalMappingError(f"{entries_label}[{index}] must be an object")
        row_id = _nonempty_mapping_string(
            raw_row.get("id"), f"{entries_label}[{index}].id"
        )
        if row_id in indexed:
            raise CanonicalMappingError(f"duplicate {duplicate_label} {row_id!r}")
        indexed[row_id] = raw_row
    return indexed


def enrich_surface_with_canonical_mappings(
    surface: dict[str, Any],
    mappings: dict[str, Any],
) -> dict[str, Any]:
    """Attach reviewed canonical or binding-only metadata to every parsed CXX row.

    The mapping inventory is exact: every source-derived row must appear once and
    every mapping must still point at a current row. The returned payload is a new
    object, and stable row IDs plus the source-only bridge fields remain unchanged.
    """

    if not isinstance(mappings, dict):
        raise CanonicalMappingError("canonical mapping document must be an object")
    if mappings.get("schema_version") != CANONICAL_MAPPING_SCHEMA_VERSION:
        raise CanonicalMappingError(
            "canonical mapping schema_version must be "
            f"{CANONICAL_MAPPING_SCHEMA_VERSION}"
        )
    surface_by_id = _index_rows_by_id(
        surface.get("entries"), "surface entries", "CXX surface row id"
    )
    mapping_by_id = _index_rows_by_id(
        mappings.get("entries"),
        "canonical mapping entries",
        "canonical mapping id",
    )

    surface_ids = set(surface_by_id)
    mapping_ids = set(mapping_by_id)
    missing = sorted(surface_ids - mapping_ids)
    stale = sorted(mapping_ids - surface_ids)
    if missing:
        raise CanonicalMappingError(
            "missing canonical mappings for CXX row ids: " + ", ".join(missing)
        )
    if stale:
        raise CanonicalMappingError(
            "stale canonical mappings for removed CXX row ids: " + ", ".join(stale)
        )

    enriched_rows: list[dict[str, Any]] = []
    for raw_row in surface_by_id.values():
        row_id = raw_row["id"]
        mapping = mapping_by_id[row_id]
        canonical_present = _CANONICAL_MAPPING_FIELDS.intersection(mapping)
        binding_only_present = _BINDING_ONLY_MAPPING_FIELDS.intersection(mapping)
        is_canonical = canonical_present == _CANONICAL_MAPPING_FIELDS
        is_binding_only = (
            binding_only_present == _BINDING_ONLY_MAPPING_FIELDS
            and not canonical_present
        )
        if not (is_canonical ^ is_binding_only):
            raise CanonicalMappingError(
                f"canonical mapping {row_id!r} must have exactly one mapping "
                "classification: ownerModule/rustCrate/coreRustSymbol or unmappedReason"
            )

        expected_fields = _MAPPING_IDENTITY_FIELDS.union(
            _CANONICAL_MAPPING_FIELDS if is_canonical else _BINDING_ONLY_MAPPING_FIELDS
        )
        if set(mapping) != expected_fields:
            unexpected = sorted(set(mapping) - expected_fields)
            missing_fields = sorted(expected_fields - set(mapping))
            raise CanonicalMappingError(
                f"canonical mapping {row_id!r} has invalid fields; "
                f"missing={missing_fields}, unexpected={unexpected}"
            )

        for field in ("rustSymbol", "kind", "bridgeModule"):
            mapped_value = _nonempty_mapping_string(
                mapping.get(field), f"canonical mapping {row_id!r}.{field}"
            )
            if mapped_value != raw_row.get(field):
                raise CanonicalMappingError(
                    f"canonical mapping {row_id!r} identity metadata for {field} "
                    f"is {mapped_value!r}, expected {raw_row.get(field)!r}"
                )

        # Keep insertion order deterministic in generated JSON; iterating the
        # frozensets used for validation would vary with Python's hash seed.
        metadata_fields = (
            ("ownerModule", "rustCrate", "coreRustSymbol")
            if is_canonical
            else ("unmappedReason",)
        )
        metadata = {
            field: _nonempty_mapping_string(
                mapping.get(field), f"canonical mapping {row_id!r}.{field}"
            )
            for field in metadata_fields
        }
        enriched_rows.append({**raw_row, **metadata})

    return {**surface, "entries": enriched_rows}


def validate_committed_canonical_metadata(
    contract: dict[str, Any],
    current_surface: dict[str, Any],
) -> None:
    """Require committed mapping metadata to match the independently enriched model.

    Only row IDs present in both models are checked here. Added and removed bridge
    rows remain the responsibility of the source-only parity diff, which preserves
    its established drift categories and comparison semantics.
    """

    committed_by_id = _index_rows_by_id(
        contract.get("entries"),
        "committed CXX contract entries",
        "committed CXX contract row id",
    )
    current_by_id = _index_rows_by_id(
        current_surface.get("entries"),
        "current CXX surface entries",
        "current CXX surface row id",
    )
    mismatched_ids = []
    for row_id in sorted(set(committed_by_id) & set(current_by_id)):
        committed_metadata = {
            field: committed_by_id[row_id][field]
            for field in _ALL_MAPPING_FIELDS
            if field in committed_by_id[row_id]
        }
        current_metadata = {
            field: current_by_id[row_id][field]
            for field in _ALL_MAPPING_FIELDS
            if field in current_by_id[row_id]
        }
        if committed_metadata != current_metadata:
            mismatched_ids.append(row_id)

    if mismatched_ids:
        raise CanonicalMappingError(
            "stale canonical metadata in committed CXX rows: "
            + ", ".join(mismatched_ids)
        )


def validate_canonical_mapping_targets(
    repo_root: Path,
    mappings: dict[str, Any],
) -> None:
    """Require every canonical mapping to resolve on the live Rust public surface.

    ``rustCrates`` is a reviewed crate/owner/path catalog inside the mapping
    document. A target that exists only as a Rust module is rejected because a
    module is not a public capability symbol that a binding row can observe.
    """

    expected_document_fields = {"schema_version", "rustCrates", "entries"}
    if set(mappings) != expected_document_fields:
        raise CanonicalMappingError(
            "canonical mapping document must contain exactly schema_version, "
            "rustCrates, and entries"
        )
    raw_crates = mappings.get("rustCrates")
    if not isinstance(raw_crates, list):
        raise CanonicalMappingError("canonical mappings rustCrates must be a list")

    target_crates: dict[str, str] = {}
    owner_by_crate: dict[str, str] = {}
    crate_fields = {"ownerModule", "rustCrate", "libRs"}
    for index, raw_crate in enumerate(raw_crates):
        if not isinstance(raw_crate, dict) or set(raw_crate) != crate_fields:
            raise CanonicalMappingError(
                f"canonical mappings rustCrates[{index}] must contain exactly "
                "ownerModule, rustCrate, and libRs"
            )
        owner = _nonempty_mapping_string(
            raw_crate.get("ownerModule"), f"rustCrates[{index}].ownerModule"
        )
        crate = _nonempty_mapping_string(
            raw_crate.get("rustCrate"), f"rustCrates[{index}].rustCrate"
        )
        lib_rs = _nonempty_mapping_string(
            raw_crate.get("libRs"), f"rustCrates[{index}].libRs"
        )
        lib_path = Path(lib_rs)
        if (
            lib_path.is_absolute()
            or ".." in lib_path.parts
            or "\\" in lib_rs
            or lib_path.as_posix() != lib_rs
        ):
            raise CanonicalMappingError(
                f"rustCrates[{index}].libRs must be a canonical repository-relative path"
            )
        if crate in target_crates:
            raise CanonicalMappingError(f"duplicate canonical Rust crate {crate!r}")
        target_crates[crate] = lib_rs
        owner_by_crate[crate] = owner

    mapping_rows = mappings.get("entries")
    if not isinstance(mapping_rows, list):
        raise CanonicalMappingError("canonical mapping entries must be a list")
    canonical_rows = [
        row
        for row in mapping_rows
        if isinstance(row, dict) and _CANONICAL_MAPPING_FIELDS.issubset(row)
    ]
    used_crates = {str(row["rustCrate"]) for row in canonical_rows}
    missing_catalog_crates = sorted(used_crates - set(target_crates))
    stale_catalog_crates = sorted(set(target_crates) - used_crates)
    if missing_catalog_crates:
        raise CanonicalMappingError(
            "canonical mapping rows reference uncatalogued Rust crates: "
            + ", ".join(missing_catalog_crates)
        )
    if stale_catalog_crates:
        raise CanonicalMappingError(
            "canonical mappings contain stale unused Rust crates: "
            + ", ".join(stale_catalog_crates)
        )

    try:
        rust_surface = parse_rust_surface(
            Path(repo_root), target_crates, owner_by_crate
        )
    except (OSError, KeyError, ValueError) as error:
        raise CanonicalMappingError(
            f"cannot inspect canonical Rust targets: {error}"
        ) from error
    live_targets = {
        (entry["owner_module"], entry["crate"], entry["symbol"])
        for entry in rust_surface["symbols"]
        if entry.get("kind") != "module"
    }
    requested_targets = {
        (row["ownerModule"], row["rustCrate"], row["coreRustSymbol"])
        for row in canonical_rows
    }
    missing_targets = sorted(requested_targets - live_targets)
    if missing_targets:
        rendered = ", ".join("/".join(target) for target in missing_targets)
        raise CanonicalMappingError(f"missing live Rust targets: {rendered}")


def generate_cxx_parity_model(
    repo_root: Path,
    bridge_crate_rel: str = "cpp-bindings/classic-cpp-bridge",
    canonical_mappings_rel: str = DEFAULT_CANONICAL_MAPPINGS,
) -> dict[str, Any]:
    """Generate the source-derived CXX model with reviewed canonical metadata.

    Raises ``CanonicalMappingError`` when the inventory cannot be read or does
    not exactly cover the current bridge rows.
    """

    surface = parse_cxx_bridge_surface(repo_root, bridge_crate_rel)
    mapping_path = Path(repo_root) / canonical_mappings_rel
    try:
        mappings = json.loads(mapping_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CanonicalMappingError(
            f"cannot read canonical CXX mappings from {mapping_path}: {error}"
        ) from error
    enriched = enrich_surface_with_canonical_mappings(surface, mappings)
    validate_canonical_mapping_targets(repo_root, mappings)
    return enriched


# ---- Diff report generation ----


def _row_key(row: dict[str, Any]) -> str:
    """Stable key for diff matching. Uses id (sha256(sym:kind:module)[:16])."""
    return row["id"]


def _normalize_row_for_compare(row: dict[str, Any]) -> dict[str, Any]:
    """Return a stripped copy of a row suitable for equality comparison.

    Strips the id field (already part of the key) and keeps only the
    semantic content: signature (functions), fields (structs), variants
    (enums), blockOrigin (always). sourceFile is NOT compared because
    moving a file does not change the API contract.
    """
    kind = row["kind"]
    result: dict[str, Any] = {
        "rustSymbol": row["rustSymbol"],
        "kind": kind,
        "bridgeModule": row["bridgeModule"],
        "blockOrigin": row.get("blockOrigin", "Rust"),
    }
    if kind == "function":
        result["signature"] = row.get("signature", {})
    elif kind == "struct":
        result["fields"] = row.get("fields", [])
    elif kind == "enum":
        result["variants"] = row.get("variants", [])
    # opaque has no additional comparable fields
    return result


def generate_diff_report(
    contract: dict[str, Any],
    current_surface: dict[str, Any],
) -> dict[str, Any]:
    """Compare committed baseline (contract) against fresh surface."""
    contract_rows = {_row_key(r): r for r in contract.get("entries", [])}
    current_rows = {_row_key(r): r for r in current_surface.get("entries", [])}

    contract_results: list[dict[str, Any]] = []
    matched_count = 0
    missing_from_current = 0
    signature_mismatch = 0

    for row_id, c_row in contract_rows.items():
        base = {
            "id": row_id,
            "rustSymbol": c_row["rustSymbol"],
            "kind": c_row["kind"],
            "bridgeModule": c_row["bridgeModule"],
        }
        if row_id not in current_rows:
            missing_from_current += 1
            contract_results.append(
                {
                    **base,
                    "status": "missing_from_current",
                    "reason": (
                        f"Symbol `{c_row['rustSymbol']}` in baseline but not in "
                        f"current bridge source for module `{c_row['bridgeModule']}`"
                    ),
                }
            )
            continue
        cur_row = current_rows[row_id]
        if _normalize_row_for_compare(c_row) != _normalize_row_for_compare(cur_row):
            signature_mismatch += 1
            contract_results.append(
                {
                    **base,
                    "status": "signature_mismatch",
                    "reason": "Signature/fields/variants differ from baseline",
                }
            )
            continue
        matched_count += 1
        contract_results.append({**base, "status": "matched", "reason": "-"})

    new_entries: list[dict[str, Any]] = []
    for row_id, cur_row in current_rows.items():
        if row_id in contract_rows:
            continue
        new_entries.append(
            {
                "id": row_id,
                "rustSymbol": cur_row["rustSymbol"],
                "kind": cur_row["kind"],
                "bridgeModule": cur_row["bridgeModule"],
                "status": "missing_from_contract",
            }
        )

    missing_from_contract = len(new_entries)

    return {
        "summary": {
            "contract_total": len(contract_rows),
            "current_total": len(current_rows),
            "matched": matched_count,
            "missing_from_current": missing_from_current,
            "missing_from_contract": missing_from_contract,
            "signature_mismatch": signature_mismatch,
        },
        "contract_results": contract_results,
        "new_entries": new_entries,
    }


# ---- Diff markdown rendering ----


def render_diff_markdown(diff_report: dict[str, Any]) -> str:
    """Render a human-readable markdown diff report.

    No '- Generated:' header line here -- the caller prepends one if needed
    (and the comparator in check_parity_gate.py skips those lines).
    """
    summary = diff_report["summary"]
    lines: list[str] = [
        "# CXX Parity Diff Report",
        "",
        f"- Contract total: **{summary['contract_total']}**",
        f"- Current total: **{summary['current_total']}**",
        f"- Matched: **{summary['matched']}**",
        f"- Missing from current: **{summary['missing_from_current']}**",
        f"- Missing from contract: **{summary['missing_from_contract']}**",
        f"- Signature mismatch: **{summary['signature_mismatch']}**",
        "",
    ]

    failing = [r for r in diff_report["contract_results"] if r["status"] != "matched"]
    new_entries = diff_report.get("new_entries", [])

    if not failing and not new_entries:
        lines.extend(("## Result", "", "No drift detected.", ""))
        return "\n".join(lines)

    if failing:
        lines.extend(
            (
                "## Contract Drift",
                "",
                "| ID | Bridge Module | Rust Symbol | Kind | Status | Reason |",
                "|---|---|---|---|---|---|",
            )
        )
        for row in failing:
            lines.append(
                f"| `{row['id']}` | `{row['bridgeModule']}` | `{row['rustSymbol']}` | "
                f"`{row['kind']}` | `{row['status']}` | {row['reason']} |"
            )
        lines.append("")

    if new_entries:
        lines.extend(
            (
                "## New Entries (in bridge source, not in baseline)",
                "",
                "| ID | Bridge Module | Rust Symbol | Kind |",
                "|---|---|---|---|",
            )
        )
        for row in new_entries:
            lines.append(
                f"| `{row['id']}` | `{row['bridgeModule']}` | "
                f"`{row['rustSymbol']}` | `{row['kind']}` |"
            )
        lines.append("")

    return "\n".join(lines)


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
        default="cpp-bindings/classic-cpp-bridge/parity-artifacts",
        help="Directory for generated artifacts, relative to repo root.",
    )
    parser.add_argument(
        "--baseline-output-dir",
        default="docs/implementation/cxx_api_parity/baseline",
        help="Directory for committed baseline artifacts, relative to repo root.",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Also write parity_contract.json to --baseline-output-dir "
        "(used by the initial bootstrap; normal operation is "
        "check_parity_gate.py --update-baseline).",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_dir = repo_root / args.output_dir
    baseline_output_dir = repo_root / args.baseline_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        surface = generate_cxx_parity_model(repo_root)
    except CanonicalMappingError as error:
        print(f"CXX canonical mapping validation failed: {error}", file=sys.stderr)
        return 1
    # Carry the committed timestamp forward when the bridge surface is
    # unchanged, so a no-op rerun leaves the tracked baseline byte-identical.
    # Applied before the scratch write as well, so both copies agree.
    preserve_baseline_generated_at(
        baseline_output_dir / "rust_api_surface.json", surface
    )
    write_json(output_dir / "rust_api_surface.json", surface)

    if args.write_baseline:
        # Bootstrap path: the contract IS the fresh surface on the first run.
        # Canonical mapping metadata is the explicit v2 schema migration.
        contract = {
            "generated_at_utc": surface["generated_at_utc"],
            "schema_version": CXX_CONTRACT_SCHEMA_VERSION,
            "entries": surface["entries"],
        }
        # Preserve against the contract's own committed copy rather than relying
        # on the surface's timestamp above: the two files are written from the
        # same run here, but their committed timestamps can legitimately differ
        # because check_parity_gate.py refreshes them on separate cadences.
        preserve_baseline_generated_at(
            baseline_output_dir / "parity_contract.json", contract
        )
        baseline_output_dir.mkdir(parents=True, exist_ok=True)
        write_json(baseline_output_dir / "parity_contract.json", contract)
        write_json(baseline_output_dir / "rust_api_surface.json", surface)
        # Bootstrap diff: contract vs current = 100% matched (empty drift).
        diff = generate_diff_report(contract, surface)
        write_json(baseline_output_dir / "cxx_diff_report.json", diff)
        (baseline_output_dir / "cxx_diff_report.md").write_text(
            render_diff_markdown(diff) + "\n",
            encoding="utf-8",
        )
        # Gate report will be written by check_parity_gate.py; the bootstrap
        # writes a placeholder that check_parity_gate.py can overwrite.
        (baseline_output_dir / "cxx_gate_report.md").write_text(
            "# CXX Parity Gate Report\n\n"
            f"- Contract rows: **{len(contract['entries'])}**\n"
            f"- Matched: **{diff['summary']['matched']}**\n"
            "\n## Result\n\nCXX parity gate passed.\n",
            encoding="utf-8",
        )
        print(f"Wrote committed baseline to {baseline_output_dir}")

    print(
        f"Wrote surface JSON with {len(surface['entries'])} entries to "
        f"{output_dir / 'rust_api_surface.json'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
