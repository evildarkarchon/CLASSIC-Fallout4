"""Common structural validation for conformance JSON documents."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, TypeGuard

from .failures import FailureKind

_STABLE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_UUID_V4 = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_SOURCE_IDENTITY = re.compile(r"^git:[0-9a-f]{40,64}:sha256:[0-9a-f]{64}$")


class ConformanceSchemaError(ValueError):
    """Raised when a conformance document violates its closed common schema."""


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build a JSON object while rejecting ambiguous duplicate field names."""

    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ConformanceSchemaError(f"duplicate JSON object key {key!r}")
        value[key] = item
    return value


def is_stable_machine_id(value: object) -> TypeGuard[str]:
    """Return whether a value uses the shared conformance identity grammar."""

    return isinstance(value, str) and _STABLE_ID.fullmatch(value) is not None


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    """Return an object-shaped schema value or raise a stable diagnostic."""

    if not isinstance(value, Mapping):
        raise ConformanceSchemaError(f"{label} must be an object")
    return value


def _list(value: object, label: str) -> list[Any]:
    """Return an array-shaped schema value or raise a stable diagnostic."""

    if not isinstance(value, list):
        raise ConformanceSchemaError(f"{label} must be an array")
    return value


def _exact_keys(value: Mapping[str, Any], required: frozenset[str], label: str) -> None:
    """Require all and only the common fields owned by one schema object."""

    missing = sorted(required - value.keys())
    unexpected = sorted(value.keys() - required)
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected {', '.join(unexpected)}")
        raise ConformanceSchemaError(f"{label} has " + "; ".join(details))


def _positive_integer(value: object, label: str, *, exact: int | None = None) -> int:
    """Return a positive JSON integer, optionally pinned to one schema version."""

    if type(value) is not int or value < 1 or (exact is not None and value != exact):
        expectation = str(exact) if exact is not None else "a positive integer"
        raise ConformanceSchemaError(f"{label} must be {expectation}")
    return value


def _nonempty_string(value: object, label: str) -> str:
    """Return a non-empty string without silently trimming source content."""

    if not isinstance(value, str) or not value.strip():
        raise ConformanceSchemaError(f"{label} must be a non-empty string")
    return value


def _pattern_string(value: object, label: str, pattern: re.Pattern[str]) -> str:
    """Return a string matching one frozen schema pattern."""

    result = _nonempty_string(value, label)
    if pattern.fullmatch(result) is None:
        raise ConformanceSchemaError(f"{label} has an invalid format")
    return result


