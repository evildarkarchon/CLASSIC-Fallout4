"""Receipt-only command orchestration for scoped conformance reports."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from .applicability import derive_applicability, load_policy_exceptions
from .consumers import derive_consumer_coverage, load_consumer_obligations
from .coverage import (
    FamilyCoveragePolicy,
    derive_row_coverage,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
)
from .failures import FailureKind
from .families.crash_log_scan_run import CRASH_LOG_SCAN_RUN_COVERAGE_POLICY
from .packs import (
    MaterializationError,
    PackValidationError,
    discover_pack_paths,
    load_and_validate_pack,
    load_prepared_run,
)
from .receipts import validate_prepared_run
from .reports import ScopedReportFailure, build_scoped_report
from .schema import (
    ConformanceSchemaError,
    reject_duplicate_json_keys,
    validate_conformance_report_document,
    validate_run_plan_document,
)


class ConformanceCommandError(ValueError):
    """Raised when receipt-only CLI inputs cannot form an honest scope."""


# Domain slices register repository-owned predicate policies here as they land.
# An absent policy leaves coverage unresolved and therefore cannot pass a scope.
FAMILY_COVERAGE_POLICIES: Mapping[str, FamilyCoveragePolicy] = {
    CRASH_LOG_SCAN_RUN_COVERAGE_POLICY.family_id: CRASH_LOG_SCAN_RUN_COVERAGE_POLICY,
}

_CXX_LOCAL_ENVIRONMENT_OUTPUT_MARKERS = (
    "vcpkg_root environment variable is not set",
    "could not find vs dev shell",
    "missing required tool:",
    "missing required environment:",
    "build prerequisites are missing",
    "could not locate a visual studio installation",
    "vs dev shell initialization completed, but",
    'cmake was unable to find a build program corresponding to "ninja"',
    "could not find toolchain file:",
    "could not resolve link.exe from cmake_linker",
    "resolved linker is not an msvc-compatible linker",
    "no cmake_cxx_compiler could be found",
    "the c++ compiler is not able to compile a simple test program",
)


def _repository_path(
    repo_root: Path,
    value: Path,
    *,
    label: str,
    must_exist: bool,
) -> Path:
    """Resolve one CLI artifact path without permitting repository escape."""

    candidate = value if value.is_absolute() else repo_root / value
    try:
        resolved = candidate.resolve(strict=must_exist)
        resolved.relative_to(repo_root)
    except (OSError, ValueError) as error:
        raise ConformanceCommandError(
            f"{label} must stay beneath the repository root"
        ) from error
    return resolved


def _run_plan_family(run_plan_path: Path) -> str:
    """Read and validate the family identity from one immutable run plan."""

    try:
        document = json.loads(
            run_plan_path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_json_keys,
        )
        if not isinstance(document, Mapping):
            raise ConformanceSchemaError("run plan must be an object")
        validate_run_plan_document(document)
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        ConformanceSchemaError,
    ) as error:
        raise ConformanceCommandError(
            f"cannot read prepared run plan: {error}"
        ) from error
    family_id = document.get("familyId")
    if not isinstance(family_id, str):  # pragma: no cover - schema invariant
        raise ConformanceCommandError("prepared run plan has no family identity")
    return family_id


def _cxx_captured_output(
    repo_root: Path,
    attempt: Mapping[str, Any],
    *,
    participant_id: str,
    execution_instance_id: str | None,
) -> tuple[str, tuple[ScopedReportFailure, ...]]:
    """Read digest-bound native logs without letting diagnostics become evidence."""

    output_parts: list[str] = []
    failures: list[ScopedReportFailure] = []
    for stream in ("stdout", "stderr"):
        metadata = attempt.get(stream)
        if not isinstance(metadata, Mapping):
            failures.append(
                ScopedReportFailure(
                    FailureKind.ADAPTER_COMMAND,
                    f"native attempt {stream} diagnostics must be an object",
                    participant_id,
                    execution_instance_id,
                )
            )
            continue
        raw_path = metadata.get("path")
        expected_digest = metadata.get("sha256")
        if (
            not isinstance(raw_path, str)
            or not Path(raw_path).is_absolute()
            or not isinstance(expected_digest, str)
            or len(expected_digest) != 64
            or any(
                character not in "0123456789abcdefABCDEF"
                for character in expected_digest
            )
        ):
            failures.append(
                ScopedReportFailure(
                    FailureKind.ADAPTER_COMMAND,
                    f"native attempt {stream} path or SHA-256 is malformed",
                    participant_id,
                    execution_instance_id,
                )
            )
            continue
        try:
            resolved = _repository_path(
                repo_root,
                Path(raw_path),
                label=f"native attempt {stream} path",
                must_exist=True,
            )
            payload = resolved.read_bytes()
        except (ConformanceCommandError, OSError) as error:
            failures.append(
                ScopedReportFailure(
                    FailureKind.ADAPTER_COMMAND,
                    f"native execution did not produce readable {stream} diagnostics: {error}",
                    participant_id,
                    execution_instance_id,
                )
            )
            continue
        if hashlib.sha256(payload).hexdigest() != expected_digest.lower():
            failures.append(
                ScopedReportFailure(
                    FailureKind.ADAPTER_COMMAND,
                    f"native attempt {stream} SHA-256 does not match the captured file",
                    participant_id,
                    execution_instance_id,
                )
            )
            continue
        output_parts.append(payload.decode("utf-8", errors="replace"))
    return "\n".join(output_parts), tuple(failures)


def _diagnostic_failures(
    repo_root: Path,
    *,
    participant_id: str,
    execution_instance_id: str | None,
    attempt_path: Path | None,
    junit_path: Path | None,
) -> tuple[ScopedReportFailure, ...]:
    """Classify companion native artifacts without treating them as facts."""

    failures: list[ScopedReportFailure] = []
    for path, label in ((attempt_path, "attempt"), (junit_path, "JUnit")):
        if path is None:
            continue
        resolved = _repository_path(
            repo_root, path, label=f"{label} path", must_exist=False
        )
        if not resolved.is_file():
            failures.append(
                ScopedReportFailure(
                    FailureKind.ADAPTER_COMMAND,
                    f"native execution did not produce its {label} artifact",
                    participant_id,
                    execution_instance_id,
                )
            )

    if attempt_path is None:
        return tuple(failures)
    resolved_attempt = _repository_path(
        repo_root, attempt_path, label="attempt path", must_exist=False
    )
    if not resolved_attempt.is_file():
        return tuple(failures)
    try:
        attempt = json.loads(
            resolved_attempt.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_json_keys,
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        ConformanceSchemaError,
    ) as error:
        failures.append(
            ScopedReportFailure(
                FailureKind.ADAPTER_COMMAND,
                f"native attempt diagnostics are malformed: {error}",
                participant_id,
                execution_instance_id,
            )
        )
        return tuple(failures)
    if not isinstance(attempt, Mapping):
        failures.append(
            ScopedReportFailure(
                FailureKind.ADAPTER_COMMAND,
                "native attempt diagnostics must be an object",
                participant_id,
                execution_instance_id,
            )
        )
        return tuple(failures)
    captured_output = ""
    if participant_id == "cxx":
        captured_output, output_failures = _cxx_captured_output(
            repo_root,
            attempt,
            participant_id=participant_id,
            execution_instance_id=execution_instance_id,
        )
        failures.extend(output_failures)
    launch_error = attempt.get("launchError")
    if isinstance(launch_error, str) and launch_error:
        failures.append(
            ScopedReportFailure(
                FailureKind.LOCAL_ENVIRONMENT,
                f"native conformance command could not start: {launch_error}",
                participant_id,
                execution_instance_id,
            )
        )
    elif launch_error is not None:
        failures.append(
            ScopedReportFailure(
                FailureKind.ADAPTER_COMMAND,
                "native attempt launchError must be a string or null",
                participant_id,
                execution_instance_id,
            )
        )
    if attempt.get("timedOut") is True:
        failures.append(
            ScopedReportFailure(
                FailureKind.ADAPTER_COMMAND,
                "native conformance command timed out",
                participant_id,
                execution_instance_id,
            )
        )
    exit_code = attempt.get("exitCode")
    if type(exit_code) is int and exit_code != 0:
        local_environment_failure = any(
            marker in captured_output.lower()
            for marker in _CXX_LOCAL_ENVIRONMENT_OUTPUT_MARKERS
        )
        failures.append(
            ScopedReportFailure(
                (
                    FailureKind.LOCAL_ENVIRONMENT
                    if local_environment_failure
                    else FailureKind.ADAPTER_COMMAND
                ),
                (
                    "native conformance command failed because local toolchain "
                    "or environment prerequisites were unavailable"
                    if local_environment_failure
                    else f"native conformance command exited with code {exit_code}"
                ),
                participant_id,
                execution_instance_id,
            )
        )
    return tuple(failures)


def build_conformance_report_from_receipts(
    repo_root: Path,
    *,
    profile: str,
    participant_id: str | None,
    execution_instance_id: str | None,
    receipt_paths: Sequence[Path],
    attempt_path: Path | None = None,
    junit_path: Path | None = None,
    coverage_policies: Mapping[str, FamilyCoveragePolicy] = FAMILY_COVERAGE_POLICIES,
) -> dict[str, Any]:
    """Validate native receipts and aggregate their source-derived exact scope.

    Receipt paths identify sibling immutable ``run_plan.json`` files. Every run
    is rebound to the current tracked family before central receipt validation;
    companion attempt/JUnit files can add diagnostics but never coverage facts.
    """

    root = repo_root.resolve()
    if not receipt_paths:
        raise ConformanceCommandError("scoped conformance requires receipt paths")
    resolved_receipts = tuple(
        _repository_path(root, path, label="receipt path", must_exist=False)
        for path in receipt_paths
    )
    run_plan_paths = tuple(path.parent / "run_plan.json" for path in resolved_receipts)
    for run_plan_path in run_plan_paths:
        if not run_plan_path.is_file():
            raise ConformanceCommandError(
                f"receipt has no sibling immutable run plan: {run_plan_path}"
            )
    family_ids = {_run_plan_family(path) for path in run_plan_paths}
    if len(family_ids) != 1:
        raise ConformanceCommandError(
            "one scoped report cannot combine multiple scenario families"
        )
    family_id = next(iter(family_ids))

    matching_packs = []
    try:
        for pack_path in discover_pack_paths(root):
            pack = load_and_validate_pack(root, pack_path)
            if pack.document()["familyId"] == family_id:
                matching_packs.append(pack)
    except PackValidationError as error:
        raise ConformanceCommandError(str(error)) from error
    if len(matching_packs) != 1:
        raise ConformanceCommandError(
            f"prepared family {family_id} must resolve to exactly one tracked pack"
        )
    pack = matching_packs[0]
    coverage_policy = coverage_policies.get(family_id)
    pack_document = pack.document()
    has_consumer_obligations = bool(pack_document.get("consumerObligations"))
    try:
        consumer_catalog = (
            load_consumer_obligations(root) if has_consumer_obligations else None
        )
    except ValueError as error:
        raise ConformanceCommandError(str(error)) from error

    prepared_reports = []
    try:
        for run_plan_path, receipt_path in zip(
            run_plan_paths, resolved_receipts, strict=True
        ):
            run = load_prepared_run(
                pack,
                run_plan_path,
                receipt_path=receipt_path,
                consumer_catalog=consumer_catalog,
            )
            prepared_reports.append(
                validate_prepared_run(
                    pack,
                    run,
                    receipt_paths=(receipt_path,),
                    coverage_policy=coverage_policy,
                    consumer_catalog=consumer_catalog,
                )
            )
        parity_rows = load_source_parity_rows(root)
        policy_exceptions = load_policy_exceptions(root)
        applicability = derive_applicability(
            pack.document(),
            parity_rows,
            policy_exceptions=policy_exceptions,
            consumer_catalog=consumer_catalog,
        )
    except (MaterializationError, PackValidationError, ValueError) as error:
        raise ConformanceCommandError(str(error)) from error

    try:
        selected_prepared_reports = tuple(
            report
            for report in prepared_reports
            if profile != "conformance"
            or (
                report.participant.get("id") == participant_id
                and (
                    execution_instance_id is None
                    or report.participant.get("executionInstanceId")
                    == execution_instance_id
                )
            )
        )
        coverage_prepared_reports = tuple(
            report
            for report in selected_prepared_reports
            if report.participant.get("role") == "semantic-adapter"
        )
        consumer_prepared_reports = tuple(
            report
            for report in selected_prepared_reports
            if report.participant.get("role") == "consumer"
        )
        selected_role = next(
            (
                participant.role
                for participant in applicability.participants
                if participant.id == participant_id
            ),
            None,
        )
        coverage = (
            derive_row_coverage(
                pack.document(),
                parity_rows,
                coverage_policy,
                coverage_prepared_reports,
                scope_participant_id=(
                    participant_id if profile == "conformance" else None
                ),
                retained_analyzers=load_retained_analyzer_kinds(root),
                policy_exceptions=policy_exceptions,
            )
            if coverage_policy is not None
            and (profile == "full" or selected_role == "semantic-adapter")
            else None
        )
        consumer_coverage = (
            derive_consumer_coverage(
                pack_document,
                consumer_catalog,
                consumer_prepared_reports,
                scope_participant_id=(
                    participant_id if profile == "conformance" else None
                ),
                scope_execution_instance_id=(
                    execution_instance_id if profile == "conformance" else None
                ),
            )
            if consumer_catalog is not None
            and (profile == "full" or selected_role == "consumer")
            else None
        )
        scoped = build_scoped_report(
            family_id=family_id,
            profile=profile,
            applicability=applicability,
            prepared_reports=tuple(prepared_reports),
            participant_id=participant_id,
            execution_instance_id=execution_instance_id,
            coverage=coverage,
            consumer_coverage=consumer_coverage,
        )
    except ValueError as error:
        raise ConformanceCommandError(str(error)) from error
    diagnostic_failures = _diagnostic_failures(
        root,
        participant_id=participant_id or "repository",
        execution_instance_id=execution_instance_id,
        attempt_path=attempt_path,
        junit_path=junit_path,
    )
    if diagnostic_failures:
        scoped = replace(scoped, failures=scoped.failures + diagnostic_failures)
    document = scoped.document()
    validate_conformance_report_document(document)
    return document
