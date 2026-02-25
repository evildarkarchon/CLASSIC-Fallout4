#!/usr/bin/env python3
"""Generate a machine-verifiable Phase 0 wave membership manifest from handoff_map."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EXPECTED_TOTAL_GAPS = 315
EXPECTED_MODULE_COUNTS: dict[str, int] = {
    "scanlog": 72,
    "config": 58,
    "version_registry": 43,
    "aux": 142,
}

WAVE_BY_MODULE: dict[str, str] = {
    "scanlog": "wave1",
    "config": "wave2",
    "version_registry": "wave3",
    "aux": "wave4",
}

WAVE_LABELS: dict[str, str] = {
    "wave1": "scanlog full Tier-2 promotion",
    "wave2": "config full Tier-2 promotion",
    "wave3": "version_registry full Tier-2 promotion",
    "wave4": "aux full Tier-2 promotion",
}

AUX_SUBWAVE_LABELS: dict[str, str] = {
    "wave4.1": "foundational utilities",
    "wave4.2": "scanner/integrity/mod/resource/xse/update/web/database surfaces",
    "wave4.3": "remaining utility APIs and constants",
}

# Ordered by precedence. First match wins.
AUX_SUBWAVE_41_TOKENS: tuple[str, ...] = (
    "backup",
    "docs",
    "document",
    "path",
    "file",
    "runtime",
    "metric",
    "timing",
    "message",
    "registry",
    "encoding",
    "permission",
    "readonly",
    "hash",
    "normalize",
    "joinpaths",
    "steam",
    "internstring",
    "processstringbatch",
    "stripemoji",
    "loadbatch",
)

AUX_SUBWAVE_42_TOKENS: tuple[str, ...] = (
    "scan",
    "integrity",
    "mod",
    "resource",
    "xse",
    "update",
    "github",
    "url",
    "database",
    "pool",
    "ba2",
    "dds",
    "enb",
    "ini",
    "wrye",
    "crash",
    "checkforupdates",
    "getlatestrelease",
    "hasupdate",
    "getmodsite",
    "buildurlwithquery",
    "joinurl",
    "extractdomain",
    "validateurl",
    "isvalidurl",
)


def clean_cell(value: str) -> str | None:
    """Normalize markdown table cell values."""
    text = value.strip().strip("`").strip()
    if text in {"-", ""}:
        return None
    return text


def stable_entry_name(entry: dict[str, Any]) -> str:
    """Select the best symbol/export name for classification output."""
    return str(entry.get("node_export") or entry.get("rust_symbol") or "")


def classify_aux_subwave(entry_name: str) -> tuple[str, str]:
    """Classify an aux entry into a deterministic subwave bucket."""
    lowered = entry_name.lower()

    for token in AUX_SUBWAVE_41_TOKENS:
        if token in lowered:
            return "wave4.1", f"token:{token}"

    for token in AUX_SUBWAVE_42_TOKENS:
        if token in lowered:
            return "wave4.2", f"token:{token}"

    return "wave4.3", "fallback:residual"


def parse_handoff_map(markdown_text: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Parse `handoff_map.md` into normalized structured rows."""
    generated_match = re.search(r"- Generated:\s*`([^`]+)`", markdown_text)
    declared_total_match = re.search(r"- Total gaps handed off:\s*\*\*(\d+)\*\*", markdown_text)
    generated_at = generated_match.group(1) if generated_match else None
    declared_total = int(declared_total_match.group(1)) if declared_total_match else None

    current_module: str | None = None
    in_gap_table = False
    table_header_seen = False

    rows: list[dict[str, Any]] = []
    module_ordinals: defaultdict[str, int] = defaultdict(int)

    for raw_line in markdown_text.splitlines():
        module_match = re.match(r"^###\s+`([^`]+)`\s*$", raw_line.strip())
        if module_match:
            current_module = module_match.group(1)
            in_gap_table = False
            table_header_seen = False
            continue

        line = raw_line.strip()
        if line == "| Gap Type | Tier | Rust Symbol | Node Export |":
            in_gap_table = True
            table_header_seen = True
            continue
        if line == "|---|---|---|---|":
            continue

        if not in_gap_table or not table_header_seen:
            continue
        if not line.startswith("|"):
            in_gap_table = False
            continue
        if current_module is None:
            raise ValueError("Encountered gap row before module heading in handoff_map.md.")

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 4:
            raise ValueError(f"Expected 4 cells in handoff_map row, got {len(cells)}: {line}")

        gap_type = clean_cell(cells[0])
        tier = clean_cell(cells[1])
        rust_symbol = clean_cell(cells[2])
        node_export = clean_cell(cells[3])
        if gap_type is None or tier is None:
            raise ValueError(f"Missing required gap fields in row: {line}")

        module_ordinals[current_module] += 1
        ordinal = module_ordinals[current_module]
        gap_id = f"{current_module}-{ordinal:03d}"

        entry: dict[str, Any] = {
            "gap_id": gap_id,
            "owner_module": current_module,
            "ordinal_in_module": ordinal,
            "gap_type": gap_type,
            "tier": tier,
            "rust_symbol": rust_symbol,
            "node_export": node_export,
        }
        rows.append(entry)

    metadata = {
        "handoff_generated_at": generated_at,
        "handoff_declared_total_gaps": declared_total,
    }
    return rows, metadata


