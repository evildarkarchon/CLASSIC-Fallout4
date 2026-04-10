#!/usr/bin/env python3
"""Build Plan 06 config promotion contract rows (scratch helper).

Plan 06 promotes:
  - 26 deferred backlog entries (ownerModule=config)
  - 2 Tier-2 runtime-verified migrations (get_application_dir, set_application_dir)
Total: 28 new tier1Mappings rows.

The other 2 Tier-2 bindings (classic_config.YamlData.classic_version /
warn_outdated) are property-based and cannot be promoted — the Python
surface parser skips @property decorators (see generate_baseline.py:378).
Wave 3a precedent: preserve python-tier2-config-runtime.
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

    config_deferred = [e for e in deferred["entries"] if e["ownerModule"] == "config"]
    assert len(config_deferred) == 26, f"expected 26 deferred config entries, got {len(config_deferred)}"

    # Index python surface for classic_config
    py_index: dict[str, dict] = {}
    for e in py_surface["exports"]:
        if e["module"] == "classic_config":
            py_index[e["export_path"]] = e

    # Map rust-only symbols to their (submod, python_proxy, python_kind) pairing
    # Submods reflect the source file inside classic-config-core:
    #   config.rs -> config (ClassicConfig, PathConfig, YamlSource)
    #   yamldata.rs -> yamldata (everything else)
    # "config" and "yamldata" as rustSymbols are also the sub-module names.
    rust_only_map: dict[str, tuple[str, str, str]] = {
        # Data model types from yamldata.rs (no Python wrappers; surfaced via YamlData getters)
        "ConfigError": ("yamldata", "YamlData", "class"),
        "CoreModEntry": ("yamldata", "YamlData", "class"),
        "CoreModExclude": ("yamldata", "YamlData", "class"),
        "CrashgenEntryRaw": ("yamldata", "YamlData", "class"),
        "ModConflictEntry": ("yamldata", "YamlData", "class"),
        "ModSolutionCriteria": ("yamldata", "YamlData", "class"),
        "ModSolutionEntry": ("yamldata", "YamlData", "class"),
        "SuspectErrorRule": ("yamldata", "YamlData", "class"),
        "SuspectStackCountRule": ("yamldata", "YamlData", "class"),
        "SuspectStackRule": ("yamldata", "YamlData", "class"),
        # Sub-module markers
        "config": ("config", "ClassicConfig", "class"),
        "yamldata": ("yamldata", "YamlData", "class"),
        # Free functions (yamldata.rs free fns have no -py counterpart)
        "format_registry_game_version": ("yamldata", "create_yamldata", "function"),
        "resolve_registry_version_info": ("yamldata", "create_yamldata", "function"),
        # Re-export from classic-shared-core
        "get_runtime": ("shared", "clear_yaml_cache", "function"),
    }

    # Map Python-only binding identifiers (top-level dot path after stripping module)
    # to their (rust_symbol, python_kind, submod) triple.
    # Sub-modules mirror the class's source file in classic-config-core.
    # For create_yamldata (no -core fn), pair with YamlDataCore.
    python_only_map: dict[str, tuple[str, str, str]] = {
        "ClassicConfig.__init__": ("ClassicConfig", "method", "config"),
        "ClassicConfig.__repr__": ("ClassicConfig", "method", "config"),
        "PathConfig.__init__": ("PathConfig", "method", "config"),
        "PathConfig.__repr__": ("PathConfig", "method", "config"),
        "YamlData.__init__": ("YamlDataCore", "method", "yamldata"),
        "YamlData.__repr__": ("YamlDataCore", "method", "yamldata"),
        "YamlSource.__eq__": ("YamlSource", "method", "config"),
        "YamlSource.__hash__": ("YamlSource", "method", "config"),
        "YamlSource.__repr__": ("YamlSource", "method", "config"),
        "YamlSource.__str__": ("YamlSource", "method", "config"),
        "create_yamldata": ("YamlDataCore", "function", "yamldata"),
    }

    def make_row(id_: str, rust_symbol: str, py_path: str, kind: str) -> dict:
        py_item = py_index.get(py_path)
        py_kind = py_item["kind"] if py_item else kind
        row = {
            "id": id_,
            "tier": "tier1",
            "ownerModule": "config",
            "rustCrate": "classic-config-core",
            "rustSymbol": rust_symbol,
            "pythonModule": "classic_config",
            "pythonExportPath": py_path,
            "pythonKind": py_kind,
        }
        if py_item and py_item.get("arity") is not None:
            row["pythonArity"] = py_item["arity"]
        return row

    rows: list[dict] = []

    # --- 15 rust-only @rust-suffixed rows ---
    rust_only_entries = [e for e in config_deferred if e.get("rustSymbols")]
    assert len(rust_only_entries) == 15, f"expected 15 rust-only, got {len(rust_only_entries)}"

    for e in sorted(rust_only_entries, key=lambda x: x["coverageId"]):
        rs = e["rustSymbols"][0]
        if rs not in rust_only_map:
            raise RuntimeError(f"Unhandled rust-only config symbol: {rs}")
        submod, py_proxy, kind = rust_only_map[rs]
        id_ = f"config.{submod}.{rs}@rust"
        rows.append(make_row(id_, rs, py_proxy, kind))

    # --- 11 python-only rows ---
    python_only_entries = [e for e in config_deferred if e.get("bindingIdentifiers")]
    assert len(python_only_entries) == 11, f"expected 11 python-only, got {len(python_only_entries)}"

    for e in sorted(python_only_entries, key=lambda x: x["coverageId"]):
        ident = e["bindingIdentifiers"][0]
        path = ident.replace("classic_config.", "")
        if path not in python_only_map:
            raise RuntimeError(f"Unhandled python-only config identifier: {path}")
        rust_sym, kind, submod = python_only_map[path]
        id_ = f"config.{submod}.{path}"
        rows.append(make_row(id_, rust_sym, path, kind))

    # --- 2 Tier-2 runtime-verified migrations ---
    # Both get_application_dir and set_application_dir are #[pyfunction] free fns
    # and ARE in the Python surface (verified from python_api_surface.json).
    tier2_migrations = [
        ("config.shared.get_application_dir", "get_application_dir", "get_application_dir", "function"),
        ("config.shared.set_application_dir", "set_application_dir", "set_application_dir", "function"),
    ]
    for id_, rust_sym, py_path, kind in tier2_migrations:
        rows.append(make_row(id_, rust_sym, py_path, kind))

    assert len(rows) == 28, f"expected 28 total rows, got {len(rows)}"
    ids = [r["id"] for r in rows]
    assert len(set(ids)) == 28, "duplicate IDs"

    # Verify every pythonExportPath exists in the Python surface
    missing_py: list[str] = []
    for r in rows:
        if r["pythonExportPath"] not in py_index:
            missing_py.append(f"{r['id']} -> {r['pythonExportPath']}")
    if missing_py:
        print("WARNING: missing from python_api_surface:")
        for m in missing_py:
            print(f"  {m}")
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
    tier2_count = sum(1 for r in rows if r["id"].startswith("config.shared."))
    python_count = len(rows) - rust_count - tier2_count
    print(f"  rust-only (@rust): {rust_count}")
    print(f"  python-only: {python_count}")
    print(f"  tier2 migrations: {tier2_count}")


if __name__ == "__main__":
    main()
