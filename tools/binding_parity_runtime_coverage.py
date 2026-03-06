#!/usr/bin/env python3
"""Shared helpers for binding runtime coverage summaries and gates."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


VALID_CLASSIFICATIONS = {
    "runtime_verified",
    "contract_mapped",
    "deferred",
    "newly_uncovered",
}


def load_json_file(path: Path) -> dict[str, Any]:
    """Load a JSON file or return an empty registry shape when absent."""
    if not path.exists():
        return {"entries": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _binding_identifier(binding: str, row: dict[str, Any]) -> str | None:
    if binding == "node":
        return row.get("node_export")

    module_name = row.get("python_module")
    export_path = row.get("python_export_path") or row.get("python_export")
    if module_name and export_path:
        return f"{module_name}.{export_path}"
    return export_path


def _lookup_maps(
    entries: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    contract_lookup: dict[str, dict[str, Any]] = {}
    identifier_lookup: dict[str, dict[str, Any]] = {}

    for entry in entries:
        for contract_id in entry.get("contractIds", []):
            contract_lookup[contract_id] = entry
        for binding_identifier in entry.get("bindingIdentifiers", []):
            identifier_lookup[binding_identifier] = entry
        for rust_symbol in entry.get("rustSymbols", []):
            identifier_lookup[f"rust:{rust_symbol}"] = entry

    return contract_lookup, identifier_lookup


def _stable_id_hash(values: list[str]) -> str:
    joined = "\n".join(sorted(values))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _selector_matches(selector: dict[str, Any], contract_row: dict[str, Any]) -> bool:
    key_map = {
        "ownerModule": "owner_module",
        "tier": "tier",
    }
    for key, expected in selector.items():
        if contract_row.get(key_map.get(key, key)) != expected:
            return False
    return True


def expand_contract_selectors(
    entries: list[dict[str, Any]], contract_results: list[dict[str, Any]]
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Expand selector-based registry entries into contract-id lookups."""
    explicit_lookup, _ = _lookup_maps(entries)
    mismatches: list[dict[str, Any]] = []

    for entry in entries:
        selector = entry.get("contractSelector")
        if not selector:
            continue

        matched_rows = [
            row for row in contract_results if _selector_matches(selector, row)
        ]
        matched_ids = [row["id"] for row in matched_rows]
        expected_count = entry.get("contractCount")
        expected_hash = entry.get("contractIdsHash")
        actual_hash = _stable_id_hash(matched_ids)

        if expected_count != len(matched_ids) or expected_hash != actual_hash:
            mismatches.append(
                {
                    "coverageId": entry.get("coverageId"),
                    "expectedCount": expected_count,
                    "actualCount": len(matched_ids),
                    "expectedHash": expected_hash,
                    "actualHash": actual_hash,
                }
            )
            continue

        for contract_id in matched_ids:
            explicit_lookup[contract_id] = entry

    return explicit_lookup, mismatches


def _surface_row_from_contract(
    binding: str,
    contract_lookup: dict[str, dict[str, Any]],
    contract_row: dict[str, Any],
) -> dict[str, Any]:
    contract_id = contract_row["id"]
    registry_entry = contract_lookup.get(contract_id)
    classification = "contract_mapped"
    if registry_entry is not None:
        classification = registry_entry["classification"]

    item = {
        "trackedId": f"contract:{contract_id}",
        "trackedType": "contract_row",
        "contractId": contract_id,
        "ownerModule": contract_row["owner_module"],
        "tier": contract_row["tier"],
        "status": contract_row["status"],
        "classification": classification,
        "rustSymbol": contract_row.get("rust_symbol"),
        "bindingIdentifier": _binding_identifier(binding, contract_row),
    }
    if registry_entry is not None:
        item.update(
            {
                "coverageId": registry_entry.get("coverageId"),
                "verificationMode": registry_entry.get("verificationMode"),
                "testSuite": registry_entry.get("testSuite"),
                "testCaseId": registry_entry.get("testCaseId"),
                "fixtureRefs": registry_entry.get("fixtureRefs", []),
                "notes": registry_entry.get("notes"),
            }
        )
    return item


def _surface_row_from_gap(
    binding: str,
    identifier_lookup: dict[str, dict[str, Any]],
    gap_row: dict[str, Any],
) -> dict[str, Any]:
    binding_identifier = _binding_identifier(binding, gap_row)
    rust_symbol = gap_row.get("rust_symbol")

    registry_entry = None
    if binding_identifier is not None:
        registry_entry = identifier_lookup.get(binding_identifier)
    if registry_entry is None and rust_symbol is not None:
        registry_entry = identifier_lookup.get(f"rust:{rust_symbol}")

    classification = "newly_uncovered"
    if registry_entry is not None:
        classification = registry_entry["classification"]

    tracked_key = binding_identifier or f"rust:{rust_symbol}"
    item = {
        "trackedId": f"binding:{tracked_key}",
        "trackedType": "gap",
        "ownerModule": gap_row["owner_module"],
        "tier": gap_row["tier"],
        "gapType": gap_row.get("gap_type"),
        "classification": classification,
        "rustSymbol": rust_symbol,
        "bindingIdentifier": binding_identifier,
    }
    if registry_entry is not None:
        item.update(
            {
                "coverageId": registry_entry.get("coverageId"),
                "verificationMode": registry_entry.get("verificationMode"),
                "testSuite": registry_entry.get("testSuite"),
                "testCaseId": registry_entry.get("testCaseId"),
                "fixtureRefs": registry_entry.get("fixtureRefs", []),
                "wave": registry_entry.get("wave"),
                "owner": registry_entry.get("owner"),
                "deferReason": registry_entry.get("deferReason"),
                "notes": registry_entry.get("notes"),
            }
        )
    return item


