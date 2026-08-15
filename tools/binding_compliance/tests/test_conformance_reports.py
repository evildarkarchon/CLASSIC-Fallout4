"""Behavior tests for honest scoped shadow conformance reports."""

from __future__ import annotations

import copy
from dataclasses import replace

import pytest
from conformance import (
    ApplicabilityMatrix,
    ApplicableParticipant,
    CoverageFailure,
    PreparedRunReport,
    RowCoverageReport,
    build_scoped_report,
    validate_conformance_report_document,
)
from conformance.receipts import ScenarioValidationResult


def _applicability() -> ApplicabilityMatrix:
    """Return a matrix with one multi-instance adapter and one owner adapter."""

    return ApplicabilityMatrix(
        (
            ApplicableParticipant(
                id="cxx",
                role="semantic-adapter",
                execution_instance_ids=("windows-clang-cl", "windows-msvc"),
                capability_ids=("example.execute",),
                scenario_ids=("base-case",),
            ),
            ApplicableParticipant(
                id="rust",
                role="semantic-adapter",
                execution_instance_ids=("rust",),
                capability_ids=("example.execute",),
                scenario_ids=("base-case",),
            ),
        )
    )


def _prepared_report(
    participant: str,
    instance: str,
    *,
    expectation_digest: str | None = None,
    source_revision: str | None = None,
    source_digest: str | None = None,
    scenario_ids: tuple[str, ...] = ("base-case",),
    participant_role: str = "semantic-adapter",
) -> PreparedRunReport:
    """Return one passing prepared-run report for a common source revision."""

    plan = {
        "familyId": "example-family",
        "familyVersion": 1,
        "expectationDigest": expectation_digest or "sha256:" + "a" * 64,
        "invocation": {
            "id": f"invocation-{participant}-{instance}",
            "runPlanDigest": "sha256:" + "b" * 64,
            "sourceIdentity": (
                "git:"
                + (source_revision or "c" * 40)
                + ":sha256:"
                + (source_digest or "d" * 64)
            ),
        },
        "participant": {
            "id": participant,
            "role": participant_role,
            "executionInstanceId": instance,
        },
    }
    return PreparedRunReport._from_plan(
        plan,
        scenarios=tuple(
            ScenarioValidationResult(
                id=scenario_id,
                execution_status="completed",
                result="pass",
                observed_fact_ids=("example.completed",),
            )
            for scenario_id in scenario_ids
        ),
    )


def _passing_coverage(
    *prepared_reports: PreparedRunReport,
) -> RowCoverageReport:
    """Return an empty but centrally derived coverage partition for test rows."""

    return RowCoverageReport._from_derivation(
        "example-family", prepared_reports=prepared_reports
    )


def test_execution_instance_report_cannot_claim_participant_or_repository() -> None:
    """An instance slice reports only its selected execution denominator."""

    report = build_scoped_report(
        family_id="example-family",
        profile="conformance",
        applicability=_applicability(),
        prepared_reports=(
            _prepared_report("cxx", "windows-msvc"),
            _prepared_report("cxx", "windows-clang-cl"),
        ),
        participant_id="cxx",
        execution_instance_id="windows-msvc",
        coverage=_passing_coverage(_prepared_report("cxx", "windows-msvc")),
    )

    document = report.document()
    assert document["scope"] == {
        "kind": "execution-instance",
        "participantId": "cxx",
        "executionInstanceId": "windows-msvc",
    }
    assert document["result"] == "pass"
    assert document["repositoryComplete"] is False
    assert document["requiredExecutions"] == [
        {"participantId": "cxx", "executionInstanceId": "windows-msvc"}
    ]
    assert document["receivedExecutions"] == document["requiredExecutions"]


def test_participant_report_requires_every_applicable_execution_instance() -> None:
    """One successful CXX toolchain cannot pass the participant denominator."""

    report = build_scoped_report(
        family_id="example-family",
        profile="conformance",
        applicability=_applicability(),
        prepared_reports=(_prepared_report("cxx", "windows-msvc"),),
        participant_id="cxx",
        coverage=_passing_coverage(_prepared_report("cxx", "windows-msvc")),
    )

    document = report.document()
    assert document["scope"] == {
        "kind": "participant",
        "participantId": "cxx",
        "executionInstanceId": None,
    }
    assert document["result"] == "fail"
    assert document["repositoryComplete"] is False
    assert document["missingExecutions"] == [
        {"participantId": "cxx", "executionInstanceId": "windows-clang-cl"}
    ]


