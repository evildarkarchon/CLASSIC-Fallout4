"""The retirement diagnostic must never promote static matches to proof."""

from dataclasses import replace
from pathlib import Path

import pytest
from conformance.coverage import (
    CoveragePredicate,
    FamilyCoveragePolicy,
    SourceParityRow,
)


def test_candidate_matching_preserves_operation_and_explicit_selector_boundaries() -> (
    None
):
    """A matching owner cannot donate coverage to an unexecuted public alias."""
    from retirement_readiness import candidate_predicates

    row = SourceParityRow(
        "parity:node:one",
        "node",
        "canonical_rust",
        "core",
        "Owner",
        "source",
        "/0",
        runtime_operation="read",
    )
    pack = {
        "familyId": "example",
        "domainOwner": {"rustCrate": "core"},
        "capabilities": [{"id": "read", "rustSymbols": ["Owner"]}],
        "scenarios": [{"action": "read", "capabilityIds": ["read"]}],
    }
    predicate = CoveragePredicate(
        "read-fact",
        "read",
        "read",
        "result",
        ("Owner",),
        lambda _: True,
        runtime_operations=("read",),
    )
    policy = FamilyCoveragePolicy("example", (predicate,))
    assert candidate_predicates(row, pack, policy) == ("read-fact",)
    assert (
        candidate_predicates(replace(row, runtime_operation="write"), pack, policy)
        == ()
    )
    assert candidate_predicates(replace(row, rust_crate="other"), pack, policy) == ()
    restricted = FamilyCoveragePolicy(
        "example", (replace(predicate, binding_obligation_ids=("parity:node:other",)),)
    )
    assert candidate_predicates(row, pack, restricted) == ()
    assert candidate_predicates(row, {**pack, "scenarios": []}, policy) == ()


def test_repository_diagnostic_accounts_for_every_occurrence_without_claiming_proof() -> (
    None
):
    """Even a matching predicate remains only an unexecuted migration candidate."""
    from retirement_readiness import build_readiness_report

    report = build_readiness_report(Path(__file__).resolve().parents[3])
    assert report["diagnosticOnly"] is True
    assert report["grantsRuntimeCoverage"] is False
    assert len(report["rows"]) == sum(report["counts"].values())
    assert len({row["obligationId"] for row in report["rows"]}) == len(report["rows"])
    assert report["counts"]["runtime-candidate"] > 0
    assert all(
        row["candidatePredicates"]
        for row in report["rows"]
        if row["disposition"] == "runtime-candidate"
    )


def test_repository_diagnostic_rejects_selector_owner_escape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid policy selectors must not disappear into the unmatched inventory."""
    import retirement_readiness
    from conformance.coverage import CoverageDerivationError, load_source_parity_rows

    root = Path(__file__).resolve().parents[3]
    row = next(
        row
        for row in load_source_parity_rows(root)
        if row.mapping_origin == "canonical_rust"
        and row.rust_crate != "classic-config-core"
    )
    policy = retirement_readiness.FAMILY_COVERAGE_POLICIES["config-operations"]
    invalid = replace(policy.predicates[0], binding_obligation_ids=(row.obligation_id,))
    monkeypatch.setitem(
        retirement_readiness.FAMILY_COVERAGE_POLICIES,
        "config-operations",
        replace(policy, predicates=(invalid, *policy.predicates[1:])),
    )
    with pytest.raises(CoverageDerivationError, match="canonical Rust mapping"):
        retirement_readiness.build_readiness_report(root)


def test_binding_only_candidates_require_exact_selectors() -> None:
    """Binding-only rows cannot borrow canonical matches from a nearby owner."""
    from retirement_readiness import candidate_predicates

    row = SourceParityRow(
        "parity:node:binding",
        "node",
        "binding_only",
        None,
        None,
        "source",
        "/0",
        runtime_operation="read",
    )
    pack = {
        "familyId": "example",
        "domainOwner": {"rustCrate": "core"},
        "capabilities": [{"id": "read", "rustSymbols": ["Owner"]}],
        "scenarios": [{"action": "read", "capabilityIds": ["read"]}],
    }
    predicate = CoveragePredicate(
        "read-fact",
        "read",
        "read",
        "result",
        ("Owner",),
        lambda _: True,
        binding_obligation_ids=(row.obligation_id,),
        runtime_operations=("read",),
    )
    policy = FamilyCoveragePolicy("example", (predicate,))
    assert candidate_predicates(row, pack, policy) == ("read-fact",)
    assert (
        candidate_predicates(
            replace(row, obligation_id="parity:node:other"), pack, policy
        )
        == ()
    )
    assert (
        candidate_predicates(replace(row, runtime_operation="write"), pack, policy)
        == ()
    )
    assert (
        candidate_predicates(
            row,
            pack,
            FamilyCoveragePolicy(
                "example", (replace(predicate, binding_obligation_ids=()),)
            ),
        )
        == ()
    )
    escaped = replace(
        row, mapping_origin="canonical_rust", rust_crate="other", rust_symbol="Owner"
    )
    assert candidate_predicates(escaped, pack, policy) == ()


def test_retained_operation_does_not_become_a_candidate() -> None:
    """A broad owner predicate cannot retire separately retained operations."""
    from retirement_readiness import candidate_predicates

    row = SourceParityRow(
        "parity:python:retained",
        "python",
        "canonical_rust",
        "classic-version-registry-core",
        "GameVersion",
        "source",
        "/0",
        runtime_operation="__hash__",
    )
    pack = {
        "familyId": "game-version-parse",
        "domainOwner": {"rustCrate": "classic-version-registry-core"},
        "capabilities": [{"id": "metadata", "rustSymbols": ["GameVersion"]}],
        "scenarios": [{"action": "metadata", "capabilityIds": ["metadata"]}],
    }
    predicate = CoveragePredicate(
        "metadata-fact",
        "metadata",
        "metadata",
        "result",
        ("GameVersion",),
        lambda _: True,
    )
    policy = FamilyCoveragePolicy("game-version-parse", (predicate,))
    assert candidate_predicates(row, pack, policy) == ()
    assert candidate_predicates(
        replace(row, runtime_operation="future_operation"), pack, policy
    ) == ("metadata-fact",)


@pytest.mark.parametrize(
    "gaps,missing,expected", [(0, [], 0), (1, [], 1), (0, ["missing"], 1)]
)
def test_fail_on_unmatched_exit_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    gaps: int,
    missing: list[str],
    expected: int,
) -> None:
    """Only unresolved static obligations fail the opt-in diagnostic gate."""
    import retirement_readiness

    monkeypatch.setattr(
        retirement_readiness,
        "build_readiness_report",
        lambda _: {
            "counts": {"runtime-without-predicate": gaps},
            "familiesWithoutPolicies": missing,
        },
    )
    output = tmp_path / "readiness.json"
    assert (
        retirement_readiness.main(["--output", str(output), "--fail-on-unmatched"])
        == expected
    )
