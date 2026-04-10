#!/usr/bin/env python3
"""Build the 74 Wave 1 contract rows for Phase 3 Plan 02 (scratch helper)."""
from __future__ import annotations
import json
from pathlib import Path

REPO_ROOT = Path.cwd()
CONTRACT = REPO_ROOT / "docs/implementation/python_api_parity/baseline/parity_contract.json"
DEFERRED = REPO_ROOT / "docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json"


def main() -> None:
    with open(DEFERRED, encoding="utf-8") as f:
        deferred = json.load(f)
    with open(CONTRACT, encoding="utf-8") as f:
        contract = json.load(f)

    w1_classes = {
        "LogParser", "ScanOutput", "FormIDAnalyzer", "FormIDAnalyzerCore",
        "RecordScanner", "PluginAnalyzer", "PatternMatcher",
    }
    w1_free_fns = {
        "extract_formids_batch", "is_valid_formid", "validate_formids_batch",
        "scan_records_batch", "contains_record", "detect_plugins_batch", "contains_plugin",
    }
    w1_rust_symbols = {
        "LogParser", "StreamingLogParser", "StreamingIteratorParser",
        "RustFormIDAnalyzer", "FormIDAnalyzer", "FormIDAnalyzerCore",
        "RecordScanner", "PluginAnalyzer", "PatternMatcher",
        "extract_formids_batch", "is_valid_formid", "validate_formids_batch",
        "scan_records_batch", "contains_record", "detect_plugins_batch", "contains_plugin",
        "parser", "formid", "formid_analyzer", "record_scanner",
        "plugin_analyzer", "patterns",
    }

    scanlog = [e for e in deferred["entries"] if e["ownerModule"] == "scanlog"]
    rust_only: list[str] = []
    python_only: list[str] = []
    for e in scanlog:
        if e.get("rustSymbols"):
            sym = e["rustSymbols"][0]
            if sym in w1_rust_symbols:
                rust_only.append(sym)
                continue
        if e.get("bindingIdentifiers"):
            ident = e["bindingIdentifiers"][0]
            path = ident.replace("classic_scanlog.", "")
            top = path.split(".")[0]
            if top in w1_classes or top in w1_free_fns:
                python_only.append(path)

    assert len(rust_only) == 19, f"expected 19 rust-only got {len(rust_only)}"
    assert len(python_only) == 55, f"expected 55 python-only got {len(python_only)}"

    class_to_rust = {
        "LogParser": "LogParser",
        "FormIDAnalyzer": "RustFormIDAnalyzer",
        "FormIDAnalyzerCore": "FormIDAnalyzerCore",
        "RecordScanner": "RecordScanner",
        "PluginAnalyzer": "PluginAnalyzer",
        "PatternMatcher": "PatternMatcher",
        "ScanOutput": "LogParser",
    }

    def submod_for_class(name: str) -> str:
        if name in ("LogParser", "ScanOutput"):
            return "parser"
        if name == "FormIDAnalyzer":
            return "formid_analyzer"
        if name == "FormIDAnalyzerCore":
            return "formid_analyzer"
        if name == "RecordScanner":
            return "record_scanner"
        if name == "PluginAnalyzer":
            return "plugin_analyzer"
        if name == "PatternMatcher":
            return "patterns"
        return "parser"

    def submod_for_free_fn(fn: str) -> str:
        if fn in ("extract_formids_batch", "is_valid_formid", "validate_formids_batch"):
            return "formid_analyzer"
        if fn in ("scan_records_batch", "contains_record"):
            return "record_scanner"
        if fn in ("detect_plugins_batch", "contains_plugin"):
            return "plugin_analyzer"
        return "parser"

    py_surface = json.load(
        open(REPO_ROOT / "docs/implementation/python_api_parity/baseline/python_api_surface.json", encoding="utf-8")
    )
    py_index = {}
    for e in py_surface["exports"]:
        if e["module"] == "classic_scanlog":
            py_index[e["export_path"]] = e

    def make_row(id_: str, rust_symbol: str, py_path: str, kind: str) -> dict:
        py_item = py_index.get(py_path)
        py_kind = py_item["kind"] if py_item else kind
        row = {
            "id": id_,
            "tier": "tier1",
            "ownerModule": "scanlog",
            "rustCrate": "classic-scanlog-core",
            "rustSymbol": rust_symbol,
            "pythonModule": "classic_scanlog",
            "pythonExportPath": py_path,
            "pythonKind": py_kind,
        }
        if py_item and py_item.get("arity") is not None:
            row["pythonArity"] = py_item["arity"]
        return row

    rows: list[dict] = []

    for path in sorted(python_only):
        top = path.split(".")[0]
        if top in w1_free_fns:
            rust_sym = top
            kind = "function"
            submod = submod_for_free_fn(top)
        elif "." in path:
            rust_sym = class_to_rust.get(top, top)
            kind = "method"
            submod = submod_for_class(top)
        else:
            rust_sym = class_to_rust.get(top, top)
            kind = "class"
            submod = submod_for_class(top)
        id_ = f"scanlog.{submod}.{path}"
        rows.append(make_row(id_, rust_sym, path, kind))

    for rs in sorted(rust_only):
        if rs in w1_free_fns:
            py_path = rs
            kind = "function"
            submod = submod_for_free_fn(rs)
        elif rs == "RustFormIDAnalyzer":
            py_path = "FormIDAnalyzer"
            kind = "class"
            submod = "formid"
        elif rs == "StreamingLogParser":
            py_path = "LogParser"
            kind = "class"
            submod = "parser"
        elif rs == "StreamingIteratorParser":
            py_path = "LogParser"
            kind = "class"
            submod = "parser"
        elif rs in ("parser", "formid", "formid_analyzer", "record_scanner", "plugin_analyzer", "patterns"):
            module_to_class = {
                "parser": "LogParser",
                "formid": "FormIDAnalyzer",
                "formid_analyzer": "FormIDAnalyzerCore",
                "record_scanner": "RecordScanner",
                "plugin_analyzer": "PluginAnalyzer",
                "patterns": "PatternMatcher",
            }
            py_path = module_to_class[rs]
            kind = "class"
            submod = rs
        elif rs == "FormIDAnalyzer":
            py_path = "FormIDAnalyzer"
            kind = "class"
            submod = "formid_analyzer"
        elif rs in ("FormIDAnalyzerCore", "PluginAnalyzer", "RecordScanner"):
            py_path = rs
            kind = "class"
            submod = submod_for_class(rs)
        else:
            raise RuntimeError(f"Unhandled rust-only symbol: {rs}")

        id_ = f"scanlog.{submod}.{rs}@rust"
        rows.append(make_row(id_, rs, py_path, kind))

    assert len(rows) == 74, f"expected 74 got {len(rows)}"
    ids = [r["id"] for r in rows]
    assert len(set(ids)) == 74, "duplicate IDs"

    rows.sort(key=lambda r: r["id"])
    contract["tier1Mappings"].extend(rows)
    contract["tier1Mappings"].sort(key=lambda r: r["id"])

    with open(CONTRACT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(contract, f, indent=2)
        f.write("\n")

    print(f"Wrote contract with {len(contract['tier1Mappings'])} tier1 rows (added {len(rows)})")
    print("---")
    print(f"Wave1 prefix counts:")
    counts = {}
    for r in rows:
        prefix = ".".join(r["id"].split(".")[:2])
        counts[prefix] = counts.get(prefix, 0) + 1
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
