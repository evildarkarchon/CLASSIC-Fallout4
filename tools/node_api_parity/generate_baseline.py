#!/usr/bin/env python3
"""Generate Phase 1 Rust<->Node parity baseline artifacts."""

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
    # Phase 1 original 10 crates (verified pre-state 2026-04-08).
    "classic-scanlog-core": "ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs",
    "classic-config-core": "ClassicLib-rs/business-logic/classic-config-core/src/lib.rs",
    "classic-version-registry-core": "ClassicLib-rs/business-logic/classic-version-registry-core/src/lib.rs",
    "classic-file-io-core": "ClassicLib-rs/business-logic/classic-file-io-core/src/lib.rs",
    "classic-path-core": "ClassicLib-rs/business-logic/classic-path-core/src/lib.rs",
    "classic-settings-core": "ClassicLib-rs/business-logic/classic-settings-core/src/lib.rs",
    "classic-message-core": "ClassicLib-rs/business-logic/classic-message-core/src/lib.rs",
    "classic-perf-core": "ClassicLib-rs/business-logic/classic-perf-core/src/lib.rs",
    "classic-registry-core": "ClassicLib-rs/business-logic/classic-registry-core/src/lib.rs",
    "classic-shared-core": "ClassicLib-rs/foundation/classic-shared-core/src/lib.rs",
    # Phase 4 Plan 1 expansion (+9 crates) — matches Phase 3's set PLUS
    # classic-crashgen-settings-core per research amendment A1 (Node has a
    # direct classic-node/src/crashgen_rules.rs binding that IS the
    # classic-crashgen-settings-core Node surface).
    "classic-yaml-core": "ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs",
    "classic-version-core": "ClassicLib-rs/business-logic/classic-version-core/src/lib.rs",
    "classic-web-core": "ClassicLib-rs/business-logic/classic-web-core/src/lib.rs",
    "classic-crashgen-settings-core": "ClassicLib-rs/business-logic/classic-crashgen-settings-core/src/lib.rs",
    "classic-update-core": "ClassicLib-rs/business-logic/classic-update-core/src/lib.rs",
    "classic-xse-core": "ClassicLib-rs/business-logic/classic-xse-core/src/lib.rs",
    "classic-database-core": "ClassicLib-rs/business-logic/classic-database-core/src/lib.rs",
    "classic-scangame-core": "ClassicLib-rs/business-logic/classic-scangame-core/src/lib.rs",
    "classic-constants-core": "ClassicLib-rs/business-logic/classic-constants-core/src/lib.rs",
}

# Phase 4 Plan 1 A5: distinct owner labels matching Phase 3 — do NOT collapse
# shared/perf/registry to ``aux``. Crashgen settings gets an explicit
# ``crashgen_settings`` label so it is never silently bucketed.
# MEDIUM concern fix: every crate MUST have an explicit entry here — the
# sizing pipeline fails loud if one is missing rather than defaulting to aux.
RUST_OWNER_BY_CRATE: dict[str, str] = {
    "classic-scanlog-core": "scanlog",
    "classic-config-core": "config",
    "classic-version-registry-core": "version_registry",
    # Foundation/aux crates kept as distinct owners per Phase 3 A5.
    "classic-file-io-core": "file_io",
    "classic-path-core": "path",
    "classic-settings-core": "settings",
    "classic-message-core": "message",
    "classic-perf-core": "perf",
    "classic-registry-core": "registry",
    "classic-shared-core": "shared",
    # Phase 4 expansion — each new crate gets its own distinct owner label.
    "classic-yaml-core": "yaml",
    "classic-version-core": "version",
    "classic-web-core": "web",
    "classic-crashgen-settings-core": "crashgen_settings",
    "classic-update-core": "update",
    "classic-xse-core": "xse",
    "classic-database-core": "database",
    "classic-scangame-core": "scangame",
    "classic-constants-core": "constants",
}

