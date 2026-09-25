#!/usr/bin/env python3
"""Run the Tier-1 Node parity gate."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from generate_baseline import (
    _effective_rust_symbol,
    generate_diff_report,
    parse_node_surface,
    parse_rust_surface,
    render_diff_markdown,
    write_json,
)
from parity_artifact_io import (
    artifacts_match,
    preserve_baseline_generated_at_all,
    sync_baseline_artifacts,
)
from resolve_node_rust_symbols import (
    Resolution,
    resolve_all,
    source_backed_crate,
    source_backed_symbol,
)


def validate_contract_surface(
        contract: dict[str, Any],
        rust_manifest: dict[str, Any],
        node_manifest: dict[str, Any],
        wrapper_resolutions: dict[str, Resolution] | None = None,
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

    2. The ``rustSymbol`` exists in the declared ``rustCrate`` on the parsed
       Rust surface. For ``@rust`` proxy rows the suffix is stripped before
       lookup. Mapped rows without a crate are rejected; missing symbols
       produce a crate-specific ``pub use`` remediation hint.

    3. The ``nodeExport`` exists in the parsed Node surface. The Node-side
       check is SKIPPED for ``@rust`` proxy rows (they have no Node binding
       by design). Missing rows produce a remediation hint that references
       ``bun run build`` + the ``index.d.ts`` regeneration cadence so the
       most common root cause (stale index.d.ts after a Rust source change,
       or a snake_case typo instead of NAPI's auto-converted camelCase) is
       called out.

    4. When the Node wrapper directly identifies its Rust crate, the row's
       ``rustCrate`` agrees with that source evidence even if another crate
       exports the same-named symbol. A single-row export with direct symbol
       evidence must also claim that exact symbol.

    Returns a list of human-readable diagnostic strings. Empty list means
    the contract is well-formed and both surfaces are in sync. A non-empty
    list causes ``main()`` to exit non-zero with the diagnostics printed to
    stderr.
    """
    # The crate belongs in the key: a namesake in another crate is not proof
    # that this row still points to the core capability its wrapper uses.
    rust_symbols: set[tuple[str | None, str]] = {
        (item.get("crate"), item["symbol"])
        for item in rust_manifest.get("symbols", [])
    }
    # Symbols whose ONLY appearance in the Rust surface is as a module. A name
    # that is both a module and a type in the same crate stays acceptable,
    # since the row may legitimately mean the type.
    # `kind` is read defensively: a manifest entry without one carries no
    # evidence that the symbol is a module, so it must not be flagged.
    rust_symbol_kinds: dict[tuple[str | None, str], set[str]] = {}
    for item in rust_manifest.get("symbols", []):
        kind = item.get("kind")
        if kind is not None:
            key = (item.get("crate"), item["symbol"])
            rust_symbol_kinds.setdefault(key, set()).add(kind)
    rust_module_only_symbols: set[tuple[str | None, str]] = {
        key for key, kinds in rust_symbol_kinds.items() if kinds == {"module"}
    }
    node_exports: set[str] = {
        item["export"] for item in node_manifest.get("exports", [])
    }
    mapped_export_counts = Counter(
        mapping.get("nodeExport")
        for mapping in contract.get("tier1Mappings", [])
        if isinstance(mapping.get("rustSymbol"), str)
        and isinstance(mapping.get("nodeExport"), str)
    )
    diagnostics: list[str] = []

    for mapping in contract.get("tier1Mappings", []):
        row_id = mapping.get("id", "<unknown>")
        rust_symbol = mapping.get("rustSymbol")
        node_export = mapping.get("nodeExport")
        rust_crate = mapping.get("rustCrate")

        # H1 fail-closed: empty row (neither field present).
        if rust_symbol is None and node_export is None:
            diagnostics.append(
                f"Row '{row_id}' is empty (no rustSymbol and no nodeExport)."
            )
            continue

        # A row may declare that no verified Rust counterpart is known, but
        # only explicitly. `rustSymbol: null` plus an `unmappedReason` records
        # the export as tracked-but-unmapped debt; it is counted in the diff
        # report's tier1_unmapped total rather than being silently treated as a
        # match. Without a reason a null rustSymbol is still a malformed row.
        if rust_symbol is None and mapping.get("unmappedReason"):
            if node_export is None:
                diagnostics.append(
                    f"Row '{row_id}' is unmapped but has no nodeExport; an "
                    f"unmapped row must still name the binding surface it tracks."
                )
            # Unmapped means "no verified *Rust* counterpart", not "unchecked".
            # The row still names a Node export, and that export is exactly the
            # binding surface this gate exists to protect, so it must still be
            # present in index.d.ts. Skipping this check let a renamed or
            # deleted export hide inside the tier1_unmapped total instead of
            # being reported as drift.
            elif node_export not in node_exports:
                diagnostics.append(
                    f"Row '{row_id}' is unmapped but its nodeExport "
                    f"'{node_export}' is not in the node surface (index.d.ts). "
                    f"An unmapped row still tracks a real binding surface: "
                    f"either restore the export, update the row to the new "
                    f"name, or delete the row if the export is intentionally "
                    f"gone."
                )
            continue

        # H1 fail-closed: missing rustSymbol.
        if rust_symbol is None:
            diagnostics.append(
                f"Row '{row_id}' missing rustSymbol. If this export genuinely "
                f"has no verified Rust counterpart, set rustSymbol to null and "
                f"add an 'unmappedReason' explaining why."
            )
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
        valid_rust_crate = isinstance(rust_crate, str) and bool(rust_crate.strip())
        if not valid_rust_crate:
            diagnostics.append(
                f"Row '{row_id}' has no valid rustCrate (<unknown>); a mapped "
                f"Rust symbol must name its owning crate."
            )

        # Positive: Rust-side lookup.
        rust_key = (rust_crate, effective_rust_symbol) if valid_rust_crate else None
        if rust_key is not None and effective_rust_symbol and rust_key not in rust_symbols:
            diagnostics.append(
                f"Row '{row_id}' rustSymbol '{effective_rust_symbol}' not in "
                f"rust surface for crate '{rust_crate}'. Add 'pub use <sub_module>::"
                f"{effective_rust_symbol};' to {rust_crate}/lib.rs."
            )

        # Direct wrapper evidence can disambiguate two crates that both still
        # export the same name. We only enforce source-backed resolver tiers;
        # name-derived guesses are not reliable enough to reject a row.
        wrapper_resolution = (
            wrapper_resolutions.get(node_export)
            if wrapper_resolutions and isinstance(node_export, str) and not is_proxy
            else None
        )
        wrapper_crate = source_backed_crate(wrapper_resolution)
        if wrapper_crate and valid_rust_crate and wrapper_crate != rust_crate:
            diagnostics.append(
                f"Row '{row_id}' rustCrate '{rust_crate}' disagrees with "
                f"nodeExport '{node_export}' wrapper source owner '{wrapper_crate}'."
            )
        # Repeated Node exports can have separate accessor rows, so their
        # symbol need not equal the resolver's single enclosing core type.
        elif (
                wrapper_crate
                and wrapper_crate == rust_crate
                and mapped_export_counts[node_export] == 1
        ):
            wrapper_symbol = source_backed_symbol(wrapper_resolution)
            if wrapper_symbol and wrapper_symbol != effective_rust_symbol:
                diagnostics.append(
                    f"Row '{row_id}' rustSymbol '{effective_rust_symbol}' disagrees "
                    f"with nodeExport '{node_export}' wrapper source symbol "
                    f"'{wrapper_symbol}' in '{rust_crate}'."
                )

        # A Node export may not claim a Rust *module* as its counterpart. The
        # existence check above is satisfied by any symbol of any kind, which is
        # how placeholder rows accumulated: 82 unrelated exports once all named
        # the module `path_core` and the gate still reported 100% matched.
        # Matching a module says nothing about the export, so it is rejected.
        #
        # @rust proxy rows are exempt: they have no nodeExport and exist
        # precisely to record that a Rust module has no binding counterpart.
        if (
                not is_proxy
                and effective_rust_symbol
                and rust_key in rust_module_only_symbols
        ):
            diagnostics.append(
                f"Row '{row_id}' maps nodeExport '{node_export}' to "
                f"'{effective_rust_symbol}', which is a Rust module rather than "
                f"a function, type, or re-export. A module match does not verify "
                f"anything about the export. Map it to the specific core symbol "
                f"the NAPI wrapper uses (see "
                f"tools/node_api_parity/resolve_node_rust_symbols.py), or set "
                f"rustSymbol to null with an 'unmappedReason'."
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
        row
        for row in diff_report["contract_results"]
        if row["status"] not in {"matched", "unmapped"}
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
            f"- Tier-1 owner mismatch: **{summary.get('tier1_owner_mismatch', 0)}**",
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
            "| ID | Owner Module | Rust Crate | Rust Symbol | Node Export | Status | Reason |",
            "|---|---|---|---|---|---|---|",
        )
    )
    for row in failing_rows:
        lines.append(
                "| `{id}` | `{owner_module}` | `{rust_crate}` | `{rust_symbol}` | `{node_export}` | `{status}` | {reason} |".format(
                    id=row["id"],
                    owner_module=row["owner_module"],
                    rust_crate=row.get("rust_crate") or "-",
                rust_symbol=row["rust_symbol"],
                node_export=row["node_export"],
                status=row["status"],
                reason=row.get("reason", "-"),
            )
        )
    lines.append("")
    return "\n".join(lines)


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
        default="node-bindings/classic-node/index.d.ts",
        help="Path to Node index.d.ts, relative to repo root.",
    )
    parser.add_argument(
        "--output-dir",
        default="node-bindings/classic-node/parity-artifacts",
        help="Directory for generated gate artifacts, relative to repo root.",
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
    wrapper_resolutions = resolve_all(repo_root, rust_manifest)

    # Phase 4 Plan 1 Task 2: bidirectional guard with H1 fail-closed
    # malformed-row rejection. Runs unconditionally before downstream diff
    # generation so a missing `pub use`, a stale `index.d.ts`, or a
    # malformed row shape is surfaced with an actionable remediation
    # message instead of being buried as `missing_rust`/`missing_node`
    # drift noise later. See docstring on `validate_contract_surface()`
    # for the full list of rejected shapes.
    guard_diagnostics = validate_contract_surface(
        contract, rust_manifest, node_manifest, wrapper_resolutions
    )
    if guard_diagnostics:
        print(
            "validate_contract_surface() found contract<->surface drift:",
            file=sys.stderr,
        )
        for message in guard_diagnostics:
            print(f"  - {message}", file=sys.stderr)
        return 2

    diff_report = generate_diff_report(
        contract, rust_manifest, node_manifest, wrapper_resolutions
    )

    # Carry the committed timestamps forward on any artifact whose substance is
    # unchanged, so `--update-baseline` copies byte-identical files into the
    # tracked baseline instead of a timestamp-only diff. The markdown reports
    # follow for free: their "- Generated:" header renders from the
    # corresponding JSON payload rather than calling the clock again.
    preserve_baseline_generated_at_all(
        baseline_output_dir,
        {
            "rust_api_surface.json": rust_manifest,
            "node_api_surface.json": node_manifest,
            "parity_diff_report.json": diff_report,
        },
    )

    write_json(output_dir / "rust_api_surface.json", rust_manifest)
    write_json(output_dir / "node_api_surface.json", node_manifest)
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
            + summary["tier1_missing_node"]
            + summary["tier1_signature_mismatch"]
            + summary["tier1_owner_mismatch"]
    )

    tracked_artifact_names = (
        "rust_api_surface.json",
        "node_api_surface.json",
        "parity_diff_report.json",
        "parity_diff_report.md",
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
    print(f"- {output_dir / 'tier1_gate_report.md'}")

    if tier1_drift_count > 0:
        print(
            "Tier-1 parity drift detected: "
            f"missing_rust={summary['tier1_missing_rust']}, "
            f"missing_node={summary['tier1_missing_node']}, "
            f"signature_mismatch={summary['tier1_signature_mismatch']}, "
            f"owner_mismatch={summary['tier1_owner_mismatch']}"
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
