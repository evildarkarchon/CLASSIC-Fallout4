#!/usr/bin/env python3
"""Deterministically merge one owner group into another inside a parity contract JSON file.

Reusable across Phases 1-3 of the v9.1.0 consolidation milestone. See
`.planning/phases/01-yaml-settings-merge/01-03-PLAN.md` section A for the design spec,
and the phase 1 plan 3 summary for live usage notes.

The helper performs all mutations in-place:

  1. Optional top-level `ownerModules[<source>]` entry removal (Python-contract only).
  2. Squad-level `squads[...].ownerModules` array updates (Node-contract only).
  3. Row-level `ownerModule` and `rustCrate` rewrites inside `tier1Mappings`.
  4. Row-level `pythonModule` / `pythonExportPath` prefix rewrites (Python rows only).
  5. Defensive recursive walk for any nested dicts that carry `ownerModule` or
     `rustCrate` keys (phase 2/3 safety — mostly a no-op for phase 1).
  6. Post-merge uniqueness check on row `id` values.

Contract schema detection is by row-field presence, NOT by filename:

  - Python rows carry `pythonModule` and/or `pythonExportPath` keys.
  - Node rows carry `nodeExport` (a simple JS export name, NOT a module path).

The helper never rewrites `nodeExport`, `rustSymbol`, or row `id` fields.

Usage:

    python tools/parity_contract_merge_owner.py \
        --contract docs/implementation/python_api_parity/baseline/parity_contract.json \
        --source-owner yaml \
        --target-owner settings \
        --rust-crate-old classic-yaml-core \
        --rust-crate-new classic-settings-core \
        --binding-module-old classic_yaml \
        --binding-module-new classic_settings \
        [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

assert sys.version_info >= (3, 7), "requires Python 3.7+ for insertion-ordered dicts"


def detect_contract_type(contract: dict[str, Any]) -> str:
    """Return 'python' or 'node' based on row field presence."""
    rows = contract.get("tier1Mappings", [])
    for row in rows:
        if not isinstance(row, dict):
            continue
        if "pythonModule" in row or "pythonExportPath" in row:
            return "python"
        if "nodeExport" in row:
            return "node"
    return "unknown"


def walk_recursive_owner_rewrite(
    node: Any,
    source_owner: str,
    target_owner: str,
    rust_crate_old: str,
    rust_crate_new: str,
) -> tuple[int, int]:
    """Defensive recursive walk. Returns (owner_rows_changed, rust_crate_changed)."""
    owner_changed = 0
    rust_changed = 0
    if isinstance(node, dict):
        if node.get("ownerModule") == source_owner:
            node["ownerModule"] = target_owner
            owner_changed += 1
        if node.get("rustCrate") == rust_crate_old:
            node["rustCrate"] = rust_crate_new
            rust_changed += 1
        for v in node.values():
            sub_owner, sub_rust = walk_recursive_owner_rewrite(
                v, source_owner, target_owner, rust_crate_old, rust_crate_new
            )
            owner_changed += sub_owner
            rust_changed += sub_rust
    elif isinstance(node, list):
        for v in node:
            sub_owner, sub_rust = walk_recursive_owner_rewrite(
                v, source_owner, target_owner, rust_crate_old, rust_crate_new
            )
            owner_changed += sub_owner
            rust_changed += sub_rust
    return owner_changed, rust_changed


def merge_owner_group(
    contract_path: Path,
    source_owner: str,
    target_owner: str,
    rust_crate_old: str,
    rust_crate_new: str,
    binding_module_old: str,
    binding_module_new: str,
    dry_run: bool = False,
) -> int:
    """Return exit code (0 success, 1 error)."""
    try:
        with contract_path.open("r", encoding="utf-8") as f:
            contract = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read/parse {contract_path}: {exc}", file=sys.stderr)
        return 1

    contract_type = detect_contract_type(contract)
    if contract_type == "unknown":
        print(
            f"ERROR: cannot detect contract type (python vs node) for {contract_path}",
            file=sys.stderr,
        )
        return 1

    owner_rows_changed = 0
    rust_crate_rows_changed = 0
    squads_changed = 0
    top_level_deleted = 0

    # Snapshot row id counts before merge so we only flag duplicates newly introduced
    # by the merge (pre-existing duplicates in the contract are tolerated).
    pre_id_counts: dict[str, int] = {}
    for row in contract.get("tier1Mappings", []):
        if not isinstance(row, dict):
            continue
        row_id = row.get("id")
        if row_id is None:
            continue
        pre_id_counts[row_id] = pre_id_counts.get(row_id, 0) + 1

    # Step 2: top-level ownerModules entry handling.
    owner_modules = contract.get("ownerModules", {})
    if isinstance(owner_modules, dict) and source_owner in owner_modules:
        del owner_modules[source_owner]
        top_level_deleted = 1

    # Contract-type branching for missing target.
    if isinstance(owner_modules, dict) and target_owner not in owner_modules:
        if contract_type == "python":
            print(
                f"ERROR: python contract ownerModules missing target '{target_owner}'. "
                f"Aborting to prevent corruption.",
                file=sys.stderr,
            )
            return 1
        # node contract: warn and continue without editing the top-level map.
        print(
            f'WARNING: Node contract top-level ownerModules has neither "{source_owner}" '
            f'nor "{target_owner}"; row-level reparenting will proceed but top-level '
            f"metadata remains minimal",
            file=sys.stderr,
        )

    # Step 3: squad metadata (Node contract only).
    if contract_type == "node":
        squads = contract.get("squads", {})
        if isinstance(squads, dict):
            for squad_name, squad_entry in squads.items():
                if not isinstance(squad_entry, dict):
                    continue
                sq_owners = squad_entry.get("ownerModules")
                if not isinstance(sq_owners, list):
                    continue
                if source_owner in sq_owners:
                    if target_owner in sq_owners:
                        sq_owners.remove(source_owner)
                    else:
                        idx = sq_owners.index(source_owner)
                        sq_owners[idx] = target_owner
                    squads_changed += 1

    # Step 4: tier1Mappings row-level rewrites.
    rows = contract.get("tier1Mappings", [])
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("ownerModule") == source_owner:
            row["ownerModule"] = target_owner
            owner_rows_changed += 1
        if row.get("rustCrate") == rust_crate_old:
            row["rustCrate"] = rust_crate_new
            rust_crate_rows_changed += 1
        # Python row schema: pythonModule and pythonExportPath
        if "pythonModule" in row and row.get("pythonModule") == binding_module_old:
            row["pythonModule"] = binding_module_new
        if "pythonExportPath" in row:
            path_val = row.get("pythonExportPath")
            if isinstance(path_val, str) and path_val.startswith(binding_module_old + "."):
                row["pythonExportPath"] = binding_module_new + path_val[len(binding_module_old):]
        # Node row schema: nodeExport is a simple identifier and is NOT rewritten.

    # Step 5: defensive recursive walk for nested dicts outside tier1Mappings.
    # Skip the already-walked tier1Mappings to avoid double-counting.
    for key, value in contract.items():
        if key in ("tier1Mappings", "ownerModules"):
            continue
        sub_owner, sub_rust = walk_recursive_owner_rewrite(
            value, source_owner, target_owner, rust_crate_old, rust_crate_new
        )
        owner_rows_changed += sub_owner
        rust_crate_rows_changed += sub_rust

    # Step 7: collision detection by row id. Only NEW duplicates introduced by the
    # merge are fatal; pre-existing duplicates in the contract are a pre-existing
    # quirk that the merge does not worsen.
    post_id_counts: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_id = row.get("id")
        if row_id is None:
            continue
        post_id_counts[row_id] = post_id_counts.get(row_id, 0) + 1

    new_collisions = [rid for rid, n in post_id_counts.items() if n > pre_id_counts.get(rid, 0) and n > 1]
    if new_collisions:
        print(
            f"ERROR: duplicate row id(s) newly introduced by merge: {new_collisions}; "
            f"helper aborted; no changes written. Manual resolution required.",
            file=sys.stderr,
        )
        return 1

    summary = (
        f"Merged {source_owner} -> {target_owner} in {contract_path} "
        f"({owner_rows_changed} owner rows reparented, {rust_crate_rows_changed} rustCrate rows "
        f"updated, {squads_changed} squads updated, {top_level_deleted} top-level ownerModules deleted)"
    )
    if dry_run:
        print(f"[DRY-RUN] {summary}")
        return 0

    # Step 8: write output.
    with contract_path.open("w", encoding="utf-8") as f:
        json.dump(contract, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(summary)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deterministically merge one owner group into another inside a parity contract JSON file.",
    )
    parser.add_argument("--contract", required=True, type=Path, help="Path to parity_contract.json")
    parser.add_argument("--source-owner", required=True, help="Source ownerModule value to merge from")
    parser.add_argument("--target-owner", required=True, help="Target ownerModule value to merge into")
    parser.add_argument("--rust-crate-old", required=True, help="Old rustCrate value")
    parser.add_argument("--rust-crate-new", required=True, help="New rustCrate value")
    parser.add_argument("--binding-module-old", required=True, help="Old binding-module value (pythonModule / prefix)")
    parser.add_argument("--binding-module-new", required=True, help="New binding-module value")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing the file")

    args = parser.parse_args()

    return merge_owner_group(
        contract_path=args.contract,
        source_owner=args.source_owner,
        target_owner=args.target_owner,
        rust_crate_old=args.rust_crate_old,
        rust_crate_new=args.rust_crate_new,
        binding_module_old=args.binding_module_old,
        binding_module_new=args.binding_module_new,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
