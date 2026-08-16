"""Aggregate prepared invocations into honest scoped shadow reports."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .applicability import ApplicabilityMatrix
from .consumers import ConsumerCoverageReport
from .coverage import RowCoverageReport, prepared_report_evidence_digest
from .failures import FailureKind
from .receipts import PreparedRunReport

_SOURCE_IDENTITY = re.compile(
    r"^git:(?P<revision>[0-9a-f]{40,64}):sha256:[0-9a-f]{64}$"
)


class ReportScopeError(ValueError):
    """Raised when a requested report scope could overclaim its evidence."""


@dataclass(frozen=True, order=True)
class RequiredExecution:
    """One participant and execution-instance denominator entry."""

    participant_id: str
    execution_instance_id: str

    def document(self) -> dict[str, str]:
        """Return the stable execution identity."""

        return {
            "participantId": self.participant_id,
            "executionInstanceId": self.execution_instance_id,
        }


@dataclass(frozen=True)
class ScopedReportFailure:
    """One aggregation failure tied to an optional execution identity."""

    kind: FailureKind
    message: str
    participant_id: str | None = None
    execution_instance_id: str | None = None

    def document(self) -> dict[str, object]:
        """Return the stable machine-readable aggregation failure."""

        return {
            "kind": self.kind.value,
            "participantId": self.participant_id,
            "executionInstanceId": self.execution_instance_id,
            "message": self.message,
        }


@dataclass(frozen=True)
class ScopedConformanceReport:
    """A deterministic shadow report whose scope is derived from evidence."""

    family_id: str
    scope_kind: str
    participant_id: str | None
    execution_instance_id: str | None
    required_executions: tuple[RequiredExecution, ...]
    received_executions: tuple[RequiredExecution, ...]
    failures: tuple[ScopedReportFailure, ...]
    coverage: RowCoverageReport | None = None
    consumer_coverage: ConsumerCoverageReport | None = None

    def document(self) -> dict[str, object]:
        """Return the closed report envelope for CI artifacts and rollups."""

        required = tuple(sorted(self.required_executions))
        received = tuple(sorted(self.received_executions))
        received_set = set(received)
        missing = tuple(item for item in required if item not in received_set)
        ordered_failures = sorted(
            self.failures,
            key=lambda failure: (
                list(FailureKind).index(failure.kind),
                failure.participant_id or "",
                failure.execution_instance_id or "",
                failure.message,
            ),
        )
        coverage_document = (
            self.coverage.document() if self.coverage is not None else None
        )
        consumer_coverage_document = (
            self.consumer_coverage.document()
            if self.consumer_coverage is not None
            else None
        )
        passed = (
            not missing
            and not ordered_failures
            and (coverage_document is None or coverage_document["result"] == "pass")
            and (
                consumer_coverage_document is None
                or consumer_coverage_document["result"] == "pass"
            )
        )
        document: dict[str, object] = {
            "schemaVersion": 1,
            "familyId": self.family_id,
            "enforcement": "shadow",
            "scope": {
                "kind": self.scope_kind,
                "participantId": self.participant_id,
                "executionInstanceId": self.execution_instance_id,
            },
            "result": "pass" if passed else "fail",
            "repositoryComplete": self.scope_kind == "full-repository" and passed,
            "requiredExecutions": [item.document() for item in required],
            "receivedExecutions": [item.document() for item in received],
            "missingExecutions": [item.document() for item in missing],
            "failures": [failure.document() for failure in ordered_failures],
            "coverage": coverage_document,
            "consumerCoverage": consumer_coverage_document,
        }
        return document

    def json_text(self) -> str:
        """Serialize the scoped report deterministically."""

        return (
            json.dumps(self.document(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        )


def _required_executions(
    applicability: ApplicabilityMatrix,
) -> tuple[RequiredExecution, ...]:
    """Flatten the source-derived applicability denominator."""

    return tuple(
        RequiredExecution(participant.id, instance_id)
        for participant in applicability.participants
        for instance_id in participant.execution_instance_ids
    )


def _source_revision(source_identity: object) -> str | None:
    """Extract the common Git revision from one validated source identity."""

    if not isinstance(source_identity, str):
        return None
    match = _SOURCE_IDENTITY.fullmatch(source_identity)
    return match.group("revision") if match is not None else None


def build_scoped_report(
    *,
    family_id: str,
    profile: str,
    applicability: ApplicabilityMatrix,
    prepared_reports: Sequence[PreparedRunReport],
    participant_id: str | None = None,
    execution_instance_id: str | None = None,
    coverage: RowCoverageReport | None = None,
    consumer_coverage: ConsumerCoverageReport | None = None,
) -> ScopedConformanceReport:
    """Build an instance, participant, or full-repository shadow report.

    Instance scope requires the exact named tuple. Participant scope expands to
    every source-derived instance for that participant. Only ``full`` expands to
    the complete applicability matrix; selectors are rejected there so a caller
    cannot attach a repository label to a partial denominator.
    """

    if coverage is not None:
        if not coverage.has_trusted_provenance:
            raise ReportScopeError(
                "scoped reports require centrally derived row coverage"
            )
        if coverage.family_id != family_id:
            raise ReportScopeError(
                "row coverage family does not match the report family"
            )
    if consumer_coverage is not None:
        if not consumer_coverage.has_trusted_provenance:
            raise ReportScopeError(
                "scoped reports require centrally derived consumer coverage"
            )
        if consumer_coverage.family_id != family_id:
            raise ReportScopeError(
                "consumer coverage family does not match the report family"
            )
    all_required = _required_executions(applicability)
    if profile == "conformance":
        if participant_id is None:
            raise ReportScopeError(
                "conformance profile requires an applicable participant"
            )
        participant_required = tuple(
            item for item in all_required if item.participant_id == participant_id
        )
        if not participant_required:
            raise ReportScopeError(
                f"participant {participant_id} is not applicable to family {family_id}"
            )
        if execution_instance_id is not None:
            required = tuple(
                item
                for item in participant_required
                if item.execution_instance_id == execution_instance_id
            )
            if not required:
                raise ReportScopeError(
                    f"execution instance {execution_instance_id} is not applicable to participant {participant_id}"
                )
            scope_kind = "execution-instance"
        else:
            required = participant_required
            scope_kind = "participant"
    elif profile == "full":
        if participant_id is not None or execution_instance_id is not None:
            raise ReportScopeError("full profile does not accept partial selectors")
        required = all_required
        scope_kind = "full-repository"
    else:
        raise ReportScopeError(
            "scoped conformance reports require profile conformance or full"
        )

    required_set = set(required)
    participants_by_id = {
        participant.id: participant for participant in applicability.participants
    }
    report_keys: list[RequiredExecution] = []
    selected_reports: list[PreparedRunReport] = []
    failures: list[ScopedReportFailure] = []
    required_roles = {participants_by_id[item.participant_id].role for item in required}
    if "semantic-adapter" in required_roles and coverage is None:
        failures.append(
            ScopedReportFailure(
                FailureKind.COVERAGE_MAPPING,
                "scoped conformance requires centrally derived source-row coverage",
            )
        )
    if "consumer" in required_roles and consumer_coverage is None:
        failures.append(
            ScopedReportFailure(
                FailureKind.COVERAGE_MAPPING,
                "scoped conformance requires centrally derived consumer obligation coverage",
            )
        )
    for report in prepared_reports:
        if (
            not isinstance(report, PreparedRunReport)
            or not report.has_trusted_coverage_provenance
        ):
            raise ReportScopeError(
                "scoped reports accept only centrally validated prepared reports"
            )
        participant = report.participant
        report_participant = participant.get("id")
        report_instance = participant.get("executionInstanceId")
        if not isinstance(report_participant, str) or not isinstance(
            report_instance, str
        ):
            continue
        key = RequiredExecution(report_participant, report_instance)
        if key not in required_set:
            continue
        report_keys.append(key)
        selected_reports.append(report)

    duplicate_keys = sorted(
        key for key, count in Counter(report_keys).items() if count > 1
    )
    for key in duplicate_keys:
        failures.append(
            ScopedReportFailure(
                FailureKind.MALFORMED_RECEIPT,
                "duplicate prepared invocation evidence for one required execution",
                key.participant_id,
                key.execution_instance_id,
            )
        )

    received = tuple(sorted(set(report_keys)))
    semantic_selected_reports = tuple(
        report
        for report in selected_reports
        if report.participant.get("role") == "semantic-adapter"
    )
    consumer_selected_reports = tuple(
        report
        for report in selected_reports
        if report.participant.get("role") == "consumer"
    )
    received_coverage_keys = {
        (
            str(report.participant["id"]),
            str(report.participant["executionInstanceId"]),
        )
        for report in semantic_selected_reports
    }
    if coverage is not None and (
        set(coverage.execution_keys) != received_coverage_keys
        or coverage.prepared_evidence_digest
        != prepared_report_evidence_digest(semantic_selected_reports)
    ):
        failures.append(
            ScopedReportFailure(
                FailureKind.COVERAGE_MAPPING,
                "row coverage is not bound to the selected prepared execution evidence",
            )
        )
    received_consumer_coverage_keys = {
        (
            str(report.participant["id"]),
            str(report.participant["executionInstanceId"]),
        )
        for report in consumer_selected_reports
    }
    if consumer_coverage is not None and (
        set(consumer_coverage.execution_keys) != received_consumer_coverage_keys
        or consumer_coverage.prepared_evidence_digest
        != prepared_report_evidence_digest(consumer_selected_reports)
    ):
        failures.append(
            ScopedReportFailure(
                FailureKind.COVERAGE_MAPPING,
                "consumer coverage is not bound to the selected prepared execution evidence",
            )
        )
    for missing in sorted(required_set - set(received)):
        failures.append(
            ScopedReportFailure(
                FailureKind.MISSING_RECEIPT,
                "required execution did not produce prepared invocation evidence",
                missing.participant_id,
                missing.execution_instance_id,
            )
        )
    source_revisions: set[str] = set()
    expectation_identities: set[tuple[object, object]] = set()
    for report in selected_reports:
        participant = report.participant
        key = RequiredExecution(
            str(participant["id"]), str(participant["executionInstanceId"])
        )
        if participant.get("role") != participants_by_id[key.participant_id].role:
            failures.append(
                ScopedReportFailure(
                    FailureKind.APPLICABILITY,
                    "prepared report role does not match source-derived applicability",
                    key.participant_id,
                    key.execution_instance_id,
                )
            )
        if report.family_id != family_id:
            failures.append(
                ScopedReportFailure(
                    FailureKind.STALE_RECEIPT,
                    "prepared report family does not match the scoped family",
                    key.participant_id,
                    key.execution_instance_id,
                )
            )
        expectation_identities.add((report.family_version, report.expectation_digest))
        invocation = report.invocation
        source_revision = (
            _source_revision(invocation.get("sourceIdentity"))
            if isinstance(invocation, Mapping)
            else None
        )
        if source_revision is None:
            failures.append(
                ScopedReportFailure(
                    FailureKind.STALE_RECEIPT,
                    "prepared invocation has no valid current source identity",
                    key.participant_id,
                    key.execution_instance_id,
                )
            )
        else:
            source_revisions.add(source_revision)
        if report.failures:
            failures.append(
                ScopedReportFailure(
                    FailureKind.SEMANTIC_MISMATCH,
                    "prepared invocation did not pass current receipt validation",
                    key.participant_id,
                    key.execution_instance_id,
                )
            )
        expected_participant = participants_by_id[key.participant_id]
        if expected_participant.role == "consumer":
            expected_evidence = set(expected_participant.obligation_ids)
            actual_evidence = [obligation.id for obligation in report.obligations]
            evidence_label = "consumer obligation"
        else:
            expected_evidence = set(expected_participant.scenario_ids)
            actual_evidence = [scenario.id for scenario in report.scenarios]
            evidence_label = "scenario"
        if (
            len(actual_evidence) != len(set(actual_evidence))
            or set(actual_evidence) != expected_evidence
        ):
            failures.append(
                ScopedReportFailure(
                    FailureKind.MISSING_RECEIPT,
                    f"prepared invocation does not contain the exact applicable {evidence_label} set",
                    key.participant_id,
                    key.execution_instance_id,
                )
            )
    if len(source_revisions) > 1:
        failures.append(
            ScopedReportFailure(
                FailureKind.STALE_RECEIPT,
                "scoped reports must describe one common Git revision",
            )
        )
    if len(expectation_identities) > 1:
        failures.append(
            ScopedReportFailure(
                FailureKind.STALE_RECEIPT,
                "scoped reports must describe one family version and expectation digest",
            )
        )

    return ScopedConformanceReport(
        family_id=family_id,
        scope_kind=scope_kind,
        participant_id=participant_id,
        execution_instance_id=execution_instance_id,
        required_executions=required,
        received_executions=received,
        failures=tuple(failures),
        coverage=coverage,
        consumer_coverage=consumer_coverage,
    )