def build_coverage_summary(
    *,
    binding: str,
    contract: dict[str, Any],
    diff_report: dict[str, Any],
    runtime_registry: dict[str, Any],
    deferred_registry: dict[str, Any],
    source_paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a machine-readable coverage summary from parity artifacts."""
    runtime_entries = runtime_registry.get("entries", [])
    deferred_entries = deferred_registry.get("entries", [])

    invalid_entries = [
        entry.get("coverageId", "unknown")
        for entry in [*runtime_entries, *deferred_entries]
        if entry.get("classification") not in VALID_CLASSIFICATIONS
    ]
    if invalid_entries:
        raise ValueError(
            "Unsupported coverage classification(s): " + ", ".join(invalid_entries)
        )

    contract_lookup, registry_mismatches = expand_contract_selectors(
        runtime_entries, diff_report.get("contract_results", [])
    )
    _, deferred_lookup = _lookup_maps(deferred_entries)
    _, runtime_identifier_lookup = _lookup_maps(runtime_entries)

    tracked_surface: list[dict[str, Any]] = []
    for contract_row in diff_report.get("contract_results", []):
        tracked_surface.append(
            _surface_row_from_contract(binding, contract_lookup, contract_row)
        )

    for gap_row in diff_report.get("gaps", []):
        runtime_or_deferred_lookup = dict(deferred_lookup)
        runtime_or_deferred_lookup.update(runtime_identifier_lookup)
        tracked_surface.append(
            _surface_row_from_gap(binding, runtime_or_deferred_lookup, gap_row)
        )

    per_owner_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    classification_counts: dict[str, int] = defaultdict(int)
    tier1_missing_runtime_total = 0

    for item in tracked_surface:
        owner_module = item["ownerModule"]
        classification = item["classification"]
        classification_counts[classification] += 1
        per_owner_counts[owner_module][classification] += 1
        per_owner_counts[owner_module]["total"] += 1

        if item["trackedType"] == "contract_row" and item["tier"] == "tier1":
            if classification != "runtime_verified":
                tier1_missing_runtime_total += 1

    summary = {
        "tracked_surface_total": len(tracked_surface),
        "runtime_verified_total": classification_counts.get("runtime_verified", 0),
        "contract_mapped_total": classification_counts.get("contract_mapped", 0),
        "deferred_total": classification_counts.get("deferred", 0),
        "newly_uncovered_total": classification_counts.get("newly_uncovered", 0),
        "tier1_contract_total": len(contract.get("tier1Mappings", [])),
        "tier1_missing_runtime_total": tier1_missing_runtime_total,
        "registry_mismatch_total": len(registry_mismatches),
    }

    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "binding": binding,
        "sources": source_paths or {},
        "summary": summary,
        "registryMismatches": registry_mismatches,
        "perOwnerModule": {
            owner: dict(counts) for owner, counts in sorted(per_owner_counts.items())
        },
        "trackedSurface": tracked_surface,
    }


def render_coverage_summary_markdown(summary_payload: dict[str, Any]) -> str:
    """Render a concise markdown summary for runtime coverage."""
    summary = summary_payload["summary"]
    lines = [
        f"# {summary_payload['binding'].title()} Runtime Coverage Summary",
        "",
        f"- Generated: `{summary_payload['generated_at_utc']}`",
        f"- Tracked surfaces: **{summary['tracked_surface_total']}**",
        f"- Runtime verified: **{summary['runtime_verified_total']}**",
        f"- Contract mapped only: **{summary['contract_mapped_total']}**",
        f"- Deferred: **{summary['deferred_total']}**",
        f"- Newly uncovered: **{summary['newly_uncovered_total']}**",
        f"- Tier-1 rows missing runtime metadata: **{summary['tier1_missing_runtime_total']}**",
        "",
        "## Per-owner totals",
        "",
        "| Owner Module | Runtime Verified | Contract Mapped | Deferred | Newly Uncovered | Total |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for owner_module, counts in summary_payload["perOwnerModule"].items():
        lines.append(
            "| `{owner}` | {runtime_verified} | {contract_mapped} | {deferred} | {newly_uncovered} | {total} |".format(
                owner=owner_module,
                runtime_verified=counts.get("runtime_verified", 0),
                contract_mapped=counts.get("contract_mapped", 0),
                deferred=counts.get("deferred", 0),
                newly_uncovered=counts.get("newly_uncovered", 0),
                total=counts.get("total", 0),
            )
        )

    lines.extend(
        (
            "",
            "Detailed tracked-surface diagnostics are in the JSON summary artifact.",
            "",
        )
    )
    return "\n".join(lines)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
