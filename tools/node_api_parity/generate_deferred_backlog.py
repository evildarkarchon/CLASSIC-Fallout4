#!/usr/bin/env python3
"""Generate Node deferred runtime backlog metadata from parity artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Node deferred runtime backlog registry."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Repository root path.",
    )
    parser.add_argument(
        "--diff-report",
        default="docs/implementation/node_api_parity/baseline/parity_diff_report.json",
        help="Path to the Node parity diff report JSON, relative to repo root.",
    )
    parser.add_argument(
        "--wave-manifest",
        default="docs/implementation/node_api_parity/governance/tier2_wave_manifest.json",
        help="Path to the Node wave manifest JSON, relative to repo root.",
    )
    parser.add_argument(
        "--runtime-registry",
        default="ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json",
        help="Path to the Node runtime coverage registry JSON, relative to repo root.",
    )
    parser.add_argument(
        "--output",
        default="docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json",
        help="Path to the deferred backlog JSON, relative to repo root.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    diff_report = json.loads((repo_root / args.diff_report).read_text(encoding="utf-8"))
    wave_manifest = json.loads(
        (repo_root / args.wave_manifest).read_text(encoding="utf-8")
    )
    runtime_registry = json.loads(
        (repo_root / args.runtime_registry).read_text(encoding="utf-8")
    )

    wave_index = {
        (row.get("node_export") or f"rust:{row.get('rust_symbol')}"): row
        for row in wave_manifest.get("gaps", [])
    }
    runtime_identifiers = {
        identifier
        for entry in runtime_registry.get("entries", [])
        if entry.get("classification") == "runtime_verified"
        and entry.get("tier") == "tier2"
        for identifier in entry.get("bindingIdentifiers", [])
    }
    runtime_rust_symbols = {
        symbol
        for entry in runtime_registry.get("entries", [])
        if entry.get("classification") == "runtime_verified"
        and entry.get("tier") == "tier2"
        for symbol in entry.get("rustSymbols", [])
    }

    entries: list[dict[str, Any]] = []
    for ordinal, gap in enumerate(
        [row for row in diff_report.get("gaps", []) if row.get("tier") == "tier2"],
        start=1,
    ):
        if gap.get("node_export") in runtime_identifiers:
            continue
        if gap.get("rust_symbol") in runtime_rust_symbols:
            continue
        key = gap.get("node_export") or f"rust:{gap.get('rust_symbol')}"
        wave_row = wave_index.get(key, {})
        owner_module = gap["owner_module"]
        entries.append(
            {
                "coverageId": f"node-deferred-{owner_module}-{ordinal:03d}",
                "classification": "deferred",
                "ownerModule": owner_module,
                "tier": "tier2",
                "wave": wave_row.get("wave"),
                "owner": "Squad A"
                if owner_module in {"scanlog", "config"}
                else "Squad B",
                "deferReason": gap.get("reason"),
                "bindingIdentifiers": [gap["node_export"]]
                if gap.get("node_export")
                else [],
                "rustSymbols": [gap["rust_symbol"]] if gap.get("rust_symbol") else [],
            }
        )

    output = {
        "schemaVersion": "1.0",
        "binding": "node",
        "entries": entries,
    }
    output_path = repo_root / args.output
    write_json(output_path, output)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
