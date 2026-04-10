#!/usr/bin/env python3
"""Build the 46 Wave 3b contract rows for Phase 3 Plan 05 (scratch helper).

Wave 3b covers the scanlog ``report`` sub-module only (5 PyO3 wrapper classes
+ 1 module marker). Per ``03-05-CONSTRUCTOR-INVENTORY.md``:

- 41 Python rows from deferred bindingIdentifiers
- 4 rust-only class markers (StringPool, ReportFragment, ReportComposer, ReportGenerator)
- 1 bare module marker (``report`` rust-only, paired with ReportComposer proxy)

Total: 46 new rows. Final tier1Mappings: 240 -> 286.

Pairs ``ParallelReportProcessor`` with ``ReportComposer`` as its ``-core`` proxy
(per Wave 3a precedent for pure ``-py`` convenience classes like
``CancellationToken``).
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path.cwd()
CONTRACT = REPO_ROOT / "docs/implementation/python_api_parity/baseline/parity_contract.json"
DEFERRED = REPO_ROOT / "docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json"
PY_SURFACE = REPO_ROOT / "docs/implementation/python_api_parity/baseline/python_api_surface.json"

# Report sub-module classes (Python-facing names)
REPORT_PY_CLASSES = {
    "StringPool",
    "ReportFragment",
    "ReportComposer",
    "ReportGenerator",
    "ParallelReportProcessor",
}

# Report rust-only class markers (-core symbols, excluding the pure -py
# ParallelReportProcessor which has no -core counterpart)
REPORT_RUST_CLASSES = {
    "StringPool",
    "ReportFragment",
    "ReportComposer",
    "ReportGenerator",
}


def main() -> None:
    with open(DEFERRED, encoding="utf-8") as f:
        deferred = json.load(f)
    with open(CONTRACT, encoding="utf-8") as f:
        contract = json.load(f)
    with open(PY_SURFACE, encoding="utf-8") as f:
        py_surface = json.load(f)

    scanlog = [e for e in deferred["entries"] if e.get("ownerModule") == "scanlog"]

    python_only: list[str] = []
    rust_only_classes: list[str] = []
    has_module_marker = False

    for e in scanlog:
        rs_list = e.get("rustSymbols") or ([e.get("rustSymbol")] if e.get("rustSymbol") else [])
        bids = e.get("bindingIdentifiers") or []

        # Rust-only rows
        if rs_list and not bids:
            sym = rs_list[0]
            if sym in REPORT_RUST_CLASSES:
                rust_only_classes.append(sym)
                continue
            if sym == "report":
                # Bare module marker
                has_module_marker = True
                continue
            # Skip rust-only symbols outside the report scope
            continue

        # Python rows
        if bids:
            ident = bids[0]
            path = ident.replace("classic_scanlog.", "")
            top = path.split(".")[0]
            if top in REPORT_PY_CLASSES:
                python_only.append(path)
            continue

    assert len(rust_only_classes) == 4, f"expected 4 rust-only class markers, got {len(rust_only_classes)}: {rust_only_classes}"
    assert has_module_marker, "expected bare 'report' module marker in deferred backlog"
    assert len(python_only) == 41, f"expected 41 python-only rows, got {len(python_only)}"

    # Already-in-contract python paths (defensive cross-check)
    existing_py_paths: dict[str, str] = {}
    for row in contract["tier1Mappings"]:
        if row.get("ownerModule") == "scanlog":
            key = row.get("pythonExportPath", "")
            if key:
                existing_py_paths.setdefault(key, row.get("id", ""))

    # Python class -> -core rust symbol mapping.
    # ParallelReportProcessor is a pure -py convenience class (no -core type);
    # pair with ReportComposer (dominant -core class in report sub-module).
    py_class_to_core_symbol: dict[str, str] = {
        "StringPool": "StringPool",
        "ReportFragment": "ReportFragment",
        "ReportComposer": "ReportComposer",
        "ReportGenerator": "ReportGenerator",
        "ParallelReportProcessor": "ReportComposer",
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

    rows: list[dict] = []

    # Python rows
    for path in sorted(set(python_only)):
        if path in existing_py_paths:
            print(f"SKIP (already in contract): {path} -> {existing_py_paths[path]}")
            continue
        top = path.split(".")[0]
        rust_sym = py_class_to_core_symbol.get(top, top)
        if "." in path:
            default_kind = "method"
        else:
            default_kind = "class"
        id_ = f"scanlog.report.{path}"
        rows.append(make_row(id_, rust_sym, path, default_kind))

    # Rust-only class markers
    for rs in sorted(set(rust_only_classes)):
        # Pair with the same-named Python class
        id_ = f"scanlog.report.{rs}@rust"
        rows.append(make_row(id_, rs, rs, "class"))

    # Bare module marker
    if has_module_marker:
        id_ = "scanlog.report.report@rust"
        rows.append(make_row(id_, "report", "ReportComposer", "module"))

    # Sanity
    assert len(rows) == 46, f"expected 46 rows, got {len(rows)}"
    ids = [r["id"] for r in rows]
    assert len(set(ids)) == 46, f"duplicate IDs in Wave 3b; count={len(ids)} unique={len(set(ids))}"

    existing_ids = {r["id"] for r in contract["tier1Mappings"]}
    for id_ in ids:
        if id_ in existing_ids:
            raise RuntimeError(f"Wave 3b ID collides with existing contract: {id_}")

    rows.sort(key=lambda r: r["id"])
    contract["tier1Mappings"].extend(rows)
    contract["tier1Mappings"].sort(key=lambda r: r["id"])

    with open(CONTRACT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(contract, f, indent=2)
        f.write("\n")

    print(f"Wrote contract with {len(contract['tier1Mappings'])} tier1 rows (added {len(rows)})")
    print("---")
    print("Wave 3b prefix counts:")
    counts: dict[str, int] = {}
    for r in rows:
        # Strip trailing @rust to group class-oriented rows together
        key = r["id"].replace("@rust", "")
        prefix = ".".join(key.split(".")[:3])
        counts[prefix] = counts.get(prefix, 0) + 1
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
