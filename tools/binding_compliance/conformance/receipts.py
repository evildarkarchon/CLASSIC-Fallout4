"""Validate receipts for one prepared invocation and compare its observations."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .applicability import (
    DEFAULT_POLICY_EXCEPTIONS_PATH,
    PolicyExceptionError,
    exception_matches,
    load_policy_exceptions,
)
from .compare import (
    NormalizationError,
    exact_differences,
    normalize_observations,
    validate_display_content_carriers,
)
from .consumers import ConsumerObligationCatalog
from .coverage import (
    CoverageDerivationError,
    FamilyCoveragePolicy,
    derive_observed_fact_ids,
)
from .failures import FailureKind
from .packs import (
    MaterializedRun,
    PackValidationError,
    ValidatedPack,
    load_and_validate_pack,
)
from .schema import (
    ConformanceSchemaError,
    reject_duplicate_json_keys,
    validate_receipt_document,
)

_COVERAGE_PROOF_SEAL = object()


@dataclass(frozen=True)
class ReceiptFailure:
    """One stable prepared-run failure with deterministic diagnostics."""

    kind: FailureKind
    message: str
    scenario_id: str | None = None
    path: str | None = None

    def document(self) -> dict[str, object]:
        """Return the stable machine-readable failure record."""

        return {
            "kind": self.kind.value,
            "scenarioId": self.scenario_id,
            "path": self.path,
            "message": self.message,
        }


@dataclass(frozen=True)
class ScenarioValidationResult:
    """Summarize validation and comparison for one planned scenario."""

    id: str
    execution_status: str
    result: str
    failure_kinds: tuple[FailureKind, ...] = ()
    observed_fact_ids: tuple[str, ...] = ()

    def document(self) -> dict[str, object]:
        """Return the stable machine-readable scenario record."""

        ordered_kinds = sorted(
            set(self.failure_kinds), key=lambda kind: list(FailureKind).index(kind)
        )
        document: dict[str, object] = {
            "id": self.id,
            "executionStatus": self.execution_status,
            "result": self.result,
            "failureKinds": [kind.value for kind in ordered_kinds],
        }
        if self.observed_fact_ids:
            document["observedFactIds"] = list(self.observed_fact_ids)
        return document


@dataclass(frozen=True)
class ObligationValidationResult:
    """Summarize central comparison for one consumer obligation profile."""

    id: str
    execution_status: str
    result: str
    failure_kinds: tuple[FailureKind, ...] = ()

    def document(self) -> dict[str, object]:
        """Return the stable machine-readable obligation result."""

        ordered_kinds = sorted(
            set(self.failure_kinds), key=lambda kind: list(FailureKind).index(kind)
        )
        return {
            "id": self.id,
            "executionStatus": self.execution_status,
            "result": self.result,
            "failureKinds": [kind.value for kind in ordered_kinds],
        }


@dataclass(frozen=True)
class PreparedRunReport:
    """Deterministic receipt result for exactly one prepared invocation."""

    family_id: str
    family_version: int
    expectation_digest: str
    invocation: Mapping[str, Any]
    participant: Mapping[str, Any]
    scenarios: tuple[ScenarioValidationResult, ...]
    failures: tuple[ReceiptFailure, ...]
    obligations: tuple[ObligationValidationResult, ...] = ()
    _coverage_proof_seal: object | None = field(
        default=None, init=False, repr=False, compare=False
    )

    @classmethod
    def _from_plan(
        cls,
        plan: Mapping[str, Any],
        *,
        scenarios: Sequence[ScenarioValidationResult] = (),
        obligations: Sequence[ObligationValidationResult] = (),
        failures: Sequence[ReceiptFailure] = (),
    ) -> PreparedRunReport:
        """Build a report using the immutable identity of one prepared run plan."""

        report = cls(
            family_id=plan["familyId"],
            family_version=plan["familyVersion"],
            expectation_digest=plan["expectationDigest"],
            invocation=plan["invocation"],
            participant=plan["participant"],
            scenarios=tuple(scenarios),
            failures=tuple(failures),
            obligations=tuple(obligations),
        )
        object.__setattr__(report, "_coverage_proof_seal", _COVERAGE_PROOF_SEAL)
        return report

    @property
    def has_trusted_coverage_provenance(self) -> bool:
        """Return whether central receipt validation created this report."""

        return self._coverage_proof_seal is _COVERAGE_PROOF_SEAL

    def document(self) -> dict[str, object]:
        """Return a detached stable report document suitable for aggregation."""

        ordered_failures = sorted(
            self.failures,
            key=lambda failure: (
                list(FailureKind).index(failure.kind),
                failure.scenario_id or "",
                failure.path or "",
                failure.message,
            ),
        )
        document: dict[str, object] = {
            "schemaVersion": 1,
            "scope": "prepared-invocation",
            "familyId": self.family_id,
            "familyVersion": self.family_version,
            "expectationDigest": self.expectation_digest,
            "invocation": dict(self.invocation),
            "participant": dict(self.participant),
            "result": "fail" if self.failures else "pass",
            "scenarios": [scenario.document() for scenario in self.scenarios],
            "failures": [failure.document() for failure in ordered_failures],
        }
        if self.obligations:
            document["obligations"] = [
                obligation.document() for obligation in self.obligations
            ]
        return document

    def json_text(self) -> str:
        """Serialize the report deterministically for CI artifact writers."""

        return (
            json.dumps(self.document(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        )


def _load_receipt(path: Path) -> Mapping[str, Any]:
    """Load one receipt object without yet classifying its current identity."""

    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_json_keys,
    )
    if not isinstance(value, Mapping):
        raise ConformanceSchemaError("receipt schema must be an object")
    return value


def _stale_identity_failures(
    receipt: Mapping[str, Any], plan: Mapping[str, Any]
) -> tuple[ReceiptFailure, ...]:
    """Return receipt identities that differ from the prepared invocation."""

    fields = (
        ("schemaVersion", receipt.get("schemaVersion"), plan["schemaVersion"]),
        ("familyId", receipt.get("familyId"), plan["familyId"]),
        ("familyVersion", receipt.get("familyVersion"), plan["familyVersion"]),
        (
            "expectationDigest",
            receipt.get("expectationDigest"),
            plan["expectationDigest"],
        ),
    )
    stale: list[ReceiptFailure] = []
    for label, actual, expected in fields:
        if actual is not None and actual != expected:
            stale.append(
                ReceiptFailure(
                    FailureKind.STALE_RECEIPT,
                    f"receipt {label} does not match the prepared invocation",
                    path=f"$.{label}",
                )
            )
    receipt_invocation = receipt.get("invocation")
    if isinstance(receipt_invocation, Mapping):
        for label in ("id", "runPlanDigest", "sourceIdentity"):
            actual = receipt_invocation.get(label)
            if actual is not None and actual != plan["invocation"][label]:
                stale.append(
                    ReceiptFailure(
                        FailureKind.STALE_RECEIPT,
                        f"receipt invocation {label} does not match the prepared invocation",
                        path=f"$.invocation.{label}",
                    )
                )
    return tuple(stale)


def _unexpected_evidence_failures(
    receipt: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> tuple[ReceiptFailure, ...]:
    """Reject receipt-controlled identities outside the prepared run plan."""

    failures: list[ReceiptFailure] = []
    receipt_participant = receipt["participant"]
    for participant_field in ("id", "role", "executionInstanceId"):
        if (
            receipt_participant[participant_field]
            != plan["participant"][participant_field]
        ):
            failures.append(
                ReceiptFailure(
                    FailureKind.MALFORMED_RECEIPT,
                    f"receipt participant {participant_field} is unexpected for this prepared run",
                    path=f"$.participant.{participant_field}",
                )
            )

    payload_field = (
        "obligations" if plan["participant"]["role"] == "consumer" else "scenarios"
    )
    planned_items = {item["id"]: item for item in plan[payload_field]}
    receipt_items = receipt[payload_field]
    scenario_ids = [item["id"] for item in receipt_items]
    duplicates = sorted(
        scenario_id
        for scenario_id in set(scenario_ids)
        if scenario_ids.count(scenario_id) > 1
    )
    for scenario_id in duplicates:
        failures.append(
            ReceiptFailure(
                FailureKind.MALFORMED_RECEIPT,
                "receipt contains duplicate scenario execution evidence",
                scenario_id=scenario_id,
            )
        )
    for scenario in receipt_items:
        scenario_id = scenario["id"]
        planned = planned_items.get(scenario_id)
        if planned is None:
            failures.append(
                ReceiptFailure(
                    FailureKind.MALFORMED_RECEIPT,
                    "receipt contains an unexpected scenario identity",
                    scenario_id=scenario_id,
                )
            )
        elif (
            payload_field == "scenarios"
            and scenario["capabilityIds"] != planned["capabilityIds"]
        ):
            failures.append(
                ReceiptFailure(
                    FailureKind.MALFORMED_RECEIPT,
                    "receipt capability identities differ from the run plan",
                    scenario_id=scenario_id,
                    path="$.capabilityIds",
                )
            )
    return tuple(failures)


def _forbidden_status_failures(
    receipt: Mapping[str, Any],
) -> tuple[ReceiptFailure, ...]:
    """Classify adapter-authored skip and unsupported outcomes as policy errors."""

    executions = receipt.get("scenarios", receipt.get("obligations"))
    if not isinstance(executions, list):
        return ()
    failures: list[ReceiptFailure] = []
    for scenario in executions:
        if not isinstance(scenario, Mapping):
            continue
        execution_status = scenario.get("executionStatus")
        if isinstance(execution_status, str) and execution_status in {
            "skipped",
            "unsupported",
        }:
            scenario_id = scenario.get("id")
            failures.append(
                ReceiptFailure(
                    FailureKind.APPLICABILITY,
                    "required execution cannot be skipped or reported as unsupported",
                    scenario_id=scenario_id if isinstance(scenario_id, str) else None,
                    path="$.executionStatus",
                )
            )
    return tuple(failures)


def _current_prepared_input_failures(
    pack: ValidatedPack, run: MaterializedRun
) -> tuple[ReceiptFailure, ...]:
    """Prove the tracked oracle and handed-off plan remain byte-current."""

    failures: list[ReceiptFailure] = []
    try:
        current_pack = load_and_validate_pack(pack.repo_root, pack.pack_path)
    except PackValidationError as error:
        failures.append(
            ReceiptFailure(
                FailureKind.STALE_RECEIPT,
                f"tracked pack or fixture is no longer valid: {error}",
            )
        )
    else:
        if (
            current_pack.canonical_json != pack.canonical_json
            or current_pack.expectation_digest != pack.expectation_digest
        ):
            failures.append(
                ReceiptFailure(
                    FailureKind.STALE_RECEIPT,
                    "tracked pack or fixture changed after run preparation",
                )
            )
    try:
        plan_bytes = run.run_plan_path.read_bytes()
    except OSError as error:
        failures.append(
            ReceiptFailure(
                FailureKind.STALE_RECEIPT,
                f"prepared run plan is no longer readable: {error}",
            )
        )
    else:
        if plan_bytes != run.canonical_json:
            failures.append(
                ReceiptFailure(
                    FailureKind.STALE_RECEIPT,
                    "prepared run plan changed after materialization",
                )
            )
    return tuple(failures)


def validate_prepared_run(
    pack: ValidatedPack,
    run: MaterializedRun,
    *,
    receipt_paths: Sequence[Path] | None = None,
    policy_exceptions_path: Path = DEFAULT_POLICY_EXCEPTIONS_PATH,
    coverage_policy: FamilyCoveragePolicy | None = None,
    consumer_catalog: ConsumerObligationCatalog | None = None,
) -> PreparedRunReport:
    """Validate and exactly compare receipts for one fresh prepared invocation.

    ``receipt_paths`` defaults to the reserved path beside the materialized run
    plan. The report contains failures rather than raising for untrusted adapter
    evidence so later participant and repository aggregators can preserve every
    diagnostic.
    """

    plan = run.document()
    pack_document = pack.document()
    paths = tuple(receipt_paths) if receipt_paths is not None else (run.receipt_path,)
    failures: list[ReceiptFailure] = []
    scenario_results: list[ScenarioValidationResult] = []
    if not run.has_trusted_provenance:
        return PreparedRunReport._from_plan(
            plan,
            failures=(
                ReceiptFailure(
                    FailureKind.STALE_RECEIPT,
                    "prepared run lacks central materialization provenance",
                ),
            ),
        )
    current_input_failures = _current_prepared_input_failures(pack, run)
    if current_input_failures:
        return PreparedRunReport._from_plan(
            plan,
            failures=current_input_failures,
        )
    if not paths:
        failures.append(
            ReceiptFailure(
                FailureKind.MISSING_RECEIPT,
                "the prepared invocation did not produce a receipt",
            )
        )
        return PreparedRunReport._from_plan(
            plan,
            failures=failures,
        )
    if len(paths) > 1:
        failures.append(
            ReceiptFailure(
                FailureKind.MALFORMED_RECEIPT,
                "the prepared invocation produced duplicate receipt evidence",
            )
        )
        return PreparedRunReport._from_plan(
            plan,
            failures=failures,
        )
    receipt_path = next(iter(paths))
    if not receipt_path.is_file():
        failures.append(
            ReceiptFailure(
                FailureKind.MISSING_RECEIPT,
                "the prepared invocation did not produce a receipt",
            )
        )
        return PreparedRunReport._from_plan(
            plan,
            failures=failures,
        )

    try:
        receipt = _load_receipt(receipt_path)
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        ConformanceSchemaError,
    ) as error:
        failures.append(ReceiptFailure(FailureKind.MALFORMED_RECEIPT, str(error)))
        return PreparedRunReport._from_plan(
            plan,
            failures=failures,
        )

    forbidden_status_failures = _forbidden_status_failures(receipt)
    if forbidden_status_failures:
        return PreparedRunReport._from_plan(
            plan,
            failures=forbidden_status_failures,
        )
    try:
        validate_receipt_document(receipt, allow_schema_version_mismatch=True)
    except ConformanceSchemaError as error:
        failures.append(ReceiptFailure(FailureKind.MALFORMED_RECEIPT, str(error)))
        return PreparedRunReport._from_plan(
            plan,
            failures=failures,
        )

    stale_failures = _stale_identity_failures(receipt, plan)
    if stale_failures:
        return PreparedRunReport._from_plan(
            plan,
            failures=stale_failures,
        )

    unexpected_failures = _unexpected_evidence_failures(receipt, plan)
    if unexpected_failures:
        return PreparedRunReport._from_plan(
            plan,
            failures=unexpected_failures,
        )

    if plan["participant"]["role"] == "consumer":
        if consumer_catalog is None or not consumer_catalog.has_trusted_provenance:
            return PreparedRunReport._from_plan(
                plan,
                failures=(
                    ReceiptFailure(
                        FailureKind.APPLICABILITY,
                        "consumer validation requires the repository obligation registry",
                    ),
                ),
            )
        try:
            participant = consumer_catalog.participant(
                str(plan["familyId"]), str(plan["participant"]["id"])
            )
        except ValueError as error:
            return PreparedRunReport._from_plan(
                plan,
                failures=(ReceiptFailure(FailureKind.APPLICABILITY, str(error)),),
            )
        expected_by_id = {
            obligation.id: obligation
            for obligation in participant.obligations
            if obligation.id in {item["id"] for item in plan["obligations"]}
        }
        actual_by_id = {
            obligation["id"]: obligation for obligation in receipt["obligations"]
        }
        obligation_results: list[ObligationValidationResult] = []
        for planned_obligation in plan["obligations"]:
            obligation_id = planned_obligation["id"]
            actual = actual_by_id.get(obligation_id)
            expected = expected_by_id.get(obligation_id)
            if actual is None or expected is None:
                failure = ReceiptFailure(
                    FailureKind.MISSING_RECEIPT,
                    "the required consumer obligation did not produce execution evidence",
                    scenario_id=obligation_id,
                )
                failures.append(failure)
                obligation_results.append(
                    ObligationValidationResult(
                        obligation_id, "missing", "fail", (failure.kind,)
                    )
                )
                continue
            if actual["executionStatus"] == "failed":
                failure = ReceiptFailure(
                    FailureKind.ADAPTER_COMMAND,
                    "consumer execution failed before producing a completed observation",
                    scenario_id=obligation_id,
                )
                failures.append(failure)
                obligation_results.append(
                    ObligationValidationResult(
                        obligation_id, "failed", "fail", (failure.kind,)
                    )
                )
                continue
            differences = exact_differences(expected.expected, actual["observation"])
            obligation_failures = [
                ReceiptFailure(
                    FailureKind.SEMANTIC_MISMATCH,
                    f"consumer obligation observation differs: {difference.kind}",
                    scenario_id=obligation_id,
                    path=difference.path,
                )
                for difference in differences
            ]
            failures.extend(obligation_failures)
            obligation_results.append(
                ObligationValidationResult(
                    obligation_id,
                    "completed",
                    "fail" if obligation_failures else "pass",
                    tuple(failure.kind for failure in obligation_failures),
                )
            )
        return PreparedRunReport._from_plan(
            plan,
            obligations=obligation_results,
            failures=failures,
        )

    receipt_scenarios = {scenario["id"]: scenario for scenario in receipt["scenarios"]}
    observation_families = {
        capability["id"]: frozenset(capability["observationFamilies"])
        for capability in pack_document["capabilities"]
    }
    policy_exceptions = ()
    policy_exception_error: str | None = None
    if any(
        scenario["executionStatus"] == "not_applicable"
        for scenario in receipt["scenarios"]
    ):
        try:
            policy_exceptions = load_policy_exceptions(
                pack.repo_root, policy_exceptions_path
            )
        except PolicyExceptionError as error:
            policy_exception_error = str(error)
    for expected_scenario in pack_document["scenarios"]:
        scenario_id = expected_scenario["id"]
        actual_scenario = receipt_scenarios.get(scenario_id)
        if actual_scenario is None:
            failure = ReceiptFailure(
                FailureKind.MISSING_RECEIPT,
                "the required scenario did not produce execution evidence",
                scenario_id=scenario_id,
            )
            failures.append(failure)
            scenario_results.append(
                ScenarioValidationResult(
                    scenario_id,
                    "missing",
                    "fail",
                    (failure.kind,),
                )
            )
            continue
        if actual_scenario["executionStatus"] == "not_applicable":
            exception_id = actual_scenario["policyExceptionId"]
            exception = next(
                (item for item in policy_exceptions or () if item.id == exception_id),
                None,
            )
            if exception is None or not exception_matches(
                exception,
                participant_id=plan["participant"]["id"],
                capability_ids=actual_scenario["capabilityIds"],
            ):
                failure = ReceiptFailure(
                    FailureKind.APPLICABILITY,
                    policy_exception_error
                    or "not_applicable execution lacks an exactly matching reviewed exception",
                    scenario_id=scenario_id,
                    path="$.policyExceptionId",
                )
                failures.append(failure)
                scenario_results.append(
                    ScenarioValidationResult(
                        scenario_id,
                        "not_applicable",
                        "fail",
                        (failure.kind,),
                    )
                )
            else:
                scenario_results.append(
                    ScenarioValidationResult(
                        scenario_id,
                        "not_applicable",
                        "pass",
                    )
                )
            continue
        if actual_scenario["executionStatus"] == "failed":
            failure = ReceiptFailure(
                FailureKind.ADAPTER_COMMAND,
                "adapter execution failed before producing a completed observation",
                scenario_id=scenario_id,
            )
            failures.append(failure)
            scenario_results.append(
                ScenarioValidationResult(
                    scenario_id,
                    "failed",
                    "fail",
                    (failure.kind,),
                )
            )
            continue
        try:
            expected_observation, actual_observation = normalize_observations(
                expected_scenario["expected"],
                actual_scenario["observation"],
                expected_scenario["normalization"],
                fixture_root=Path(plan["fixtureRoot"]),
            )
            if (
                pack_document["familyId"] == "user-settings"
                and expected_scenario["action"] != "user-settings.open"
            ):
                from .families.user_settings import normalize_operation_observation

                actual_observation = normalize_operation_observation(
                    expected_observation, actual_observation
                )
            if any(
                "display-content" in observation_families[capability_id]
                for capability_id in expected_scenario["capabilityIds"]
            ):
                validate_display_content_carriers(
                    expected_observation, actual_observation
                )
        except NormalizationError as error:
            failure = ReceiptFailure(
                FailureKind.NORMALIZATION,
                str(error),
                scenario_id=scenario_id,
                path=error.path,
            )
            failures.append(failure)
            scenario_results.append(
                ScenarioValidationResult(
                    scenario_id,
                    actual_scenario["executionStatus"],
                    "fail",
                    (failure.kind,),
                )
            )
            continue
        differences = exact_differences(expected_observation, actual_observation)
        scenario_failures = [
            ReceiptFailure(
                FailureKind.SEMANTIC_MISMATCH,
                f"exact observation differs: {difference.kind}",
                scenario_id=scenario_id,
                path=difference.path,
            )
            for difference in differences
        ]
        observed_fact_ids: tuple[str, ...] = ()
        if not scenario_failures and coverage_policy is not None:
            try:
                observed_fact_ids = derive_observed_fact_ids(
                    pack_document,
                    expected_scenario,
                    actual_observation,
                    coverage_policy,
                )
            except CoverageDerivationError as error:
                scenario_failures.append(
                    ReceiptFailure(
                        FailureKind.COVERAGE_MAPPING,
                        str(error),
                        scenario_id=scenario_id,
                    )
                )
        failures.extend(scenario_failures)
        scenario_results.append(
            ScenarioValidationResult(
                scenario_id,
                actual_scenario["executionStatus"],
                "fail" if scenario_failures else "pass",
                tuple(failure.kind for failure in scenario_failures),
                observed_fact_ids,
            )
        )

    return PreparedRunReport._from_plan(
        plan,
        scenarios=scenario_results,
        failures=failures,
    )
