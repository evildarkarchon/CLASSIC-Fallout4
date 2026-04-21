#!/usr/bin/env python3
"""Generate Rust<->Python parity baseline artifacts for Python bindings."""

from __future__ import annotations

import argparse
import hashlib
import json
import operator
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from binding_parity_runtime_coverage import (
    build_coverage_summary,
    load_json_file,
    render_coverage_summary_markdown,
)

RUST_TARGET_CRATES: dict[str, str] = {
    # Existing 3 (preserved for stability)
    "classic-scanlog-core": "business-logic/classic-scanlog-core/src/lib.rs",
    "classic-config-core": "business-logic/classic-config-core/src/lib.rs",
    "classic-version-registry-core": "business-logic/classic-version-registry-core/src/lib.rs",
    # Phase 3 additions -- 14 additional business-logic crates (the former yaml-core was absorbed into settings-core in v9.1.0 Phase 1)
    "classic-database-core": "business-logic/classic-database-core/src/lib.rs",
    "classic-file-io-core": "business-logic/classic-file-io-core/src/lib.rs",
    "classic-scangame-core": "business-logic/classic-scangame-core/src/lib.rs",
    "classic-registry-core": "business-logic/classic-registry-core/src/lib.rs",
    "classic-perf-core": "business-logic/classic-perf-core/src/lib.rs",
    "classic-settings-core": "business-logic/classic-settings-core/src/lib.rs",
    "classic-message-core": "business-logic/classic-message-core/src/lib.rs",
    "classic-path-core": "business-logic/classic-path-core/src/lib.rs",
    "classic-version-core": "business-logic/classic-version-core/src/lib.rs",
    "classic-resource-core": "business-logic/classic-resource-core/src/lib.rs",
    "classic-xse-core": "business-logic/classic-xse-core/src/lib.rs",
    "classic-web-core": "business-logic/classic-web-core/src/lib.rs",
    "classic-update-core": "business-logic/classic-update-core/src/lib.rs",
    # Foundation crates (Phase 3 adds GameId in shared-core while parity still
    # tracks Python-visible wrappers from classic-shared-py).
    "classic-shared-core": "foundation/classic-shared-core/src/lib.rs",
    "classic-shared-py": "foundation/classic-shared-py/src/lib.rs",
    # NOTE: classic-crashgen-settings-core is INTENTIONALLY EXCLUDED -- its symbols
    # flow through classic-config-py / classic-scanlog-py / classic-scangame-py
    # wrappers (see .planning/phases/03-python-tier-collapse/03-RESEARCH.md A5).
}

RUST_OWNER_BY_CRATE: dict[str, str] = {
    "classic-scanlog-core": "scanlog",
    "classic-config-core": "config",
    "classic-version-registry-core": "version_registry",
    "classic-database-core": "database",
    "classic-file-io-core": "file_io",
    "classic-scangame-core": "scangame",
    "classic-registry-core": "registry",
    "classic-perf-core": "perf",
    "classic-settings-core": "settings",
    "classic-message-core": "message",
    "classic-path-core": "path",
    "classic-version-core": "version",
    "classic-resource-core": "resource",
    "classic-xse-core": "xse",
    "classic-web-core": "web",
    "classic-update-core": "update",
    "classic-shared-core": "shared",
    "classic-shared-py": "shared",
}

PYTHON_TARGET_MODULES: dict[str, str] = {
    "classic_scanlog": "python-bindings/classic-scanlog-py/classic_scanlog.pyi",
    "classic_config": "python-bindings/classic-config-py/classic_config.pyi",
    "classic_version_registry": "python-bindings/classic-version-registry-py/classic_version_registry.pyi",
    "classic_database": "python-bindings/classic-database-py/classic_database.pyi",
    "classic_file_io": "python-bindings/classic-file-io-py/classic_file_io.pyi",
    "classic_scangame": "python-bindings/classic-scangame-py/classic_scangame.pyi",
    "classic_registry": "python-bindings/classic-registry-py/classic_registry.pyi",
    "classic_perf": "python-bindings/classic-perf-py/classic_perf.pyi",
    "classic_settings": "python-bindings/classic-settings-py/classic_settings.pyi",
    "classic_message": "python-bindings/classic-message-py/classic_message.pyi",
    "classic_path": "python-bindings/classic-path-py/classic_path.pyi",
    "classic_version": "python-bindings/classic-version-py/classic_version.pyi",
    "classic_resource": "python-bindings/classic-resource-py/classic_resource.pyi",
    "classic_xse": "python-bindings/classic-xse-py/classic_xse.pyi",
    "classic_web": "python-bindings/classic-web-py/classic_web.pyi",
    "classic_update": "python-bindings/classic-update-py/classic_update.pyi",
    "classic_shared": "foundation/classic-shared-py/classic_shared.pyi",
}

