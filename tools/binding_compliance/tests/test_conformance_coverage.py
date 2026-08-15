"""Behavior tests for source-derived conformance applicability and coverage."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from conformance import (
    CoverageDerivationError,
    CoveragePredicate,
    FamilyCoveragePolicy,
    PolicyException,
    PolicyExceptionError,
    PreparedRunReport,
    SourceParityRow,
    derive_applicability,
    derive_row_coverage,
    load_policy_exceptions,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
    prepared_report_evidence_digest,
)
from conformance.receipts import ScenarioValidationResult

REPO_ROOT = Path(__file__).resolve().parents[3]


def _pack() -> dict[str, object]:
    """Return a small validated-pack-shaped capability inventory."""

    return {
        "familyId": "example-family",
        "domainOwner": {"rustCrate": "classic-example-core"},
        "capabilities": [
            {
                "id": "example.execute",
                "rustSymbols": ["Request", "execute"],
                "observationFamilies": ["result"],
            }
        ],
        "scenarios": [
            {
                "id": "base-case",
                "action": "example.execute",
                "capabilityIds": ["example.execute"],
            }
        ],
        "consumerObligations": [],
    }


def _prepared_report(
    participant_id: str,
    fact_ids: tuple[str, ...],
    *,
    execution_instance_id: str | None = None,
    participant_role: str = "semantic-adapter",
) -> PreparedRunReport:
    """Return one centrally typed passing coverage proof for a participant."""

    plan = {
        "familyId": "example-family",
        "familyVersion": 1,
        "expectationDigest": "sha256:" + "a" * 64,
        "invocation": {"sourceIdentity": "git:" + "b" * 40 + ":sha256:" + "c" * 64},
        "participant": {
            "id": participant_id,
            "role": participant_role,
            "executionInstanceId": execution_instance_id or participant_id,
        },
    }
    return PreparedRunReport._from_plan(
        plan,
        scenarios=(
            ScenarioValidationResult(
                id="base-case",
                execution_status="completed",
                result="pass",
                observed_fact_ids=fact_ids,
            ),
        ),
        failures=(),
    )


def test_applicability_comes_from_canonical_source_rows() -> None:
    """A caller-supplied participant name cannot make an adapter applicable."""

    rows = (
        SourceParityRow(
            obligation_id="parity:cxx:execute",
            participant_id="cxx",
            mapping_origin="canonical_rust",
            rust_crate="classic-example-core",
            rust_symbol="execute",
            artifact="cxx.json",
            locator="/entries/0#id=execute",
        ),
        SourceParityRow(
            obligation_id="parity:node:request",
            participant_id="node",
            mapping_origin="canonical_rust",
            rust_crate="classic-example-core",
            rust_symbol="Request",
            artifact="node.json",
            locator="/tier1Mappings/0#id=request",
        ),
        SourceParityRow(
            obligation_id="parity:python:other",
            participant_id="python",
            mapping_origin="canonical_rust",
            rust_crate="classic-other-core",
            rust_symbol="execute",
            artifact="python.json",
            locator="/tier1Mappings/0#id=other",
        ),
    )

    applicability = derive_applicability(_pack(), rows)

    assert applicability.document() == {
        "participants": [
            {
                "id": "cxx",
                "role": "semantic-adapter",
                "executionInstanceIds": ["windows-clang-cl", "windows-msvc"],
                "capabilityIds": ["example.execute"],
                "scenarioIds": ["base-case"],
            },
            {
                "id": "node",
                "role": "semantic-adapter",
                "executionInstanceIds": ["node"],
                "capabilityIds": ["example.execute"],
                "scenarioIds": ["base-case"],
            },
            {
                "id": "rust",
                "role": "semantic-adapter",
                "executionInstanceIds": ["rust"],
                "capabilityIds": ["example.execute"],
                "scenarioIds": ["base-case"],
            },
        ]
    }


def test_applicability_requires_the_validated_action_mapping() -> None:
    """A mapped supporting DTO cannot enroll an adapter that lacks the action."""

    pack = _pack()
    pack["capabilities"].append(
        {
            "id": "example.request",
            "rustSymbols": ["SupportingDto"],
            "observationFamilies": ["result"],
        }
    )
    pack["scenarios"][0]["capabilityIds"].append("example.request")
    rows = (
        SourceParityRow(
            obligation_id="parity:python:request",
            participant_id="python",
            mapping_origin="canonical_rust",
            rust_crate="classic-example-core",
            rust_symbol="SupportingDto",
            artifact="python.json",
            locator="/tier1Mappings/0#id=request",
        ),
    )

    applicability = derive_applicability(pack, rows)

    assert [participant.id for participant in applicability.participants] == ["rust"]


def test_fact_coverage_preserves_every_source_row_occurrence() -> None:
    """One repeated row ID remains two independently credited obligations."""

    rows = tuple(
        SourceParityRow(
            obligation_id=f"parity:node:execute:occurrence:{occurrence}",
            participant_id="node",
            mapping_origin="canonical_rust",
            rust_crate="classic-example-core",
            rust_symbol="execute",
            artifact="node.json",
            locator=f"/tier1Mappings/{occurrence - 1}#id=execute",
        )
        for occurrence in (1, 2)
    )
    policy = FamilyCoveragePolicy(
        family_id="example-family",
        predicates=(
            CoveragePredicate(
                id="example.completed",
                capability_id="example.execute",
                action="example.execute",
                observation_family="result",
                rust_symbols=("execute",),
                matches=lambda observation: observation.get("status") == "completed",
            ),
        ),
    )
    prepared_reports = (_prepared_report("node", ("example.completed",)),)

    report = derive_row_coverage(
        _pack(),
        rows,
        policy,
        prepared_reports,
    )

    assert [row["obligationId"] for row in report.document()["rows"]] == [
        "parity:node:execute:occurrence:1",
        "parity:node:execute:occurrence:2",
    ]
    assert {row["evidenceKind"] for row in report.document()["rows"]} == {"executable"}
    assert all(
        row["evidenceIds"] == ["example.completed"] for row in report.document()["rows"]
    )
    assert report.document()["failures"] == []


def test_explicit_row_selector_does_not_credit_a_same_symbol_sibling() -> None:
    """A predicate-owned row selector narrows credit below Rust-symbol scope."""

    selected = SourceParityRow(
        obligation_id="parity:node:selected",
        participant_id="node",
        mapping_origin="canonical_rust",
        rust_crate="classic-example-core",
        rust_symbol="execute",
        artifact="node.json",
        locator="/tier1Mappings/0#id=selected",
    )
    sibling = SourceParityRow(
        obligation_id="parity:node:sibling",
        participant_id="node",
        mapping_origin="canonical_rust",
        rust_crate="classic-example-core",
        rust_symbol="execute",
        artifact="node.json",
        locator="/tier1Mappings/1#id=sibling",
    )
    policy = FamilyCoveragePolicy(
        "example-family",
        (
            CoveragePredicate(
                id="example.selected",
                capability_id="example.execute",
                action="example.execute",
                observation_family="result",
                rust_symbols=("execute",),
                matches=lambda observation: observation.get("status") == "completed",
                binding_obligation_ids=(selected.obligation_id,),
            ),
        ),
    )
    prepared = (_prepared_report("node", ("example.selected",)),)

    report = derive_row_coverage(
        _pack(),
        (selected, sibling),
        policy,
        prepared,
    ).document()

    assert [row["obligationId"] for row in report["rows"]] == [selected.obligation_id]
    assert [failure["obligationId"] for failure in report["failures"]] == [
        sibling.obligation_id
    ]


def test_participant_scope_ignores_explicit_rows_for_other_adapters() -> None:
    """A cross-adapter policy remains valid for a participant-only denominator."""

    node_row = SourceParityRow(
        obligation_id="parity:node:selected",
        participant_id="node",
        mapping_origin="canonical_rust",
        rust_crate="classic-example-core",
        rust_symbol="execute",
        artifact="node.json",
        locator="/tier1Mappings/0#id=selected",
    )
    python_row = SourceParityRow(
        obligation_id="parity:python:selected",
        participant_id="python",
        mapping_origin="canonical_rust",
        rust_crate="classic-example-core",
        rust_symbol="execute",
        artifact="python.json",
        locator="/tier1Mappings/0#id=selected",
    )
    policy = FamilyCoveragePolicy(
        "example-family",
        (
            CoveragePredicate(
                id="example.completed",
                capability_id="example.execute",
                action="example.execute",
                observation_family="result",
                rust_symbols=("execute",),
                matches=lambda observation: observation.get("status") == "completed",
                binding_obligation_ids=(
                    node_row.obligation_id,
                    python_row.obligation_id,
                ),
            ),
        ),
    )

    report = derive_row_coverage(
        _pack(),
        (node_row, python_row),
        policy,
        (_prepared_report("node", ("example.completed",)),),
        scope_participant_id="node",
    ).document()

    assert [row["obligationId"] for row in report["rows"]] == [node_row.obligation_id]
    assert report["failures"] == []


def test_new_uncovered_row_blocks_regardless_of_migration_state() -> None:
    """A ledger label cannot grandfather a public row added after Phase 0."""

    row = SourceParityRow(
        obligation_id="parity:node:new-public-row",
        participant_id="node",
        mapping_origin="canonical_rust",
        rust_crate="classic-example-core",
        rust_symbol="execute",
        artifact="node.json",
        locator="/tier1Mappings/0#id=new-public-row",
    )
    policy = FamilyCoveragePolicy("example-family", ())
    report = derive_row_coverage(
        _pack(),
        (row,),
        policy,
        (),
    )

    assert report.document()["rows"] == []
    assert report.document()["failures"] == [
        {
            "kind": "coverage_mapping_gap",
            "obligationId": row.obligation_id,
            "blocking": True,
            "message": "source parity row lacks predicate-derived executable coverage",
        }
    ]


def test_caller_authored_report_dictionary_cannot_grant_a_fact() -> None:
    """Only the central prepared-report type may carry predicate results."""

    row = SourceParityRow(
        obligation_id="parity:node:execute",
        participant_id="node",
        mapping_origin="canonical_rust",
        rust_crate="classic-example-core",
        rust_symbol="execute",
        artifact="node.json",
        locator="/tier1Mappings/0#id=execute",
    )
    policy = FamilyCoveragePolicy(
        "example-family",
        (
            CoveragePredicate(
                id="example.completed",
                capability_id="example.execute",
                action="example.execute",
                observation_family="result",
                rust_symbols=("execute",),
                matches=lambda observation: True,
            ),
        ),
    )
    invented = {
        "participant": {"id": "node"},
        "result": "pass",
        "scenarios": [{"result": "pass", "observedFactIds": ["example.completed"]}],
    }

    with pytest.raises(CoverageDerivationError, match="PreparedRunReport"):
        derive_row_coverage(_pack(), (row,), policy, (invented,))


def test_directly_constructed_prepared_report_cannot_grant_a_fact() -> None:
    """A public dataclass constructor cannot counterfeit central validation."""

    invented = PreparedRunReport(
        family_id="example-family",
        family_version=1,
        expectation_digest="sha256:" + "a" * 64,
        invocation={"sourceIdentity": "git:" + "b" * 40 + ":sha256:" + "c" * 64},
        participant={
            "id": "node",
            "role": "semantic-adapter",
            "executionInstanceId": "node",
        },
        scenarios=(
            ScenarioValidationResult(
                id="base-case",
                execution_status="completed",
                result="pass",
                observed_fact_ids=("example.completed",),
            ),
        ),
        failures=(),
    )

    with pytest.raises(CoverageDerivationError, match="central receipt validation"):
        derive_row_coverage(
            _pack(),
            (),
            FamilyCoveragePolicy("example-family", ()),
            (invented,),
        )

    centrally_derived_then_replaced = replace(
        _prepared_report("node", ()),
        scenarios=invented.scenarios,
    )
    with pytest.raises(CoverageDerivationError, match="central receipt validation"):
        derive_row_coverage(
            _pack(),
            (),
            FamilyCoveragePolicy("example-family", ()),
            (centrally_derived_then_replaced,),
        )


def test_runtime_fact_must_be_observed_by_every_execution_instance() -> None:
    """One passing CXX toolchain cannot grant participant-wide row credit."""

    row = SourceParityRow(
        obligation_id="parity:cxx:execute",
        participant_id="cxx",
        mapping_origin="canonical_rust",
        rust_crate="classic-example-core",
        rust_symbol="execute",
        artifact="cxx.json",
        locator="/entries/0#id=execute",
    )
    policy = FamilyCoveragePolicy(
        "example-family",
        (
            CoveragePredicate(
                id="example.completed",
                capability_id="example.execute",
                action="example.execute",
                observation_family="result",
                rust_symbols=("execute",),
                matches=lambda observation: True,
            ),
        ),
    )
    reports = (
        _prepared_report(
            "cxx",
            ("example.completed",),
            execution_instance_id="windows-msvc",
        ),
        _prepared_report("cxx", (), execution_instance_id="windows-clang-cl"),
    )

    report = derive_row_coverage(_pack(), (row,), policy, reports).document()

    assert report["rows"] == []
    assert report["failures"][0]["obligationId"] == row.obligation_id


def test_consumer_receipt_cannot_grant_semantic_parity_coverage() -> None:
    """A colliding consumer participant ID never satisfies adapter rows."""

    with pytest.raises(CoverageDerivationError, match="consumer receipts"):
        derive_row_coverage(
            _pack(),
            (),
            FamilyCoveragePolicy("example-family", ()),
            (
                _prepared_report(
                    "cxx",
                    (),
                    execution_instance_id="windows-msvc",
                    participant_role="consumer",
                ),
            ),
        )


def test_consumer_obligations_fail_closed_without_a_source_registry() -> None:
    """An undeclared consumer denominator cannot yield repository completeness."""

    pack = _pack()
    pack["consumerObligations"] = [{"id": "example-rendering"}]

    with pytest.raises(PolicyExceptionError, match="consumer obligation registry"):
        derive_applicability(pack, ())


def test_family_coverage_ignores_unrelated_live_repository_rows() -> None:
    """A family denominator contains only canonical or explicitly selected rows."""

    unrelated = SourceParityRow(
        obligation_id="parity:python:other",
        participant_id="python",
        mapping_origin="canonical_rust",
        rust_crate="classic-other-core",
        rust_symbol="execute",
        artifact="python.json",
        locator="/tier1Mappings/0#id=other",
    )

    report = derive_row_coverage(
        _pack(),
        (unrelated,),
        FamilyCoveragePolicy("example-family", ()),
        (),
    ).document()

    assert report == {
        "familyId": "example-family",
        "result": "pass",
        "executionEvidence": [],
        "preparedEvidenceDigest": prepared_report_evidence_digest(()),
        "rows": [],
        "failures": [],
    }


def test_mapped_only_or_manual_classification_is_never_success() -> None:
    """No acknowledgement-style classification can resolve a parity row."""

    rows = tuple(
        SourceParityRow(
            obligation_id=f"parity:node:{classification}",
            participant_id="node",
            mapping_origin="canonical_rust",
            rust_crate="classic-example-core",
            rust_symbol="execute",
            artifact="node.json",
            locator=f"/tier1Mappings/{index}#id={classification}",
            required_evidence_kind=classification,
        )
        for index, classification in enumerate(("mapped_only", "manual"))
    )

    report = derive_row_coverage(
        _pack(),
        rows,
        FamilyCoveragePolicy("example-family", ()),
        (),
    )

    assert report.document()["rows"] == []
    assert [failure["blocking"] for failure in report.document()["failures"]] == [
        True,
        True,
    ]
    assert all(
        "unsupported source-derived evidence classification" in failure["message"]
        for failure in report.document()["failures"]
    )


def test_live_parity_loader_preserves_canonical_metadata_and_occurrences() -> None:
    """Coverage reads the source-gated row inventories without collapsing IDs."""

    rows = load_source_parity_rows(REPO_ROOT)

    assert {
        participant: sum(row.participant_id == participant for row in rows)
        for participant in ("cxx", "node", "python")
    } == {
        "cxx": 644,
        "node": 907,
        "python": 1_225,
    }
    obligation_ids = [row.obligation_id for row in rows]
    assert len(obligation_ids) == len(set(obligation_ids))
    assert any(":occurrence:1" in obligation_id for obligation_id in obligation_ids)
    assert sum(row.required_evidence_kind == "structural" for row in rows) == 309
    cxx_canonical = next(
        row
        for row in rows
        if row.participant_id == "cxx" and row.mapping_origin == "canonical_rust"
    )
    assert cxx_canonical.rust_crate
    assert cxx_canonical.rust_symbol


def test_retained_analyzers_resolve_only_from_current_blocking_owners() -> None:
    """The permanent catalog exposes kinds without reading ledger row state."""

    analyzers = load_retained_analyzer_kinds(REPO_ROOT)

    assert analyzers["cxx-source-parity"] == "structural"
    assert analyzers["user-settings-exclusive-ownership"] == "negative"


def test_retained_analyzer_and_exception_must_come_from_trusted_catalogs(
    tmp_path: Path,
) -> None:
    """Ledger target strings alone cannot resolve non-executable evidence."""

    structural_row = SourceParityRow(
        obligation_id="parity:node:request",
        participant_id="node",
        mapping_origin="canonical_rust",
        rust_crate="classic-example-core",
        rust_symbol="Request",
        artifact="node.json",
        locator="/tier1Mappings/0#id=request",
        required_evidence_kind="structural",
        retained_analyzer_id="node-source-and-declaration-parity",
    )
    exception_row = SourceParityRow(
        obligation_id="parity:cxx:execute",
        participant_id="cxx",
        mapping_origin="canonical_rust",
        rust_crate="classic-example-core",
        rust_symbol="execute",
        artifact="cxx.json",
        locator="/entries/0#id=execute",
    )
    exception = PolicyException(
        id="cxx-example-exception",
        capability_id="example.execute",
        participant_id="cxx",
        rationale="The example is intentionally absent from CXX.",
        policy_page="docs/api/binding-parity-policy.md",
    )

    untrusted = derive_row_coverage(
        _pack(),
        (structural_row, exception_row),
        FamilyCoveragePolicy("example-family", ()),
        (),
    )
    policy_page = tmp_path / "docs" / "policy.md"
    policy_page.parent.mkdir(parents=True)
    policy_page.write_text("# Reviewed exception\n", encoding="utf-8")
    exception_path = tmp_path / "tests" / "conformance" / "policy_exceptions.json"
    exception_path.parent.mkdir(parents=True)
    exception_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "exceptions": [
                    {
                        "id": exception.id,
                        "capabilityId": exception.capability_id,
                        "participantId": exception.participant_id,
                        "rationale": exception.rationale,
                        "policyPage": "docs/policy.md",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    trusted = derive_row_coverage(
        _pack(),
        (structural_row, exception_row),
        FamilyCoveragePolicy("example-family", ()),
        (),
        retained_analyzers=load_retained_analyzer_kinds(REPO_ROOT),
        policy_exceptions=load_policy_exceptions(tmp_path),
    )

    with pytest.raises(CoverageDerivationError, match="permanent repository catalog"):
        derive_row_coverage(
            _pack(),
            (structural_row,),
            FamilyCoveragePolicy("example-family", ()),
            (),
            retained_analyzers={"node-source-and-declaration-parity": "structural"},
        )
    with pytest.raises(CoverageDerivationError, match="reviewed repository catalog"):
        derive_row_coverage(
            _pack(),
            (exception_row,),
            FamilyCoveragePolicy("example-family", ()),
            (),
            policy_exceptions=(exception,),
        )

    assert untrusted.document()["rows"] == []
    assert len(untrusted.document()["failures"]) == 2
    assert {row["evidenceKind"] for row in trusted.document()["rows"]} == {
        "structural",
        "policy-exception",
    }
    assert trusted.document()["failures"] == []


def test_applicability_rejects_dangling_or_duplicate_exception_scopes() -> None:
    """Reviewed exceptions must bind one known participant/capability scope."""

    exception = PolicyException(
        id="example-exception",
        capability_id="example.execute",
        participant_id="cxx",
        rationale="The public capability is intentionally absent.",
        policy_page="docs/api/binding-parity-policy.md",
    )
    duplicate_scope = PolicyException(
        id="same-scope-second-id",
        capability_id="example.execute",
        participant_id="cxx",
        rationale="A duplicate review must not create ambiguous ownership.",
        policy_page="docs/api/binding-parity-policy.md",
    )
    dangling = PolicyException(
        id="dangling-capability",
        capability_id="example.missing",
        participant_id="node",
        rationale="This capability does not exist.",
        policy_page="docs/api/binding-parity-policy.md",
    )

    with pytest.raises(PolicyExceptionError, match="duplicate policy exception scope"):
        derive_applicability(
            _pack(), (), policy_exceptions=(exception, duplicate_scope)
        )
    with pytest.raises(PolicyExceptionError, match="unknown capability"):
        derive_applicability(_pack(), (), policy_exceptions=(dangling,))
