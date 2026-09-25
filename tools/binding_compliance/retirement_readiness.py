#!/usr/bin/env python3
"""Reproduce the static retirement inventory without granting runtime evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from conformance.command import FAMILY_COVERAGE_POLICIES
from conformance.coverage import (
    CoverageDerivationError,
    FamilyCoveragePolicy,
    SourceParityRow,
    derive_row_coverage,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
)
from conformance.families.operation_scope import is_retained_operation
from conformance.packs import discover_pack_paths, load_and_validate_pack


def candidate_predicates(
        row: SourceParityRow,
        pack: Mapping[str, Any],
        policy: FamilyCoveragePolicy,
) -> tuple[str, ...]:
    """Find potential facts using the executable derivation's selection rules.

    This inspects selectors and available scenario actions only. It does not
    evaluate predicates, authenticate receipts, or establish applicability.
    """
    if is_retained_operation(policy.family_id, row):
        return ()
    canonical = {
        capability["id"]
        for capability in pack["capabilities"]
        if row.mapping_origin == "canonical_rust"
           and row.rust_crate
           == capability.get("rustCrate", pack["domainOwner"]["rustCrate"])
           and row.rust_symbol in capability["rustSymbols"]
    }
    # An explicit selector may name a binding-only operation, but cannot escape
    # the declared Rust owner when the source row has a canonical mapping.
    if row.mapping_origin == "canonical_rust" and not canonical:
        return ()
    return tuple(
        sorted(
            predicate.id
            for predicate in policy.predicates
            if predicate.covers_runtime_operation(row.runtime_operation)
            and (
                row.obligation_id in predicate.binding_obligation_ids
                if predicate.binding_obligation_ids
                else predicate.capability_id in canonical
                     and row.rust_symbol in predicate.rust_symbols
            )
            and any(
                scenario["action"] == predicate.action
                and predicate.capability_id in scenario["capabilityIds"]
                for scenario in pack["scenarios"]
            )
        )
    )


def build_readiness_report(repo_root: Path) -> dict[str, Any]:
    """Inventory every live row and its remaining static migration work.

    Pack and analyzer validation errors propagate instead of producing an
    incomplete inventory. Counts never represent executed conformance.
    """
    root = repo_root.resolve()
    source_rows = load_source_parity_rows(root)
    rows_by_id = {row.obligation_id: row for row in source_rows}
    analyzers = load_retained_analyzer_kinds(root)
    families = []
    missing_policies = []
    for path in discover_pack_paths(root):
        pack = load_and_validate_pack(root, path).document()
        family_id = pack["familyId"]
        policy = FAMILY_COVERAGE_POLICIES.get(family_id)
        if policy is None:
            missing_policies.append(family_id)
            continue
        # Reuse central validation for stale explicit row IDs and capabilities;
        # no synthetic execution reports are created for the diagnostic.
        derive_row_coverage(pack, source_rows, policy, (), retained_analyzers=analyzers)
        # Central derivation records owner escapes as row failures rather than
        # raising. Reject those malformed selectors even without runtime facts.
        for predicate in policy.predicates:
            for obligation_id in predicate.binding_obligation_ids:
                row = rows_by_id[obligation_id]
                if row.mapping_origin == "canonical_rust" and not any(
                        row.rust_crate
                        == capability.get("rustCrate", pack["domainOwner"]["rustCrate"])
                        and row.rust_symbol in capability["rustSymbols"]
                        for capability in pack["capabilities"]
                ):
                    raise CoverageDerivationError(
                        f"{family_id}: explicit row selector {obligation_id} "
                        "escapes the pack's canonical Rust mapping"
                    )
        families.append((pack, policy))
    rows = []
    counts: Counter[str] = Counter()
    unmatched: Counter[tuple[str, str]] = Counter()
    for row in source_rows:
        candidates = [
            {"familyId": policy.family_id, "predicateId": predicate_id}
            for pack, policy in families
            for predicate_id in candidate_predicates(row, pack, policy)
        ]
        retained = (
                row.required_evidence_kind in {"structural", "negative"}
                and row.retained_analyzer_id is not None
                and analyzers.get(row.retained_analyzer_id) == row.required_evidence_kind
        )
        disposition = (
            "retained-source"
            if retained
            else "runtime-candidate"
            if candidates and row.required_evidence_kind == "runtime"
            else "runtime-without-predicate"
            if row.required_evidence_kind == "runtime"
            else "unowned-source"
        )
        counts[disposition] += 1
        if disposition == "runtime-without-predicate":
            unmatched[(row.participant_id, row.rust_crate or "binding-only")] += 1
        rows.append(
            {
                "obligationId": row.obligation_id,
                "participantId": row.participant_id,
                "mappingOrigin": row.mapping_origin,
                "rustCrate": row.rust_crate,
                "rustSymbol": row.rust_symbol,
                "runtimeOperation": row.runtime_operation,
                "artifact": row.artifact,
                "locator": row.locator,
                "disposition": disposition,
                "retainedAnalyzerId": row.retained_analyzer_id if retained else None,
                "candidatePredicates": candidates,
            }
        )
    return {
        "schemaVersion": 1,
        "diagnosticOnly": True,
        "grantsRuntimeCoverage": False,
        "counts": dict(sorted(counts.items())),
        "familiesWithoutPolicies": sorted(missing_policies),
        "unmatchedByOwner": [
            {"participantId": participant, "rustCrate": crate, "count": count}
            for (participant, crate), count in sorted(unmatched.items())
        ],
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    """Write a diagnostic inventory; optionally fail on statically unmatched rows."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fail-on-unmatched", action="store_true")
    args = parser.parse_args(argv)
    report = build_readiness_report(args.repo_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["counts"], sort_keys=True))
    print("Diagnostic only: candidate predicates do not prove runtime conformance.")
    return int(
        args.fail_on_unmatched
        and bool(
            report["counts"].get("runtime-without-predicate", 0)
            or report["counts"].get("unowned-source", 0)
            or report["familiesWithoutPolicies"]
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
