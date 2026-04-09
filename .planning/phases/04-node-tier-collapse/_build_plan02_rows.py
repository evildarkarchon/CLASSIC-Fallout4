"""Helper script for Phase 4 Plan 2: build scanlog promotion contract rows.

Reads deferred_runtime_backlog.json, filters scanlog entries, splits into
rust-only (proxy @rust rows) vs node-exposed (normal rows), and emits the
new tier1Mappings rows for parity_contract.json.

Per A2: GLOBAL_FCX_HANDLER is excluded (Phase 3 R9 precedent).
Per A3: every new row has rustCrate: 'classic-scanlog-core'.
Per A7: @rust proxy rows have no nodeExport field.

Usage:
    python .planning/phases/04-node-tier-collapse/_build_plan02_rows.py --inspect
    python .planning/phases/04-node-tier-collapse/_build_plan02_rows.py --emit
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BACKLOG_PATH = REPO / "docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json"
CONTRACT_PATH = REPO / "docs/implementation/node_api_parity/baseline/parity_contract.json"
RUST_SURFACE_PATH = REPO / "docs/implementation/node_api_parity/baseline/rust_api_surface.json"
NODE_SURFACE_PATH = REPO / "docs/implementation/node_api_parity/baseline/node_api_surface.json"
SCANLOG_LIB_RS = REPO / "ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs"

# Deterministic mapping from a Rust free function to its sub-module, per source
# layout in classic-scanlog-core. Used only for nicer row IDs; the rustSymbol
# remains the bare name that rust_api_surface.json indexes.
#
# Anything not in this table falls through to SUBMODULE_BY_TYPE below.
FREE_FN_SUBMODULE = {
    "contains_plugin": "plugin_analyzer",
    "contains_record": "record_scanner",
    "crashgen_version_gen": "version",
    "detect_mods_batch": "mod_detector",
    "detect_mods_double": "mod_detector",
    "detect_mods_important": "mod_detector",
    "detect_mods_single": "mod_detector",
    "detect_plugins_batch": "plugin_analyzer",
    "extract_formids_batch": "formid",
    "is_valid_formid": "formid",
    "scan_records_batch": "record_scanner",
    "validate_formids_batch": "formid_analyzer",
    "resolve_batch_concurrency": "orchestrator",
}

# Sub-module mapping for Rust types (classes/enums/structs) in scanlog.
# Only used to produce stable, readable row IDs — not load-bearing on rust_surface.
TYPE_SUBMODULE = {
    "AnalysisResult": "orchestrator",
    "CheckId": "settings_validator",
    "ConfigIssue": "settings_validator",
    "CrashgenEntry": "crashgen_registry",
    "CrashgenRegistry": "crashgen_registry",
    "FcxModeHandler": "fcx_handler",
    "FcxResetError": "fcx_handler",
    "FormIDAnalyzer": "formid_analyzer",
    "FormIDAnalyzerCore": "formid_analyzer",
    "GpuDetector": "gpu_detector",
    "GpuVendor": "gpu_detector",
    "PapyrusAnalyzer": "papyrus",
    "PapyrusError": "papyrus",
    "PluginAnalyzer": "plugin_analyzer",
    "RecordScanner": "record_scanner",
    "ReportComposer": "report",
    "ReportFragment": "report",
    "ReportGenerator": "report",
    "RustFormIDAnalyzer": "formid_analyzer",
    "ScanLogError": "error",
    "SettingsValidator": "settings_validator",
    "StreamingIteratorParser": "parser",
    "StreamingLogParser": "parser",
    "StringPool": "parser",
    "SuspectScanner": "suspect_scanner",
    "ScanProgressPhase": "orchestrator",
}

# Sub-module markers (the `pub mod` declarations themselves).
MODULE_MARKERS = {
    "crashgen_registry",
    "error",
    "fcx_handler",
    "formid",
    "formid_analyzer",
    "gpu_detector",
    "mod_detector",
    "orchestrator",
    "papyrus",
    "parser",
    "patterns",
    "plugin_analyzer",
    "record_scanner",
    "report",
    "segment_key",
    "settings_validator",
    "suspect_scanner",
    "version",
}


def classify_symbol(symbol: str) -> tuple[str, str]:
    """Return (rustKind, sub_module) for a scanlog symbol."""
    if symbol in MODULE_MARKERS:
        return "module", symbol
    if symbol in FREE_FN_SUBMODULE:
        return "function", FREE_FN_SUBMODULE[symbol]
    if symbol in TYPE_SUBMODULE:
        # Determine class vs enum heuristically: a few of these are enums.
        enum_names = {"CheckId", "FcxResetError", "GpuVendor", "ScanLogError", "PapyrusError", "ScanProgressPhase"}
        kind = "enum" if symbol in enum_names else "class"
        return kind, TYPE_SUBMODULE[symbol]
    # Unknown symbol — fall back to class with empty sub-module.
    return "class", ""


# Node-exposed scanlog deferred entries. Each entry maps a coverage ID to the
# concrete rustSymbol and nodeKind used in the contract row.
#
# rustSymbol values are verified against classic-scanlog-core's actual public
# surface (rust_api_surface.json) and the corresponding NAPI wrapper types in
# ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs. Two entries
# (JsAnalysisBuildOptions, JsLogSegments) have no 1:1 core-type analog, so
# they are pinned to the nearest semantic core symbol that IS present in
# rust_api_surface.json (the build-config function and LogParser, respectively).
NODE_EXPOSED_ROWS = [
    # (row_id, nodeExport, rustSymbol, rustKind, nodeKind)
    ("scanlog.patterns.CRASH_LOG_PATTERN", "CRASH_LOG_PATTERN", "CRASH_LOG_PATTERN", "const", "const"),
    ("scanlog.orchestrator.JsAnalysisBuildOptions", "JsAnalysisBuildOptions", "build_analysis_config_from_yaml", "function", "interface"),
    ("scanlog.orchestrator.JsAnalysisResult", "JsAnalysisResult", "AnalysisResult", "class", "interface"),
    ("scanlog.gpu_detector.JsGpuInfo", "JsGpuInfo", "GpuInfo", "class", "interface"),
    ("scanlog.parser.JsLogErrorEntry", "JsLogErrorEntry", "LogErrorEntry", "class", "interface"),
    ("scanlog.parser.JsLogSegments", "JsLogSegments", "LogParser", "class", "interface"),
    ("scanlog.papyrus.JsPapyrusStats", "JsPapyrusStats", "PapyrusStats", "class", "interface"),
    ("scanlog.settings_validator.checkXsePlugins", "checkXsePlugins", "XseChecker", "class", "function"),
    ("scanlog.parser.parseXseLog", "parseXseLog", "parse_xse_log", "function", "function"),
]


def load_backlog() -> list[dict]:
    data = json.loads(BACKLOG_PATH.read_text(encoding="utf-8"))
    return [e for e in data["entries"] if e.get("ownerModule") == "scanlog"]


def reconcile_counts(scanlog_entries: list[dict]) -> dict:
    rust_only = [
        e for e in scanlog_entries
        if not e.get("bindingIdentifiers")
        and "GLOBAL_FCX_HANDLER" not in e.get("rustSymbols", [])
    ]
    node_exposed = [e for e in scanlog_entries if e.get("bindingIdentifiers")]
    global_fcx = [e for e in scanlog_entries if "GLOBAL_FCX_HANDLER" in e.get("rustSymbols", [])]
    rust_only_symbols = sum(len(e.get("rustSymbols", [])) for e in rust_only)
    return {
        "total_scanlog": len(scanlog_entries),
        "rust_only_entries": len(rust_only),
        "rust_only_symbols": rust_only_symbols,
        "node_exposed_entries": len(node_exposed),
        "global_fcx_handler_entries": len(global_fcx),
        "expected_proxy_rows": rust_only_symbols,
        "expected_normal_rows": len(node_exposed),
        "expected_total_new_rows": rust_only_symbols + len(node_exposed),
    }


def build_proxy_rows(scanlog_entries: list[dict]) -> list[dict]:
    rows = []
    seen_ids = set()
    for entry in scanlog_entries:
        if entry.get("bindingIdentifiers"):
            continue
        for symbol in entry.get("rustSymbols", []):
            if symbol == "GLOBAL_FCX_HANDLER":
                continue
            rust_kind, sub_module = classify_symbol(symbol)
            row_id = (
                f"scanlog.{sub_module}.{symbol}@rust" if sub_module else f"scanlog.{symbol}@rust"
            )
            if row_id in seen_ids:
                continue
            seen_ids.add(row_id)
            rows.append({
                "id": row_id,
                "tier": "tier1",
                "ownerModule": "scanlog",
                "rustCrate": "classic-scanlog-core",
                "rustSymbol": f"{symbol}@rust",
                "rustKind": rust_kind,
            })
    return rows


def build_normal_rows() -> list[dict]:
    rows = []
    for row_id, node_export, rust_symbol, rust_kind, node_kind in NODE_EXPOSED_ROWS:
        rows.append({
            "id": row_id,
            "tier": "tier1",
            "ownerModule": "scanlog",
            "rustCrate": "classic-scanlog-core",
            "rustSymbol": rust_symbol,
            "rustKind": rust_kind,
            "nodeExport": node_export,
            "nodeKind": node_kind,
        })
    return rows


def validate_against_surfaces(proxy_rows: list[dict], normal_rows: list[dict]) -> dict:
    """Validate generated rows against rust_api_surface.json + node_api_surface.json.

    The real file shapes (post-Plan-1):
      - rust_api_surface.json["symbols"] is a flat list of dicts with key "symbol"
      - node_api_surface.json["exports"] is a flat list of dicts with key "export"
    """
    rust_surface = json.loads(RUST_SURFACE_PATH.read_text(encoding="utf-8"))
    node_surface = json.loads(NODE_SURFACE_PATH.read_text(encoding="utf-8"))

    rust_syms = {s["symbol"] for s in rust_surface.get("symbols", [])}
    node_exports = {e["export"] for e in node_surface.get("exports", [])}

    # Count scanlog-owned rust symbols for reference.
    scanlog_rust_count = sum(
        1 for s in rust_surface.get("symbols", []) if s.get("crate") == "classic-scanlog-core"
    )

    proxy_missing = []
    for row in proxy_rows:
        bare = row["rustSymbol"].removesuffix("@rust")
        if bare not in rust_syms:
            proxy_missing.append(bare)

    normal_rust_missing = []
    normal_node_missing = []
    for row in normal_rows:
        if row["rustSymbol"] not in rust_syms:
            normal_rust_missing.append(row["rustSymbol"])
        if row["nodeExport"] not in node_exports:
            normal_node_missing.append(row["nodeExport"])

    return {
        "total_rust_symbols": len(rust_syms),
        "scanlog_rust_symbol_count": scanlog_rust_count,
        "total_node_exports": len(node_exports),
        "proxy_missing_from_rust_surface": proxy_missing,
        "normal_missing_from_rust_surface": normal_rust_missing,
        "normal_missing_from_node_surface": normal_node_missing,
    }


def apply_to_contract(proxy_rows: list[dict], normal_rows: list[dict], mode: str) -> dict:
    """Append rows to parity_contract.json::tier1Mappings.

    mode='proxy'   -> append proxy_rows only
    mode='normal'  -> append normal_rows only
    mode='both'    -> append both (used for dry-run verification)

    Returns a summary dict with counts added and final row totals.
    """
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    existing_ids = {r.get("id") for r in contract["tier1Mappings"]}
    before_count = len(contract["tier1Mappings"])

    to_add: list[dict] = []
    if mode in ("proxy", "both"):
        to_add.extend(proxy_rows)
    if mode in ("normal", "both"):
        to_add.extend(normal_rows)

    duplicates = [r for r in to_add if r.get("id") in existing_ids]
    if duplicates:
        raise RuntimeError(
            f"Refusing to add {len(duplicates)} duplicate row IDs: "
            f"{[r['id'] for r in duplicates][:5]}..."
        )

    contract["tier1Mappings"].extend(to_add)
    # Preserve existing CRLF line endings (file is `text: set` in gitattributes
    # and git's core.autocrlf=true is active on this Windows worktree).
    text = json.dumps(contract, indent=2, ensure_ascii=False) + "\n"
    CONTRACT_PATH.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))

    return {
        "mode": mode,
        "before_count": before_count,
        "after_count": len(contract["tier1Mappings"]),
        "added_count": len(to_add),
        "proxy_added": len(proxy_rows) if mode in ("proxy", "both") else 0,
        "normal_added": len(normal_rows) if mode in ("normal", "both") else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspect", action="store_true", help="Print reconciled counts")
    parser.add_argument("--emit", action="store_true", help="Print JSON of new rows")
    parser.add_argument("--validate", action="store_true", help="Validate rows against surface files")
    parser.add_argument(
        "--apply",
        choices=["proxy", "normal", "both"],
        help="Write rows to parity_contract.json (mutates file).",
    )
    args = parser.parse_args()

    scanlog_entries = load_backlog()
    counts = reconcile_counts(scanlog_entries)

    if args.inspect or not (args.emit or args.validate):
        print("=== Scanlog reconciliation (live data) ===")
        for k, v in counts.items():
            print(f"  {k}: {v}")
        print()
        print("A7 research figure: 58 (rust-only symbols)")
        print(f"Live figure: {counts['rust_only_symbols']}")
        print(f"Delta: {counts['rust_only_symbols'] - 58}")
        print("Acceptance window: (57, 58) per Plan 2 Issue 7 reconciliation.")
        if counts["rust_only_symbols"] not in (57, 58):
            print("ERROR: live count outside acceptance window", file=sys.stderr)
            return 2

    if args.emit:
        proxy = build_proxy_rows(scanlog_entries)
        normal = build_normal_rows()
        print(json.dumps({
            "counts": counts,
            "proxy_row_count": len(proxy),
            "normal_row_count": len(normal),
            "proxy_rows": proxy,
            "normal_rows": normal,
        }, indent=2))

    if args.validate:
        proxy = build_proxy_rows(scanlog_entries)
        normal = build_normal_rows()
        result = validate_against_surfaces(proxy, normal)
        print(json.dumps(result, indent=2))
        if result["proxy_missing_from_rust_surface"] or result["normal_missing_from_rust_surface"] or result["normal_missing_from_node_surface"]:
            return 3

    if args.apply:
        proxy = build_proxy_rows(scanlog_entries)
        normal = build_normal_rows()
        summary = apply_to_contract(proxy, normal, args.apply)
        print(json.dumps(summary, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
