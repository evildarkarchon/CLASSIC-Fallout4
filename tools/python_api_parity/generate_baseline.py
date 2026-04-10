#!/usr/bin/env python3
"""Generate Rust<->Python parity baseline artifacts for Python bindings."""

from __future__ import annotations

import argparse
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
    "classic-scanlog-core":          "ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs",
    "classic-config-core":           "ClassicLib-rs/business-logic/classic-config-core/src/lib.rs",
    "classic-version-registry-core": "ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs",
    # Phase 3 additions -- 15 additional business-logic crates
    "classic-yaml-core":             "ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs",
    "classic-database-core":         "ClassicLib-rs/business-logic/classic-database-core/src/lib.rs",
    "classic-file-io-core":          "ClassicLib-rs/business-logic/classic-file-io-core/src/lib.rs",
    "classic-scangame-core":         "ClassicLib-rs/business-logic/classic-scangame-core/src/lib.rs",
    "classic-registry-core":         "ClassicLib-rs/business-logic/classic-registry-core/src/lib.rs",
    "classic-perf-core":             "ClassicLib-rs/business-logic/classic-perf-core/src/lib.rs",
    "classic-settings-core":         "ClassicLib-rs/business-logic/classic-settings-core/src/lib.rs",
    "classic-message-core":          "ClassicLib-rs/business-logic/classic-message-core/src/lib.rs",
    "classic-path-core":             "ClassicLib-rs/business-logic/classic-path-core/src/lib.rs",
    "classic-constants-core":        "ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs",
    "classic-version-core":          "ClassicLib-rs/business-logic/classic-version-core/src/lib.rs",
    "classic-resource-core":         "ClassicLib-rs/business-logic/classic-resource-core/src/lib.rs",
    "classic-xse-core":              "ClassicLib-rs/business-logic/classic-xse-core/src/lib.rs",
    "classic-web-core":              "ClassicLib-rs/business-logic/classic-web-core/src/lib.rs",
    "classic-update-core":           "ClassicLib-rs/business-logic/classic-update-core/src/lib.rs",
    # Foundation crate (Phase 3 D-09 / HARM-03)
    "classic-shared-py":             "ClassicLib-rs/foundation/classic-shared-py/src/lib.rs",
    # NOTE: classic-crashgen-settings-core is INTENTIONALLY EXCLUDED -- its symbols
    # flow through classic-config-py / classic-scanlog-py / classic-scangame-py
    # wrappers (see .planning/phases/03-python-tier-collapse/03-RESEARCH.md A5).
}

RUST_OWNER_BY_CRATE: dict[str, str] = {
    "classic-scanlog-core":          "scanlog",
    "classic-config-core":           "config",
    "classic-version-registry-core": "version_registry",
    "classic-yaml-core":             "yaml",
    "classic-database-core":         "database",
    "classic-file-io-core":          "file_io",
    "classic-scangame-core":         "scangame",
    "classic-registry-core":         "registry",
    "classic-perf-core":             "perf",
    "classic-settings-core":         "settings",
    "classic-message-core":          "message",
    "classic-path-core":             "path",
    "classic-constants-core":        "constants",
    "classic-version-core":          "version",
    "classic-resource-core":         "resource",
    "classic-xse-core":              "xse",
    "classic-web-core":              "web",
    "classic-update-core":           "update",
    "classic-shared-py":             "shared",
}

PYTHON_TARGET_MODULES: dict[str, str] = {
    "classic_scanlog":          "ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi",
    "classic_config":           "ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi",
    "classic_version_registry": "ClassicLib-rs/python-bindings/classic-version-registry-py/classic_version_registry.pyi",
    "classic_yaml":             "ClassicLib-rs/python-bindings/classic-yaml-py/classic_yaml.pyi",
    "classic_database":         "ClassicLib-rs/python-bindings/classic-database-py/classic_database.pyi",
    "classic_file_io":          "ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi",
    "classic_scangame":         "ClassicLib-rs/python-bindings/classic-scangame-py/classic_scangame.pyi",
    "classic_registry":         "ClassicLib-rs/python-bindings/classic-registry-py/classic_registry.pyi",
    "classic_perf":             "ClassicLib-rs/python-bindings/classic-perf-py/classic_perf.pyi",
    "classic_settings":         "ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi",
    "classic_message":          "ClassicLib-rs/python-bindings/classic-message-py/classic_message.pyi",
    "classic_path":             "ClassicLib-rs/python-bindings/classic-path-py/classic_path.pyi",
    "classic_constants":        "ClassicLib-rs/python-bindings/classic-constants-py/classic_constants.pyi",
    "classic_version":          "ClassicLib-rs/python-bindings/classic-version-py/classic_version.pyi",
    "classic_resource":         "ClassicLib-rs/python-bindings/classic-resource-py/classic_resource.pyi",
    "classic_xse":              "ClassicLib-rs/python-bindings/classic-xse-py/classic_xse.pyi",
    "classic_web":              "ClassicLib-rs/python-bindings/classic-web-py/classic_web.pyi",
    "classic_update":           "ClassicLib-rs/python-bindings/classic-update-py/classic_update.pyi",
    "classic_shared":           "ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi",
}