PYTHON_OWNER_BY_MODULE: dict[str, str] = {
    "classic_scanlog": "scanlog",
    "classic_config": "config",
    "classic_version_registry": "version_registry",
    "classic_database": "database",
    "classic_file_io": "file_io",
    "classic_scangame": "scangame",
    "classic_registry": "registry",
    "classic_perf": "perf",
    "classic_settings": "settings",
    "classic_message": "message",
    "classic_path": "path",
    "classic_version": "version",
    "classic_resource": "resource",
    "classic_xse": "xse",
    "classic_web": "web",
    "classic_update": "update",
    "classic_shared": "shared",
}

SQUAD_BY_OWNER: dict[str, str] = {
    # Existing (pre-Phase-3) labels preserved for historical compatibility.
    "scanlog": "Squad A (scanlog/config)",
    "config": "Squad A (scanlog/config)",
    "version_registry": "Squad B (version-registry)",
    # Phase 3 owner labels -- every new owner needs a squad label for reporting.
    # yaml was absorbed into settings in v9.1.0 Phase 1.
    "database": "Squad D (database/file_io/resource)",
    "file_io": "Squad D (database/file_io/resource)",
    "scangame": "Squad E (scangame/xse)",
    "registry": "Squad C (yaml/settings/registry)",
    "perf": "Squad F (perf/message/path/version/web/update)",
    "settings": "Squad C (yaml/settings/registry)",
    "message": "Squad F (perf/message/path/version/web/update)",
    "path": "Squad F (perf/message/path/version/web/update)",
    "version": "Squad F (perf/message/path/version/web/update)",
    "resource": "Squad D (database/file_io/resource)",
    "xse": "Squad E (scangame/xse)",
    "web": "Squad F (perf/message/path/version/web/update)",
    "update": "Squad F (perf/message/path/version/web/update)",
    "shared": "Squad G (foundation/classic-shared-py)",
    # The 'aux' bucket captures owner-less rows such as the file-io
    # FileHasher.cache_size entry tracked outside the primary crate owners.
    "aux": "Squad D (database/file_io/resource)",
}

# Module-level rendering order for the owner/tier gap table in
# render_diff_markdown(). Derived from RUST_OWNER_BY_CRATE values plus the
# 'aux' label so adding a new crate to RUST_TARGET_CRATES automatically
# propagates to the rendered report (LOW drift guard, enforced by
# tests/test_owner_render_drift.py).
_OWNER_RENDER_ORDER: tuple[str, ...] = tuple(RUST_OWNER_BY_CRATE.values()) + ("aux",)

PYTHON_PHASE3_ROUTE_FAMILIES: dict[str, dict[str, str]] = {
    "Fallout4Version": {
        "ownerModule": "version_registry",
        "rustCrate": "classic-version-registry-core",
        "pythonModule": "classic_version_registry",
        "idPrefix": "version_registry.lib.",
        "anchorExport": "Fallout4Version",
    },
    "GameId": {
        "ownerModule": "shared",
        "rustCrate": "classic-shared-core",
        "pythonModule": "classic_shared",
        "idPrefix": "shared.lib.",
        "anchorExport": "GameId",
    },
    "YamlFile": {
        "ownerModule": "settings",
        "rustCrate": "classic-settings-core",
        "pythonModule": "classic_settings",
        "idPrefix": "settings.lib.",
        "anchorExport": "YamlFile",
    },
}

