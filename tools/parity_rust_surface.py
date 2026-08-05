#!/usr/bin/env python3
"""Shared Rust public-surface parser for the binding parity gates.

The Node and Python parity gates both answer the same question about the same
crates -- *what is the public Rust surface?* -- and until this module existed
they answered it with two independently maintained copies of the same ~180-line
parser. Two copies means the gates can silently disagree about which Rust
exports exist, each internally consistent and both reporting success.

What stays per-binding is the *crate list*, not the parsing. Python scans
``classic-shared-py`` (a binding-local crate) that Node has no reason to look
at, so :func:`parse_rust_surface` takes the crate configuration as arguments
rather than reading module globals. Each tool keeps a thin wrapper that passes
its own ``RUST_TARGET_CRATES`` / ``RUST_OWNER_BY_CRATE`` in at call time -- that
also keeps the existing tests working, since several of them monkeypatch those
dictionaries on the tool module and expect the change to take effect.

Language-specific parameter counting deliberately does NOT live here. Node
counts TypeScript parameters and Python counts Python parameters (where a bare
``/`` or ``*`` is a marker rather than an argument); only :func:`count_rust_params`
belongs to the Rust parser, and it is what :func:`extract_rust_symbols` uses.
"""

from __future__ import annotations

import operator
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

#: Bracket pairs tracked when splitting a signature's parameter list.
_DEPTH_PAIRS = {"(": ")", "[": "]", "{": "}", "<": ">"}
_OPENING = set(_DEPTH_PAIRS)
_CLOSING = set(_DEPTH_PAIRS.values())


def normalize_whitespace(value: str) -> str:
    """Collapse consecutive whitespace to a single space."""
    return re.sub(r"\s+", " ", value).strip()


def split_top_level_items(params: str) -> list[str]:
    """Split a signature parameter string on commas that are not nested.

    Bracket-aware: commas inside ``(...)``, ``[...]``, ``{...}`` or ``<...>``
    belong to the enclosing item. Empty items are dropped, so a stray double
    comma does not inflate the count. This is the language-agnostic core --
    callers layer their own language's rules on top.
    """
    candidate = params.strip()
    if not candidate:
        return []

    items: list[str] = []
    current: list[str] = []
    stack: list[str] = []

    for ch in candidate:
        if ch in _OPENING:
            stack.append(_DEPTH_PAIRS[ch])
        elif ch in _CLOSING and stack and ch == stack[-1]:
            stack.pop()

        if ch == "," and not stack:
            items.append("".join(current).strip())
            current = []
            continue
        current.append(ch)

    tail = "".join(current).strip()
    if tail:
        items.append(tail)

    return [item for item in items if item]


def count_rust_params(params: str) -> int:
    """Count top-level parameters in a Rust ``fn`` parameter list.

    ``&self`` / ``self`` are counted like any other parameter, matching the
    arity recorded in the committed baselines.
    """
    return len(split_top_level_items(params))


def expand_pub_use_statement(body: str) -> list[tuple[str, str]]:
    """Expand a Rust `pub use` statement into exported symbols and source paths.

    Returns ``[(export_name, source_path), ...]``. Handles brace groups
    (``pub use foo::{A, B as C};``), ``self`` inside a group (which re-exports
    the module under its own or an aliased name), and plain aliased paths.
    """
    statement = normalize_whitespace(body).rstrip(";")
    if not statement:
        return []

    expanded: list[tuple[str, str]] = []

    def split_parts(chunk: str) -> list[str]:
        return [part.strip() for part in chunk.split(",") if part.strip()]

    if "{" in statement and "}" in statement:
        prefix, remainder = statement.split("{", 1)
        inner = remainder.rsplit("}", 1)[0]
        prefix = prefix.strip()
        prefix = prefix.removesuffix("::")
        for part in split_parts(inner):
            alias_name_inner: str | None = None
            symbol_expr = part
            if " as " in part:
                symbol_expr, alias_name_inner = [
                    piece.strip() for piece in part.split(" as ", 1)
                ]

            if symbol_expr == "self":
                source_path = prefix
                export_name = alias_name_inner or prefix.split("::")[-1]
            else:
                source_path = f"{prefix}::{symbol_expr}" if prefix else symbol_expr
                export_name = alias_name_inner or symbol_expr.split("::")[-1]

            expanded.append((export_name, source_path))
        return expanded

    for part in split_parts(statement):
        alias_name_outer: str | None = None
        symbol_expr = part
        if " as " in part:
            symbol_expr, alias_name_outer = [
                piece.strip() for piece in part.split(" as ", 1)
            ]
        export_name = alias_name_outer or symbol_expr.split("::")[-1]
        expanded.append((export_name, symbol_expr))

    return expanded


