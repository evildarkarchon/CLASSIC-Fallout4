#!/usr/bin/env python3
"""Build Plan 07 version_registry promotion contract rows (scratch helper).

Plan 07 promotes:
  - 34 deferred backlog entries (ownerModule=version_registry)
      * 10 rust-only @rust-suffixed proxy rows
      * 24 python-only rows (dunder + method + class entries)
  - 1 Tier-2 runtime-verified migration (GameVersion.semantic_distance)
Total: 35 new tier1Mappings rows.

The python-tier2-version-registry-runtime registry entry has only 1 binding
(GameVersion.semantic_distance) which is promoted here — the entry can be
DELETED outright in Task 4.

Expected final tier1Mappings length: 314 + 35 = 349
(NOT 347 as the plan scaffold says — Plan 06 landed at 314 not 312.)
"""
from __future__ import annotations
import json
from pathlib import Path

REPO_ROOT = Path.cwd()
CONTRACT = REPO_ROOT / "docs/implementation/python_api_parity/baseline/parity_contract.json"
DEFERRED = REPO_ROOT / "docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json"
PY_SURFACE = REPO_ROOT / "docs/implementation/python_api_parity/baseline/python_api_surface.json"
RUST_SURFACE = REPO_ROOT / "docs/implementation/python_api_parity/baseline/rust_api_surface.json"