PYTHON_PHASE3_SYMBOL_ROUTE: dict[str, dict[str, str]] = {
    "NULL_VERSION": PYTHON_PHASE3_ROUTE_FAMILIES["Fallout4Version"],
    "display_name": PYTHON_PHASE3_ROUTE_FAMILIES["Fallout4Version"],
    "display_name_string": PYTHON_PHASE3_ROUTE_FAMILIES["Fallout4Version"],
    "fn": PYTHON_PHASE3_ROUTE_FAMILIES["Fallout4Version"],
    "game_version": PYTHON_PHASE3_ROUTE_FAMILIES["Fallout4Version"],
    "get_version_info": PYTHON_PHASE3_ROUTE_FAMILIES["Fallout4Version"],
    "short_name": PYTHON_PHASE3_ROUTE_FAMILIES["Fallout4Version"],
    "version_semver": PYTHON_PHASE3_ROUTE_FAMILIES["Fallout4Version"],
    "xse_acronym": PYTHON_PHASE3_ROUTE_FAMILIES["Fallout4Version"],
    "xse_acronym_string": PYTHON_PHASE3_ROUTE_FAMILIES["Fallout4Version"],
    "xse_config": PYTHON_PHASE3_ROUTE_FAMILIES["Fallout4Version"],
    "SETTINGS_IGNORE_NONE": {
        **PYTHON_PHASE3_ROUTE_FAMILIES["YamlFile"],
        "anchorExport": "YamlFile",
    },
    "must_not_be_none": {
        **PYTHON_PHASE3_ROUTE_FAMILIES["YamlFile"],
        "anchorExport": "must_not_be_none",
    },
}


def _stable_id_hash(values: list[str]) -> str:
    """Return a stable hash for a list of contract IDs."""
    joined = "\n".join(sorted(values))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _python_phase3_route_for_mapping(mapping: dict[str, Any]) -> dict[str, str] | None:
    """Return the deterministic owner route for redistributed constants rows."""
    row_id = str(mapping.get("id", ""))
    export_path = str(mapping.get("pythonExportPath", ""))
    rust_symbol = str(mapping.get("rustSymbol", ""))

    for family, route in PYTHON_PHASE3_ROUTE_FAMILIES.items():
        if row_id.startswith(f"constants.lib.{family}") or export_path.startswith(
            family
        ):
            return route

    return PYTHON_PHASE3_SYMBOL_ROUTE.get(rust_symbol)


def normalize_phase3_python_contract(contract: dict[str, Any]) -> dict[str, Any]:
    """Reparent retired constants rows to version_registry/settings/shared."""
    retired_owner = "const" + "ants"
    owner_modules = contract.get("ownerModules")
    if isinstance(owner_modules, dict):
        owner_modules.pop(retired_owner, None)

    for mapping in contract.get("tier1Mappings", []):
        route = _python_phase3_route_for_mapping(mapping)
        if route is None:
            continue

        old_id = str(mapping.get("id", ""))
        if old_id.startswith("constants.lib."):
            mapping["id"] = route["idPrefix"] + old_id[len("constants.lib.") :]

        mapping["ownerModule"] = route["ownerModule"]
        mapping["rustCrate"] = route["rustCrate"]
        mapping["pythonModule"] = route["pythonModule"]

        if old_id.endswith("@rust"):
            mapping["pythonExportPath"] = route["anchorExport"]

    return contract