# Squad assignments mirror Phase 3's two-squad shape. The squad label is not
# load-bearing for the gate's exit code — it only controls handoff markdown
# grouping — but every owner referenced in RUST_OWNER_BY_CRATE MUST have a
# squad entry to avoid KeyError in render_handoff_markdown().
SQUAD_BY_OWNER: dict[str, str] = {
    "scanlog": "Squad A (scanlog/config)",
    "config": "Squad A (scanlog/config)",
    "version_registry": "Squad B (version-registry/aux)",
    "aux": "Squad B (version-registry/aux)",
    # Foundation/aux owners (Phase 3 A5 distinct labels).
    "file_io": "Squad B (version-registry/aux)",
    "path": "Squad B (version-registry/aux)",
    "settings": "Squad B (version-registry/aux)",
    "message": "Squad B (version-registry/aux)",
    "perf": "Squad B (version-registry/aux)",
    "registry": "Squad B (version-registry/aux)",
    "shared": "Squad B (version-registry/aux)",
    # Phase 4 Plan 1 expansion owners.
    "yaml": "Squad B (version-registry/aux)",
    "version": "Squad B (version-registry/aux)",
    "web": "Squad B (version-registry/aux)",
    "crashgen_settings": "Squad B (version-registry/aux)",
    "update": "Squad B (version-registry/aux)",
    "xse": "Squad B (version-registry/aux)",
    "database": "Squad B (version-registry/aux)",
    "scangame": "Squad B (version-registry/aux)",
    "constants": "Squad B (version-registry/aux)",
}


def snake_to_camel(name: str) -> str:
    """Convert snake_case to camelCase."""
    chunks = name.split("_")
    if not chunks:
        return name
    return chunks[0] + "".join(chunk.capitalize() for chunk in chunks[1:])


def count_top_level_params(params: str) -> int:
    """Count top-level function parameters in a TypeScript signature string."""
    candidate = params.strip()
    if not candidate:
        return 0

    items: list[str] = []
    current: list[str] = []
    depth = 0
    depth_pairs = {"(": ")", "[": "]", "{": "}", "<": ">"}
    closing = set(depth_pairs.values())
    opening = set(depth_pairs.keys())
    stack: list[str] = []

    for ch in candidate:
        if ch in opening:
            stack.append(depth_pairs[ch])
            depth += 1
        elif ch in closing and stack and ch == stack[-1]:
            stack.pop()
            depth -= 1

        if ch == "," and depth == 0:
            items.append("".join(current).strip())
            current = []
            continue
        current.append(ch)

    tail = "".join(current).strip()
    if tail:
        items.append(tail)

    # Filter out accidental empty entries.
    return len([item for item in items if item])


def normalize_whitespace(value: str) -> str:
    """Collapse consecutive whitespace to a single space."""
    return re.sub(r"\s+", " ", value).strip()


def expand_pub_use_statement(body: str) -> list[tuple[str, str]]:
    """Expand a Rust `pub use` statement into exported symbols and source paths."""
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