def main() -> None:
    with open(DEFERRED, encoding="utf-8") as f:
        deferred = json.load(f)
    with open(CONTRACT, encoding="utf-8") as f:
        contract = json.load(f)
    with open(PY_SURFACE, encoding="utf-8") as f:
        py_surface = json.load(f)
    with open(RUST_SURFACE, encoding="utf-8") as f:
        rust_surface = json.load(f)

    vr_deferred = [e for e in deferred["entries"] if e["ownerModule"] == "version_registry"]
    assert len(vr_deferred) == 34, f"expected 34 deferred version_registry, got {len(vr_deferred)}"

    # Index Python surface for classic_version_registry
    py_index: dict[str, dict] = {}
    for e in py_surface["exports"]:
        if e["module"] == "classic_version_registry":
            py_index[e["export_path"]] = e

    # Index Rust surface for classic-version-registry-core
    rust_index: set[str] = set()
    for s in rust_surface["symbols"]:
        if s.get("crate") == "classic-version-registry-core":
            rust_index.add(s["symbol"])

    # Rust-only symbol -> (sub_module, python_proxy, kind)
    # sub_module reflects source file inside classic-version-registry-core:
    #   version.rs    -> "version"
    #   models.rs     -> "models"
    #   matching.rs   -> "matching"
    #   registry.rs   -> "registry"
    #   error.rs      -> "error"
    #   lib.rs        -> "lib"  (for Result<T> type alias)
    rust_only_map: dict[str, tuple[str, str, str]] = {
        # models.rs types without PyO3 wrappers (AddressLibFormat, LogLevel, UnknownVersionStrategy)
        "AddressLibFormat": ("models", "AddressLibraryConfig", "class"),
        "LogLevel": ("models", "UnknownVersionHandling", "class"),
        "UnknownVersionStrategy": ("models", "UnknownVersionHandling", "class"),
        # models.rs types WITH PyO3 wrappers — redundant deferred rust entries; pair with their own class
        "AddressLibraryConfig": ("models", "AddressLibraryConfig", "class"),
        "CompatibleRange": ("models", "CompatibleRange", "class"),
        "CrashgenConfig": ("models", "CrashgenConfig", "class"),
        "XseConfig": ("models", "XseConfig", "class"),
        # matching.rs: VersionMatcher has no PyO3 wrapper
        "VersionMatcher": ("matching", "MatchResult", "class"),
        # error.rs: VersionRegistryError has no Python exception class
        "VersionRegistryError": ("error", "VersionRegistry", "class"),
        # lib.rs: Result<T> type alias
        "Result": ("lib", "VersionRegistry", "class"),
    }

    # Python-only binding identifier (dot path after stripping module) -> (rust_symbol, kind, sub_module)
    python_only_map: dict[str, tuple[str, str, str]] = {
        "AddressLibraryConfig": ("AddressLibraryConfig", "class", "models"),
        "CompatibleRange": ("CompatibleRange", "class", "models"),
        "CompatibleRange.contains": ("CompatibleRange", "method", "models"),
        "CrashgenConfig": ("CrashgenConfig", "class", "models"),
        "CrashgenConfig.is_compatible_with": ("CrashgenConfig", "method", "models"),
        "GameVersion.__eq__": ("GameVersion", "method", "version"),
        "GameVersion.__ge__": ("GameVersion", "method", "version"),
        "GameVersion.__gt__": ("GameVersion", "method", "version"),
        "GameVersion.__hash__": ("GameVersion", "method", "version"),
        "GameVersion.__init__": ("GameVersion", "method", "version"),
        "GameVersion.__le__": ("GameVersion", "method", "version"),
        "GameVersion.__lt__": ("GameVersion", "method", "version"),
        "GameVersion.same_major": ("GameVersion", "method", "version"),
        "MatchConfidence.__eq__": ("MatchConfidence", "method", "matching"),
        "MatchConfidence.__hash__": ("MatchConfidence", "method", "matching"),
        "MatchConfidence.is_high_confidence": ("MatchConfidence", "method", "matching"),
        "VersionInfo.__eq__": ("VersionInfo", "method", "models"),
        "VersionInfo.__hash__": ("VersionInfo", "method", "models"),
        "VersionInfo.get_compatible_crashgens": ("VersionInfo", "method", "models"),
        "VersionInfo.get_crashgen_for_version": ("VersionInfo", "method", "models"),
        "VersionInfo.get_crashgen_version_strings": ("VersionInfo", "method", "models"),
        "VersionInfo.is_compatible_with": ("VersionInfo", "method", "models"),
        "VersionRegistry.__init__": ("VersionRegistry", "method", "registry"),
        "XseConfig": ("XseConfig", "class", "models"),
    }

    def make_row(id_: str, rust_symbol: str, py_path: str, kind: str) -> dict:
        py_item = py_index.get(py_path)
        py_kind = py_item["kind"] if py_item else kind
        row = {
            "id": id_,
            "tier": "tier1",
            "ownerModule": "version_registry",
            "rustCrate": "classic-version-registry-core",
            "rustSymbol": rust_symbol,
            "pythonModule": "classic_version_registry",
            "pythonExportPath": py_path,
            "pythonKind": py_kind,
        }
        if py_item and py_item.get("arity") is not None:
            row["pythonArity"] = py_item["arity"]
        return row

    rows: list[dict] = []

    # --- 10 rust-only @rust-suffixed rows ---
    rust_only_entries = [e for e in vr_deferred if e.get("rustSymbols")]
    assert len(rust_only_entries) == 10, f"expected 10 rust-only, got {len(rust_only_entries)}"

    for e in sorted(rust_only_entries, key=lambda x: x["coverageId"]):
        rs = e["rustSymbols"][0]
        if rs not in rust_only_map:
            raise RuntimeError(f"Unhandled rust-only version_registry symbol: {rs}")
        if rs not in rust_index:
            raise RuntimeError(f"Rust symbol {rs} not in parsed rust_api_surface (Pitfall 2)")
        submod, py_proxy, kind = rust_only_map[rs]
        id_ = f"version_registry.{submod}.{rs}@rust"
        rows.append(make_row(id_, rs, py_proxy, kind))

    # --- 24 python-only rows ---
    python_only_entries = [e for e in vr_deferred if e.get("bindingIdentifiers")]
    assert len(python_only_entries) == 24, f"expected 24 python-only, got {len(python_only_entries)}"

    for e in sorted(python_only_entries, key=lambda x: x["coverageId"]):
        ident = e["bindingIdentifiers"][0]
        path = ident.replace("classic_version_registry.", "")
        if path not in python_only_map:
            raise RuntimeError(f"Unhandled python-only version_registry identifier: {path}")
        rust_sym, kind, submod = python_only_map[path]
        id_ = f"version_registry.{submod}.{path}"
        rows.append(make_row(id_, rust_sym, path, kind))

    # --- 1 Tier-2 runtime-verified migration ---
    # GameVersion.semantic_distance is the ONLY binding in python-tier2-version-registry-runtime;
    # the registry entry can be safely deleted in Task 4.
    tier2_migrations = [
        (
            "version_registry.version.GameVersion.semantic_distance",
            "GameVersion",
            "GameVersion.semantic_distance",
            "method",
        ),
    ]
    for id_, rust_sym, py_path, kind in tier2_migrations:
        rows.append(make_row(id_, rust_sym, py_path, kind))

    assert len(rows) == 35, f"expected 35 total rows, got {len(rows)}"
    ids = [r["id"] for r in rows]
    assert len(set(ids)) == 35, "duplicate IDs"

    # Verify every pythonExportPath exists in the Python surface
    missing_py: list[str] = []
    for r in rows:
        if r["pythonExportPath"] not in py_index:
            missing_py.append(f"{r['id']} -> {r['pythonExportPath']}")
    if missing_py:
        print("ERROR: missing from python_api_surface:")
        for m in missing_py:
            print(f"  {m}")
        raise SystemExit(1)

    # Detect collisions with existing rows
    existing_ids = {r["id"] for r in contract["tier1Mappings"]}
    collisions = [r["id"] for r in rows if r["id"] in existing_ids]
    if collisions:
        print(f"ERROR: {len(collisions)} ID collisions with existing contract rows:")
        for c in collisions:
            print(f"  {c}")
        raise SystemExit(1)

    rows.sort(key=lambda r: r["id"])
    contract["tier1Mappings"].extend(rows)
    contract["tier1Mappings"].sort(key=lambda r: r["id"])

    with open(CONTRACT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(contract, f, indent=2)
        f.write("\n")

    print(f"Wrote contract with {len(contract['tier1Mappings'])} tier1 rows (added {len(rows)})")
    print("--- Row breakdown ---")
    rust_count = sum(1 for r in rows if r["id"].endswith("@rust"))
    tier2_count = sum(
        1 for r in rows if r["id"] == "version_registry.version.GameVersion.semantic_distance"
    )
    python_count = len(rows) - rust_count - tier2_count
    print(f"  rust-only (@rust): {rust_count}")
    print(f"  python-only: {python_count}")
    print(f"  tier2 migrations: {tier2_count}")


if __name__ == "__main__":
    main()