def test_full_report_is_the_only_repository_complete_scope() -> None:
    """A full exact denominator may claim repository-wide conformance."""

    reports = (
        _prepared_report("cxx", "windows-clang-cl"),
        _prepared_report("cxx", "windows-msvc"),
        _prepared_report("rust", "rust"),
    )

    report = build_scoped_report(
        family_id="example-family",
        profile="full",
        applicability=_applicability(),
        prepared_reports=reports,
        coverage=_passing_coverage(*reports),
    )

    document = report.document()
    assert document["scope"] == {
        "kind": "full-repository",
        "participantId": None,
        "executionInstanceId": None,
    }
    assert document["result"] == "pass"
    assert document["repositoryComplete"] is True
    assert (
        report.json_text()
        == build_scoped_report(
            family_id="example-family",
            profile="full",
            applicability=_applicability(),
            prepared_reports=tuple(reversed(reports)),
            coverage=_passing_coverage(*reports),
        ).json_text()
    )


def test_full_report_accepts_distinct_digests_from_one_source_revision() -> None:
    """Participant-specific source roots may differ within one current commit."""

    reports = (
        _prepared_report(
            "cxx",
            "windows-clang-cl",
            source_digest="1" * 64,
        ),
        _prepared_report(
            "cxx",
            "windows-msvc",
            source_digest="2" * 64,
        ),
        _prepared_report("rust", "rust", source_digest="3" * 64),
    )

    document = build_scoped_report(
        family_id="example-family",
        profile="full",
        applicability=_applicability(),
        prepared_reports=reports,
        coverage=_passing_coverage(*reports),
    ).document()

    assert document["result"] == "pass"
    assert document["repositoryComplete"] is True


def test_full_report_rejects_mixed_source_revisions() -> None:
    """Individually current receipts from different commits cannot aggregate."""

    reports = (
        _prepared_report("cxx", "windows-clang-cl"),
        _prepared_report("cxx", "windows-msvc"),
        _prepared_report("rust", "rust", source_revision="e" * 40),
    )

    document = build_scoped_report(
        family_id="example-family",
        profile="full",
        applicability=_applicability(),
        prepared_reports=reports,
        coverage=_passing_coverage(*reports),
    ).document()

    assert document["result"] == "fail"
    assert [failure["kind"] for failure in document["failures"]] == [
        "stale_execution_receipt"
    ]


def test_report_validator_rejects_a_broadened_completeness_claim() -> None:
    """A valid participant report cannot be relabeled repository-complete."""

    report = build_scoped_report(
        family_id="example-family",
        profile="conformance",
        applicability=_applicability(),
        prepared_reports=(
            _prepared_report("cxx", "windows-clang-cl"),
            _prepared_report("cxx", "windows-msvc"),
        ),
        participant_id="cxx",
        coverage=_passing_coverage(
            _prepared_report("cxx", "windows-clang-cl"),
            _prepared_report("cxx", "windows-msvc"),
        ),
    ).document()
    validate_conformance_report_document(report)
    broadened = copy.deepcopy(report)
    broadened["repositoryComplete"] = True

    with pytest.raises(ValueError, match="full-repository"):
        validate_conformance_report_document(broadened)


def test_scoped_report_exposes_coverage_gaps_in_shadow_result() -> None:
    """A row gap is visible but remains inside the shadow report envelope."""

    prepared_reports = (
        _prepared_report("cxx", "windows-clang-cl"),
        _prepared_report("cxx", "windows-msvc"),
        _prepared_report("rust", "rust"),
    )
    coverage = RowCoverageReport._from_derivation(
        "example-family",
        prepared_reports=prepared_reports,
        failures=(
            CoverageFailure(
                obligation_id="parity:cxx:new-row",
                message="source parity row lacks executable coverage",
                blocking=True,
            ),
        ),
    )
    report = build_scoped_report(
        family_id="example-family",
        profile="full",
        applicability=_applicability(),
        prepared_reports=prepared_reports,
        coverage=coverage,
    )

    document = report.document()
    assert document["result"] == "fail"
    assert document["repositoryComplete"] is False
    assert document["coverage"]["failures"][0]["kind"] == "coverage_mapping_gap"


def test_aggregation_rejects_mixed_expectations_and_missing_scenarios() -> None:
    """A passing label cannot hide stale oracle identity or a partial scenario set."""

    clang_report = _prepared_report(
        "cxx",
        "windows-clang-cl",
        expectation_digest="sha256:" + "e" * 64,
    )
    msvc_report = _prepared_report("cxx", "windows-msvc", scenario_ids=())

    document = build_scoped_report(
        family_id="example-family",
        profile="conformance",
        applicability=_applicability(),
        prepared_reports=(clang_report, msvc_report),
        participant_id="cxx",
        coverage=_passing_coverage(clang_report, msvc_report),
    ).document()

    assert document["result"] == "fail"
    assert {failure["kind"] for failure in document["failures"]} == {
        "missing_execution_receipt",
        "stale_execution_receipt",
    }
    validate_conformance_report_document(document)