def parse_rust_surface(repo_root: Path, tier1_rust_symbols: set[str]) -> dict[str, Any]:
    """Extract Rust public API symbols from target crate `lib.rs` files."""
    entries: list[dict[str, Any]] = []

    for crate_name, rel_path in RUST_TARGET_CRATES.items():
        source_path = repo_root / rel_path
        content = source_path.read_text(encoding="utf-8")
        owner_module = RUST_OWNER_BY_CRATE[crate_name]

        for match in re.finditer(r"(?m)^\s*pub\s+mod\s+([A-Za-z0-9_]+)\s*;", content):
            symbol = match.group(1)
            # Phase 4 Plan 1: include every public symbol for every tracked
            # crate unconditionally. The RUST_FULL_INVENTORY_CRATES filter
            # was deleted along with include_rust_symbol().
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
            arity = count_top_level_params(match.group(2))
            entries.append(
                {
                    "symbol": symbol,
                    "kind": "function",
                    "arity": arity,
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


def infer_node_owner(name: str, tier1_owner_map: dict[str, str]) -> str:
    """Infer owner module for a Node export."""
    if name in tier1_owner_map:
        return tier1_owner_map[name]

    lower_name = name.lower()
    version_tokens = ("version", "crashgen", "addresslib", "addresslibrary", "fallout4")
    config_tokens = ("yaml", "config", "settings", "cache", "pathdetection")
    scanlog_tokens = ("log", "analysis", "formid", "plugin", "papyrus", "gpu", "vr")

    if any(token in lower_name for token in version_tokens):
        return "version_registry"
    if any(token in lower_name for token in config_tokens):
        return "config"
    if any(token in lower_name for token in scanlog_tokens):
        return "scanlog"
    return "aux"


def parse_node_surface(
    repo_root: Path,
    tier1_node_exports: set[str],
    tier1_owner_map: dict[str, str],
    index_dts_rel: str,
) -> dict[str, Any]:
    """Extract Node export surface from classic-node index.d.ts."""
    index_path = repo_root / index_dts_rel
    lines = index_path.read_text(encoding="utf-8").splitlines()
    exports: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    class_re = re.compile(r"^export\s+declare\s+class\s+([A-Za-z0-9_]+)")
    function_re = re.compile(
        r"^export\s+declare\s+function\s+([A-Za-z0-9_]+)\((.*)\)\s*:\s*(.+)$"
    )
    const_enum_re = re.compile(r"^export\s+declare\s+const\s+enum\s+([A-Za-z0-9_]+)")
    interface_re = re.compile(r"^export\s+interface\s+([A-Za-z0-9_]+)")
    type_re = re.compile(r"^export\s+type\s+([A-Za-z0-9_]+)\s*=")
    const_re = re.compile(r"^export\s+const\s+([A-Za-z0-9_]+)\s*:")

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("export "):
            continue

        kind: str | None = None
        name: str | None = None
        arity: int | None = None
        signature: str | None = None

        match = function_re.match(stripped)
        if match:
            kind = "function"
            name = match.group(1)
            params = match.group(2)
            arity = count_top_level_params(params)
            signature = stripped
        else:
            for regex, inferred_kind in (
                (class_re, "class"),
                (const_enum_re, "const_enum"),
                (interface_re, "interface"),
                (type_re, "type"),
                (const_re, "const"),
            ):
                fallback = regex.match(stripped)
                if fallback:
                    kind = inferred_kind
                    name = fallback.group(1)
                    signature = stripped
                    break

        if not kind or not name:
            continue

        dedupe_key = (name, kind)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        owner_module = infer_node_owner(name, tier1_owner_map)
        entry: dict[str, Any] = {
            "export": name,
            "kind": kind,
            "owner_module": owner_module,
            "tier": "tier1" if name in tier1_node_exports else "tier2",
            "source_file": index_dts_rel,
            "signature": signature,
        }
        if arity is not None:
            entry["arity"] = arity
        exports.append(entry)

    exports.sort(key=operator.itemgetter("export", "kind"))
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "scope": {
            "source_file": index_dts_rel,
        },
        "exports": exports,
    }


def _effective_rust_symbol(rust_symbol: Any) -> str:
    """Strip the optional @rust proxy suffix from a contract rustSymbol.

    Phase 4 Plan 2 introduces @rust-suffix proxy rows for Rust-only scanlog
    symbols with no Node binding. The suffix is a marker consumed by the
    bidirectional guard (validate_contract_surface) to skip the Node-side
    lookup; everywhere else (diff report, rust_unmapped bucketing) the
    effective symbol is the bare name before @rust.
    """
    if not isinstance(rust_symbol, str):
        return ""
    if rust_symbol.endswith("@rust"):
        return rust_symbol[: -len("@rust")]
    return rust_symbol


def build_lookup(
    items: list[dict[str, Any]], key_field: str
) -> dict[str, dict[str, Any]]:
    """Build a name lookup dictionary from manifest entries."""
    lookup: dict[str, dict[str, Any]] = {}
    for item in items:
        key = item[key_field]
        if key not in lookup:
            lookup[key] = item
    return lookup


def generate_diff_report(
    contract: dict[str, Any],
    rust_manifest: dict[str, Any],
    node_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Generate contract results and parity gaps."""
    tier1_mappings: list[dict[str, Any]] = contract["tier1Mappings"]
    rust_symbols: list[dict[str, Any]] = rust_manifest["symbols"]
    node_exports: list[dict[str, Any]] = node_manifest["exports"]

    rust_lookup = build_lookup(rust_symbols, "symbol")
    node_lookup = build_lookup(node_exports, "export")

    # Phase 4 Plan 2: @rust-suffix proxy rows intentionally omit nodeExport.
    # Strip the suffix to get the effective Rust symbol for tier1 tracking
    # (so a proxy row for `FormIDAnalyzer@rust` marks `FormIDAnalyzer` as
    # tier1-mapped for the rust_unmapped gap calculation below).
    tier1_rust_symbols = {
        _effective_rust_symbol(mapping["rustSymbol"]) for mapping in tier1_mappings
    }
    tier1_node_exports = {
        mapping["nodeExport"]
        for mapping in tier1_mappings
        if mapping.get("nodeExport") is not None
    }

    contract_results: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    for mapping in tier1_mappings:
        rust_symbol = mapping["rustSymbol"]
        node_export = mapping.get("nodeExport")
        expected_arity = mapping.get("nodeArity")
        expected_kind = mapping.get("nodeKind")
        owner_module = mapping["ownerModule"]
        is_proxy = isinstance(rust_symbol, str) and rust_symbol.endswith("@rust")
        effective_rust_symbol = _effective_rust_symbol(rust_symbol)

        rust_item = rust_lookup.get(effective_rust_symbol)
        node_item = node_lookup.get(node_export) if node_export is not None else None
        status = "matched"
        reason = ""

        if rust_item is None:
            status = "missing_rust"
            reason = f"Rust symbol '{effective_rust_symbol}' not found in target crate exports."
        elif is_proxy:
            # @rust-suffix proxy rows: Rust-side only, no Node surface check.
            status = "matched"
        elif node_item is None:
            status = "missing_node"
            reason = f"Node export '{node_export}' not found in index.d.ts."
        elif expected_kind and node_item["kind"] != expected_kind:
            status = "signature_mismatch"
            reason = (
                f"Expected Node kind '{expected_kind}', found '{node_item['kind']}'."
            )
        elif expected_arity is not None and node_item.get("arity") != expected_arity:
            status = "signature_mismatch"
            reason = f"Expected Node arity {expected_arity}, found {node_item.get('arity', 'n/a')}."

        contract_row = {
            "id": mapping["id"],
            "tier": mapping["tier"],
            "owner_module": owner_module,
            "squad": SQUAD_BY_OWNER[owner_module],
            "rust_symbol": rust_symbol,
            "node_export": node_export,
            "status": status,
            "expected_node_kind": expected_kind,
            "actual_node_kind": node_item["kind"] if node_item else None,
            "expected_node_arity": expected_arity,
            "actual_node_arity": node_item.get("arity") if node_item else None,
        }
        if reason:
            contract_row["reason"] = reason
        contract_results.append(contract_row)

        if status != "matched":
            gaps.append(
                {
                    "gap_type": f"tier1_{status}",
                    "tier": "tier1",
                    "owner_module": owner_module,
                    "squad": SQUAD_BY_OWNER[owner_module],
                    "rust_symbol": rust_symbol,
                    "node_export": node_export,
                    "reason": reason,
                }
            )

    for rust_item in rust_symbols:
        symbol = rust_item["symbol"]
        if symbol in tier1_rust_symbols:
            continue
        owner_module = rust_item["owner_module"]
        gaps.append(
            {
                "gap_type": "rust_unmapped",
                "tier": "tier2",
                "owner_module": owner_module,
                "squad": SQUAD_BY_OWNER[owner_module],
                "rust_symbol": symbol,
                "node_export": None,
                "reason": "Rust public symbol is outside Tier-1 mapping scope (deferred).",
                "crate": rust_item["crate"],
                "kind": rust_item["kind"],
            }
        )

    for node_item in node_exports:
        export_name = node_item["export"]
        if export_name in tier1_node_exports:
            continue
        owner_module = node_item["owner_module"]
        gaps.append(
            {
                "gap_type": "node_unmapped",
                "tier": "tier2",
                "owner_module": owner_module,
                "squad": SQUAD_BY_OWNER[owner_module],
                "rust_symbol": None,
                "node_export": export_name,
                "reason": "Node export is outside Tier-1 mapping scope (deferred).",
                "kind": node_item["kind"],
            }
        )

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
        "tier1_missing_node": status_counts.get("missing_node", 0),
        "tier1_signature_mismatch": status_counts.get("signature_mismatch", 0),
        "total_gaps": len(gaps),
        "tier1_gap_total": sum(1 for gap in gaps if gap["tier"] == "tier1"),
        "tier2_gap_total": sum(1 for gap in gaps if gap["tier"] == "tier2"),
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
    """Render a concise Markdown parity diff summary."""
    summary = diff_report["summary"]
    lines: list[str] = []
    lines.extend(
        (
            "# Rust<->Node Parity Diff Baseline (Phase 1)",
            "",
            f"- Generated: `{diff_report['generated_at_utc']}`",
            f"- Tier-1 contract rows: **{summary['tier1_contract_total']}**",
            f"- Tier-1 matched: **{summary['tier1_matched']}**",
            f"- Tier-1 missing Rust: **{summary['tier1_missing_rust']}**",
            f"- Tier-1 missing Node: **{summary['tier1_missing_node']}**",
            f"- Tier-1 signature mismatch: **{summary['tier1_signature_mismatch']}**",
            f"- Total gaps (Tier-1 + Tier-2): **{summary['total_gaps']}**",
            "",
            "## Tier-1 Contract Evaluation",
            "",
            "| ID | Owner Module | Rust Symbol | Node Export | Status |",
            "|---|---|---|---|---|",
        )
    )
    for row in diff_report["contract_results"]:
        lines.append(
            f"| `{row['id']}` | `{row['owner_module']}` | `{row['rust_symbol']}` | `{row['node_export']}` | `{row['status']}` |"
        )

    lines.extend(
        (
            "",
            "## Gap Counts By Owner/Tier",
            "",
            "| Owner Module | Tier 1 Gaps | Tier 2 Gaps |",
            "|---|---:|---:|",
        )
    )
    # Phase 4 Plan 1: iterate every owner that appears in the diff report
    # rather than hard-coding a short tuple. With the RUST_TARGET_CRATES
    # expansion from 10 to 19 crates there are now 19+ distinct owner
    # labels, and any new one would silently drop rows under the old
    # hard-coded tuple.
    _owner_render_order = sorted(diff_report.get("gap_counts_by_owner_tier", {}))
    for owner in _owner_render_order:
        tier_counts = diff_report["gap_counts_by_owner_tier"].get(owner, {})
        lines.append(
            f"| `{owner}` | {tier_counts.get('tier1', 0)} | {tier_counts.get('tier2', 0)} |"
        )

    lines.extend(
        (
            "",
            "Detailed, per-gap annotations (including `tier`, `owner_module`, and `squad`) are in `parity_diff_report.json`.",
            "",
        )
    )
    return "\n".join(lines)


def render_handoff_markdown(diff_report: dict[str, Any]) -> str:
    """Render the engineering handoff map for module squads."""
    gaps = diff_report["gaps"]
    by_squad_module: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for gap in gaps:
        by_squad_module[gap["squad"]][gap["owner_module"]].append(gap)

    lines: list[str] = []
    lines.extend(
        (
            "# Phase 1 Engineering Handoff Map",
            "",
            f"- Generated: `{diff_report['generated_at_utc']}`",
            f"- Total gaps handed off: **{len(gaps)}**",
            "",
        )
    )

    for squad in ("Squad A (scanlog/config)", "Squad B (version-registry/aux)"):
        lines.extend((f"## {squad}", ""))
        module_map = by_squad_module.get(squad, {})
        if not module_map:
            lines.extend(("- No gaps assigned.", ""))
            continue

        for owner_module in sorted(module_map):
            module_gaps = module_map[owner_module]
            tier1_count = sum(1 for gap in module_gaps if gap["tier"] == "tier1")
            tier2_count = sum(1 for gap in module_gaps if gap["tier"] == "tier2")
            lines.extend(
                (
                    f"### `{owner_module}`",
                    "",
                    f"- Total gaps: **{len(module_gaps)}**",
                    f"- Tier 1 gaps: **{tier1_count}**",
                    f"- Tier 2 gaps: **{tier2_count}**",
                    "",
                    "| Gap Type | Tier | Rust Symbol | Node Export |",
                    "|---|---|---|---|",
                )
            )
            for gap in module_gaps:
                lines.append(
                    f"| `{gap['gap_type']}` | `{gap['tier']}` | `{gap.get('rust_symbol') or '-'}` | `{gap.get('node_export') or '-'}` |"
                )
            lines.append("")

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
        description="Generate Rust/Node API surfaces and parity diff artifacts."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Repository root path.",
    )
    parser.add_argument(
        "--contract",
        default="docs/implementation/node_api_parity/baseline/parity_contract.json",
        help="Path to parity contract JSON, relative to repo root.",
    )
    parser.add_argument(
        "--index-dts",
        default="ClassicLib-rs/node-bindings/classic-node/index.d.ts",
        help="Path to Node index.d.ts, relative to repo root.",
    )
    parser.add_argument(
        "--output-dir",
        default="docs/implementation/node_api_parity/baseline",
        help="Directory for generated output files, relative to repo root.",
    )
    parser.add_argument(
        "--runtime-registry",
        default="ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json",
        help="Path to the Node runtime coverage registry JSON, relative to repo root.",
    )
    parser.add_argument(
        "--deferred-registry",
        default="docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json",
        help="Path to the Node deferred backlog registry JSON, relative to repo root.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    contract_path = repo_root / args.contract
    output_dir = repo_root / args.output_dir

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    tier1_mappings: list[dict[str, Any]] = contract["tier1Mappings"]
    # Phase 4 Plan 2: @rust proxy rows only have Rust symbols; strip the
    # suffix for tier1 rust-set tracking and skip proxy rows in the node-side
    # lookup because they intentionally omit nodeExport.
    tier1_rust_symbols = {
        _effective_rust_symbol(mapping["rustSymbol"]) for mapping in tier1_mappings
    }
    tier1_node_exports = {
        mapping["nodeExport"]
        for mapping in tier1_mappings
        if mapping.get("nodeExport") is not None
    }
    tier1_owner_map = {
        mapping["nodeExport"]: mapping["ownerModule"]
        for mapping in tier1_mappings
        if mapping.get("nodeExport") is not None
    }

    rust_manifest = parse_rust_surface(repo_root, tier1_rust_symbols)
    node_manifest = parse_node_surface(
        repo_root,
        tier1_node_exports=tier1_node_exports,
        tier1_owner_map=tier1_owner_map,
        index_dts_rel=args.index_dts,
    )
    diff_report = generate_diff_report(contract, rust_manifest, node_manifest)
    runtime_registry = load_json_file(repo_root / args.runtime_registry)
    deferred_registry = load_json_file(repo_root / args.deferred_registry)
    coverage_summary = build_coverage_summary(
        binding="node",
        contract=contract,
        diff_report=diff_report,
        runtime_registry=runtime_registry,
        deferred_registry=deferred_registry,
        source_paths={
            "contract": args.contract,
            "runtime_registry": args.runtime_registry,
            "deferred_registry": args.deferred_registry,
            "index_dts": args.index_dts,
        },
    )

    write_json(output_dir / "rust_api_surface.json", rust_manifest)
    write_json(output_dir / "node_api_surface.json", node_manifest)
    write_json(output_dir / "parity_diff_report.json", diff_report)
    (output_dir / "parity_diff_report.md").write_text(
        render_diff_markdown(diff_report), encoding="utf-8"
    )
    write_json(output_dir / "runtime_coverage_summary.json", coverage_summary)
    (output_dir / "runtime_coverage_summary.md").write_text(
        render_coverage_summary_markdown(coverage_summary), encoding="utf-8"
    )
    (output_dir / "handoff_map.md").write_text(
        render_handoff_markdown(diff_report), encoding="utf-8"
    )

    print("Phase 1 parity baseline generated:")
    print(f"- {output_dir / 'rust_api_surface.json'}")
    print(f"- {output_dir / 'node_api_surface.json'}")
    print(f"- {output_dir / 'parity_diff_report.json'}")
    print(f"- {output_dir / 'parity_diff_report.md'}")
    print(f"- {output_dir / 'runtime_coverage_summary.json'}")
    print(f"- {output_dir / 'runtime_coverage_summary.md'}")
    print(f"- {output_dir / 'handoff_map.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
