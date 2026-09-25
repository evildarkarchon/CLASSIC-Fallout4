"""Transfer executed retained-gate results between same-run CI jobs."""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from catalog import CommandSpec, ComplianceRequirement  # type: ignore
from suite import RequirementResult  # type: ignore


class GateEvidenceError(ValueError):
    """Raised when retained-gate evidence cannot prove the current full run."""


# These owners prevent three participant source profiles from donating the same
# shared guard three times. Every profile still runs its entire own catalog.
PROFILE_GATE_IDS: dict[str, tuple[str, ...]] = {
    "cxx-ci": (
        "cxx-opaque-map-reachability",
        "node-package-metadata",
        "user-settings-exclusive-ownership",
        "scan-run-contract-variants",
        "scan-run-workflow-policy",
        "cxx-parity-gate",
    ),
    "node-ci": ("node-parity-gate", "node-dts-freshness"),
    "python-ci": (
        "python-parity-gate",
        "python-stub-validation",
        "python-tooling-sync",
        "python-schema-version-drift",
    ),
}
SINGLE_GATE_IDS = frozenset(
    {
        "node-bun-runtime-tests",
        "node-node-runtime-tests",
        "python-bindings-rebuild",
        "python-runtime-smoke-tests",
    }
)
EVIDENCE_FILENAME = "gate_evidence.json"


