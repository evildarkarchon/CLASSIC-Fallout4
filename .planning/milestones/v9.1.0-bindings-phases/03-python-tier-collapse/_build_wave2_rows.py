#!/usr/bin/env python3
"""Build the 57 Wave 2 contract rows for Phase 3 Plan 03 (scratch helper).

Wave 2 covers the scanlog detection and analysis sub-modules:
mod_detector, suspect_scanner, settings_validator, fcx_handler, gpu_detector.

Per R9: GLOBAL_FCX_HANDLER (a LazyLock static) is excluded from
tier1Mappings because LazyLock statics are not first-class Python module
attributes. Result: 58 candidate entries - 1 exclusion = 57 new rows.

Two Wave 2 rows already live in the contract as legacy kebab IDs
(GpuDetector class + GpuDetector.extract_gpu_info), so the python-only
count is 41 (not 43).
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

    # Wave 2 Python-side classes and free functions
    w2_classes_py = {
        "SuspectScanner", "SettingsValidator", "FcxModeHandler", "ConfigIssue",
        "GpuDetector", "GpuInfo", "GpuVendor",
    }
    w2_free_fns = {
        "detect_mods_single", "detect_mods_double",
        "detect_mods_important", "detect_mods_batch",
    }
    # Rust-side class symbols that have Python wrappers
    w2_rust_classes = {
        "SuspectScanner", "SettingsValidator", "FcxModeHandler", "ConfigIssue",
        "GpuDetector", "GpuInfo", "GpuVendor",
    }
    # Extra rust-side symbols: module markers + exception + excluded LazyLock
    w2_extra_rust = {
        "mod_detector", "suspect_scanner", "settings_validator",
        "fcx_handler", "gpu_detector",
        "GLOBAL_FCX_HANDLER",  # R9 EXCLUSION
        "FcxResetError",
    }

    scanlog = [e for e in deferred["entries"] if e.get("ownerModule") == "scanlog"]
    rust_only: list[str] = []
    python_only: list[str] = []
    for e in scanlog:
        if e.get("rustSymbols"):
            sym = e["rustSymbols"][0]
            if sym in w2_rust_classes or sym in w2_extra_rust or sym in w2_free_fns:
                rust_only.append(sym)
                continue
        if e.get("bindingIdentifiers"):
            ident = e["bindingIdentifiers"][0]
            path = ident.replace("classic_scanlog.", "")
            top = path.split(".")[0]
            if top in w2_classes_py or top in w2_free_fns:
                python_only.append(path)

    # R9: exclude GLOBAL_FCX_HANDLER from promotion
    rust_only = [r for r in rust_only if r != "GLOBAL_FCX_HANDLER"]

    assert len(rust_only) == 16, f"expected 16 rust-only (17 - GLOBAL_FCX_HANDLER) got {len(rust_only)}"
    assert len(python_only) == 41, f"expected 41 python-only got {len(python_only)}"

    # Already-in-contract Wave 2 rows to skip (legacy kebab IDs)
    existing_py_paths = set()
    for row in contract["tier1Mappings"]:
        if row.get("ownerModule") == "scanlog":
            existing_py_paths.add(row.get("pythonExportPath", ""))

    # Sub-module classification for Python paths
    def submod_for_class(name: str) -> str:
        if name == "SuspectScanner":
            return "suspect_scanner"
        if name == "SettingsValidator":
            return "settings_validator"
        if name in ("FcxModeHandler", "ConfigIssue"):
            return "fcx_handler"
        if name in ("GpuDetector", "GpuInfo", "GpuVendor"):
            return "gpu_detector"
        raise RuntimeError(f"Unhandled class: {name}")

    def submod_for_free_fn(fn: str) -> str:
        if fn in w2_free_fns:
            return "mod_detector"
        raise RuntimeError(f"Unhandled free fn: {fn}")

    # Rust symbol -> closest Python proxy name (for the rust-only rows)
    rust_to_py_proxy: dict[str, str] = {
        "SuspectScanner": "SuspectScanner",
        "SettingsValidator": "SettingsValidator",
        "FcxModeHandler": "FcxModeHandler",
        "ConfigIssue": "ConfigIssue",
        "GpuDetector": "GpuDetector",
        "GpuInfo": "GpuInfo",
        "GpuVendor": "GpuVendor",
        "FcxResetError": "FcxResetError",  # now a real Python exception class
        "detect_mods_single": "detect_mods_single",
        "detect_mods_double": "detect_mods_double",
        "detect_mods_important": "detect_mods_important",
        "detect_mods_batch": "detect_mods_batch",
        # Module markers pair with the dominant class in that sub-module
        "mod_detector": "detect_mods_single",
        "suspect_scanner": "SuspectScanner",
        "settings_validator": "SettingsValidator",
        "fcx_handler": "FcxModeHandler",
        "gpu_detector": "GpuDetector",
    }

    def submod_for_rust(rs: str) -> str:
        if rs in ("SuspectScanner", "suspect_scanner"):
            return "suspect_scanner"
        if rs in ("SettingsValidator", "settings_validator"):
            return "settings_validator"
        if rs in ("FcxModeHandler", "ConfigIssue", "FcxResetError", "fcx_handler"):
            return "fcx_handler"
        if rs in ("GpuDetector", "GpuInfo", "GpuVendor", "gpu_detector"):
            return "gpu_detector"
        if rs in w2_free_fns or rs == "mod_detector":
            return "mod_detector"
        raise RuntimeError(f"Unhandled rust submod for: {rs}")

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

    # FcxResetError is a module-level exception class (no arity in python_api_surface
    # because the .pyi will declare it without methods)
    rows: list[dict] = []

    # Python-only paths -> rows
    for path in sorted(python_only):
        # Skip ones already in contract (shouldn't happen for wave 2 per our inventory)
        if path in existing_py_paths:
            continue
        top = path.split(".")[0]
        if top in w2_free_fns:
            rust_sym = top
            default_kind = "function"
            submod = submod_for_free_fn(top)
        elif "." in path:
            # e.g. FcxModeHandler.reset_fcx_checks
            rust_sym = top  # same name in rust (or close enough)
            default_kind = "method"
            submod = submod_for_class(top)
        else:
            rust_sym = top
            default_kind = "class"
            submod = submod_for_class(top)
        id_ = f"scanlog.{submod}.{path}"
        rows.append(make_row(id_, rust_sym, path, default_kind))

    # Rust-only symbols -> proxy rows with @rust suffix
    for rs in sorted(rust_only):
        py_proxy = rust_to_py_proxy.get(rs)
        if py_proxy is None:
            raise RuntimeError(f"No python proxy for rust-only symbol: {rs}")
        submod = submod_for_rust(rs)
        if rs in w2_free_fns:
            default_kind = "function"
        elif rs == "FcxResetError":
            default_kind = "class"  # real Python exception class now
        elif rs in ("mod_detector", "suspect_scanner", "settings_validator", "fcx_handler", "gpu_detector"):
            default_kind = "module"
        else:
            default_kind = "class"
        id_ = f"scanlog.{submod}.{rs}@rust"
        rows.append(make_row(id_, rs, py_proxy, default_kind))

    # Sanity
    assert len(rows) == 57, f"expected 57 got {len(rows)}"
    ids = [r["id"] for r in rows]
    assert len(set(ids)) == 57, "duplicate IDs"

    rows.sort(key=lambda r: r["id"])
    contract["tier1Mappings"].extend(rows)
    contract["tier1Mappings"].sort(key=lambda r: r["id"])

    with open(CONTRACT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(contract, f, indent=2)
        f.write("\n")

    print(f"Wrote contract with {len(contract['tier1Mappings'])} tier1 rows (added {len(rows)})")
    print("---")
    print("Wave2 prefix counts:")
    counts: dict[str, int] = {}
    for r in rows:
        prefix = ".".join(r["id"].split(".")[:2])
        counts[prefix] = counts.get(prefix, 0) + 1
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
