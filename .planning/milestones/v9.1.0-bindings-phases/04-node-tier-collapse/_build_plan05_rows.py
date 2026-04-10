"""
Plan 05 row builder: generates all promotion rows for the residual sweep.
Reads deferred_runtime_backlog.json, rust_api_surface.json, node_api_surface.json,
and parity_contract.json. Outputs new rows to append to parity_contract.json.

Also handles:
- Cross-owner overlap symbols (from routing table)
- Node-only gaps (from parity_diff_report.json)
- GLOBAL_FCX_HANDLER exclusion

Usage:
  python .planning/phases/04-node-tier-collapse/_build_plan05_rows.py [--apply] [--dry-run]
"""
import json
import sys
from pathlib import Path
from collections import Counter

REPO_ROOT = Path(".")

def load_json(path):
    return json.load(open(REPO_ROOT / path))

def build_rust_lookup(rust_surface):
    """Build symbol -> {crate, kind} lookup from rust_api_surface.json"""
    lookup = {}
    for item in rust_surface.get("symbols", []):
        sym = item.get("symbol")
        crate = item.get("crate")
        kind = item.get("kind")
        if sym and crate:
            lookup[sym] = {"crate": crate, "kind": kind}
    return lookup

def build_node_lookup(node_surface):
    """Build export -> kind lookup from node_api_surface.json"""
    lookup = {}
    for item in node_surface.get("exports", []):
        name = item.get("export") or item.get("name")
        kind = item.get("kind")
        if name:
            lookup[name] = kind
    return lookup

def build_existing_sets(contract):
    """Build sets of existing IDs, nodeExports, and rustSymbols"""
    ids = set()
    node_exports = set()
    rust_symbols = set()
    for row in contract.get("tier1Mappings", []):
        ids.add(row["id"])
        if "nodeExport" in row:
            node_exports.add(row["nodeExport"])
        rs = row.get("rustSymbol", "")
        if rs.endswith("@rust"):
            rust_symbols.add(rs[:-5])
        elif rs:
            rust_symbols.add(rs)
    return ids, node_exports, rust_symbols

# Cross-owner routing table (from Task 0 verification)
ROUTING_TABLE = {
    "getApplicationDir": {
        "owner": "aux",
        "rustCrate": "classic-registry-core",
        "rustSymbol": "get_application_dir",
        "nodeKind": "function",
    },
    "setApplicationDir": {
        "owner": "aux",
        "rustCrate": "classic-registry-core",
        "rustSymbol": "set_application_dir",
        "nodeKind": "function",
    },
    "resetFcxGlobalState": {
        "owner": "aux",
        "rustCrate": "classic-scanlog-core",
        "rustSymbol": "reset_fcx_global_state",
        "nodeKind": "function",
    },
    "writeAutoscanReport": {
        "owner": "aux",
        "rustCrate": "classic-file-io-core",
        "rustSymbol": "write_autoscan_report",
        "nodeKind": "function",
    },
    "JsModConflictEntry": {
        "owner": "config",
        "rustCrate": "classic-config-core",
        "rustSymbol": "ModConflictEntry",
        "nodeKind": "interface",
    },
    "migrateGameVersionSetting": {
        "owner": "version_registry",
        "rustCrate": "classic-scangame-core",
        "rustSymbol": "migrate_game_version_setting",
        "nodeKind": "function",
    },
    # Additional node_unmapped symbols found in diff report
    "createLogger": {
        "owner": "scanlog",
        "rustCrate": "classic-message-core",
        "rustSymbol": "Logger",
        "nodeKind": "function",
    },
    "processGameLogs": {
        "owner": "scanlog",
        "rustCrate": "classic-scangame-core",
        "rustSymbol": "LogProcessor",
        "nodeKind": "function",
    },
    "JsLogCollector": {
        "owner": "scanlog",
        "rustCrate": "classic-file-io-core",
        "rustSymbol": "LogCollector",
        "nodeKind": "class",
    },
    "JsLogProcessor": {
        "owner": "scanlog",
        "rustCrate": "classic-scangame-core",
        "rustSymbol": "LogProcessor",
        "nodeKind": "class",
    },
    "JsLogger": {
        "owner": "scanlog",
        "rustCrate": "classic-message-core",
        "rustSymbol": "Logger",
        "nodeKind": "class",
    },
}

