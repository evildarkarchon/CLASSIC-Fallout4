#!/usr/bin/env python3
"""Build Plan 08 classic_shared + classic_file_io promotion contract rows (scratch helper).

Plan 08 enrolls TWO new owner modules as tier1-gated:

  1. classic_shared (HARM-03 + HARM-04)
     - 42 python_unmapped gaps (PathHandler/StringProcessor/RustPerformanceMonitor/
       RuntimeStats classes + methods + 2 free functions)
     - 23 rust_unmapped gaps (classic-shared-py re-exports, modules, helpers)

  2. classic_file_io (R3 — all file_io gaps, not the scaffold's 5)
     - 70 python_unmapped gaps (DDSHeader/EncodingDetector/FileGenerator/
       FileGeneratorConfig/FileHasher/FileHasherCacheStats/FileIOCore/PyLineStreamer/
       PyLogCollector/PySyncLineStreamer/RustFileIO*Error + methods + 2 module fns)
     - 35 rust_unmapped gaps (classic-file-io-core re-exports and modules)

R3: Plan 08 owns ALL file_io rows surfaced by the parser (105 total). Plan 09a
explicitly excludes file_io residuals.

Expected final tier1Mappings length: 349 (pre-plan) + 65 + 105 = 519

The row-authoring rules match Wave 1 / Plan 06 / Plan 07 precedent:
- Python-only rows: id = "<owner>.<submodule>.<ExportPath>"
- Rust-only rows: id = "<owner>.<submodule>.<rust_symbol>@rust"  paired with nearest Python class
- Class rows for Python classes already in the surface reuse the class as its own anchor
- pythonExportPath matches python_api_surface export_path (class-prefixed for methods)
- rustSymbol matches rust_api_surface symbol or the PyO3 source type name (PyPathHandler etc.)
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path.cwd()
CONTRACT = REPO_ROOT / "docs/implementation/python_api_parity/baseline/parity_contract.json"
PY_SURFACE = REPO_ROOT / "docs/implementation/python_api_parity/baseline/python_api_surface.json"
RUST_SURFACE = REPO_ROOT / "docs/implementation/python_api_parity/baseline/rust_api_surface.json"
DIFF_REPORT = REPO_ROOT / "docs/implementation/python_api_parity/baseline/parity_diff_report.json"


# ----------------------------------------------------------------------
# classic_shared routing
# ----------------------------------------------------------------------

# Map each Python class to (sub_module, rust_symbol for class row, rust_symbol for methods)
SHARED_CLASS_ROUTING: dict[str, tuple[str, str]] = {
    "PathHandler":             ("path",        "PyPathHandler"),
    "StringProcessor":         ("strings",     "PyStringProcessor"),
    "RustPerformanceMonitor":  ("performance", "PyRustPerformanceMonitor"),
    "RuntimeStats":            ("runtime",     "RuntimeStats"),
}

# Rust-only shared symbols: rust_symbol -> (sub_module, python_anchor_class)
SHARED_RUST_ONLY: dict[str, tuple[str, str]] = {
    "ClassicError":                     ("runtime",     "RuntimeStats"),
    "ClassicResult":                    ("runtime",     "RuntimeStats"),
    "PathLike":                         ("path",        "PathHandler"),
    "PyPathHandler":                    ("path",        "PathHandler"),
    "PyRustPerformanceMonitor":         ("performance", "RustPerformanceMonitor"),
    "PyStringProcessor":                ("strings",     "StringProcessor"),
    "ResultExt":                        ("runtime",     "RuntimeStats"),
    "ToPyErr":                          ("runtime",     "RuntimeStats"),
    "error_convert":                    ("runtime",     "RuntimeStats"),
    "exceptions":                       ("runtime",     "RuntimeStats"),
    "get_runtime":                      ("runtime",     "RuntimeStats"),
    "indexmap_utils":                   ("runtime",     "RuntimeStats"),
    "path":                             ("path",        "PathHandler"),
    "path_py":                          ("path",        "PathHandler"),
    "performance_py":                   ("performance", "RustPerformanceMonitor"),
    "pyany_to_indexmap_str":            ("runtime",     "RuntimeStats"),
    "pyany_to_indexmap_vecstr":         ("runtime",     "RuntimeStats"),
    "pydict_to_indexmap_str":           ("runtime",     "RuntimeStats"),
    "pydict_to_indexmap_str_optional":  ("runtime",     "RuntimeStats"),
    "pydict_to_indexmap_vecstr":        ("runtime",     "RuntimeStats"),
    "resolve_python_entry_dir":         ("runtime",     "RuntimeStats"),
    "strings_py":                       ("strings",     "StringProcessor"),
    "to_py_err":                        ("runtime",     "RuntimeStats"),
}

# Module-level functions that are not members of any class
SHARED_MODULE_FUNCTIONS: dict[str, tuple[str, str]] = {
    # export_path -> (sub_module, rust_symbol)
    "get_runtime_stats":  ("runtime", "get_runtime_stats"),
    "is_runtime_healthy": ("runtime", "is_runtime_healthy"),
}


# ----------------------------------------------------------------------
# classic_file_io routing
# ----------------------------------------------------------------------

# Python class -> (sub_module, rust_symbol_for_class_row)
FILE_IO_CLASS_ROUTING: dict[str, tuple[str, str]] = {
    "FileIOCore":            ("core",           "FileIOCore"),
    "FileHasher":            ("hash",           "FileHasher"),
    "DDSHeader":             ("dds",            "DDSHeader"),
    "EncodingDetector":      ("encoding",       "EncodingDetector"),
    "FileGenerator":         ("generation",     "FileGenerator"),
    "FileGeneratorConfig":   ("generation",     "FileGeneratorConfig"),
    "PyLogCollector":        ("log_collection", "LogCollector"),
    "PyLineStreamer":        ("log_collection", "LogCollector"),
    "PySyncLineStreamer":    ("log_collection", "LogCollector"),
    "FileHasherCacheStats":  ("hash",           "FileHasher"),
    "RustFileIOError":       ("error",          "FileIOError"),
    "RustFileIOIOError":     ("error",          "FileIOError"),
    "RustFileIOParseError":  ("error",          "FileIOError"),
}

# Rust-only classic-file-io-core symbols
FILE_IO_RUST_ONLY: dict[str, tuple[str, str]] = {
    "BackupInfo":              ("core",           "FileIOCore"),
    "BackupManager":           ("core",           "FileIOCore"),
    "BackupType":              ("core",           "FileIOCore"),
    "CRASH_AUTOSCAN_PATTERN":  ("log_collection", "PyLogCollector"),
    "CRASH_LOG_PATTERN":       ("log_collection", "PyLogCollector"),
    "DDSAnalyzer":             ("dds",            "DDSHeader"),
    "DDSHeader":               ("dds",            "DDSHeader"),
    "DDSIssue":                ("dds",            "DDSHeader"),
    "EncodingDetector":        ("encoding",       "EncodingDetector"),
    "FileGenerator":           ("generation",     "FileGenerator"),
    "FileGeneratorConfig":     ("generation",     "FileGeneratorConfig"),
    "FileHasher":              ("hash",           "FileHasher"),
    "FileIOCore":              ("core",           "FileIOCore"),
    "FileIOError":             ("error",          "RustFileIOError"),
    "FileOperation":           ("core",           "FileIOCore"),
    "FileOperationResult":     ("core",           "FileIOCore"),
    "GameFilesManager":        ("core",           "FileIOCore"),
    "GameTarget":              ("core",           "FileIOCore"),
    "LogCollector":            ("log_collection", "PyLogCollector"),
    "RejectedInput":           ("core",           "FileIOCore"),
    "TargetedResolution":      ("core",           "FileIOCore"),
    "backup":                  ("core",           "FileIOCore"),
    "calculate_similarity":    ("core",           "FileIOCore"),
    "core":                    ("core",           "FileIOCore"),
    "dds":                     ("dds",            "DDSHeader"),
    "encoding":                ("encoding",       "EncodingDetector"),
    "game_files":              ("core",           "FileIOCore"),
    "generate_ignore_file":    ("generation",     "FileGenerator"),
    "generate_local_yaml":     ("generation",     "FileGenerator"),
    "generation":              ("generation",     "FileGenerator"),
    "hash":                    ("hash",           "FileHasher"),
    "log_collection":          ("log_collection", "PyLogCollector"),
    "resolve_targeted_inputs": ("core",           "FileIOCore"),
    "similarity":              ("core",           "FileIOCore"),
    "similarity_ratio":        ("core",           "FileIOCore"),
}

# Module-level file_io functions
FILE_IO_MODULE_FUNCTIONS: dict[str, tuple[str, str]] = {
    "generate_ignore_file_async": ("generation", "generate_ignore_file"),
    "generate_local_yaml_async":  ("generation", "generate_local_yaml"),
}


def main() -> None:
    with open(CONTRACT, encoding="utf-8") as f:
        contract = json.load(f)
    with open(PY_SURFACE, encoding="utf-8") as f:
        py_surface = json.load(f)
    with open(RUST_SURFACE, encoding="utf-8") as f:
        rust_surface = json.load(f)
    with open(DIFF_REPORT, encoding="utf-8") as f:
        diff_report = json.load(f)

    # ------------------------------------------------------------------
    # Index surfaces
    # ------------------------------------------------------------------

    shared_py_index: dict[str, dict] = {}
    file_io_py_index: dict[str, dict] = {}
    for e in py_surface["exports"]:
        if e["module"] == "classic_shared":
            shared_py_index[e["export_path"]] = e
        elif e["module"] == "classic_file_io":
            file_io_py_index[e["export_path"]] = e

    shared_rust_set: set[str] = {
        s["symbol"] for s in rust_surface["symbols"] if s.get("crate") == "classic-shared-py"
    }
    file_io_rust_set: set[str] = {
        s["symbol"] for s in rust_surface["symbols"] if s.get("crate") == "classic-file-io-core"
    }

    shared_gaps = [
        g for g in diff_report["gaps"] if g.get("owner_module") == "shared"
    ]
    file_io_gaps = [
        g for g in diff_report["gaps"] if g.get("owner_module") == "file_io"
    ]

    rows: list[dict] = []

    # ------------------------------------------------------------------
    # classic_shared rows
    # ------------------------------------------------------------------

    def shared_make_row(id_: str, rust_symbol: str, py_path: str | None,
                        rust_crate: str, python_kind: str) -> dict:
        row = {
            "id": id_,
            "tier": "tier1",
            "ownerModule": "shared",
            "rustCrate": rust_crate,
            "rustSymbol": rust_symbol,
            "pythonModule": "classic_shared",
            "pythonExportPath": py_path,
            "pythonKind": python_kind,
        }
        if py_path is not None:
            info = shared_py_index.get(py_path)
            if info and info.get("arity") is not None:
                row["pythonArity"] = info["arity"]
        return row

    # Python-unmapped shared gaps -> contract rows
    shared_py_gap_paths = [
        g["python_export_path"] for g in shared_gaps
        if g["gap_type"] == "python_unmapped"
    ]
    for gap_path in shared_py_gap_paths:
        py_info = shared_py_index.get(gap_path)
        if py_info is None:
            raise RuntimeError(
                f"Shared python gap '{gap_path}' not in python_api_surface"
            )

        if "." in gap_path:
            class_name, method = gap_path.split(".", 1)
            route = SHARED_CLASS_ROUTING.get(class_name)
            if route is None:
                raise RuntimeError(f"Unhandled shared class: {class_name}")
            sub_module, rust_symbol = route
            id_ = f"shared.{sub_module}.{gap_path}"
            rows.append(shared_make_row(
                id_, rust_symbol, gap_path,
                "classic-shared-py", py_info["kind"],
            ))
        else:
            # Top-level export — class or free function
            if gap_path in SHARED_CLASS_ROUTING:
                sub_module, rust_symbol = SHARED_CLASS_ROUTING[gap_path]
                id_ = f"shared.{sub_module}.{gap_path}"
                rows.append(shared_make_row(
                    id_, rust_symbol, gap_path,
                    "classic-shared-py", py_info["kind"],
                ))
            elif gap_path in SHARED_MODULE_FUNCTIONS:
                sub_module, rust_symbol = SHARED_MODULE_FUNCTIONS[gap_path]
                id_ = f"shared.{sub_module}.{gap_path}"
                rows.append(shared_make_row(
                    id_, rust_symbol, gap_path,
                    "classic-shared-py", py_info["kind"],
                ))
            else:
                raise RuntimeError(f"Unhandled shared top-level export: {gap_path}")

    # Rust-unmapped shared gaps -> @rust proxy rows
    # Skip symbols that are already covered by a Python class row whose
    # rustSymbol matches the gap symbol (e.g. RuntimeStats is a Python class
    # AND a Rust struct — one contract row satisfies both gap types).
    already_covered_rust_symbols: set[str] = {r["rustSymbol"] for r in rows}
    for g in shared_gaps:
        if g["gap_type"] != "rust_unmapped":
            continue
        rs = g["rust_symbol"]
        if rs in already_covered_rust_symbols:
            # Covered by the Python class row already added (e.g. RuntimeStats
            # is both a #[pyclass] and a Rust struct). The class row's
            # rustSymbol satisfies the rust_unmapped gap directly — no
            # @rust proxy row needed.
            continue
        if rs not in shared_rust_set:
            raise RuntimeError(
                f"Shared rust gap '{rs}' not in rust_api_surface (Pitfall 2)"
            )
        route = SHARED_RUST_ONLY.get(rs)
        if route is None:
            raise RuntimeError(f"Unhandled shared rust-only symbol: {rs}")
        sub_module, anchor = route
        id_ = f"shared.{sub_module}.{rs}@rust"
        rows.append(shared_make_row(
            id_, rs, anchor, "classic-shared-py", "class",
        ))

    shared_count = len(rows)
    print(f"classic_shared rows: {shared_count}")

    # ------------------------------------------------------------------
    # classic_file_io rows
    # ------------------------------------------------------------------

    def file_io_make_row(id_: str, rust_symbol: str, py_path: str | None,
                         rust_crate: str, python_kind: str) -> dict:
        row = {
            "id": id_,
            "tier": "tier1",
            "ownerModule": "file_io",
            "rustCrate": rust_crate,
            "rustSymbol": rust_symbol,
            "pythonModule": "classic_file_io",
            "pythonExportPath": py_path,
            "pythonKind": python_kind,
        }
        if py_path is not None:
            info = file_io_py_index.get(py_path)
            if info and info.get("arity") is not None:
                row["pythonArity"] = info["arity"]
        return row

    file_io_py_gap_paths = [
        g["python_export_path"] for g in file_io_gaps
        if g["gap_type"] == "python_unmapped"
    ]
    for gap_path in file_io_py_gap_paths:
        py_info = file_io_py_index.get(gap_path)
        if py_info is None:
            raise RuntimeError(
                f"file_io python gap '{gap_path}' not in python_api_surface"
            )

        if "." in gap_path:
            class_name, method = gap_path.split(".", 1)
            route = FILE_IO_CLASS_ROUTING.get(class_name)
            if route is None:
                raise RuntimeError(f"Unhandled file_io class: {class_name}")
            sub_module, rust_symbol = route
            id_ = f"file_io.{sub_module}.{gap_path}"
            rows.append(file_io_make_row(
                id_, rust_symbol, gap_path,
                "classic-file-io-core", py_info["kind"],
            ))
        else:
            if gap_path in FILE_IO_CLASS_ROUTING:
                sub_module, rust_symbol = FILE_IO_CLASS_ROUTING[gap_path]
                id_ = f"file_io.{sub_module}.{gap_path}"
                rows.append(file_io_make_row(
                    id_, rust_symbol, gap_path,
                    "classic-file-io-core", py_info["kind"],
                ))
            elif gap_path in FILE_IO_MODULE_FUNCTIONS:
                sub_module, rust_symbol = FILE_IO_MODULE_FUNCTIONS[gap_path]
                id_ = f"file_io.{sub_module}.{gap_path}"
                rows.append(file_io_make_row(
                    id_, rust_symbol, gap_path,
                    "classic-file-io-core", py_info["kind"],
                ))
            else:
                raise RuntimeError(
                    f"Unhandled file_io top-level export: {gap_path}"
                )

    # Rust-only file_io gaps -> @rust proxy rows
    # Skip symbols already covered by a Python class row with matching rustSymbol
    # (e.g. FileIOCore, FileHasher, DDSHeader, EncodingDetector, FileGenerator,
    #  FileGeneratorConfig are both Rust reexports and Python classes — one contract row each).
    file_io_covered_rust_symbols: set[str] = {
        r["rustSymbol"] for r in rows if r["ownerModule"] == "file_io"
    }
    for g in file_io_gaps:
        if g["gap_type"] != "rust_unmapped":
            continue
        rs = g["rust_symbol"]
        if rs in file_io_covered_rust_symbols:
            continue
        if rs not in file_io_rust_set:
            raise RuntimeError(
                f"file_io rust gap '{rs}' not in rust_api_surface (Pitfall 2)"
            )
        route = FILE_IO_RUST_ONLY.get(rs)
        if route is None:
            raise RuntimeError(f"Unhandled file_io rust-only symbol: {rs}")
        sub_module, anchor = route
        id_ = f"file_io.{sub_module}.{rs}@rust"
        rows.append(file_io_make_row(
            id_, rs, anchor, "classic-file-io-core", "class",
        ))

    file_io_count = len(rows) - shared_count
    print(f"classic_file_io rows: {file_io_count}")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    total = len(rows)
    ids = [r["id"] for r in rows]
    if len(set(ids)) != total:
        dupes = [i for i in ids if ids.count(i) > 1]
        raise RuntimeError(f"Duplicate ids: {set(dupes)}")

    # Collisions with existing rows
    existing_ids = {r["id"] for r in contract["tier1Mappings"]}
    collisions = [r["id"] for r in rows if r["id"] in existing_ids]
    if collisions:
        raise RuntimeError(f"ID collisions with existing contract: {collisions[:10]}")

    # Verify pythonExportPath exists in surface where non-null
    missing_py: list[str] = []
    for r in rows:
        ep = r["pythonExportPath"]
        if ep is None:
            continue
        module = r["pythonModule"]
        if module == "classic_shared" and ep not in shared_py_index:
            missing_py.append(f"{r['id']} -> classic_shared.{ep}")
        elif module == "classic_file_io" and ep not in file_io_py_index:
            missing_py.append(f"{r['id']} -> classic_file_io.{ep}")
    if missing_py:
        print("ERROR: missing from python_api_surface:")
        for m in missing_py:
            print(f"  {m}")
        raise SystemExit(1)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    rows.sort(key=lambda r: r["id"])
    contract["tier1Mappings"].extend(rows)
    contract["tier1Mappings"].sort(key=lambda r: r["id"])

    with open(CONTRACT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(contract, f, indent=2)
        f.write("\n")

    print(f"Wrote contract with {len(contract['tier1Mappings'])} tier1 rows (added {total})")
    print("--- Row breakdown ---")
    shared_rust = sum(1 for r in rows if r["id"].startswith("shared.") and r["id"].endswith("@rust"))
    shared_py = sum(1 for r in rows if r["id"].startswith("shared.") and not r["id"].endswith("@rust"))
    file_io_rust = sum(1 for r in rows if r["id"].startswith("file_io.") and r["id"].endswith("@rust"))
    file_io_py = sum(1 for r in rows if r["id"].startswith("file_io.") and not r["id"].endswith("@rust"))
    print(f"  classic_shared python-only: {shared_py}")
    print(f"  classic_shared rust-only (@rust): {shared_rust}")
    print(f"  classic_file_io python-only: {file_io_py}")
    print(f"  classic_file_io rust-only (@rust): {file_io_rust}")


if __name__ == "__main__":
    main()
