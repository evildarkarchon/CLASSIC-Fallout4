#!/usr/bin/env python3
"""Run the CXX parity gate.

CLI surface (locked by CONTEXT.md D-12):
    --repo-root             Repo root (default: parents[2])
    --contract              Path to parity_contract.json (default: docs/.../baseline/parity_contract.json)
    --output-dir            Ephemeral artifacts dir (default: ClassicLib-rs/.../parity-artifacts)
    --baseline-output-dir   Committed artifacts dir (default: docs/.../baseline)
    --update-baseline       Refresh committed artifacts from output_dir before stale check

There is INTENTIONALLY no --deferred-registry argument (CXXG-04 / D-12).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_baseline import (  # noqa: E402
    generate_diff_report,
    parse_cxx_bridge_surface,
    render_diff_markdown,
    write_json,
)


TRACKED_ARTIFACT_NAMES: tuple[str, ...] = (
    "parity_contract.json",
    "rust_api_surface.json",
    "cxx_diff_report.json",
    "cxx_diff_report.md",
    "cxx_gate_report.md",
)


def render_cxx_gate_markdown(diff_report: dict[str, Any]) -> str:
    """Concise gate report markdown. No Tier-1/Tier-2 language (D-04)."""
    summary = diff_report["summary"]
    drift_count = (
        summary["missing_from_current"]
        + summary["missing_from_contract"]
        + summary["signature_mismatch"]
    )
    lines: list[str] = [
        "# CXX Parity Gate Report",
        "",
        f"- Contract rows: **{summary['contract_total']}**",
        f"- Current rows: **{summary['current_total']}**",
        f"- Matched: **{summary['matched']}**",
        f"- Missing from current: **{summary['missing_from_current']}**",
        f"- Missing from contract: **{summary['missing_from_contract']}**",
        f"- Signature mismatch: **{summary['signature_mismatch']}**",
        "",
    ]
    if drift_count == 0:
        lines.extend(("## Result", "", "CXX parity gate passed.", ""))
        return "\n".join(lines)

    failing = [r for r in diff_report["contract_results"] if r["status"] != "matched"]
    new_entries = diff_report.get("new_entries", [])
    lines.extend(("## Result", "", "Drift detected. Review failing rows below.", ""))
    if failing:
        lines.extend((
            "| ID | Bridge Module | Rust Symbol | Kind | Status | Reason |",
            "|---|---|---|---|---|---|",
        ))
        for row in failing:
            lines.append(
                f"| `{row['id']}` | `{row['bridgeModule']}` | `{row['rustSymbol']}` | "
                f"`{row['kind']}` | `{row['status']}` | {row['reason']} |"
            )
        lines.append("")
    if new_entries:
        lines.extend((
            "## New Entries Not in Baseline",
            "",
            "| ID | Bridge Module | Rust Symbol | Kind |",
            "|---|---|---|---|",
        ))
        for row in new_entries:
            lines.append(
                f"| `{row['id']}` | `{row['bridgeModule']}` | "
                f"`{row['rustSymbol']}` | `{row['kind']}` |"
            )
        lines.append("")
    return "\n".join(lines)


def artifacts_match(expected: Path, actual: Path) -> bool:
    """True iff both files exist and have identical content.

    JSON: pop generated_at_utc before comparing.
    Markdown: skip '- Generated:' lines before comparing.
    """
    if not expected.exists() or not actual.exists():
        return False
    if expected.suffix == ".json":
        expected_payload = json.loads(expected.read_text(encoding="utf-8"))
        actual_payload = json.loads(actual.read_text(encoding="utf-8"))
        expected_payload.pop("generated_at_utc", None)
        actual_payload.pop("generated_at_utc", None)
        return expected_payload == actual_payload
    expected_lines = [
        l for l in expected.read_text(encoding="utf-8").splitlines()
        if not l.startswith("- Generated:")
    ]
    actual_lines = [
        l for l in actual.read_text(encoding="utf-8").splitlines()
        if not l.startswith("- Generated:")
    ]
    return expected_lines == actual_lines


def sync_baseline_artifacts(
    output_dir: Path,
    baseline_output_dir: Path,
    artifact_names: tuple[str, ...],
) -> None:
    """Copy generated artifacts into the checked-in baseline directory."""
    baseline_output_dir.mkdir(parents=True, exist_ok=True)
    for name in artifact_names:
        src = output_dir / name
        if not src.exists():
            continue
        shutil.copyfile(src, baseline_output_dir / name)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the CXX bridge parity gate."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Repository root path.",
    )
    parser.add_argument(
        "--contract",
        default="docs/implementation/cxx_api_parity/baseline/parity_contract.json",
        help="Path to parity contract JSON, relative to repo root.",
    )
    parser.add_argument(
        "--output-dir",
        default="ClassicLib-rs/cpp-bindings/classic-cpp-bridge/parity-artifacts",
        help="Directory for generated gate artifacts, relative to repo root.",
    )
    parser.add_argument(
        "--baseline-output-dir",
        default="docs/implementation/cxx_api_parity/baseline",
        help="Directory containing checked-in baseline artifacts, relative to repo root.",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Refresh checked-in baseline artifacts from generated outputs.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    contract_path = repo_root / args.contract
    output_dir = repo_root / args.output_dir
    baseline_output_dir = repo_root / args.baseline_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if not contract_path.exists():
        print(
            f"CXX parity gate: contract file not found at {contract_path}. "
            f"Run `python tools/cxx_api_parity/generate_baseline.py --repo-root . "
            f"--write-baseline` to bootstrap.",
            file=sys.stderr,
        )
        return 1

    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    # Fresh surface scan
    current_surface = parse_cxx_bridge_surface(repo_root)
    diff_report = generate_diff_report(contract, current_surface)

    # Write ephemeral artifacts
    write_json(output_dir / "rust_api_surface.json", current_surface)
    write_json(output_dir / "cxx_diff_report.json", diff_report)
    (output_dir / "cxx_diff_report.md").write_text(
        render_diff_markdown(diff_report) + "\n", encoding="utf-8",
    )
    (output_dir / "cxx_gate_report.md").write_text(
        render_cxx_gate_markdown(diff_report) + "\n", encoding="utf-8",
    )
    # Copy the current contract into output_dir so sync_baseline_artifacts()
    # can mirror it back during --update-baseline. When the gate runs in
    # normal mode this is still the committed contract (no-op copy).
    write_json(output_dir / "parity_contract.json", contract)

    if args.update_baseline:
        sync_baseline_artifacts(
            output_dir, baseline_output_dir, TRACKED_ARTIFACT_NAMES
        )

    summary = diff_report["summary"]
    drift_count = (
        summary["missing_from_current"]
        + summary["missing_from_contract"]
        + summary["signature_mismatch"]
    )

    print("CXX parity gate artifacts generated:")
    for name in (
        "rust_api_surface.json",
        "cxx_diff_report.json",
        "cxx_diff_report.md",
        "cxx_gate_report.md",
    ):
        print(f"- {output_dir / name}")

    if drift_count > 0:
        print(
            f"CXX parity drift detected: "
            f"missing_from_current={summary['missing_from_current']}, "
            f"missing_from_contract={summary['missing_from_contract']}, "
            f"signature_mismatch={summary['signature_mismatch']}",
            file=sys.stderr,
        )
        return 1

    stale_artifacts = [
        name
        for name in TRACKED_ARTIFACT_NAMES
        if not artifacts_match(baseline_output_dir / name, output_dir / name)
    ]
    if stale_artifacts:
        print(
            "Checked-in CXX parity artifacts are stale: "
            + ", ".join(stale_artifacts)
            + ". Run with --update-baseline to refresh.",
            file=sys.stderr,
        )
        return 1

    print("CXX parity gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
