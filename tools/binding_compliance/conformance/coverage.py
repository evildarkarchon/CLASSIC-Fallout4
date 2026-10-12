"""Derive observed fact IDs from trusted family predicates.

Parity-row coverage (CXX parity rows, retained analyzers, operation-scoped row
selection) was deleted with the CXX parity gate (T1, #306); semantic
applicability now comes from ``participants.json``. What remains here is the
per-family fact vocabulary that receipts still record, which the engine port
deletes.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any


class CoverageDerivationError(ValueError):
    """Raised when family coverage policy cannot produce trustworthy facts."""


@dataclass(frozen=True)
class CoveragePredicate:
    """One family-owned fact predicate over a normalized observation.

    ``matches`` receives only the centrally normalized actual observation. The
    trusted scenario action is matched separately, so receipt runner metadata,
    test names, selector hashes, and migration state cannot influence the fact.
    ``runtime_operations`` names the public operations the fact speaks for;
    ``None`` inside that tuple names carriers. Since the parity rows were
    deleted (T1) nothing consumes it beyond ``covers_runtime_operation``.
    """

    id: str
    capability_id: str
    action: str
    observation_family: str
    rust_symbols: tuple[str, ...]
    matches: Callable[[Mapping[str, Any]], bool]
    runtime_operations: tuple[str | None, ...] | None = None

    def covers_runtime_operation(self, operation: str | None) -> bool:
        """Return whether this fact may cover the source-derived public operation."""
        return self.runtime_operations is None or operation in self.runtime_operations


@dataclass(frozen=True)
class FamilyCoveragePolicy:
    """The executable fact predicates owned by one scenario family."""

    family_id: str
    predicates: tuple[CoveragePredicate, ...]


def derive_observed_fact_ids(
    pack: Mapping[str, Any],
    scenario: Mapping[str, Any],
    normalized_observation: Mapping[str, Any],
    policy: FamilyCoveragePolicy,
) -> tuple[str, ...]:
    """Return facts proved by one trusted action and normalized observation.

    Raises ``CoverageDerivationError`` when policy references a capability,
    observation family, or Rust symbol outside the validated scenario pack, or
    when a predicate does not return a boolean result.
    """

    if policy.family_id != pack["familyId"]:
        raise CoverageDerivationError(
            "coverage policy family does not match the validated scenario pack"
        )

    capabilities = {capability["id"]: capability for capability in pack["capabilities"]}
    scenario_capability_ids = frozenset(scenario["capabilityIds"])
    fact_ids: list[str] = []
    seen_fact_ids: set[str] = set()
    for predicate in policy.predicates:
        if predicate.id in seen_fact_ids:
            raise CoverageDerivationError(
                f"duplicate family coverage predicate id: {predicate.id}"
            )
        seen_fact_ids.add(predicate.id)
        capability = capabilities.get(predicate.capability_id)
        if capability is None:
            raise CoverageDerivationError(
                f"coverage predicate {predicate.id} references an unknown capability"
            )
        if predicate.observation_family not in capability["observationFamilies"]:
            raise CoverageDerivationError(
                f"coverage predicate {predicate.id} references an undeclared observation family"
            )
        unknown_symbols = sorted(
            set(predicate.rust_symbols) - set(capability["rustSymbols"])
        )
        if unknown_symbols:
            raise CoverageDerivationError(
                f"coverage predicate {predicate.id} references undeclared Rust symbols: "
                + ", ".join(unknown_symbols)
            )
        if (
            predicate.capability_id not in scenario_capability_ids
            or predicate.action != scenario["action"]
        ):
            continue
        try:
            matched = predicate.matches(normalized_observation)
        except Exception as error:
            raise CoverageDerivationError(
                f"coverage predicate {predicate.id} could not evaluate: {error}"
            ) from error
        if type(matched) is not bool:
            raise CoverageDerivationError(
                f"coverage predicate {predicate.id} must return a boolean"
            )
        if matched:
            fact_ids.append(predicate.id)
    return tuple(sorted(fact_ids))


def predicates_for_facts(
    policy: FamilyCoveragePolicy, fact_ids: Sequence[str]
) -> tuple[CoveragePredicate, ...]:
    """Return policy predicates for centrally derived fact IDs.

    This lookup is intentionally policy-owned; callers cannot introduce a fact
    identity that was not emitted by ``derive_observed_fact_ids``.
    """

    requested = set(fact_ids)
    return tuple(
        predicate for predicate in policy.predicates if predicate.id in requested
    )