# Crashgen rules JS -> Rust mapping (manually verified from crashgen_rules.rs)
CRASHGEN_RULES_MAP = {
    "JsCheckRule": "CheckRule",
    "JsExpectedValue": "ExpectedValue",
    "JsPreflightAction": "PreflightAction",
    "JsPreflightRule": "PreflightRule",
    "JsRuleMessages": "RuleMessages",
    "JsRuleTarget": "RuleTarget",
    "JsModSolutionCriteria": "ModSolutionCriteria",
    "JsModSolutionEntry": "ModSolutionEntry",
    "JsSuspectErrorRule": "SuspectErrorRule",
    "JsSuspectStackCountRule": "SuspectStackCountRule",
    "JsSuspectStackRule": "SuspectStackRule",
}


def main():
    apply_mode = "--apply" in sys.argv
    dry_run = "--dry-run" in sys.argv or not apply_mode

    # Load all sources
    backlog = load_json("docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json")
    diff = load_json("docs/implementation/node_api_parity/baseline/parity_diff_report.json")
    rust_surface = load_json("docs/implementation/node_api_parity/baseline/rust_api_surface.json")
    node_surface = load_json("docs/implementation/node_api_parity/baseline/node_api_surface.json")
    contract = load_json("docs/implementation/node_api_parity/baseline/parity_contract.json")

    rust_lookup = build_rust_lookup(rust_surface)
    node_lookup = build_node_lookup(node_surface)
    existing_ids, existing_node_exports, existing_rust_symbols = build_existing_sets(contract)

    new_rows = []
    skipped = []

    # 1. Process backlog entries (322 Rust-only + 12 Node-exposed)
    for entry in backlog["entries"]:
        owner = entry.get("ownerModule", "unknown")
        rust_symbols = entry.get("rustSymbols", [])
        binding_ids = entry.get("bindingIdentifiers", [])

        # Skip GLOBAL_FCX_HANDLER
        if any("GLOBAL_FCX_HANDLER" in rs for rs in rust_symbols):
            skipped.append(("GLOBAL_FCX_HANDLER", "Phase 3 R9 precedent exclusion"))
            continue

        if binding_ids:
            # Node-exposed entries -> normal rows
            for bid in binding_ids:
                if bid in existing_node_exports:
                    skipped.append((bid, "already in contract"))
                    continue

                # Check routing table first
                if bid in ROUTING_TABLE:
                    rt = ROUTING_TABLE[bid]
                    row_id = f"{rt['owner']}.{bid}"
                    if row_id in existing_ids:
                        skipped.append((bid, f"already in contract as {row_id}"))
                        continue
                    new_rows.append({
                        "id": row_id,
                        "tier": "tier1",
                        "ownerModule": rt["owner"],
                        "rustCrate": rt["rustCrate"],
                        "rustSymbol": rt["rustSymbol"],
                        "nodeExport": bid,
                        "nodeKind": rt["nodeKind"],
                    })
                    continue

                # Check crashgen rules map
                if bid in CRASHGEN_RULES_MAP:
                    rust_sym = CRASHGEN_RULES_MAP[bid]
                    rust_info = rust_lookup.get(rust_sym, {})
                    rust_crate = rust_info.get("crate", "classic-crashgen-settings-core")
                    # But some are from classic-config-core (ModConflict*)
                    row_id = f"aux.{bid}"
                    if row_id in existing_ids:
                        skipped.append((bid, f"already in contract as {row_id}"))
                        continue
                    new_rows.append({
                        "id": row_id,
                        "tier": "tier1",
                        "ownerModule": "aux",
                        "rustCrate": rust_crate,
                        "rustSymbol": rust_sym,
                        "nodeExport": bid,
                        "nodeKind": "interface",
                    })
                    continue

                # General case: strip Js prefix to find Rust symbol
                bare = bid[2:] if bid.startswith("Js") else bid
                rust_info = rust_lookup.get(bare, {})
                rust_crate = rust_info.get("crate")
                rust_sym = bare if rust_crate else bid

                # Determine nodeKind from node_surface
                node_kind = node_lookup.get(bid, "interface")

                row_id = f"{owner}.{bid}"
                if row_id in existing_ids:
                    skipped.append((bid, f"already in contract as {row_id}"))
                    continue
                new_rows.append({
                    "id": row_id,
                    "tier": "tier1",
                    "ownerModule": owner,
                    "rustCrate": rust_crate or "unknown",
                    "rustSymbol": rust_sym,
                    "nodeExport": bid,
                    "nodeKind": node_kind,
                })
        else:
            # Rust-only entries -> proxy rows
            for rs in rust_symbols:
                if rs in existing_rust_symbols:
                    skipped.append((rs, "already in contract"))
                    continue

                rust_info = rust_lookup.get(rs, {})
                rust_crate = rust_info.get("crate")
                rust_kind = rust_info.get("kind", "unknown")

                row_id = f"{owner}.{rs}@rust"
                if row_id in existing_ids:
                    skipped.append((rs, f"already in contract as {row_id}"))
                    continue

                if not rust_crate:
                    # Symbol not in rust surface - may be a sub-symbol
                    # Use owner_module -> crate mapping
                    owner_crate_map = {
                        "config": "classic-config-core",
                        "constants": "classic-constants-core",
                        "crashgen_settings": "classic-crashgen-settings-core",
                        "database": "classic-database-core",
                        "file_io": "classic-file-io-core",
                        "message": "classic-message-core",
                        "path": "classic-path-core",
                        "perf": "classic-perf-core",
                        "registry": "classic-registry-core",
                        "scangame": "classic-scangame-core",
                        "scanlog": "classic-scanlog-core",
                        "settings": "classic-settings-core",
                        "shared": "classic-shared-core",
                        "update": "classic-update-core",
                        "version": "classic-version-core",
                        "version_registry": "classic-version-registry-core",
                        "web": "classic-web-core",
                        "xse": "classic-xse-core",
                        "yaml": "classic-yaml-core",
                        "aux": "classic-scanlog-core",  # fallback for aux
                    }
                    rust_crate = owner_crate_map.get(owner, "unknown")

                new_rows.append({
                    "id": row_id,
                    "tier": "tier1",
                    "ownerModule": owner,
                    "rustCrate": rust_crate,
                    "rustSymbol": f"{rs}@rust",
                    "rustKind": rust_kind,
                })

    # 2. Process diff-report-only gaps (node_unmapped that aren't in backlog)
    # These are node exports with no Rust equivalent that need normal rows
    diff_gaps = diff.get("gaps", [])
    node_unmapped = [g for g in diff_gaps if g.get("gap_type") == "node_unmapped"]

    for gap in node_unmapped:
        ne = gap.get("node_export")
        if not ne:
            continue
        if ne in existing_node_exports:
            continue
        # Check if already added from backlog
        already_added = any(r.get("nodeExport") == ne for r in new_rows)
        if already_added:
            continue

        # Check routing table
        if ne in ROUTING_TABLE:
            rt = ROUTING_TABLE[ne]
            row_id = f"{rt['owner']}.{ne}"
            if row_id not in existing_ids and not any(r["id"] == row_id for r in new_rows):
                new_rows.append({
                    "id": row_id,
                    "tier": "tier1",
                    "ownerModule": rt["owner"],
                    "rustCrate": rt["rustCrate"],
                    "rustSymbol": rt["rustSymbol"],
                    "nodeExport": ne,
                    "nodeKind": rt["nodeKind"],
                })
        else:
            owner = gap.get("owner_module", "aux")
            kind = gap.get("kind", "function")
            bare = ne[2:] if ne.startswith("Js") else ne
            rust_info = rust_lookup.get(bare, {})
            rust_crate = rust_info.get("crate", "unknown")
            row_id = f"{owner}.{ne}"
            if row_id not in existing_ids and not any(r["id"] == row_id for r in new_rows):
                new_rows.append({
                    "id": row_id,
                    "tier": "tier1",
                    "ownerModule": owner,
                    "rustCrate": rust_crate,
                    "rustSymbol": bare if rust_crate != "unknown" else ne,
                    "nodeExport": ne,
                    "nodeKind": kind,
                })

    # Stats
    by_owner = Counter(r["ownerModule"] for r in new_rows)
    proxy_count = sum(1 for r in new_rows if r.get("rustSymbol", "").endswith("@rust"))
    normal_count = len(new_rows) - proxy_count

    print(f"Total new rows: {len(new_rows)}")
    print(f"  Proxy (@rust): {proxy_count}")
    print(f"  Normal (nodeExport): {normal_count}")
    print(f"  Skipped: {len(skipped)}")
    print(f"By owner:")
    for o, c in sorted(by_owner.items()):
        print(f"  {o}: {c}")

    # Check for unknowns
    unknowns = [r for r in new_rows if r.get("rustCrate") == "unknown"]
    if unknowns:
        print(f"\nWARNING: {len(unknowns)} rows with unknown rustCrate:")
        for u in unknowns[:10]:
            print(f"  {u['id']}: rustSymbol={u.get('rustSymbol')}")

    if apply_mode:
        # Apply rows to contract
        contract["tier1Mappings"].extend(new_rows)
        with open(REPO_ROOT / "docs/implementation/node_api_parity/baseline/parity_contract.json", "w") as f:
            json.dump(contract, f, indent=2)
            f.write("\n")
        print(f"\nApplied {len(new_rows)} rows. New total: {len(contract['tier1Mappings'])}")
    elif dry_run:
        print("\nDry run -- no changes written. Use --apply to write.")

    return new_rows


if __name__ == "__main__":
    main()