PYTHON_OWNER_BY_MODULE: dict[str, str] = {
    "classic_scanlog":          "scanlog",
    "classic_config":           "config",
    "classic_version_registry": "version_registry",
    "classic_yaml":             "yaml",
    "classic_database":         "database",
    "classic_file_io":          "file_io",
    "classic_scangame":         "scangame",
    "classic_registry":         "registry",
    "classic_perf":             "perf",
    "classic_settings":         "settings",
    "classic_message":          "message",
    "classic_path":             "path",
    "classic_constants":        "constants",
    "classic_version":          "version",
    "classic_resource":         "resource",
    "classic_xse":              "xse",
    "classic_web":              "web",
    "classic_update":           "update",
    "classic_shared":           "shared",
}

SQUAD_BY_OWNER: dict[str, str] = {
    # Existing (pre-Phase-3) labels preserved for historical compatibility.
    "scanlog":          "Squad A (scanlog/config)",
    "config":           "Squad A (scanlog/config)",
    "version_registry": "Squad B (version-registry)",
    # Phase 3 owner labels -- every new owner needs a squad label for reporting.
    "yaml":             "Squad C (yaml/settings/registry)",
    "database":         "Squad D (database/file_io/resource)",
    "file_io":          "Squad D (database/file_io/resource)",
    "scangame":         "Squad E (scangame/xse)",
    "registry":         "Squad C (yaml/settings/registry)",
    "perf":             "Squad F (perf/message/path/constants/version/web/update)",
    "settings":         "Squad C (yaml/settings/registry)",
    "message":          "Squad F (perf/message/path/constants/version/web/update)",
    "path":             "Squad F (perf/message/path/constants/version/web/update)",
    "constants":        "Squad F (perf/message/path/constants/version/web/update)",
    "version":          "Squad F (perf/message/path/constants/version/web/update)",
    "resource":         "Squad D (database/file_io/resource)",
    "xse":              "Squad E (scangame/xse)",
    "web":              "Squad F (perf/message/path/constants/version/web/update)",
    "update":           "Squad F (perf/message/path/constants/version/web/update)",
    "shared":           "Squad G (foundation/classic-shared-py)",
    # The 'aux' bucket captures owner-less rows such as the file-io
    # FileHasher.cache_size entry tracked outside the primary crate owners.
    "aux":              "Squad D (database/file_io/resource)",
}

# Module-level rendering order for the owner/tier gap table in
# render_diff_markdown(). Derived from RUST_OWNER_BY_CRATE values plus the
# 'aux' label so adding a new crate to RUST_TARGET_CRATES automatically
# propagates to the rendered report (LOW drift guard, enforced by
# tests/test_owner_render_drift.py).
_OWNER_RENDER_ORDER: tuple[str, ...] = tuple(RUST_OWNER_BY_CRATE.values()) + ("aux",)


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


def parse_rust_surface(repo_root: Path, tier1_rust_symbols: set[str]) -> dict[str, Any]:
    """Extract Rust symbols from target crate `lib.rs` files."""
    entries: list[dict[str, Any]] = []

    for crate_name, rel_path in RUST_TARGET_CRATES.items():
        source_path = repo_root / rel_path
        content = source_path.read_text(encoding="utf-8")
        owner_module = RUST_OWNER_BY_CRATE[crate_name]

        for match in re.finditer(r"(?m)^\s*pub\s+mod\s+([A-Za-z0-9_]+)\s*;", content):
            symbol = match.group(1)
            entries.append(
                {
                    "symbol": symbol,
                    "kind": "module",
                    "crate": crate_name,
                    "owner_module": owner_module,
                    "source_file": rel_path,
                    "source_decl": match.group(0).strip(),
                    "tier": "tier1" if symbol in tier1_rust_symbols else "tier2",
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
                    "source_file": rel_path,
                    "source_decl": match.group(0).strip(),
                    "tier": "tier1" if symbol in tier1_rust_symbols else "tier2",
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
                    "source_file": rel_path,
                    "source_decl": match.group(0).strip(),
                    "tier": "tier1" if symbol in tier1_rust_symbols else "tier2",
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
                        "source_file": rel_path,
                        "source_decl": f"pub use {normalize_whitespace(use_body)};",
                        "source_expr": source_expr,
                        "tier": "tier1" if symbol in tier1_rust_symbols else "tier2",
                    }
                )

    entries.sort(key=operator.itemgetter("crate", "symbol", "kind"))
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
                            "tier": "tier1"
                            if class_name in tier1_python_exports
                            else "tier2",
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
                                        "tier": "tier1"
                                        if export_path in tier1_python_exports
                                        or export_name in tier1_python_exports
                                        else "tier2",
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
                            "tier": "tier1"
                            if export_name in tier1_python_exports
                            else "tier2",
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

    # Plan 09b removed the Tier-2 gap emission branches (formerly iterated rust
    # symbols and python exports outside the Tier-1 mapping). Phase 3 enrolled
    # every in-scope Python binding as a Tier-1 contract row, so those deferral
    # branches no longer contribute gate signal. See
    # .planning/phases/03-python-tier-collapse/03-09b-TIER2-CASCADE-AUDIT.md for
    # the full remediation trace and Plan 09b SUMMARY for the C3 endgame details.

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
        lines.append(
            f"| `{owner}` | {tier_counts.get('tier1', 0)} |"
        )

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
        default="ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json",
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
