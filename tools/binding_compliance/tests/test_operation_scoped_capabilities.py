"""Operation-level families must preserve the complete repository denominator."""

from dataclasses import replace
from pathlib import Path

import pytest
from conformance.applicability import derive_applicability
from conformance.coverage import (
    CoverageDerivationError,
    CoveragePredicate,
    FamilyCoveragePolicy,
    SourceParityRow,
    derive_row_coverage,
)


def test_scoped_plan_projection_uses_the_same_source_denominator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Immutable plans must omit unsupported actions and rederive after source change."""
    from conformance import command, coverage, packs

    pack, rows, policy = _inputs()
    monkeypatch.setitem(command.FAMILY_COVERAGE_POLICIES, "getter", policy)
    monkeypatch.setattr(coverage, "load_source_parity_rows", lambda _: rows)
    assert [
        case["id"] for case in packs._semantic_scenarios(Path("."), pack, "python")
    ] == ["one"]
    with pytest.raises(packs.MaterializationError, match="not applicable"):
        packs._semantic_scenarios(Path("."), pack, "cxx")
    changed = (
        *rows,
        replace(rows[1], obligation_id="cxx.read", runtime_operation="read"),
    )
    monkeypatch.setattr(coverage, "load_source_parity_rows", lambda _: changed)
    assert [
        case["id"] for case in packs._semantic_scenarios(Path("."), pack, "cxx")
    ] == ["one"]


def test_supporting_capability_keeps_its_explicit_rust_owner() -> None:
    """A shared scenario may consume a second core crate without erasing ownership."""
    pack, rows, policy = _inputs()
    pack["domainOwner"]["rustCrate"] = "analyzer-core"
    pack["capabilities"][0]["rustCrate"] = "example-core"
    assert {
        p.id
        for p in derive_applicability(pack, rows, coverage_policy=policy).participants
    } == {"rust", "python"}
    report = derive_row_coverage(pack, rows, policy, ())
    assert {failure.obligation_id for failure in report.failures} == {"python.read"}
    unrelated = tuple(replace(row, rust_crate="other-core") for row in rows)
    assert not derive_row_coverage(pack, unrelated, policy, ()).failures


def test_structural_declarations_do_not_invent_scoped_execution() -> None:
    """An accepted carrier operation still needs a callable runtime source row."""
    pack, rows, policy = _inputs()
    policy = replace(
        policy,
        predicates=(replace(policy.predicates[0], runtime_operations=(None, "read")),),
    )
    declaration = replace(
        rows[1],
        required_evidence_kind="structural",
        runtime_operation=None,
        retained_analyzer_id="cxx-source-parity",
    )
    matrix = derive_applicability(pack, (rows[0], declaration), coverage_policy=policy)
    assert {participant.id for participant in matrix.participants} == {"rust", "python"}


def test_binding_only_operations_require_exact_scoped_selectors() -> None:
    """Interface-owned helpers enroll without fabricating a canonical core mapping."""
    pack, rows, policy = _inputs()
    binding = replace(
        rows[1],
        mapping_origin="binding_only",
        rust_crate=None,
        rust_symbol=None,
        runtime_operation="read",
    )
    selected = replace(
        policy,
        predicates=(
            replace(
                policy.predicates[0], binding_obligation_ids=(binding.obligation_id,)
            ),
        ),
    )
    matrix = derive_applicability(pack, (rows[0], binding), coverage_policy=selected)
    assert {participant.id for participant in matrix.participants} == {"rust", "cxx"}
    assert "cxx" not in {
        p.id
        for p in derive_applicability(
            pack, (binding,), coverage_policy=policy
        ).participants
    }
    wrong = replace(binding, runtime_operation="future")
    assert "cxx" not in {
        p.id
        for p in derive_applicability(
            pack, (wrong,), coverage_policy=selected
        ).participants
    }
    with pytest.raises(CoverageDerivationError, match="missing.*source"):
        derive_applicability(pack, rows[:1], coverage_policy=selected)


def _inputs():
    """Represent two bindings of one aggregate owner with distinct public calls."""
    pack = {
        "familyId": "getter",
        "domainOwner": {"rustCrate": "example-core"},
        "capabilities": [
            {
                "id": "getter.read",
                "rustSymbols": ["Owner"],
                "observationFamilies": ["value"],
                "operationScoped": True,
            }
        ],
        "scenarios": [
            {"id": "one", "action": "getter.read", "capabilityIds": ["getter.read"]}
        ],
        "consumerObligations": [],
    }
    rows = (
        SourceParityRow(
            "python.read",
            "python",
            "canonical_rust",
            "example-core",
            "Owner",
            "source",
            "/0",
            runtime_operation="read",
        ),
        SourceParityRow(
            "cxx.other",
            "cxx",
            "canonical_rust",
            "example-core",
            "Owner",
            "source",
            "/1",
            runtime_operation="other",
        ),
    )
    policy = FamilyCoveragePolicy(
        "getter",
        (
            CoveragePredicate(
                "read",
                "getter.read",
                "getter.read",
                "value",
                ("Owner",),
                lambda _: True,
                runtime_operations=("read",),
            ),
        ),
    )
    return pack, rows, policy


def test_scoped_family_selects_only_existing_public_operations() -> None:
    """An unrelated CXX method cannot obligate a Python getter scenario."""
    pack, rows, policy = _inputs()
    matrix = derive_applicability(pack, rows, coverage_policy=policy)
    assert {participant.id for participant in matrix.participants} == {"rust", "python"}
    report = derive_row_coverage(pack, rows, policy, ())
    assert {failure.obligation_id for failure in report.failures} == {"python.read"}
    # Global inventory is not rewritten or removed by narrower family selection.
    assert {row.obligation_id for row in rows} == {"python.read", "cxx.other"}
    new_export = replace(rows[1], obligation_id="cxx.read", runtime_operation="read")
    expanded = derive_applicability(pack, (*rows, new_export), coverage_policy=policy)
    assert {participant.id for participant in expanded.participants} == {
        "rust",
        "python",
        "cxx",
    }


def test_unscoped_capability_preserves_class_wide_obligations() -> None:
    """Opt-in filtering must not silently narrow established family contracts."""
    pack, rows, policy = _inputs()
    del pack["capabilities"][0]["operationScoped"]
    assert {p.id for p in derive_applicability(pack, rows).participants} == {
        "rust",
        "python",
        "cxx",
    }
    assert {
        f.obligation_id for f in derive_row_coverage(pack, rows, policy, ()).failures
    } == {"python.read", "cxx.other"}


@pytest.mark.parametrize("operations", [None, ()])
def test_scoped_capability_rejects_absent_or_wildcard_operation_policy(
    operations,
) -> None:
    """A missing explicit operation denominator cannot become a passing scope."""
    pack, rows, policy = _inputs()
    invalid = replace(
        policy,
        predicates=(replace(policy.predicates[0], runtime_operations=operations),),
    )
    with pytest.raises(CoverageDerivationError, match="explicit.*operation"):
        derive_applicability(pack, rows, coverage_policy=invalid)


def test_carrier_and_unknown_alias_cannot_borrow_scoped_getter() -> None:
    """Only the named operation is applicable, even when a carrier shares its owner."""
    pack, rows, policy = _inputs()
    unrelated = tuple(
        replace(row, runtime_operation=None if index == 0 else "future")
        for index, row in enumerate(rows)
    )
    assert {
        p.id
        for p in derive_applicability(
            pack, unrelated, coverage_policy=policy
        ).participants
    } == {"rust"}
