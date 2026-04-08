#!/usr/bin/env python3
"""Generate Python deferred runtime backlog and wave manifest artifacts."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


WAVE_BY_OWNER = {
    # Existing (pre-Phase-3) waves preserved for historical compatibility.
    "scanlog":          "wave1",
    "config":           "wave2",
    "version_registry": "wave3",
    "aux":              "wave4",
    # Phase 3 additions -- one wave label per new owner. The wave label is
    # used only for reporting; the actual promotion schedule is governed by
    # the downstream Phase 3 plan sequence (Plans 02-09b) in the
    # .planning/phases/03-python-tier-collapse/ directory.
    "yaml":             "wave5",
    "database":         "wave6",
    "file_io":          "wave7",
    "scangame":         "wave8",
    "registry":         "wave9",
    "perf":             "wave10",
    "settings":         "wave11",
    "message":          "wave12",
    "path":             "wave13",
    "constants":        "wave14",
    "version":          "wave15",
    "resource":         "wave16",
    "xse":              "wave17",
    "web":              "wave18",
    "update":           "wave19",
    "shared":           "wave20",
}

WAVE_LABELS = {
    "wave1":  "scanlog deferred runtime backlog",
    "wave2":  "config deferred runtime backlog",
    "wave3":  "version_registry deferred runtime backlog",
    "wave4":  "aux deferred runtime backlog",
    "wave5":  "yaml deferred runtime backlog",
    "wave6":  "database deferred runtime backlog",
    "wave7":  "file_io deferred runtime backlog",
    "wave8":  "scangame deferred runtime backlog",
    "wave9":  "registry deferred runtime backlog",
    "wave10": "perf deferred runtime backlog",
    "wave11": "settings deferred runtime backlog",
    "wave12": "message deferred runtime backlog",
    "wave13": "path deferred runtime backlog",
    "wave14": "constants deferred runtime backlog",
    "wave15": "version deferred runtime backlog",
    "wave16": "resource deferred runtime backlog",
    "wave17": "xse deferred runtime backlog",
    "wave18": "web deferred runtime backlog",
    "wave19": "update deferred runtime backlog",
    "wave20": "shared (foundation/classic-shared-py) deferred runtime backlog",
}

# Squad assignment for deferred backlog entries. Aligns with
# tools/python_api_parity/generate_baseline.py::SQUAD_BY_OWNER (Phase 3
# Plan 01 Task 2). Kept local to this tool to avoid a module-level import
# between the two baseline scripts.
SQUAD_BY_OWNER: dict[str, str] = {
    "scanlog":          "Squad A",
    "config":           "Squad A",
    "version_registry": "Squad B",
    "aux":              "Squad B",
    "yaml":             "Squad C",
    "database":         "Squad D",
    "file_io":          "Squad D",
    "scangame":         "Squad E",
    "registry":         "Squad C",
    "perf":             "Squad F",
    "settings":         "Squad C",
    "message":          "Squad F",
    "path":             "Squad F",
    "constants":        "Squad F",
    "version":          "Squad F",
    "resource":         "Squad D",
    "xse":              "Squad E",
    "web":              "Squad F",
    "update":           "Squad F",
    "shared":           "Squad G",
}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Python deferred runtime backlog and wave manifest."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Repository root path.",
    )
    parser.add_argument(
        "--diff-report",
        default="docs/implementation/python_api_parity/baseline/parity_diff_report.json",
        help="Path to the Python parity diff report JSON, relative to repo root.",
    )
    parser.add_argument(
        "--wave-output",
        default="docs/implementation/python_api_parity/governance/tier2_wave_manifest.json",
        help="Path to the Python wave manifest JSON, relative to repo root.",
    )
    parser.add_argument(
        "--runtime-registry",
        default="ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json",
        help="Path to the Python runtime coverage registry JSON, relative to repo root.",
    )
    parser.add_argument(
        "--deferred-output",
        default="docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json",
        help="Path to the Python deferred backlog JSON, relative to repo root.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    diff_report = json.loads((repo_root / args.diff_report).read_text(encoding="utf-8"))
    runtime_registry = json.loads(
        (repo_root / args.runtime_registry).read_text(encoding="utf-8")
    )
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

    per_owner_ordinals: defaultdict[str, int] = defaultdict(int)
    backlog_entries: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []

    for ordinal, gap in enumerate(
        [row for row in diff_report.get("gaps", []) if row.get("tier") == "tier2"],
        start=1,
    ):
        owner_module = gap["owner_module"]
        export_path = gap.get("python_export_path")
        module_name = gap.get("python_module")
        binding_identifier = (
            f"{module_name}.{export_path}" if module_name and export_path else None
        )
        if binding_identifier in runtime_identifiers:
            continue
        if gap.get("rust_symbol") in runtime_rust_symbols:
            continue
        per_owner_ordinals[owner_module] += 1
        wave = WAVE_BY_OWNER.get(owner_module, "wave4")

        backlog_entries.append(
            {
                "coverageId": f"python-deferred-{owner_module}-{ordinal:03d}",
                "classification": "deferred",
                "ownerModule": owner_module,
                "tier": "tier2",
                "wave": wave,
                "owner": SQUAD_BY_OWNER.get(owner_module, "Squad B"),
                "deferReason": gap.get("reason"),
                "bindingIdentifiers": [binding_identifier]
                if binding_identifier
                else [],
                "rustSymbols": [gap["rust_symbol"]] if gap.get("rust_symbol") else [],
            }
        )
        manifest_rows.append(
            {
                "gap_id": f"{owner_module}-{per_owner_ordinals[owner_module]:03d}",
                "owner_module": owner_module,
                "ordinal_in_module": per_owner_ordinals[owner_module],
                "gap_type": gap.get("gap_type"),
                "tier": gap.get("tier"),
                "rust_symbol": gap.get("rust_symbol"),
                "python_module": module_name,
                "python_export_path": export_path,
                "wave": wave,
            }
        )

    write_json(
        repo_root / args.deferred_output,
        {
            "schemaVersion": "1.0",
            "binding": "python",
            "entries": backlog_entries,
        },
    )
    wave_output_path = repo_root / args.wave_output
    write_json(
        wave_output_path,
        {
            "manifest_version": "1.0",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "source": {
                "parity_diff_report_path": args.diff_report,
            },
            "wave_labels": WAVE_LABELS,
            "gaps": manifest_rows,
        },
    )
    print(wave_output_path)
    print(repo_root / args.deferred_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