def current_source_revision(repo_root: Path) -> str:
    """Return this checkout's exact Git HEAD for same-revision evidence checks."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--verify", "HEAD"],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise GateEvidenceError(f"cannot read checkout Git HEAD: {error}") from error
    revision = completed.stdout.strip()
    if completed.returncode != 0 or re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", revision) is None:
        raise GateEvidenceError("cannot read checkout Git HEAD")
    return revision.lower()


def github_run_identity(environment: Mapping[str, str] | None = None) -> tuple[str, int]:
    """Read the current GitHub run and attempt from the producer or full job."""
    values = os.environ if environment is None else environment
    run_id = values.get("GITHUB_RUN_ID", "")
    attempt_text = values.get("GITHUB_RUN_ATTEMPT", "")
    if not re.fullmatch(r"[0-9]+", run_id) or not re.fullmatch(r"[0-9]+", attempt_text):
        raise GateEvidenceError("gate evidence requires GITHUB_RUN_ID and GITHUB_RUN_ATTEMPT")
    attempt = int(attempt_text)
    if int(run_id) <= 0 or attempt <= 0:
        raise GateEvidenceError("GitHub run ID and attempt must be positive")
    return run_id, attempt


def command_identity(command: CommandSpec) -> dict[str, Any]:
    """Describe the exact catalog command whose result can be reused."""
    return {
        "argv": list(command.argv),
        "cwd": command.cwd,
        "env": dict(command.env),
        "timeoutSeconds": command.timeout_seconds,
    }


def _owned_ids(profile: str, requirements: Sequence[ComplianceRequirement]) -> tuple[str, ...]:
    """Return the exact command IDs this producer may contribute."""
    if profile in PROFILE_GATE_IDS:
        return PROFILE_GATE_IDS[profile]
    if profile == "single-gate" and len(requirements) == 1:
        gate_id = requirements[0].id
        if gate_id in SINGLE_GATE_IDS:
            return (gate_id,)
    raise GateEvidenceError(f"unsupported retained-gate producer profile: {profile}")


def write_gate_evidence(
    repo_root: Path,
    output_path: Path,
    report: Mapping[str, Any],
    requirements: Sequence[ComplianceRequirement],
    *,
    source_revision: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> Path:
    """Write command outcomes and CI identity from one actual producer report.

    Source profiles contribute only their assigned command IDs, while their
    whole-profile result records failures in common guards run by every job.
    The explicit revision parameter exists for tests; normal callers derive it
    directly from the checkout rather than trusting a CLI supplied value.
    """
    profile = report.get("profile")
    if not isinstance(profile, str):
        raise GateEvidenceError("producer report has no profile")
    owned = _owned_ids(profile, requirements)
    catalog = {requirement.id: requirement for requirement in requirements}
    observed = report.get("requirements")
    if not isinstance(observed, list):
        raise GateEvidenceError("producer report has no requirement results")
    observed_by_id: dict[str, Mapping[str, Any]] = {}
    for result in observed:
        if not isinstance(result, Mapping) or not isinstance(result.get("id"), str):
            raise GateEvidenceError("producer report has malformed requirement result")
        gate_id = result["id"]
        if gate_id in observed_by_id:
            raise GateEvidenceError(f"producer report repeats requirement {gate_id}")
        observed_by_id[gate_id] = result
    entries = []
    for gate_id in owned:
        requirement = catalog.get(gate_id)
        result = observed_by_id.get(gate_id)
        if requirement is None or requirement.command is None or result is None:
            raise GateEvidenceError(f"producer report omits owned command {gate_id}")
        entries.append(
            {
                "id": gate_id,
                "status": result.get("status"),
                "command": command_identity(requirement.command),
            }
        )
    summary = report.get("summary")
    if not isinstance(summary, Mapping) or summary.get("result") not in {"pass", "fail"}:
        raise GateEvidenceError("producer report has no final result")
    run_id, run_attempt = github_run_identity(environment)
    revision = source_revision or current_source_revision(repo_root)
    payload = {
        "schemaVersion": 1,
        "profile": profile,
        "result": summary["result"],
        "sourceRevision": revision,
        "runId": run_id,
        "runAttempt": run_attempt,
        "results": entries,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_path


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject ambiguous JSON keys before validating an artifact's identity."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GateEvidenceError(f"gate evidence repeats JSON key {key}")
        result[key] = value
    return result


def load_gate_evidence(
    repo_root: Path,
    directory: Path,
    requirements: Sequence[ComplianceRequirement],
    *,
    source_revision: str,
    run_id: str,
    run_attempt: int,
) -> dict[str, RequirementResult]:
    """Authenticate all retained gates from this run without running commands.

    A successful producer from an earlier attempt of the same workflow run is
    acceptable because failed-only retries retain its immutable artifact. Every
    command result must match the current catalog and exactly one declared owner.
    """
    root = repo_root.resolve()
    candidate = directory if directory.is_absolute() else root / directory
    try:
        artifact_root = candidate.resolve(strict=True)
        artifact_root.relative_to(root)
    except (OSError, ValueError) as error:
        raise GateEvidenceError("gate evidence directory must stay in the checkout") from error
    if not artifact_root.is_dir():
        raise GateEvidenceError("gate evidence directory must be a directory")
    paths = sorted(artifact_root.rglob(EVIDENCE_FILENAME))
    if not paths:
        raise GateEvidenceError("gate evidence directory contains no evidence files")

    catalog = {
        requirement.id: requirement
        for requirement in requirements
        if requirement.command is not None
    }
    expected = set().union(*PROFILE_GATE_IDS.values(), SINGLE_GATE_IDS)
    if set(catalog) != expected:
        raise GateEvidenceError("retained gate owners do not match the current full catalog")
    seen_profiles: set[str] = set()
    results: dict[str, RequirementResult] = {}
    for path in paths:
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(root)
            payload = json.loads(
                resolved.read_text(encoding="utf-8"),
                object_pairs_hook=_reject_duplicate_keys,
            )
        except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as error:
            raise GateEvidenceError(f"cannot read gate evidence {path}: {error}") from error
        if not isinstance(payload, Mapping) or payload.get("schemaVersion") != 1:
            raise GateEvidenceError(f"gate evidence has unsupported schema: {path}")
        profile = payload.get("profile")
        if not isinstance(profile, str) or profile not in {*PROFILE_GATE_IDS, "single-gate"}:
            raise GateEvidenceError(f"gate evidence has unknown producer profile: {path}")
        if profile in PROFILE_GATE_IDS:
            if profile in seen_profiles:
                raise GateEvidenceError(f"duplicate retained-gate producer profile: {profile}")
            seen_profiles.add(profile)
        if payload.get("result") != "pass":
            raise GateEvidenceError(f"retained-gate producer did not pass: {path}")
        if payload.get("sourceRevision") != source_revision:
            raise GateEvidenceError(f"retained-gate source revision differs: {path}")
        if payload.get("runId") != run_id:
            raise GateEvidenceError(f"retained-gate workflow run differs: {path}")
        attempt = payload.get("runAttempt")
        if type(attempt) is not int or not 1 <= attempt <= run_attempt:
            raise GateEvidenceError(f"retained-gate attempt is invalid: {path}")
        entries = payload.get("results")
        if not isinstance(entries, list):
            raise GateEvidenceError(f"retained-gate results are missing: {path}")
        ids = [entry.get("id") if isinstance(entry, Mapping) else None for entry in entries]
        owned = PROFILE_GATE_IDS.get(profile)
        if profile == "single-gate":
            if len(ids) != 1 or ids[0] not in SINGLE_GATE_IDS:
                raise GateEvidenceError(f"single-gate evidence has invalid gate ID: {path}")
            owned = (ids[0],)
        if set(ids) != set(owned or ()) or len(ids) != len(owned or ()):
            raise GateEvidenceError(f"retained-gate producer has wrong command set: {path}")
        for entry in entries:
            gate_id = entry["id"]
            if gate_id in results:
                raise GateEvidenceError(f"duplicate retained-gate result: {gate_id}")
            requirement = catalog[gate_id]
            if entry.get("status") != "passed":
                raise GateEvidenceError(f"retained gate did not pass: {gate_id}")
            if entry.get("command") != command_identity(requirement.command):
                raise GateEvidenceError(f"retained-gate command differs from catalog: {gate_id}")
            results[gate_id] = RequirementResult(
                id=gate_id,
                title=requirement.title,
                surface=requirement.surface,
                classification=requirement.classification,
                status="passed",
                blocking=requirement.blocking,
                summary=requirement.summary,
                evidence=[
                    f"Passed in current GitHub run {run_id}, attempt {attempt}: "
                    f"{resolved.relative_to(root).as_posix()}"
                ],
            )
    missing_profiles = set(PROFILE_GATE_IDS) - seen_profiles
    if missing_profiles:
        raise GateEvidenceError(
            f"missing retained-gate producer profiles: {', '.join(sorted(missing_profiles))}"
        )
    missing = set(catalog) - set(results)
    if missing:
        raise GateEvidenceError(f"missing retained-gate results: {', '.join(sorted(missing))}")
    return results
