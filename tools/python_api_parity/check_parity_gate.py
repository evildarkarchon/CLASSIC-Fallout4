#!/usr/bin/env python3
"""Run the Tier-1 Python parity gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from generate_baseline import (
    generate_diff_report,
    parse_python_surface,
    parse_rust_surface,
    render_diff_markdown,
    write_json,
)


def render_tier1_gate_markdown(diff_report: dict[str, Any]) -> str:
    """Render concise Tier-1 gate report for CI diagnostics."""
    summary = diff_report["summary"]
    failing_rows = [
        row for row in diff_report["contract_results"] if row["status"] != "matched"
    ]

    lines: list[str] = []
    lines.extend(
        (
            "# Tier-1 Python Parity Gate Report",
            "",
            f"- Tier-1 contract rows: **{summary['tier1_contract_total']}**",
            f"- Tier-1 matched: **{summary['tier1_matched']}**",
            f"- Tier-1 missing Rust: **{summary['tier1_missing_rust']}**",
            f"- Tier-1 missing Python: **{summary['tier1_missing_python']}**",
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
            "| ID | Owner Module | Rust Symbol | Python Export | Status | Reason |",
            "|---|---|---|---|---|---|",
        )
    )
    for row in failing_rows:
        lines.append(
            "| `{id}` | `{owner_module}` | `{rust_symbol}` | `{python_module}.{python_export}` | `{status}` | {reason} |".format(
                id=row["id"],
                owner_module=row["owner_module"],
                rust_symbol=row["rust_symbol"],
                python_module=row["python_module"],
                python_export=row["python_export"],
                status=row["status"],
                reason=row.get("reason", "-"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Run Tier-1 parity gate for Python bindings."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Repository root path.",
    )
    parser.add_argument(
        "--contract",
        default="docs/implementation/python_api_parity/baseline/parity_contract.json",
        help="Path to parity contract JSON, relative to repo root.",
    )
    parser.add_argument(
        "--output-dir",
        default="ClassicLib-rs/python-bindings/parity-artifacts",
        help="Directory for generated gate artifacts, relative to repo root.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    contract_path = repo_root / args.contract
    output_dir = repo_root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    tier1_mappings: list[dict[str, Any]] = contract["tier1Mappings"]
    tier1_rust_symbols = {mapping["rustSymbol"] for mapping in tier1_mappings}
    tier1_python_exports = {mapping["pythonExport"] for mapping in tier1_mappings}

    rust_manifest = parse_rust_surface(repo_root, tier1_rust_symbols)
    python_manifest = parse_python_surface(repo_root, tier1_python_exports)
    diff_report = generate_diff_report(contract, rust_manifest, python_manifest)

    write_json(output_dir / "rust_api_surface.json", rust_manifest)
    write_json(output_dir / "python_api_surface.json", python_manifest)
    write_json(output_dir / "parity_diff_report.json", diff_report)
    (output_dir / "parity_diff_report.md").write_text(
        render_diff_markdown(diff_report), encoding="utf-8"
    )
    (output_dir / "tier1_gate_report.md").write_text(
        render_tier1_gate_markdown(diff_report), encoding="utf-8"
    )

    summary = diff_report["summary"]
    tier1_drift_count = (
        summary["tier1_missing_rust"]
        + summary["tier1_missing_python"]
        + summary["tier1_signature_mismatch"]
    )

    print("Python parity gate artifacts generated:")
    print(f"- {output_dir / 'rust_api_surface.json'}")
    print(f"- {output_dir / 'python_api_surface.json'}")
    print(f"- {output_dir / 'parity_diff_report.json'}")
    print(f"- {output_dir / 'parity_diff_report.md'}")
    print(f"- {output_dir / 'tier1_gate_report.md'}")

    if tier1_drift_count > 0:
        print(
            "Tier-1 parity drift detected: "
            f"missing_rust={summary['tier1_missing_rust']}, "
            f"missing_python={summary['tier1_missing_python']}, "
            f"signature_mismatch={summary['tier1_signature_mismatch']}"
        )
        return 1

    print("Tier-1 parity gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