def enrich_with_wave_membership(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assign deterministic wave/subwave membership per handoff row."""
    enriched: list[dict[str, Any]] = []

    for row in rows:
        owner_module = row["owner_module"]
        wave = WAVE_BY_MODULE.get(owner_module)
        if wave is None:
            raise ValueError(f"Unexpected owner module in handoff map: {owner_module}")

        item = dict(row)
        item["wave"] = wave
        item["wave_label"] = WAVE_LABELS[wave]

        if owner_module != "aux":
            item["subwave"] = None
            item["subwave_label"] = None
            item["subwave_rule"] = "not_applicable"
        else:
            entry_name = stable_entry_name(item)
            subwave, rule = classify_aux_subwave(entry_name)
            item["subwave"] = subwave
            item["subwave_label"] = AUX_SUBWAVE_LABELS[subwave]
            item["subwave_rule"] = rule

        enriched.append(item)

    return enriched


def validate_baseline(rows: list[dict[str, Any]], declared_total_gaps: int | None) -> dict[str, Any]:
    """Validate expected Phase 0 baseline invariants."""
    module_counts: dict[str, int] = defaultdict(int)
    tier_counts: dict[str, int] = defaultdict(int)
    wave_counts: dict[str, int] = defaultdict(int)
    subwave_counts: dict[str, int] = defaultdict(int)

    for row in rows:
        module_counts[row["owner_module"]] += 1
        tier_counts[row["tier"]] += 1
        wave_counts[row["wave"]] += 1
        if row["subwave"] is not None:
            subwave_counts[row["subwave"]] += 1

    actual_total = len(rows)
    errors: list[str] = []

    if declared_total_gaps is not None and declared_total_gaps != actual_total:
        errors.append(f"Declared handoff total {declared_total_gaps} does not match parsed total {actual_total}.")
    if actual_total != EXPECTED_TOTAL_GAPS:
        errors.append(f"Expected total gaps {EXPECTED_TOTAL_GAPS}, found {actual_total}.")

    for owner_module, expected_count in EXPECTED_MODULE_COUNTS.items():
        actual_count = module_counts.get(owner_module, 0)
        if actual_count != expected_count:
            errors.append(f"Expected {expected_count} gaps for {owner_module}, found {actual_count}.")

    if set(module_counts.keys()) != set(EXPECTED_MODULE_COUNTS.keys()):
        errors.append(f"Unexpected module set: {sorted(module_counts.keys())}")

    locked = not errors
    return {
        "locked": locked,
        "errors": errors,
        "expected_total_gaps": EXPECTED_TOTAL_GAPS,
        "actual_total_gaps": actual_total,
        "expected_module_counts": EXPECTED_MODULE_COUNTS,
        "actual_module_counts": dict(module_counts),
        "tier_counts": dict(tier_counts),
        "wave_counts": dict(wave_counts),
        "subwave_counts": dict(subwave_counts),
    }


def build_manifest_payload(
    rows: list[dict[str, Any]],
    source_path: Path,
    handoff_metadata: dict[str, Any],
    validation: dict[str, Any],
) -> dict[str, Any]:
    """Build final JSON payload."""
    source_bytes = source_path.read_bytes()
    sha256 = hashlib.sha256(source_bytes).hexdigest()

    return {
        "manifest_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source": {
            "handoff_map_path": str(source_path).replace("\\", "/"),
            "handoff_map_sha256": sha256,
            "handoff_generated_at": handoff_metadata.get("handoff_generated_at"),
            "handoff_declared_total_gaps": handoff_metadata.get("handoff_declared_total_gaps"),
        },
        "phase0": {
            "objective": "Lock 315-item Tier-2 baseline and exact wave/subwave membership.",
            "wave_labels": WAVE_LABELS,
            "aux_subwave_labels": AUX_SUBWAVE_LABELS,
        },
        "baseline_validation": validation,
        "gaps": rows,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write stable JSON output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Generate Phase 0 wave/subwave manifest from handoff_map.md.")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Repository root path.",
    )
    parser.add_argument(
        "--handoff-map",
        default="docs/implementation/node_api_parity/phase1/handoff_map.md",
        help="Path to handoff_map.md relative to repo root.",
    )
    parser.add_argument(
        "--output",
        default="docs/implementation/node_api_parity/phase5/tier2_wave_manifest.json",
        help="Output manifest path relative to repo root.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    handoff_map_path = repo_root / args.handoff_map
    output_path = repo_root / args.output

    markdown_text = handoff_map_path.read_text(encoding="utf-8")
    parsed_rows, handoff_metadata = parse_handoff_map(markdown_text)
    enriched_rows = enrich_with_wave_membership(parsed_rows)
    validation = validate_baseline(enriched_rows, handoff_metadata.get("handoff_declared_total_gaps"))

    manifest_payload = build_manifest_payload(enriched_rows, handoff_map_path, handoff_metadata, validation)
    write_json(output_path, manifest_payload)

    print(f"- {output_path}")
    if validation["locked"]:
        print("Phase 0 baseline lock passed (315-item baseline and module counts verified).")
        return 0

    print("Phase 0 baseline lock FAILED:")
    for error in validation["errors"]:
        print(f"- {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