def collect_crate_sources(repo_root: Path, lib_rs_rel: str) -> list[tuple[str, str]]:
    """Return ordered [(rel_path, content), ...] for lib.rs and child modules.

    Rust resolves ``mod child;`` differently depending on the declaring source:
    ``lib.rs``/``mod.rs`` search beside the file, while a file module such as
    ``yaml_ops.rs`` searches below ``yaml_ops/``. The parity scanner mirrors
    that source layout so nested facades keep their public inherent methods in
    the generated Rust surface.
    """
    lib_path = repo_root / lib_rs_rel

    def module_search_dir(source_path: Path) -> Path:
        if source_path.name in {"lib.rs", "main.rs", "mod.rs"}:
            return source_path.parent
        return source_path.with_suffix("")

    def resolve_module_path(source_path: Path, mod_name: str) -> Path | None:
        base_dir = module_search_dir(source_path)
        candidate_file = base_dir / f"{mod_name}.rs"
        candidate_mod = base_dir / mod_name / "mod.rs"
        if candidate_file.exists():
            return candidate_file
        if candidate_mod.exists():
            return candidate_mod
        return None

    sources: list[tuple[str, str]] = []
    seen: set[Path] = set()

    def visit(source_path: Path) -> None:
        try:
            resolved = source_path.resolve()
        except OSError:
            return
        if resolved in seen:
            return

        try:
            content = source_path.read_text(encoding="utf-8")
        except OSError:
            return

        seen.add(resolved)
        rel_path = str(source_path.relative_to(repo_root)).replace("\\", "/")
        sources.append((rel_path, content))

        # Restricted modules are implementation details; public re-exports
        # must be discovered through an unrestricted facade instead.
        for match in re.finditer(
            r"(?m)^\s*(?:pub\s+)?mod\s+([A-Za-z0-9_]+)\s*;", content
        ):
            child_path = resolve_module_path(source_path, match.group(1))
            if child_path is not None:
                visit(child_path)

    visit(lib_path)
    return sources


def extract_rust_symbols(
    entries: list[dict[str, Any]],
    content: str,
    source_rel: str,
    crate_name: str,
    owner_module: str,
) -> None:
    """Append every public symbol found in one Rust source file to ``entries``."""
    for match in re.finditer(r"(?m)^\s*pub\s+mod\s+([A-Za-z0-9_]+)\s*;", content):
        symbol = match.group(1)
        entries.append(
            {
                "symbol": symbol,
                "kind": "module",
                "crate": crate_name,
                "owner_module": owner_module,
                "source_file": source_rel,
                "source_decl": match.group(0).strip(),
                "tier": "tier1",
            }
        )

    for match in re.finditer(
        r"^\s*pub\s+fn\s+([A-Za-z0-9_]+)\s*\((.*?)\)",
        content,
        flags=re.MULTILINE | re.DOTALL,
    ):
        symbol = match.group(1)
        arity = count_rust_params(match.group(2))
        entries.append(
            {
                "symbol": symbol,
                "kind": "function",
                "arity": arity,
                "crate": crate_name,
                "owner_module": owner_module,
                "source_file": source_rel,
                "source_decl": match.group(0).strip(),
                "tier": "tier1",
            }
        )

    for match in re.finditer(
        r"(?m)^\s*pub\s+(struct|enum|type|trait|const|static)\s+([A-Za-z0-9_]+)",
        content,
    ):
        kind = match.group(1)
        symbol = match.group(2)
        entries.append(
            {
                "symbol": symbol,
                "kind": kind,
                "crate": crate_name,
                "owner_module": owner_module,
                "source_file": source_rel,
                "source_decl": match.group(0).strip(),
                "tier": "tier1",
            }
        )

    for match in re.finditer(
        r"pub\s+use\s+([^;]+);", content, flags=re.MULTILINE | re.DOTALL
    ):
        use_body = match.group(1)
        for symbol, source_expr in expand_pub_use_statement(use_body):
            entries.append(
                {
                    "symbol": symbol,
                    "kind": "reexport",
                    "crate": crate_name,
                    "owner_module": owner_module,
                    "source_file": source_rel,
                    "source_decl": f"pub use {normalize_whitespace(use_body)};",
                    "source_expr": source_expr,
                    "tier": "tier1",
                }
            )


def parse_rust_surface(
    repo_root: Path,
    target_crates: dict[str, str],
    owner_by_crate: dict[str, str],
) -> dict[str, Any]:
    """Extract Rust public API symbols from each target crate's `lib.rs` + child modules.

    ``target_crates`` maps crate name to its ``lib.rs`` path relative to
    ``repo_root``; ``owner_by_crate`` maps the same crate names to owner module
    labels. Both are passed in rather than read from globals so each binding's
    gate keeps its own crate list -- and so tests can substitute a fixture crate.

    Raises ``KeyError`` if a crate in ``target_crates`` has no ``owner_by_crate``
    entry. That is deliberate: the sizing pipeline must fail loudly rather than
    silently default a new crate to ``aux``.
    """
    entries: list[dict[str, Any]] = []

    for crate_name, rel_path in target_crates.items():
        owner_module = owner_by_crate[crate_name]
        for source_rel, content in collect_crate_sources(repo_root, rel_path):
            extract_rust_symbols(
                entries, content, source_rel, crate_name, owner_module
            )

    entries.sort(key=operator.itemgetter("crate", "symbol", "kind"))
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "scope": {
            "target_crates": list(target_crates.keys()),
            "source_files": list(target_crates.values()),
        },
        "symbols": entries,
    }


def build_lookup(
    items: list[dict[str, Any]], key_field: str
) -> dict[str, dict[str, Any]]:
    """Build a single-key name lookup dictionary from manifest entries.

    First entry wins on duplicate keys, matching the committed baselines.
    Raises ``KeyError`` if an entry lacks ``key_field`` -- a malformed manifest
    should fail loudly rather than silently drop symbols from the lookup.
    """
    lookup: dict[str, dict[str, Any]] = {}
    for item in items:
        key = item[key_field]
        if key not in lookup:
            lookup[key] = item
    return lookup
