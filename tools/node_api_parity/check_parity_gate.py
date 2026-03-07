#!/usr/bin/env python3
"""Run the Tier-1 Node parity gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from binding_parity_runtime_coverage import (
    build_coverage_summary,
    load_json_file,
    render_coverage_summary_markdown,
)

from generate_baseline import (
    generate_diff_report,
    parse_node_surface,
    parse_rust_surface,
    render_diff_markdown,
    write_json,
)


def render_tier1_gate_markdown(diff_report: dict[str, Any]) -> str:
    """Render a concise Tier-1 gate report for CI diagnostics."""
    summary = diff_report["summary"]
    failing_rows = [
        row for row in diff_report["contract_results"] if row["status"] != "matched"
    ]

    lines: list[str] = []
    lines.extend(
        (
            "# Tier-1 Parity Gate Report",
            "",
            f"- Tier-1 contract rows: **{summary['tier1_contract_total']}**",
            f"- Tier-1 matched: **{summary['tier1_matched']}**",
            f"- Tier-1 missing Rust: **{summary['tier1_missing_rust']}**",
            f"- Tier-1 missing Node: **{summary['tier1_missing_node']}**",
            f"- Tier-1 signature mismatch: **{summary['tier1_signature_mismatch']}**",
            "",
        )
    )

    if not failing_rows:
        lines.extend(("## Result", "", "Tier-1 gate passed.", ""))
        return "\n".join(lines)

    lines.extend(
        (
            "## Result",
            "",
            "Tier-1 drift detected. Review failing contract rows below.",
            "",
            "| ID | Owner Module | Rust Symbol | Node Export | Status | Reason |",
            "|---|---|---|---|---|---|",
        )
    )
    for row in failing_rows:
        lines.append(
            "| `{id}` | `{owner_module}` | `{rust_symbol}` | `{node_export}` | `{status}` | {reason} |".format(
                id=row["id"],
                owner_module=row["owner_module"],
                rust_symbol=row["rust_symbol"],
                node_export=row["node_export"],
                status=row["status"],
                reason=row.get("reason", "-"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def artifacts_match(expected: Path, actual: Path) -> bool:
    """Return whether two artifact files have identical content."""
    if not expected.exists() or not actual.exists():
        return False
    if expected.suffix == ".json":
        expected_payload = json.loads(expected.read_text(encoding="utf-8"))
        actual_payload = json.loads(actual.read_text(encoding="utf-8"))
        expected_payload.pop("generated_at_utc", None)
        actual_payload.pop("generated_at_utc", None)
        return expected_payload == actual_payload

    expected_lines = [
        line
        for line in expected.read_text(encoding="utf-8").splitlines()
        if not line.startswith("- Generated:")
    ]
    actual_lines = [
        line
        for line in actual.read_text(encoding="utf-8").splitlines()
        if not line.startswith("- Generated:")
    ]
    return expected_lines == actual_lines


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Run Tier-1 parity gate for classic-node."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Repository root path.",
    )
    parser.add_argument(
        "--contract",
        default="docs/implementation/node_api_parity/baseline/parity_contract.json",
        help="Path to parity contract JSON, relative to repo root.",
    )
    parser.add_argument(
        "--index-dts",
        default="ClassicLib-rs/node-bindings/classic-node/index.d.ts",
        help="Path to Node index.d.ts, relative to repo root.",
    )
    parser.add_argument(
        "--output-dir",
        default="ClassicLib-rs/node-bindings/classic-node/parity-artifacts",
        help="Directory for generated gate artifacts, relative to repo root.",
    )
    parser.add_argument(
        "--runtime-registry",
        default="ClassicLib-rs/node-bindings/classic-node/__test__/fixtures/runtime_coverage_registry.json",
        help="Path to the Node runtime coverage registry JSON, relative to repo root.",
    )
    parser.add_argument(
        "--deferred-registry",
        default="docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json",
        help="Path to the Node deferred backlog registry JSON, relative to repo root.",
    )
    parser.add_argument(
        "--baseline-output-dir",
        default="docs/implementation/node_api_parity/baseline",
        help="Directory containing checked-in baseline artifacts, relative to repo root.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    contract_path = repo_root / args.contract
    output_dir = repo_root / args.output_dir
    baseline_output_dir = repo_root / args.baseline_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    tier1_mappings: list[dict[str, Any]] = contract["tier1Mappings"]
    tier1_rust_symbols = {mapping["rustSymbol"] for mapping in tier1_mappings}
    tier1_node_exports = {mapping["nodeExport"] for mapping in tier1_mappings}
    tier1_owner_map = {
        mapping["nodeExport"]: mapping["ownerModule"] for mapping in tier1_mappings
    }

    rust_manifest = parse_rust_surface(repo_root, tier1_rust_symbols)
    node_manifest = parse_node_surface(
        repo_root,
        tier1_node_exports=tier1_node_exports,
        tier1_owner_map=tier1_owner_map,
        index_dts_rel=args.index_dts,
    )
    diff_report = generate_diff_report(contract, rust_manifest, node_manifest)
    runtime_registry = load_json_file(repo_root / args.runtime_registry)
    deferred_registry = load_json_file(repo_root / args.deferred_registry)
    coverage_summary = build_coverage_summary(
        binding="node",
        contract=contract,
        diff_report=diff_report,
        runtime_registry=runtime_registry,
        deferred_registry=deferred_registry,
        source_paths={
            "contract": args.contract,
            "runtime_registry": args.runtime_registry,
            "deferred_registry": args.deferred_registry,
            "index_dts": args.index_dts,
        },
    )

    write_json(output_dir / "rust_api_surface.json", rust_manifest)
    write_json(output_dir / "node_api_surface.json", node_manifest)
    write_json(output_dir / "parity_diff_report.json", diff_report)
    (output_dir / "parity_diff_report.md").write_text(
        render_diff_markdown(diff_report), encoding="utf-8"
    )
    write_json(output_dir / "runtime_coverage_summary.json", coverage_summary)
    (output_dir / "runtime_coverage_summary.md").write_text(
        render_coverage_summary_markdown(coverage_summary), encoding="utf-8"
    )
    (output_dir / "tier1_gate_report.md").write_text(
        render_tier1_gate_markdown(diff_report), encoding="utf-8"
    )

    summary = diff_report["summary"]
    tier1_drift_count = (
        summary["tier1_missing_rust"]
        + summary["tier1_missing_node"]
        + summary["tier1_signature_mismatch"]
    )
    coverage_totals = coverage_summary["summary"]

    stale_artifacts = [
        name
        for name in (
            "parity_diff_report.json",
            "parity_diff_report.md",
            "runtime_coverage_summary.json",
            "runtime_coverage_summary.md",
        )
        if not artifacts_match(baseline_output_dir / name, output_dir / name)
    ]

    print("Phase 2 parity gate artifacts generated:")
    print(f"- {output_dir / 'rust_api_surface.json'}")
    print(f"- {output_dir / 'node_api_surface.json'}")
    print(f"- {output_dir / 'parity_diff_report.json'}")
    print(f"- {output_dir / 'parity_diff_report.md'}")
    print(f"- {output_dir / 'runtime_coverage_summary.json'}")
    print(f"- {output_dir / 'runtime_coverage_summary.md'}")
    print(f"- {output_dir / 'tier1_gate_report.md'}")

    if tier1_drift_count > 0:
        print(
            "Tier-1 parity drift detected: "
            f"missing_rust={summary['tier1_missing_rust']}, "
            f"missing_node={summary['tier1_missing_node']}, "
            f"signature_mismatch={summary['tier1_signature_mismatch']}"
        )
        return 1

    if coverage_totals["tier1_missing_runtime_total"] > 0:
        print(
            "Tier-1 runtime coverage metadata missing for "
            f"{coverage_totals['tier1_missing_runtime_total']} contract row(s)."
        )
        return 1

    if coverage_totals["registry_mismatch_total"] > 0:
        print(
            "Node runtime coverage registry snapshot mismatch detected for "
            f"{coverage_totals['registry_mismatch_total']} selector row(s)."
        )
        return 1

    if coverage_totals["newly_uncovered_total"] > 0:
        print(
            "Newly uncovered Node surfaces detected: "
            f"{coverage_totals['newly_uncovered_total']}"
        )
        return 1

    if stale_artifacts:
        print(
            "Checked-in Node parity artifacts are stale: " + ", ".join(stale_artifacts)
        )
        return 1

    print("Tier-1 parity gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
