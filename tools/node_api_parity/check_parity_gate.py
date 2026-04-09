#!/usr/bin/env python3
"""Run the Tier-1 Node parity gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
from typing import Any
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from binding_parity_runtime_coverage import (
    build_coverage_summary,
    load_json_file,
    render_coverage_summary_markdown,
)

from generate_baseline import (
    _effective_rust_symbol,
    generate_diff_report,
    parse_node_surface,
    parse_rust_surface,
    render_diff_markdown,
    write_json,
)


def validate_contract_surface(
    contract: dict[str, Any],
    rust_manifest: dict[str, Any],
    node_manifest: dict[str, Any],
) -> list[str]:
    """Bidirectional contract ↔ surface guard with H1 fail-closed row rejection.

    Walks every ``tier1Mappings`` row and asserts:

    1. The row has a well-formed shape. Malformed rows are REJECTED with
       explicit diagnostics (H1 hardening + Round 2 Fix 1.1):

       - **Empty row** (neither ``rustSymbol`` nor ``nodeExport``) →
         ``"Row '{id}' is empty ..."``.
       - **Missing rustSymbol** (any ``nodeExport`` state) →
         ``"Row '{id}' missing rustSymbol"``.
       - **Non-string rustSymbol** (list / dict / int) →
         ``"Row '{id}' has non-string rustSymbol ..."``.
       - **Empty-string rustSymbol** (``""``) →
         ``"Row '{id}' has empty rustSymbol ..."``.
       - **Non-string nodeExport on a normal-shape row** →
         ``"Row '{id}' has non-string nodeExport ..."``.
       - **Empty-string nodeExport on a normal-shape row** →
         ``"Row '{id}' has empty nodeExport ..."``.
       - **Missing nodeExport on a normal-shape row** (rustSymbol does NOT
         end in ``@rust``) → ``"Row '{id}' is normal-shape but missing
         nodeExport ..."``.

       Only rows whose ``rustSymbol`` ends in ``@rust`` may legitimately
       omit ``nodeExport`` (Phase 3 A7 precedent for proxy rows that cover
       Rust-only symbols without a direct Node binding).

    2. The ``rustSymbol`` exists in the parsed Rust surface. For ``@rust``
       proxy rows the suffix is stripped before lookup. Missing rows produce
       a remediation hint that names the declared ``rustCrate`` (with
       ``<unknown>`` fallback for legacy rows) and suggests the ``pub use``
       statement to add to ``lib.rs``.

    3. The ``nodeExport`` exists in the parsed Node surface. The Node-side
       check is SKIPPED for ``@rust`` proxy rows (they have no Node binding
       by design). Missing rows produce a remediation hint that references
       ``bun run build`` + the ``index.d.ts`` regeneration cadence so the
       most common root cause (stale index.d.ts after a Rust source change,
       or a snake_case typo instead of NAPI's auto-converted camelCase) is
       called out.

    Returns a list of human-readable diagnostic strings. Empty list means
    the contract is well-formed and both surfaces are in sync. A non-empty
    list causes ``main()`` to exit non-zero with the diagnostics printed to
    stderr.
    """
    rust_symbols: set[str] = {
        item["symbol"] for item in rust_manifest.get("symbols", [])
    }
    node_exports: set[str] = {
        item["export"] for item in node_manifest.get("exports", [])
    }
    diagnostics: list[str] = []

    for mapping in contract.get("tier1Mappings", []):
        row_id = mapping.get("id", "<unknown>")
        rust_symbol = mapping.get("rustSymbol")
        node_export = mapping.get("nodeExport")
        rust_crate = mapping.get("rustCrate", "<unknown>")

        # H1 fail-closed: empty row (neither field present).
        if rust_symbol is None and node_export is None:
            diagnostics.append(
                f"Row '{row_id}' is empty (no rustSymbol and no nodeExport)."
            )
            continue

        # H1 fail-closed: missing rustSymbol.
        if rust_symbol is None:
            diagnostics.append(f"Row '{row_id}' missing rustSymbol.")
            continue

        # Round 2 Fix 1.1: non-string rustSymbol (list, dict, int, ...).
        if not isinstance(rust_symbol, str):
            diagnostics.append(
                f"Row '{row_id}' has non-string rustSymbol "
                f"(got {type(rust_symbol).__name__}; expected string)."
            )
            continue

        # Round 2 Fix 1.1: empty-string rustSymbol.
        if rust_symbol == "":
            diagnostics.append(
                f"Row '{row_id}' has empty rustSymbol "
                f"(empty string is not a valid symbol name)."
            )
            continue

        is_proxy = rust_symbol.endswith("@rust")

        # Round 2 Fix 1.1: non-string nodeExport on a normal-shape row.
        if (
            not is_proxy
            and node_export is not None
            and not isinstance(node_export, str)
        ):
            diagnostics.append(
                f"Row '{row_id}' has non-string nodeExport "
                f"(got {type(node_export).__name__}; expected string or None)."
            )
            continue

        # Round 2 Fix 1.1: empty-string nodeExport on a normal-shape row.
        if not is_proxy and node_export == "":
            diagnostics.append(
                f"Row '{row_id}' has empty nodeExport "
                f"(empty string is not a valid export name)."
            )
            continue

        # H1 fail-closed: normal-shape row with missing nodeExport.
        # Only @rust proxy rows are allowed to omit nodeExport.
        if not is_proxy and node_export is None:
            diagnostics.append(
                f"Row '{row_id}' is normal-shape but missing nodeExport "
                f"(only @rust proxy rows may omit nodeExport)."
            )
            continue

        effective_rust_symbol = (
            rust_symbol[: -len("@rust")] if is_proxy else rust_symbol
        )

        # Positive: Rust-side lookup.
        if effective_rust_symbol and effective_rust_symbol not in rust_symbols:
            diagnostics.append(
                f"Row '{row_id}' rustSymbol '{effective_rust_symbol}' not in "
                f"rust surface. Add 'pub use <sub_module>::"
                f"{effective_rust_symbol};' to {rust_crate}/lib.rs."
            )

        # Positive: Node-side lookup (skipped for @rust proxy rows).
        if not is_proxy and node_export and node_export not in node_exports:
            diagnostics.append(
                f"Row '{row_id}' nodeExport '{node_export}' not in node "
                f"surface (index.d.ts). Either the Rust function still uses "
                f"snake_case (NAPI auto-converts to camelCase), or "
                f"'{node_export}' is a typo. Run `bun run build` to refresh "
                f"index.d.ts and confirm the export was generated."
            )

    return diagnostics


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


def sync_baseline_artifacts(
    output_dir: Path, baseline_output_dir: Path, artifact_names: tuple[str, ...]
) -> None:
    """Copy generated artifacts into the checked-in baseline directory."""
    baseline_output_dir.mkdir(parents=True, exist_ok=True)
    for name in artifact_names:
        shutil.copyfile(output_dir / name, baseline_output_dir / name)


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
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Refresh checked-in baseline artifacts from generated outputs before comparing them.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    contract_path = repo_root / args.contract
    output_dir = repo_root / args.output_dir
    baseline_output_dir = repo_root / args.baseline_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    tier1_mappings: list[dict[str, Any]] = contract["tier1Mappings"]
    # Phase 4 Plan 2 fix: @rust-suffix proxy rows intentionally omit
    # `nodeExport` (they represent Rust-only symbols with no Node wrapper).
    # Strip the @rust suffix for the tier1 rust-symbol set (so proxy rows
    # mark their stripped symbol as tier1-mapped in parse_rust_surface()
    # and in the rust_unmapped gap calculation) and skip proxy rows for
    # node-side lookups. The bidirectional guard already validates proxy-row
    # shape via validate_contract_surface().
    tier1_rust_symbols = {
        _effective_rust_symbol(mapping["rustSymbol"]) for mapping in tier1_mappings
    }
    tier1_node_exports = {
        mapping["nodeExport"]
        for mapping in tier1_mappings
        if mapping.get("nodeExport") is not None
    }
    tier1_owner_map = {
        mapping["nodeExport"]: mapping["ownerModule"]
        for mapping in tier1_mappings
        if mapping.get("nodeExport") is not None
    }

    rust_manifest = parse_rust_surface(repo_root, tier1_rust_symbols)
    node_manifest = parse_node_surface(
        repo_root,
        tier1_node_exports=tier1_node_exports,
        tier1_owner_map=tier1_owner_map,
        index_dts_rel=args.index_dts,
    )

    # Phase 4 Plan 1 Task 2: bidirectional guard with H1 fail-closed
    # malformed-row rejection. Runs unconditionally before downstream diff
    # generation so a missing `pub use`, a stale `index.d.ts`, or a
    # malformed row shape is surfaced with an actionable remediation
    # message instead of being buried as `missing_rust`/`missing_node`
    # drift noise later. See docstring on `validate_contract_surface()`
    # for the full list of rejected shapes.
    guard_diagnostics = validate_contract_surface(
        contract, rust_manifest, node_manifest
    )
    if guard_diagnostics:
        print(
            "validate_contract_surface() found contract<->surface drift:",
            file=sys.stderr,
        )
        for message in guard_diagnostics:
            print(f"  - {message}", file=sys.stderr)
        return 2

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

    tracked_artifact_names = (
        "parity_diff_report.json",
        "parity_diff_report.md",
        "runtime_coverage_summary.json",
        "runtime_coverage_summary.md",
    )

    if args.update_baseline:
        sync_baseline_artifacts(output_dir, baseline_output_dir, tracked_artifact_names)

    stale_artifacts = [
        name
        for name in tracked_artifact_names
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
