"""Bump runtime_coverage_registry.json selectors after contract row changes.

Phase 4 Plan 2:
- After Task 1 (57 proxy rows added), the `node-tier1-scanlog` selector
  matches 16 + 57 = 73 contract rows. Recompute contractCount + contractIdsHash.
- After Task 2 (9 normal rows added), the same selector matches 82 rows.
  Recompute again.

The selector-matching logic (via tools.binding_parity_runtime_coverage) works
by filtering contract_results rows that match the selector keys. Since that
module operates on the diff-report contract_results (normalized snake_case
keys), we mirror the filter here directly against the raw contract file.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CONTRACT_PATH = REPO / "docs/implementation/node_api_parity/baseline/parity_contract.json"
REGISTRY_PATH = REPO / "ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json"

sys.path.insert(0, str(REPO / "tools"))
from binding_parity_runtime_coverage import _stable_id_hash  # noqa: E402 - mandatory D-HASH-01 import


def _selector_matches(selector: dict, row: dict) -> bool:
    """Match selector keys against a contract row (raw JSON shape)."""
    for key, expected in selector.items():
        if row.get(key) != expected:
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--coverage-id",
        default="node-tier1-scanlog",
        help="coverageId of the selector entry to bump",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print new hash/count without writing",
    )
    args = parser.parse_args()

    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    target = None
    for entry in registry["entries"]:
        if entry.get("coverageId") == args.coverage_id:
            target = entry
            break
    if target is None:
        print(f"ERROR: coverageId '{args.coverage_id}' not found", file=sys.stderr)
        return 2

    selector = target.get("contractSelector")
    if not selector:
        print(f"ERROR: entry '{args.coverage_id}' has no contractSelector", file=sys.stderr)
        return 2

    matched_ids = sorted(
        row["id"]
        for row in contract["tier1Mappings"]
        if _selector_matches(selector, row)
    )
    new_count = len(matched_ids)
    new_hash = _stable_id_hash(matched_ids)

    old_count = target.get("contractCount")
    old_hash = target.get("contractIdsHash")
    print(f"coverageId: {args.coverage_id}")
    print(f"old contractCount: {old_count}")
    print(f"new contractCount: {new_count}")
    print(f"old contractIdsHash: {old_hash}")
    print(f"new contractIdsHash: {new_hash}")
    print(f"hash length: {len(new_hash)} (expected 64)")
    assert len(new_hash) == 64, "hash length mismatch — _stable_id_hash must return full SHA-256 hex"

    if args.dry_run:
        return 0

    target["contractCount"] = new_count
    target["contractIdsHash"] = new_hash

    # Preserve CRLF line endings on the registry file.
    text = json.dumps(registry, indent=2, ensure_ascii=False) + "\n"
    REGISTRY_PATH.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    print(f"Updated {REGISTRY_PATH.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
