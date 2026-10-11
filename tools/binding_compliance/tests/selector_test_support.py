"""Selector diagnostics shared by family coverage tests.

``candidate_predicates`` moved here unchanged from the retired
``retirement_readiness.py`` inventory script (Retire, #304); the tests still
use it to prove that every named parity row keeps a selectable fact.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from conformance.coverage import FamilyCoveragePolicy, SourceParityRow
from conformance.families.operation_scope import is_retained_operation


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