def _reject_floating_point_values(value: object, label: str) -> None:
    """Reject floating-point values anywhere in common receipt observations."""

    if isinstance(value, float):
        raise ConformanceSchemaError(f"{label} contains a floating-point value")
    if isinstance(value, Mapping):
        for key, child in value.items():
            _reject_floating_point_values(child, f"{label}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_floating_point_values(child, f"{label}[{index}]")


def _string_array(value: object, label: str, *, nonempty: bool = False) -> list[str]:
    """Return an array of strings and enforce any schema-level cardinality."""

    values = _list(value, label)
    if nonempty and not values:
        raise ConformanceSchemaError(f"{label} must not be empty")
    if not all(isinstance(item, str) and item for item in values):
        raise ConformanceSchemaError(f"{label} must contain non-empty strings")
    if len(values) != len(set(values)):
        raise ConformanceSchemaError(f"{label} must contain unique strings")
    return values


def _validate_normalization_envelope(value: object, label: str) -> None:
    """Validate the common narrow-normalization object shared by packs and plans.

    Raises ``ConformanceSchemaError`` when the value is not the closed version-one
    normalization envelope.
    """

    normalization = _mapping(value, label)
    _exact_keys(
        normalization,
        frozenset({"rootRelativePaths", "unorderedPaths", "excludedPaths"}),
        label,
    )
    if not isinstance(normalization["rootRelativePaths"], bool):
        raise ConformanceSchemaError(f"{label}.rootRelativePaths must be boolean")
    _string_array(normalization["unorderedPaths"], f"{label}.unorderedPaths")
    exclusions = _list(normalization["excludedPaths"], f"{label}.excludedPaths")
    for exclusion_index, raw_exclusion in enumerate(exclusions):
        exclusion_label = f"{label}.excludedPaths[{exclusion_index}]"
        exclusion = _mapping(raw_exclusion, exclusion_label)
        _exact_keys(exclusion, frozenset({"path", "rationale"}), exclusion_label)
        _nonempty_string(exclusion["path"], f"{exclusion_label}.path")
        _nonempty_string(exclusion["rationale"], f"{exclusion_label}.rationale")


def validate_pack_document(document: Mapping[str, Any]) -> None:
    """Validate the closed common structure of a version-one scenario pack.

    Family-specific input and expectation payloads remain opaque JSON objects;
    generic validation owns only their envelope and the cross-adapter metadata.
    Raises ``ConformanceSchemaError`` when any common field violates that
    version-one contract.
    """

    prefix = "pack schema"
    _exact_keys(
        document,
        frozenset(
            {
                "schemaVersion",
                "familyId",
                "familyVersion",
                "domainOwner",
                "fixtureRoot",
                "fixtures",
                "capabilities",
                "scenarios",
                "consumerObligations",
            }
        ),
        prefix,
    )
    _positive_integer(document["schemaVersion"], f"{prefix}.schemaVersion", exact=1)
    _positive_integer(document["familyVersion"], f"{prefix}.familyVersion")
    _nonempty_string(document["familyId"], f"{prefix}.familyId")
    _nonempty_string(document["fixtureRoot"], f"{prefix}.fixtureRoot")

    owner = _mapping(document["domainOwner"], f"{prefix}.domainOwner")
    _exact_keys(owner, frozenset({"rustCrate"}), f"{prefix}.domainOwner")
    _nonempty_string(owner["rustCrate"], f"{prefix}.domainOwner.rustCrate")

    fixtures = _mapping(document["fixtures"], f"{prefix}.fixtures")
    for reference, path in fixtures.items():
        _nonempty_string(reference, f"{prefix}.fixtures reference")
        _nonempty_string(path, f"{prefix}.fixtures.{reference}")

    capabilities = _list(document["capabilities"], f"{prefix}.capabilities")
    if not capabilities:
        raise ConformanceSchemaError(f"{prefix}.capabilities must not be empty")
    for index, raw_capability in enumerate(capabilities):
        label = f"{prefix}.capabilities[{index}]"
        capability = _mapping(raw_capability, label)
        _exact_keys(
            capability,
            frozenset({"id", "rustSymbols", "observationFamilies"}),
            label,
        )
        _nonempty_string(capability["id"], f"{label}.id")
        _string_array(capability["rustSymbols"], f"{label}.rustSymbols", nonempty=True)
        _string_array(
            capability["observationFamilies"],
            f"{label}.observationFamilies",
            nonempty=True,
        )

    scenarios = _list(document["scenarios"], f"{prefix}.scenarios")
    if not scenarios:
        raise ConformanceSchemaError(f"{prefix}.scenarios must not be empty")
    scenario_keys = frozenset(
        {
            "id",
            "action",
            "capabilityIds",
            "fixtureRefs",
            "input",
            "expected",
            "normalization",
        }
    )
    for index, raw_scenario in enumerate(scenarios):
        label = f"{prefix}.scenarios[{index}]"
        scenario = _mapping(raw_scenario, label)
        _exact_keys(scenario, scenario_keys, label)
        _nonempty_string(scenario["id"], f"{label}.id")
        _nonempty_string(scenario["action"], f"{label}.action")
        _string_array(
            scenario["capabilityIds"], f"{label}.capabilityIds", nonempty=True
        )
        _string_array(scenario["fixtureRefs"], f"{label}.fixtureRefs")
        _mapping(scenario["input"], f"{label}.input")
        _mapping(scenario["expected"], f"{label}.expected")
        _validate_normalization_envelope(
            scenario["normalization"], f"{label}.normalization"
        )

    obligations = _list(
        document["consumerObligations"], f"{prefix}.consumerObligations"
    )
    for index, raw_obligation in enumerate(obligations):
        label = f"{prefix}.consumerObligations[{index}]"
        obligation = _mapping(raw_obligation, label)
        _exact_keys(obligation, frozenset({"id"}), label)
        _nonempty_string(obligation["id"], f"{label}.id")


def validate_run_plan_document(document: Mapping[str, Any]) -> None:
    """Validate the closed, input-only structure of a materialized run plan.

    Raises ``ConformanceSchemaError`` when a common plan field is missing,
    unknown, or invalid.
    """

    prefix = "run-plan schema"
    _exact_keys(
        document,
        frozenset(
            {
                "schemaVersion",
                "familyId",
                "familyVersion",
                "expectationDigest",
                "fixtureRoot",
                "fixtures",
                "sourcePaths",
                "participant",
                "invocation",
                "scenarios",
            }
        ),
        prefix,
    )
    _positive_integer(document["schemaVersion"], f"{prefix}.schemaVersion", exact=1)
    _positive_integer(document["familyVersion"], f"{prefix}.familyVersion")
    for field in ("familyId", "expectationDigest", "fixtureRoot"):
        _nonempty_string(document[field], f"{prefix}.{field}")

    fixtures = _mapping(document["fixtures"], f"{prefix}.fixtures")
    for reference, path in fixtures.items():
        _nonempty_string(reference, f"{prefix}.fixtures reference")
        _nonempty_string(path, f"{prefix}.fixtures.{reference}")

    _string_array(document["sourcePaths"], f"{prefix}.sourcePaths", nonempty=True)

    participant = _mapping(document["participant"], f"{prefix}.participant")
    _exact_keys(
        participant,
        frozenset({"id", "role", "executionInstanceId"}),
        f"{prefix}.participant",
    )
    for field in ("id", "role", "executionInstanceId"):
        _nonempty_string(participant[field], f"{prefix}.participant.{field}")

    invocation = _mapping(document["invocation"], f"{prefix}.invocation")
    _exact_keys(
        invocation,
        frozenset({"id", "sourceIdentity", "runPlanDigest"}),
        f"{prefix}.invocation",
    )
    for field in ("id", "sourceIdentity", "runPlanDigest"):
        _nonempty_string(invocation[field], f"{prefix}.invocation.{field}")

    scenarios = _list(document["scenarios"], f"{prefix}.scenarios")
    if not scenarios:
        raise ConformanceSchemaError(f"{prefix}.scenarios must not be empty")
    scenario_keys = frozenset(
        {"id", "action", "capabilityIds", "fixtureRefs", "input", "normalization"}
    )
    for index, raw_scenario in enumerate(scenarios):
        label = f"{prefix}.scenarios[{index}]"
        scenario = _mapping(raw_scenario, label)
        _exact_keys(scenario, scenario_keys, label)
        _nonempty_string(scenario["id"], f"{label}.id")
        _nonempty_string(scenario["action"], f"{label}.action")
        _string_array(
            scenario["capabilityIds"], f"{label}.capabilityIds", nonempty=True
        )
        _string_array(scenario["fixtureRefs"], f"{label}.fixtureRefs")
        _mapping(scenario["input"], f"{label}.input")
        _validate_normalization_envelope(
            scenario["normalization"], f"{label}.normalization"
        )


def validate_receipt_document(
    document: Mapping[str, Any],
    *,
    allow_schema_version_mismatch: bool = False,
) -> None:
    """Validate the closed common structure of a version-one execution receipt.

    Family-specific observations remain opaque JSON objects. Raises
    ``ConformanceSchemaError`` when common execution evidence is incomplete or
    has an invalid type. ``allow_schema_version_mismatch`` lets current-launch
    validation distinguish a well-formed older schema identity from malformed
    evidence without trusting a differently shaped envelope.
    """

    prefix = "receipt schema"
    _exact_keys(
        document,
        frozenset(
            {
                "schemaVersion",
                "familyId",
                "familyVersion",
                "expectationDigest",
                "invocation",
                "participant",
                "runner",
                "scenarios",
            }
        ),
        prefix,
    )
    _positive_integer(
        document["schemaVersion"],
        f"{prefix}.schemaVersion",
        exact=None if allow_schema_version_mismatch else 1,
    )
    _positive_integer(document["familyVersion"], f"{prefix}.familyVersion")
    _pattern_string(document["familyId"], f"{prefix}.familyId", _STABLE_ID)
    _pattern_string(
        document["expectationDigest"], f"{prefix}.expectationDigest", _SHA256
    )

    invocation = _mapping(document["invocation"], f"{prefix}.invocation")
    _exact_keys(
        invocation,
        frozenset({"id", "sourceIdentity", "runPlanDigest"}),
        f"{prefix}.invocation",
    )
    _pattern_string(invocation["id"], f"{prefix}.invocation.id", _UUID_V4)
    _pattern_string(
        invocation["sourceIdentity"],
        f"{prefix}.invocation.sourceIdentity",
        _SOURCE_IDENTITY,
    )
    _pattern_string(
        invocation["runPlanDigest"],
        f"{prefix}.invocation.runPlanDigest",
        _SHA256,
    )

    participant = _mapping(document["participant"], f"{prefix}.participant")
    _exact_keys(
        participant,
        frozenset({"id", "role", "executionInstanceId"}),
        f"{prefix}.participant",
    )
    _pattern_string(participant["id"], f"{prefix}.participant.id", _STABLE_ID)
    _pattern_string(
        participant["executionInstanceId"],
        f"{prefix}.participant.executionInstanceId",
        _STABLE_ID,
    )
    participant_role = _nonempty_string(
        participant["role"], f"{prefix}.participant.role"
    )
    if participant_role not in {"semantic-adapter", "consumer"}:
        raise ConformanceSchemaError(
            f"{prefix}.participant.role must be semantic-adapter or consumer"
        )

    runner = _mapping(document["runner"], f"{prefix}.runner")
    _exact_keys(
        runner,
        frozenset({"id", "version", "platform", "toolchain"}),
        f"{prefix}.runner",
    )
    _pattern_string(runner["id"], f"{prefix}.runner.id", _STABLE_ID)
    _positive_integer(runner["version"], f"{prefix}.runner.version")
    _pattern_string(runner["platform"], f"{prefix}.runner.platform", _STABLE_ID)
    _pattern_string(runner["toolchain"], f"{prefix}.runner.toolchain", _STABLE_ID)

    scenarios = _list(document["scenarios"], f"{prefix}.scenarios")
    for index, raw_scenario in enumerate(scenarios):
        label = f"{prefix}.scenarios[{index}]"
        scenario = _mapping(raw_scenario, label)
        status = scenario.get("executionStatus")
        common_keys = {
            "id",
            "executionStatus",
            "capabilityIds",
            "observation",
            "failure",
        }
        if status == "not_applicable":
            common_keys.add("policyExceptionId")
        _exact_keys(scenario, frozenset(common_keys), label)
        _pattern_string(scenario["id"], f"{label}.id", _STABLE_ID)
        _nonempty_string(status, f"{label}.executionStatus")
        capability_ids = _string_array(
            scenario["capabilityIds"], f"{label}.capabilityIds", nonempty=True
        )
        for capability_index, capability_id in enumerate(capability_ids):
            _pattern_string(
                capability_id,
                f"{label}.capabilityIds[{capability_index}]",
                _STABLE_ID,
            )
        if status in {"completed", "failed"}:
            observation = _mapping(scenario["observation"], f"{label}.observation")
            _reject_floating_point_values(observation, f"{label}.observation")
        elif status == "not_applicable":
            if scenario["observation"] is not None or scenario["failure"] is not None:
                raise ConformanceSchemaError(
                    f"{label} not_applicable evidence needs null observation and failure"
                )
            _pattern_string(
                scenario["policyExceptionId"],
                f"{label}.policyExceptionId",
                _STABLE_ID,
            )
        else:
            raise ConformanceSchemaError(
                f"{label}.executionStatus must be completed, failed, or not_applicable"
            )
        if status == "completed" and scenario["failure"] is not None:
            raise ConformanceSchemaError(f"{label}.failure must be null when completed")
        if status == "failed":
            failure = _mapping(scenario["failure"], f"{label}.failure")
            _exact_keys(failure, frozenset({"kind", "message"}), f"{label}.failure")
            _pattern_string(failure["kind"], f"{label}.failure.kind", _STABLE_ID)
            _nonempty_string(failure["message"], f"{label}.failure.message")


def validate_conformance_report_document(document: Mapping[str, Any]) -> None:
    """Validate one closed instance, participant, or repository shadow report.

    The scope selector and completeness claim are checked together so a caller
    cannot broaden an otherwise valid partial report by changing a label.
    Raises ``ConformanceSchemaError`` for malformed or inconsistent reports.
    """

    prefix = "conformance-report schema"
    _exact_keys(
        document,
        frozenset(
            {
                "schemaVersion",
                "familyId",
                "enforcement",
                "scope",
                "result",
                "repositoryComplete",
                "requiredExecutions",
                "receivedExecutions",
                "missingExecutions",
                "failures",
                "coverage",
            }
        ),
        prefix,
    )
    _positive_integer(document["schemaVersion"], f"{prefix}.schemaVersion", exact=1)
    _pattern_string(document["familyId"], f"{prefix}.familyId", _STABLE_ID)
    if document["enforcement"] != "shadow":
        raise ConformanceSchemaError(f"{prefix}.enforcement must be shadow")
    if document["result"] not in {"pass", "fail"}:
        raise ConformanceSchemaError(f"{prefix}.result must be pass or fail")
    if not isinstance(document["repositoryComplete"], bool):
        raise ConformanceSchemaError(f"{prefix}.repositoryComplete must be boolean")

    scope = _mapping(document["scope"], f"{prefix}.scope")
    _exact_keys(
        scope,
        frozenset({"kind", "participantId", "executionInstanceId"}),
        f"{prefix}.scope",
    )
    scope_kind = scope["kind"]
    if scope_kind == "execution-instance":
        _pattern_string(
            scope["participantId"], f"{prefix}.scope.participantId", _STABLE_ID
        )
        _pattern_string(
            scope["executionInstanceId"],
            f"{prefix}.scope.executionInstanceId",
            _STABLE_ID,
        )
    elif scope_kind == "participant":
        _pattern_string(
            scope["participantId"], f"{prefix}.scope.participantId", _STABLE_ID
        )
        if scope["executionInstanceId"] is not None:
            raise ConformanceSchemaError(
                f"{prefix}.scope participant needs null executionInstanceId"
            )
    elif scope_kind == "full-repository":
        if (
            scope["participantId"] is not None
            or scope["executionInstanceId"] is not None
        ):
            raise ConformanceSchemaError(
                f"{prefix}.scope full-repository needs null selectors"
            )
    else:
        raise ConformanceSchemaError(f"{prefix}.scope has an unsupported kind")

    def execution_set(field: str) -> set[tuple[str, str]]:
        """Validate and return one exact execution identity set."""

        raw_executions = _list(document[field], f"{prefix}.{field}")
        executions: list[tuple[str, str]] = []
        for index, raw_execution in enumerate(raw_executions):
            label = f"{prefix}.{field}[{index}]"
            execution = _mapping(raw_execution, label)
            _exact_keys(
                execution,
                frozenset({"participantId", "executionInstanceId"}),
                label,
            )
            executions.append(
                (
                    _pattern_string(
                        execution["participantId"],
                        f"{label}.participantId",
                        _STABLE_ID,
                    ),
                    _pattern_string(
                        execution["executionInstanceId"],
                        f"{label}.executionInstanceId",
                        _STABLE_ID,
                    ),
                )
            )
        if len(executions) != len(set(executions)):
            raise ConformanceSchemaError(f"{prefix}.{field} contains duplicates")
        return set(executions)

    required = execution_set("requiredExecutions")
    received = execution_set("receivedExecutions")
    missing = execution_set("missingExecutions")
    if received - required:
        raise ConformanceSchemaError(
            f"{prefix}.receivedExecutions contains out-of-scope evidence"
        )
    if missing != required - received:
        raise ConformanceSchemaError(
            f"{prefix}.missingExecutions does not match the required denominator"
        )

    failures = _list(document["failures"], f"{prefix}.failures")
    for index, raw_failure in enumerate(failures):
        label = f"{prefix}.failures[{index}]"
        failure = _mapping(raw_failure, label)
        _exact_keys(
            failure,
            frozenset({"kind", "participantId", "executionInstanceId", "message"}),
            label,
        )
        if failure["kind"] not in {kind.value for kind in FailureKind}:
            raise ConformanceSchemaError(f"{label}.kind is unsupported")
        _nonempty_string(failure["message"], f"{label}.message")
        for selector in ("participantId", "executionInstanceId"):
            value = failure[selector]
            if value is not None:
                _pattern_string(value, f"{label}.{selector}", _STABLE_ID)

    coverage = document["coverage"]
    # A scoped pass is a coverage claim, so a missing partition must fail
    # closed even when all execution receipts are otherwise present.
    coverage_passed = False
    if coverage is not None:
        coverage_object = _mapping(coverage, f"{prefix}.coverage")
        _exact_keys(
            coverage_object,
            frozenset(
                {
                    "familyId",
                    "result",
                    "executionEvidence",
                    "preparedEvidenceDigest",
                    "rows",
                    "failures",
                }
            ),
            f"{prefix}.coverage",
        )
        if coverage_object["familyId"] != document["familyId"]:
            raise ConformanceSchemaError(
                f"{prefix}.coverage family does not match the report"
            )
        if coverage_object["result"] not in {"pass", "fail"}:
            raise ConformanceSchemaError(
                f"{prefix}.coverage.result must be pass or fail"
            )
        coverage_executions = _list(
            coverage_object["executionEvidence"],
            f"{prefix}.coverage.executionEvidence",
        )
        coverage_execution_keys: list[tuple[str, str]] = []
        for index, raw_execution in enumerate(coverage_executions):
            label = f"{prefix}.coverage.executionEvidence[{index}]"
            execution = _mapping(raw_execution, label)
            _exact_keys(
                execution,
                frozenset({"participantId", "executionInstanceId"}),
                label,
            )
            coverage_execution_keys.append(
                (
                    _pattern_string(
                        execution["participantId"],
                        f"{label}.participantId",
                        _STABLE_ID,
                    ),
                    _pattern_string(
                        execution["executionInstanceId"],
                        f"{label}.executionInstanceId",
                        _STABLE_ID,
                    ),
                )
            )
        if len(coverage_execution_keys) != len(set(coverage_execution_keys)):
            raise ConformanceSchemaError(
                f"{prefix}.coverage.executionEvidence contains duplicates"
            )
        _pattern_string(
            coverage_object["preparedEvidenceDigest"],
            f"{prefix}.coverage.preparedEvidenceDigest",
            _SHA256,
        )
        coverage_rows = _list(coverage_object["rows"], f"{prefix}.coverage.rows")
        row_ids: list[str] = []
        for index, raw_row in enumerate(coverage_rows):
            label = f"{prefix}.coverage.rows[{index}]"
            row = _mapping(raw_row, label)
            _exact_keys(
                row,
                frozenset(
                    {
                        "obligationId",
                        "participantId",
                        "mappingOrigin",
                        "capabilityId",
                        "evidenceKind",
                        "evidenceIds",
                    }
                ),
                label,
            )
            row_ids.append(
                _nonempty_string(row["obligationId"], f"{label}.obligationId")
            )
            _pattern_string(row["participantId"], f"{label}.participantId", _STABLE_ID)
            if row["mappingOrigin"] not in {
                "canonical_rust",
                "binding_only",
                "rust_only",
            }:
                raise ConformanceSchemaError(
                    f"{label}.mappingOrigin has an unsupported value"
                )
            capability_id = row["capabilityId"]
            if capability_id is not None:
                _pattern_string(capability_id, f"{label}.capabilityId", _STABLE_ID)
            if row["evidenceKind"] not in {
                "executable",
                "structural",
                "negative",
                "policy-exception",
            }:
                raise ConformanceSchemaError(
                    f"{label}.evidenceKind has an unsupported value"
                )
            evidence_ids = _string_array(
                row["evidenceIds"], f"{label}.evidenceIds", nonempty=True
            )
            if len(evidence_ids) != len(set(evidence_ids)):
                raise ConformanceSchemaError(f"{label}.evidenceIds contains duplicates")
            for evidence_index, evidence_id in enumerate(evidence_ids):
                _pattern_string(
                    evidence_id,
                    f"{label}.evidenceIds[{evidence_index}]",
                    _STABLE_ID,
                )
        if len(row_ids) != len(set(row_ids)):
            raise ConformanceSchemaError(
                f"{prefix}.coverage.rows contains duplicate obligations"
            )
        coverage_failures = _list(
            coverage_object["failures"], f"{prefix}.coverage.failures"
        )
        failure_ids: list[str] = []
        for index, raw_failure in enumerate(coverage_failures):
            label = f"{prefix}.coverage.failures[{index}]"
            failure = _mapping(raw_failure, label)
            _exact_keys(
                failure,
                frozenset({"kind", "obligationId", "blocking", "message"}),
                label,
            )
            if failure["kind"] != FailureKind.COVERAGE_MAPPING.value:
                raise ConformanceSchemaError(
                    f"{label}.kind must be coverage_mapping_gap"
                )
            failure_ids.append(
                _nonempty_string(failure["obligationId"], f"{label}.obligationId")
            )
            if not isinstance(failure["blocking"], bool):
                raise ConformanceSchemaError(f"{label}.blocking must be boolean")
            _nonempty_string(failure["message"], f"{label}.message")
        if len(failure_ids) != len(set(failure_ids)):
            raise ConformanceSchemaError(
                f"{prefix}.coverage.failures contains duplicate obligations"
            )
        expected_coverage_result = "fail" if coverage_failures else "pass"
        if coverage_object["result"] != expected_coverage_result:
            raise ConformanceSchemaError(
                f"{prefix}.coverage.result does not match coverage failures"
            )
        coverage_passed = coverage_object["result"] == "pass" and not coverage_failures
    passed = not missing and not failures and coverage_passed
    if document["result"] != ("pass" if passed else "fail"):
        raise ConformanceSchemaError(
            f"{prefix}.result does not match missing executions and failures"
        )
    repository_complete = document["repositoryComplete"]
    if repository_complete and scope_kind != "full-repository":
        raise ConformanceSchemaError(
            f"{prefix}.repositoryComplete requires full-repository scope"
        )
    if repository_complete != (scope_kind == "full-repository" and passed):
        raise ConformanceSchemaError(
            f"{prefix}.repositoryComplete does not match full-repository success"
        )