def normalize_phase3_python_runtime_registry(
    runtime_registry: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    """Update selector-based runtime coverage metadata after Phase 3 reparenting."""
    retired_owner = "const" + "ants"
    constants_coverage_ids = {"python-tier1-constants"}
    entries = [
        entry
        for entry in runtime_registry.get("entries", [])
        if entry.get("coverageId") not in constants_coverage_ids
        and entry.get("ownerModule") != retired_owner
    ]

    tier1_rows = contract.get("tier1Mappings", [])
    grouped_ids: dict[str, list[str]] = {
        "version_registry": [],
        "settings": [],
        "shared": [],
    }
    for row in tier1_rows:
        owner = row.get("ownerModule")
        if row.get("tier") == "tier1" and owner in grouped_ids:
            grouped_ids[owner].append(row["id"])

    for entry in entries:
        selector = entry.get("contractSelector")
        if not isinstance(selector, dict):
            continue
        owner = selector.get("ownerModule")
        if owner not in grouped_ids:
            continue
        entry["ownerModule"] = owner
        entry["contractCount"] = len(grouped_ids[owner])
        entry["contractIdsHash"] = _stable_id_hash(grouped_ids[owner])

    runtime_registry["entries"] = entries
    return runtime_registry


def count_top_level_params(params: str) -> int:
    """Count top-level function parameters in a signature parameter string."""
    return len(split_top_level_params(params))


def split_top_level_params(params: str) -> list[str]:
    """Split a signature parameter string into top-level parameter items."""
    candidate = params.strip()
    if not candidate:
        return []

    items: list[str] = []
    current: list[str] = []
    depth_pairs = {"(": ")", "[": "]", "{": "}", "<": ">"}
    closing = set(depth_pairs.values())
    opening = set(depth_pairs.keys())
    stack: list[str] = []

    for ch in candidate:
        if ch in opening:
            stack.append(depth_pairs[ch])
        elif ch in closing and stack and ch == stack[-1]:
            stack.pop()

        if ch == "," and not stack:
            items.append("".join(current).strip())
            current = []
            continue
        current.append(ch)

    tail = "".join(current).strip()
    if tail:
        items.append(tail)

    return [item for item in items if item and item not in {"/", "*"}]


def count_call_arity(params: str, decorators: list[str] | None = None) -> int:
    """Count Python call-site arity, ignoring implicit self/cls when applicable."""
    items = split_top_level_params(params)
    if not items:
        return 0

    decorators = decorators or []
    if any(decorator == "@staticmethod" for decorator in decorators):
        return len(items)

    first_name = items[0].split(":", 1)[0].split("=", 1)[0].strip() if items else ""
    if first_name in {"self", "cls"}:
        return len(items) - 1
    return len(items)


def normalize_whitespace(value: str) -> str:
    """Collapse consecutive whitespace to a single space."""
    return re.sub(r"\s+", " ", value).strip()


def expand_pub_use_statement(body: str) -> list[tuple[str, str]]:
    """Expand a Rust `pub use` statement into export names and source paths."""
    statement = normalize_whitespace(body).rstrip(";")
    if not statement:
        return []

    expanded: list[tuple[str, str]] = []

    def split_parts(chunk: str) -> list[str]:
        return [part.strip() for part in chunk.split(",") if part.strip()]

    if "{" in statement and "}" in statement:
        prefix, remainder = statement.split("{", 1)
        inner = remainder.rsplit("}", 1)[0]
        prefix = prefix.strip().removesuffix("::")

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


def _collect_crate_sources(repo_root: Path, lib_rs_rel: str) -> list[tuple[str, str]]:
    """Return ordered [(rel_path, content), ...] for lib.rs + referenced sub-modules.

    Scans `mod foo;` and `pub mod foo;` declarations inside `lib.rs` and resolves
    each to either `<crate_src>/foo.rs` or `<crate_src>/foo/mod.rs` if the file
    exists. One level deep is enough for the parity gate's use case (post-v9.1.0
    Phase 1 merge: yaml_ops.rs lives as a sibling of lib.rs in settings-core).
    """
    lib_path = repo_root / lib_rs_rel
    content = lib_path.read_text(encoding="utf-8")
    sources = [(lib_rs_rel, content)]
    src_dir = lib_path.parent
    mod_names: list[str] = []
    for match in re.finditer(r"(?m)^\s*(?:pub\s+)?mod\s+([A-Za-z0-9_]+)\s*;", content):
        mod_names.append(match.group(1))
    for mod_name in mod_names:
        candidate_file = src_dir / f"{mod_name}.rs"
        candidate_mod = src_dir / mod_name / "mod.rs"
        chosen: Path | None = None
        if candidate_file.exists():
            chosen = candidate_file
        elif candidate_mod.exists():
            chosen = candidate_mod
        if chosen is not None:
            sub_rel = str(chosen.relative_to(repo_root)).replace("\\", "/")
            try:
                sub_content = chosen.read_text(encoding="utf-8")
            except OSError:
                continue
            sources.append((sub_rel, sub_content))
    return sources


def parse_rust_surface(repo_root: Path, tier1_rust_symbols: set[str]) -> dict[str, Any]:
    """Extract Rust symbols from target crate `lib.rs` files.

    Post v9.1.0 Phase 1: when a `-core` crate uses a sub-module (e.g.,
    `classic-settings-core/src/yaml_ops.rs`), this function also scans that
    sub-module file for `pub fn` / `pub struct` / `pub use` declarations so the
    parity gate can see methods and types declared there.
    """
    entries: list[dict[str, Any]] = []

    for crate_name, rel_path in RUST_TARGET_CRATES.items():
        owner_module = RUST_OWNER_BY_CRATE[crate_name]
        crate_sources = _collect_crate_sources(repo_root, rel_path)

        for source_rel, content in crate_sources:
            _extract_rust_symbols(
                entries, content, source_rel, crate_name, owner_module, rel_path
            )

    entries.sort(key=operator.itemgetter("crate", "symbol", "kind"))
    return _finalize_rust_manifest(entries)


def _extract_rust_symbols(
    entries: list[dict[str, Any]],
    content: str,
    source_rel: str,
    crate_name: str,
    owner_module: str,
    crate_lib_rel: str,
) -> None:
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
        r"(?m)^\s*pub\s+fn\s+([A-Za-z0-9_]+)\s*\((.*?)\)", content
    ):
        symbol = match.group(1)
        entries.append(
            {
                "symbol": symbol,
                "kind": "function",
                "arity": count_top_level_params(match.group(2)),
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


def _finalize_rust_manifest(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "scope": {
            "target_crates": list(RUST_TARGET_CRATES.keys()),
            "source_files": list(RUST_TARGET_CRATES.values()),
        },
        "symbols": entries,
    }


def _collect_signature(lines: list[str], start_idx: int) -> tuple[str, int]:
    """Collect a top-level function signature across multiple lines."""
    signature_parts: list[str] = []
    idx = start_idx
    paren_depth = 0
    seen_open = False

    while idx < len(lines):
        piece = lines[idx].strip()
        if not piece:
            idx += 1
            continue
        signature_parts.append(piece)

        for ch in piece:
            if ch == "(":
                seen_open = True
                paren_depth += 1
            elif ch == ")" and paren_depth > 0:
                paren_depth -= 1

        if seen_open and paren_depth == 0 and ":" in piece:
            break
        idx += 1

    return (" ".join(signature_parts), idx)


def _indent_of(line: str) -> int:
    """Return leading space count for a line."""
    return len(line) - len(line.lstrip(" "))


def _is_property_decorator(decorators: list[str]) -> bool:
    """Return whether decorators describe a property accessor."""
    return any(
        decorator == "@property"
        or decorator.endswith(".setter")
        or decorator.endswith(".deleter")
        for decorator in decorators
    )


def parse_python_surface(
    repo_root: Path, tier1_python_exports: set[str]
) -> dict[str, Any]:
    """Extract public classes, top-level functions, and callable methods from `.pyi` files."""
    exports: list[dict[str, Any]] = []

    class_re = re.compile(r"^class\s+([A-Za-z0-9_]+)\b")

    for module_name, rel_path in PYTHON_TARGET_MODULES.items():
        path = repo_root / rel_path
        owner_module = PYTHON_OWNER_BY_MODULE[module_name]
        lines = path.read_text(encoding="utf-8").splitlines()

        idx = 0
        while idx < len(lines):
            line = lines[idx]
            stripped = line.strip()

            if line.startswith("class "):
                match = class_re.match(stripped)
                if match:
                    class_name = match.group(1)
                    exports.append(
                        {
                            "module": module_name,
                            "export": class_name,
                            "export_path": class_name,
                            "kind": "class",
                            "owner_module": owner_module,
                            "tier": "tier1",
                            "source_file": rel_path,
                            "signature": stripped,
                        }
                    )
                    class_indent = _indent_of(line)
                    idx += 1
                    pending_decorators: list[str] = []

                    while idx < len(lines):
                        class_line = lines[idx]
                        class_stripped = class_line.strip()

                        if not class_stripped:
                            idx += 1
                            continue

                        class_member_indent = _indent_of(class_line)
                        if class_member_indent <= class_indent:
                            break

                        if class_stripped.startswith("@"):
                            pending_decorators.append(class_stripped)
                            idx += 1
                            continue

                        if class_stripped.startswith(
                            "def "
                        ) or class_stripped.startswith("async def "):
                            signature, end_idx = _collect_signature(lines, idx)
                            method_match = re.match(
                                r"^(?:async\s+)?def\s+([A-Za-z0-9_]+)\s*\((.*)\)",
                                signature,
                            )
                            if method_match and not _is_property_decorator(
                                pending_decorators
                            ):
                                export_name = method_match.group(1)
                                params = method_match.group(2)
                                export_path = f"{class_name}.{export_name}"
                                exports.append(
                                    {
                                        "module": module_name,
                                        "export": export_name,
                                        "export_path": export_path,
                                        "parent_class": class_name,
                                        "kind": "method",
                                        "arity": count_call_arity(
                                            params, pending_decorators
                                        ),
                                        "owner_module": owner_module,
                                        "tier": "tier1",
                                        "source_file": rel_path,
                                        "signature": signature,
                                    }
                                )
                            pending_decorators = []
                            idx = end_idx + 1
                            continue

                        pending_decorators = []
                        idx += 1
                    continue
                idx += 1
                continue

            if line.startswith("def ") or line.startswith("async def "):
                signature, end_idx = _collect_signature(lines, idx)
                match = re.match(
                    r"^(?:async\s+)?def\s+([A-Za-z0-9_]+)\s*\((.*)\)", signature
                )
                if match:
                    export_name = match.group(1)
                    params = match.group(2)
                    exports.append(
                        {
                            "module": module_name,
                            "export": export_name,
                            "export_path": export_name,
                            "kind": "function",
                            "arity": count_top_level_params(params),
                            "owner_module": owner_module,
                            "tier": "tier1",
                            "source_file": rel_path,
                            "signature": signature,
                        }
                    )
                idx = end_idx + 1
                continue

            idx += 1

    exports.sort(key=operator.itemgetter("module", "export_path", "kind"))
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "scope": {
            "target_modules": list(PYTHON_TARGET_MODULES.keys()),
            "source_files": list(PYTHON_TARGET_MODULES.values()),
        },
        "exports": exports,
    }


def build_lookup(
    items: list[dict[str, Any]], key_field: str
) -> dict[str, dict[str, Any]]:
    """Build single-key lookup from manifest entries."""
    lookup: dict[str, dict[str, Any]] = {}
    for item in items:
        key = item[key_field]
        if key not in lookup:
            lookup[key] = item
    return lookup


def build_python_lookup(
    items: list[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    """Build `(module, export_path)` lookup for Python exports."""
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for item in items:
        key = (item["module"], item.get("export_path", item["export"]))
        if key not in lookup:
            lookup[key] = item
    return lookup


def collect_tier1_python_targets(tier1_mappings: list[dict[str, Any]]) -> set[str]:
    """Collect Python export identifiers used for Tier-1 tagging.

    During migration, contracts may carry either legacy ``pythonExport`` values
    or method-aware ``pythonExportPath`` values. Include both when present so
    manifest tagging remains stable across mixed contracts.
    """
    targets: set[str] = set()
    for mapping in tier1_mappings:
        python_export = mapping.get("pythonExport")
        python_export_path = mapping.get("pythonExportPath")
        if python_export:
            targets.add(python_export)
        if python_export_path:
            targets.add(python_export_path)
    return targets


def get_contract_python_export_identifier(mapping: dict[str, Any]) -> str | None:
    """Return the method-aware or legacy Python export identifier from a mapping."""
    export_identifier = mapping.get("pythonExportPath") or mapping.get("pythonExport")
    return export_identifier if isinstance(export_identifier, str) else None


def generate_diff_report(
    contract: dict[str, Any],
    rust_manifest: dict[str, Any],
    python_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Generate contract status rows and parity gap inventory."""
    tier1_mappings: list[dict[str, Any]] = contract["tier1Mappings"]
    rust_symbols: list[dict[str, Any]] = rust_manifest["symbols"]
    python_exports: list[dict[str, Any]] = python_manifest["exports"]

    rust_lookup = build_lookup(rust_symbols, "symbol")
    python_lookup = build_python_lookup(python_exports)

    tier1_rust_symbols = {mapping["rustSymbol"] for mapping in tier1_mappings}
    tier1_python_pairs = {
        (mapping["pythonModule"], python_export_path)
        for mapping in tier1_mappings
        if (python_export_path := get_contract_python_export_identifier(mapping))
        is not None
    }

    contract_results: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    for mapping in tier1_mappings:
        rust_symbol = mapping["rustSymbol"]
        python_module = mapping["pythonModule"]
        python_export_path = get_contract_python_export_identifier(mapping)
        python_export = mapping.get("pythonExport") or python_export_path
        expected_kind = mapping.get("pythonKind")
        expected_arity = mapping.get("pythonArity")
        owner_module = mapping["ownerModule"]

        rust_item = rust_lookup.get(rust_symbol)
        py_item = (
            python_lookup.get((python_module, python_export_path))
            if python_export_path is not None
            else None
        )
        status = "matched"
        reason = ""

        if rust_item is None:
            status = "missing_rust"
            reason = f"Rust symbol '{rust_symbol}' not found in target crate exports."
        elif python_export_path is None:
            status = "missing_python"
            reason = (
                "Tier-1 mapping is missing a Python export identifier "
                "(`pythonExportPath` or legacy `pythonExport`)."
            )
        elif py_item is None:
            status = "missing_python"
            reason = f"Python export '{python_module}.{python_export_path}' not found in target .pyi surfaces."
        elif expected_kind and py_item["kind"] != expected_kind:
            status = "signature_mismatch"
            reason = (
                f"Expected Python kind '{expected_kind}', found '{py_item['kind']}'."
            )
        elif expected_arity is not None and py_item.get("arity") != expected_arity:
            status = "signature_mismatch"
            reason = f"Expected Python arity {expected_arity}, found {py_item.get('arity', 'n/a')}."

        row = {
            "id": mapping["id"],
            "tier": mapping["tier"],
            "owner_module": owner_module,
            "squad": SQUAD_BY_OWNER[owner_module],
            "rust_symbol": rust_symbol,
            "python_module": python_module,
            "python_export": python_export,
            "python_export_path": python_export_path,
            "status": status,
            "expected_python_kind": expected_kind,
            "actual_python_kind": py_item["kind"] if py_item else None,
            "expected_python_arity": expected_arity,
            "actual_python_arity": py_item.get("arity") if py_item else None,
        }
        if reason:
            row["reason"] = reason
        contract_results.append(row)

        if status != "matched":
            gaps.append(
                {
                    "gap_type": f"tier1_{status}",
                    "tier": "tier1",
                    "owner_module": owner_module,
                    "squad": SQUAD_BY_OWNER[owner_module],
                    "rust_symbol": rust_symbol,
                    "python_module": python_module,
                    "python_export": python_export,
                    "python_export_path": python_export_path,
                    "reason": reason,
                }
            )

    # Plan 09b removed the former deferred-gap emission branches (which iterated
    # rust symbols and python exports outside the enforced mapping). Phase 3
    # enrolled every in-scope Python binding as a contract row, so those deferral
    # branches no longer contribute gate signal. See the Plan 09b SUMMARY and the
    # cascade audit in .planning/phases/03-python-tier-collapse/ for details.

    status_counts: dict[str, int] = defaultdict(int)
    for row in contract_results:
        status_counts[row["status"]] += 1

    gap_counts_by_owner_tier: dict[str, dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    for gap in gaps:
        gap_counts_by_owner_tier[gap["owner_module"]][gap["tier"]] += 1

    summary = {
        "tier1_contract_total": len(contract_results),
        "tier1_matched": status_counts.get("matched", 0),
        "tier1_missing_rust": status_counts.get("missing_rust", 0),
        "tier1_missing_python": status_counts.get("missing_python", 0),
        "tier1_signature_mismatch": status_counts.get("signature_mismatch", 0),
        "total_gaps": len(gaps),
        "tier1_gap_total": sum(1 for gap in gaps if gap["tier"] == "tier1"),
    }

    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "summary": summary,
        "contract_results": contract_results,
        "gaps": gaps,
        "gap_counts_by_owner_tier": {
            owner: dict(tier_counts)
            for owner, tier_counts in gap_counts_by_owner_tier.items()
        },
    }


def render_diff_markdown(diff_report: dict[str, Any]) -> str:
    """Render concise markdown summary of parity results."""
    summary = diff_report["summary"]
    lines: list[str] = []
    lines.extend(
        (
            "# Rust<->Python Parity Diff Baseline",
            "",
            f"- Generated: `{diff_report['generated_at_utc']}`",
            f"- Tier-1 contract rows: **{summary['tier1_contract_total']}**",
            f"- Tier-1 matched: **{summary['tier1_matched']}**",
            f"- Tier-1 missing Rust: **{summary['tier1_missing_rust']}**",
            f"- Tier-1 missing Python: **{summary['tier1_missing_python']}**",
            f"- Tier-1 signature mismatch: **{summary['tier1_signature_mismatch']}**",
            f"- Total gaps: **{summary['total_gaps']}**",
            "",
            "## Tier-1 Contract Evaluation",
            "",
            "| ID | Owner Module | Rust Symbol | Python Export | Status |",
            "|---|---|---|---|---|",
        )
    )
    for row in diff_report["contract_results"]:
        python_target = row.get("python_export_path", row["python_export"])
        lines.append(
            f"| `{row['id']}` | `{row['owner_module']}` | `{row['rust_symbol']}` | `{row['python_module']}.{python_target}` | `{row['status']}` |"
        )

    lines.extend(
        (
            "",
            "## Gap Counts By Owner/Tier",
            "",
            "| Owner Module | Tier 1 Gaps |",
            "|---|---:|",
        )
    )
    for owner in _OWNER_RENDER_ORDER:
        tier_counts = diff_report["gap_counts_by_owner_tier"].get(owner, {})
        lines.append(f"| `{owner}` | {tier_counts.get('tier1', 0)} |")

    lines.extend(
        ("", "Detailed per-gap diagnostics are in `parity_diff_report.json`.", "")
    )
    return "\n".join(lines)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Generate Rust/Python API parity baseline artifacts."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Repository root path.",
    )
    parser.add_argument(
        "--contract",
        default="docs/implementation/python_api_parity/baseline/parity_contract.json",
        help="Path to parity contract JSON, relative to repo root.",
    )
    parser.add_argument(
        "--output-dir",
        default="docs/implementation/python_api_parity/baseline",
        help="Directory for generated output files, relative to repo root.",
    )
    parser.add_argument(
        "--runtime-registry",
        default="python-bindings/tests/fixtures/runtime_coverage_registry.json",
        help="Path to the Python runtime coverage registry JSON, relative to repo root.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    contract_path = repo_root / args.contract
    output_dir = repo_root / args.output_dir

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    tier1_mappings: list[dict[str, Any]] = contract["tier1Mappings"]
    tier1_rust_symbols = {mapping["rustSymbol"] for mapping in tier1_mappings}
    tier1_python_exports = collect_tier1_python_targets(tier1_mappings)

    rust_manifest = parse_rust_surface(repo_root, tier1_rust_symbols)
    python_manifest = parse_python_surface(repo_root, tier1_python_exports)
    diff_report = generate_diff_report(contract, rust_manifest, python_manifest)
    runtime_registry = load_json_file(repo_root / args.runtime_registry)
    coverage_summary = build_coverage_summary(
        binding="python",
        contract=contract,
        diff_report=diff_report,
        runtime_registry=runtime_registry,
        source_paths={
            "contract": args.contract,
            "runtime_registry": args.runtime_registry,
        },
    )

    write_json(output_dir / "rust_api_surface.json", rust_manifest)
    write_json(output_dir / "python_api_surface.json", python_manifest)
    write_json(output_dir / "parity_diff_report.json", diff_report)
    (output_dir / "parity_diff_report.md").write_text(
        render_diff_markdown(diff_report), encoding="utf-8"
    )
    write_json(output_dir / "runtime_coverage_summary.json", coverage_summary)
    (output_dir / "runtime_coverage_summary.md").write_text(
        render_coverage_summary_markdown(coverage_summary), encoding="utf-8"
    )

    print("Python parity baseline generated:")
    print(f"- {output_dir / 'rust_api_surface.json'}")
    print(f"- {output_dir / 'python_api_surface.json'}")
    print(f"- {output_dir / 'parity_diff_report.json'}")
    print(f"- {output_dir / 'parity_diff_report.md'}")
    print(f"- {output_dir / 'runtime_coverage_summary.json'}")
    print(f"- {output_dir / 'runtime_coverage_summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