def test_report_validator_closes_coverage_rows_and_failures() -> None:
    """Nested coverage evidence cannot admit self-asserted selector metadata."""

    prepared_reports = (
        _prepared_report("cxx", "windows-clang-cl"),
        _prepared_report("cxx", "windows-msvc"),
    )
    coverage = RowCoverageReport._from_derivation(
        "example-family",
        prepared_reports=prepared_reports,
        failures=(
            CoverageFailure(
                obligation_id="parity:cxx:new-row",
                message="source parity row lacks executable coverage",
                blocking=True,
            ),
        ),
    )
    report = build_scoped_report(
        family_id="example-family",
        profile="conformance",
        applicability=_applicability(),
        prepared_reports=prepared_reports,
        participant_id="cxx",
        coverage=coverage,
    ).document()
    validate_conformance_report_document(report)
    report["coverage"]["failures"][0]["selectorHash"] = "invented"

    with pytest.raises(ValueError, match="unexpected selectorHash"):
        validate_conformance_report_document(report)


def test_missing_coverage_cannot_pass_or_claim_repository_completeness() -> None:
    """Receipt completeness alone is not a source-row coverage partition."""

    report = build_scoped_report(
        family_id="example-family",
        profile="full",
        applicability=_applicability(),
        prepared_reports=(
            _prepared_report("cxx", "windows-clang-cl"),
            _prepared_report("cxx", "windows-msvc"),
            _prepared_report("rust", "rust"),
        ),
    ).document()

    assert report["result"] == "fail"
    assert report["repositoryComplete"] is False
    assert report["coverage"] is None
    validate_conformance_report_document(report)


def test_caller_constructed_prepared_report_cannot_enter_aggregation() -> None:
    """A report-shaped Python object cannot counterfeit receipt validation."""

    invented = PreparedRunReport(
        family_id="example-family",
        family_version=1,
        expectation_digest="sha256:" + "a" * 64,
        invocation={"sourceIdentity": "git:" + "c" * 40 + ":sha256:" + "d" * 64},
        participant={
            "id": "rust",
            "role": "semantic-adapter",
            "executionInstanceId": "rust",
        },
        scenarios=(),
        failures=(),
    )

    with pytest.raises(ValueError, match="centrally validated"):
        build_scoped_report(
            family_id="example-family",
            profile="full",
            applicability=_applicability(),
            prepared_reports=(invented,),
            coverage=_passing_coverage(),
        )

    replaced_coverage = replace(_passing_coverage())
    with pytest.raises(ValueError, match="centrally derived row coverage"):
        build_scoped_report(
            family_id="example-family",
            profile="full",
            applicability=_applicability(),
            prepared_reports=(),
            coverage=replaced_coverage,
        )


def test_consumer_role_cannot_satisfy_a_semantic_participant_scope() -> None:
    """Participant and instance names do not erase the source-derived role."""

    report = build_scoped_report(
        family_id="example-family",
        profile="conformance",
        applicability=_applicability(),
        prepared_reports=(
            _prepared_report(
                "cxx",
                "windows-msvc",
                participant_role="consumer",
            ),
        ),
        participant_id="cxx",
        execution_instance_id="windows-msvc",
        coverage=_passing_coverage(
            _prepared_report(
                "cxx",
                "windows-msvc",
                participant_role="consumer",
            )
        ),
    ).document()

    assert report["result"] == "fail"
    assert report["failures"][0]["kind"] == "applicability_violation"


def test_coverage_cannot_be_reused_for_different_prepared_evidence() -> None:
    """A legitimate coverage result is bound to its exact validated receipt set."""

    selected = _prepared_report("cxx", "windows-msvc")
    different_evidence = _prepared_report(
        "cxx",
        "windows-msvc",
        expectation_digest="sha256:" + "e" * 64,
    )

    report = build_scoped_report(
        family_id="example-family",
        profile="conformance",
        applicability=_applicability(),
        prepared_reports=(selected,),
        participant_id="cxx",
        execution_instance_id="windows-msvc",
        coverage=_passing_coverage(different_evidence),
    ).document()

    assert report["result"] == "fail"
    assert report["failures"][0]["kind"] == "coverage_mapping_gap"
