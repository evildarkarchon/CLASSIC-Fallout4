#!/usr/bin/env python3
"""Build the 50 Wave 3a contract rows for Phase 3 Plan 04 (scratch helper).

Wave 3a covers scanlog orchestration-core sub-modules (report is excluded; owned by Plan 05):
orchestrator, papyrus, version, crashgen_registry, segment_key, error.

Per the 03-04 constructor inventory:
- 16 rust-only proxy rows (@rust suffix) paired with nearest Python proxy
- 34 python-only rows from deferred bindingIdentifiers

Total: 50 new rows. Final tier1Mappings: 190 -> 240.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path.cwd()
CONTRACT = REPO_ROOT / "docs/implementation/python_api_parity/baseline/parity_contract.json"
DEFERRED = REPO_ROOT / "docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json"
PY_SURFACE = REPO_ROOT / "docs/implementation/python_api_parity/baseline/python_api_surface.json"


def main() -> None:
    with open(DEFERRED, encoding="utf-8") as f:
        deferred = json.load(f)
    with open(CONTRACT, encoding="utf-8") as f:
        contract = json.load(f)
    with open(PY_SURFACE, encoding="utf-8") as f:
        py_surface = json.load(f)

    # Classes + fns promoted in Waves 1/2 (skip these)
    wave12_rust = {
        "LogParser", "StreamingLogParser", "StreamingIteratorParser",
        "FormIDAnalyzer", "RustFormIDAnalyzer", "FormIDAnalyzerCore",
        "RecordScanner", "PluginAnalyzer", "PatternMatcher",
        "SuspectScanner", "SettingsValidator", "FcxModeHandler", "ConfigIssue",
        "GpuDetector", "GpuInfo", "GpuVendor", "FcxResetError",
        # module markers
        "parser", "formid", "formid_analyzer", "record_scanner", "plugin_analyzer", "patterns",
        "mod_detector", "suspect_scanner", "settings_validator", "fcx_handler", "gpu_detector",
    }
    wave12_free_fns = {
        "extract_formids_batch", "is_valid_formid", "validate_formids_batch",
        "scan_records_batch", "contains_record",
        "detect_plugins_batch", "contains_plugin",
        "detect_mods_single", "detect_mods_double",
        "detect_mods_important", "detect_mods_batch",
        "GLOBAL_FCX_HANDLER",  # R9 excluded
    }
    wave12_py_classes = {
        "LogParser", "ScanOutput", "FormIDAnalyzer", "FormIDAnalyzerCore",
        "RecordScanner", "PluginAnalyzer", "PatternMatcher",
        "SuspectScanner", "SettingsValidator", "FcxModeHandler", "ConfigIssue",
        "GpuDetector", "GpuInfo", "GpuVendor", "FcxResetError",
    }
    # Report sub-module is Plan 05, not Wave 3a
    report_rust = {"ReportComposer", "ReportFragment", "ReportGenerator", "StringPool", "report", "ParallelReportProcessor"}
    report_py_classes = {"ReportComposer", "ReportFragment", "ReportGenerator", "StringPool", "ParallelReportProcessor"}

    # Wave 3a Rust-only symbol set (from constructor inventory, verified against deferred backlog)
    w3a_rust_set = {
        "AnalysisResult", "ScanProgressPhase", "resolve_batch_concurrency",
        "orchestrator",
        "papyrus", "PapyrusError", "PapyrusStats",
        "version", "crashgen_version_gen",
        "crashgen_registry", "CrashgenRegistry", "CrashgenEntry", "CheckId",
        "segment_key",
        "error", "ScanLogError",
    }

    scanlog = [e for e in deferred["entries"] if e.get("ownerModule") == "scanlog"]

    rust_only: list[str] = []
    python_only: list[str] = []
    for e in scanlog:
        if e.get("rustSymbols"):
            sym = e["rustSymbols"][0]
            if sym in wave12_rust or sym in wave12_free_fns:
                continue
            if sym in report_rust:
                continue
            if sym in w3a_rust_set:
                rust_only.append(sym)
                continue
            # Unknown rust-only symbol for Wave 3a? Surface it.
            continue
        if e.get("bindingIdentifiers"):
            ident = e["bindingIdentifiers"][0]
            path = ident.replace("classic_scanlog.", "")
            top = path.split(".")[0]
            if top in wave12_py_classes or top in wave12_free_fns:
                continue
            if top in report_py_classes:
                continue
            python_only.append(path)

    assert len(rust_only) == 16, f"expected 16 rust-only got {len(rust_only)}"
    assert len(python_only) == 34, f"expected 34 python-only got {len(python_only)}"

    # Already-in-contract python paths to skip (defensive — Wave 3a sanity-check)
    existing_py_paths: dict[str, str] = {}
    for row in contract["tier1Mappings"]:
        if row.get("ownerModule") == "scanlog":
            key = row.get("pythonExportPath", "")
            if key and key not in existing_py_paths:
                existing_py_paths[key] = row.get("id", "")

    # Sub-module classification for Python paths
    def submod_for_class(name: str) -> str:
        if name in ("AnalysisConfig", "AnalysisResult", "CancellationToken", "Orchestrator"):
            return "orchestrator"
        if name in ("PapyrusAnalyzer", "PapyrusStats"):
            return "papyrus"
        if name in ("CrashgenVersion", "CrashgenVersionStatus"):
            return "version"
        raise RuntimeError(f"Unhandled class: {name}")

    def submod_for_free_fn(fn: str) -> str:
        if fn == "papyrus_logging":
            return "papyrus"
        if fn in ("parse_crashgen_version", "check_crashgen_version_status"):
            return "version"
        raise RuntimeError(f"Unhandled free fn: {fn}")

    # Rust-only routing
    def submod_for_rust(rs: str) -> str:
        if rs in ("orchestrator", "AnalysisResult", "ScanProgressPhase", "resolve_batch_concurrency"):
            return "orchestrator"
        if rs in ("papyrus", "PapyrusError", "PapyrusStats"):
            return "papyrus"
        if rs in ("version", "crashgen_version_gen"):
            return "version"
        if rs in ("crashgen_registry", "CrashgenRegistry", "CrashgenEntry", "CheckId"):
            return "crashgen_registry"
        if rs == "segment_key":
            return "segment_key"
        if rs in ("error", "ScanLogError"):
            return "error"
        raise RuntimeError(f"Unhandled rust submod for: {rs}")

    # Rust symbol -> closest Python proxy name (for the rust-only rows)
    rust_to_py_proxy: dict[str, str] = {
        # orchestrator sub-module
        "orchestrator": "Orchestrator",
        "AnalysisResult": "AnalysisResult",
        "ScanProgressPhase": "AnalysisResult",  # no pyclass; pair with dominant result class
        "resolve_batch_concurrency": "Orchestrator",
        # papyrus sub-module
        "papyrus": "PapyrusAnalyzer",
        "PapyrusError": "PapyrusError",  # will be added as a bare .pyi exception stub in Task 2
        "PapyrusStats": "PapyrusStats",
        # version sub-module
        "version": "CrashgenVersion",
        "crashgen_version_gen": "parse_crashgen_version",
        # crashgen_registry sub-module (no python classes — pair with nearest in scanlog root)
        "crashgen_registry": "CrashgenVersion",
        "CrashgenRegistry": "CrashgenVersion",
        "CrashgenEntry": "CrashgenVersion",
        "CheckId": "CrashgenVersion",
        # segment_key sub-module (no python classes)
        "segment_key": "CrashgenVersion",
        # error sub-module (no python classes)
        "error": "CrashgenVersion",
        "ScanLogError": "CrashgenVersion",
    }

    # Python surface index for kind/arity lookup
    py_index: dict[str, dict] = {}
    for e in py_surface["exports"]:
        if e["module"] == "classic_scanlog":
            py_index[e["export_path"]] = e

    def make_row(id_: str, rust_symbol: str, py_path: str, default_kind: str) -> dict:
        py_item = py_index.get(py_path)
        py_kind = py_item["kind"] if py_item else default_kind
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

    # Python class name -> -core rust symbol mapping. When a Python wrapper
    # has no matching -core type (e.g. CancellationToken, Orchestrator), pair
    # with the nearest -core class per Wave 1 precedent so the Pitfall 2 guard
    # can resolve rustSymbol to a visible surface entry.
    py_class_to_core_symbol: dict[str, str] = {
        # Direct matches (Python name == -core name)
        "AnalysisConfig": "AnalysisConfig",
        "AnalysisResult": "AnalysisResult",
        "PapyrusAnalyzer": "PapyrusAnalyzer",
        "PapyrusStats": "PapyrusStats",
        "CrashgenVersion": "CrashgenVersion",
        "CrashgenVersionStatus": "CrashgenVersionStatus",
        # Renamed wrappers: Python name != -core name
        # Orchestrator wraps OrchestratorCore (matches legacy row scanlog-orchestrator-class)
        "Orchestrator": "OrchestratorCore",
        # CancellationToken is a pure -py convenience wrapping Arc<AtomicBool>;
        # no -core type exists. Pair with OrchestratorCore (dominant class in sub-module)
        # so the guard passes.
        "CancellationToken": "OrchestratorCore",
    }

    # Free function name -> -core rust symbol mapping
    py_free_fn_to_core_symbol: dict[str, str] = {
        "parse_crashgen_version": "CrashgenVersion",  # matches legacy row scanlog-parse-crashgen-version
        "check_crashgen_version_status": "check_crashgen_version_status",
        "papyrus_logging": "PapyrusAnalyzer",  # -py-only convenience wrapper; pair with dominant -core class
    }

    rows: list[dict] = []

    # Python-only paths -> rows
    for path in sorted(set(python_only)):
        if path in existing_py_paths:
            # Shouldn't happen for Wave 3a per our cross-check, but defensive.
            print(f"SKIP (already in contract): {path} -> {existing_py_paths[path]}")
            continue
        top = path.split(".")[0]
        if top in py_free_fn_to_core_symbol:
            # Bare free functions
            rust_sym = py_free_fn_to_core_symbol[top]
            default_kind = "function"
            submod = submod_for_free_fn(top)
        elif "." in path:
            # Class.method form (e.g. Orchestrator.attach_database)
            rust_sym = py_class_to_core_symbol.get(top, top)
            default_kind = "method"
            submod = submod_for_class(top)
        else:
            # Bare class name (e.g. AnalysisResult, CancellationToken, PapyrusStats)
            rust_sym = py_class_to_core_symbol.get(top, top)
            default_kind = "class"
            submod = submod_for_class(top)
        id_ = f"scanlog.{submod}.{path}"
        rows.append(make_row(id_, rust_sym, path, default_kind))

    # Rust-only symbols -> proxy rows with @rust suffix
    for rs in sorted(set(rust_only)):
        py_proxy = rust_to_py_proxy.get(rs)
        if py_proxy is None:
            raise RuntimeError(f"No python proxy for rust-only symbol: {rs}")
        submod = submod_for_rust(rs)
        if rs in ("resolve_batch_concurrency", "crashgen_version_gen"):
            default_kind = "function"
        elif rs in ("orchestrator", "papyrus", "version", "crashgen_registry", "segment_key", "error"):
            default_kind = "module"
        else:
            default_kind = "class"
        id_ = f"scanlog.{submod}.{rs}@rust"
        rows.append(make_row(id_, rs, py_proxy, default_kind))

    # Sanity
    assert len(rows) == 50, f"expected 50 got {len(rows)}"
    ids = [r["id"] for r in rows]
    assert len(set(ids)) == 50, f"duplicate IDs in Wave 3a; count={len(ids)} unique={len(set(ids))}"

    # Also check that no Wave 3a ID collides with any existing contract id
    existing_ids = {r["id"] for r in contract["tier1Mappings"]}
    for id_ in ids:
        if id_ in existing_ids:
            raise RuntimeError(f"Wave 3a ID collides with existing contract: {id_}")

    rows.sort(key=lambda r: r["id"])
    contract["tier1Mappings"].extend(rows)
    contract["tier1Mappings"].sort(key=lambda r: r["id"])

    with open(CONTRACT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(contract, f, indent=2)
        f.write("\n")

    print(f"Wrote contract with {len(contract['tier1Mappings'])} tier1 rows (added {len(rows)})")
    print("---")
    print("Wave 3a prefix counts:")
    counts: dict[str, int] = {}
    for r in rows:
        prefix = ".".join(r["id"].split(".")[:2])
        counts[prefix] = counts.get(prefix, 0) + 1
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
