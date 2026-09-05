"""Static policy audit for blocking Crash Log Scan Run receipt jobs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


class WorkflowPolicyError(ValueError):
    """Raised when tracked CI no longer runs the promoted receipt denominator."""


@dataclass(frozen=True)
class WorkflowExecutionPolicy:
    """One required participant execution step and its retained legacy predecessor."""

    workflow: str
    job_id: str
    participant_id: str
    legacy_marker: str
    launcher_marker: str
    artifact_marker: str
    launcher_condition: str = "if: ${{ !cancelled() }}"
    upload_condition: str = "if: always()"
    matrix_marker: str | None = None
    job_timeout_minutes: int | None = None


_EXECUTION_POLICIES = (
    WorkflowExecutionPolicy(
        workflow=".github/workflows/ci-rust.yml",
        job_id="test",
        participant_id="rust",
        legacy_marker="Run Rust tests with all features",
        launcher_marker="run_scan_run_conformance.py --participant rust",
        artifact_marker="name: rust-scan-run-conformance",
    ),
    WorkflowExecutionPolicy(
        workflow=".github/workflows/ci-rust.yml",
        job_id="test",
        participant_id="tui",
        legacy_marker="Run Rust tests with all features",
        launcher_marker="run_scan_run_consumer_conformance.py --participant tui",
        artifact_marker="name: tui-consumer-conformance",
    ),
    WorkflowExecutionPolicy(
        workflow=".github/workflows/ci-typescript.yml",
        job_id="build-and-test",
        participant_id="node",
        legacy_marker="Run Node runtime smoke tests",
        launcher_marker="run_scan_run_conformance.py --participant node",
        artifact_marker="name: node-scan-run-conformance",
        launcher_condition="if: matrix.runtime == 'node' && !cancelled()",
        upload_condition="if: matrix.runtime == 'node' && always()",
        matrix_marker="runtime: [bun, node]",
    ),
    WorkflowExecutionPolicy(
        workflow=".github/workflows/ci-python-bindings.yml",
        job_id="build-and-test",
        participant_id="python",
        legacy_marker="Run Python bindings smoke tests",
        launcher_marker="run_scan_run_conformance.py --participant python",
        artifact_marker="name: python-scan-run-conformance",
    ),
    WorkflowExecutionPolicy(
        workflow=".github/workflows/ci-cpp.yml",
        job_id="cli-tests",
        participant_id="cxx",
        legacy_marker="Build and test CLI",
        launcher_marker="run_cxx_conformance.ps1 -Compiler ${{ matrix.compiler }}",
        artifact_marker="name: cxx-conformance-${{ matrix.compiler }}",
        matrix_marker="compiler: [msvc, clang-cl]",
        job_timeout_minutes=180,
    ),
    WorkflowExecutionPolicy(
        workflow=".github/workflows/ci-cpp.yml",
        job_id="cli-tests",
        participant_id="cli",
        legacy_marker="Build and test CLI",
        launcher_marker=(
            "run_cli_consumer_conformance.ps1 -Compiler ${{ matrix.compiler }}"
        ),
        artifact_marker="name: cli-consumer-conformance-${{ matrix.compiler }}",
        matrix_marker="compiler: [msvc, clang-cl]",
        job_timeout_minutes=180,
    ),
    WorkflowExecutionPolicy(
        workflow=".github/workflows/ci-cpp.yml",
        job_id="gui-tests",
        participant_id="gui",
        legacy_marker="Build and test GUI",
        launcher_marker=(
            "run_gui_consumer_conformance.ps1 -Compiler ${{ matrix.compiler }}"
        ),
        artifact_marker="name: gui-consumer-conformance-${{ matrix.compiler }}",
        matrix_marker="compiler: [msvc, clang-cl]",
        job_timeout_minutes=180,
    ),
)


def _job_block(source: str, job_id: str) -> str:
    """Return one top-level workflow job without parsing expression syntax as YAML."""

    match = re.search(rf"(?m)^  {re.escape(job_id)}:\s*$", source)
    if match is None:
        raise WorkflowPolicyError(f"missing required workflow job {job_id}")
    next_job = re.search(r"(?m)^  [a-zA-Z0-9_-]+:\s*$", source[match.end() :])
    end = match.end() + next_job.start() if next_job is not None else len(source)
    return source[match.start() : end]


def _step_block(job: str, marker: str, *, label: str) -> str:
    """Return the unique YAML step containing a required command or artifact marker."""

    if job.count(marker) != 1:
        raise WorkflowPolicyError(f"{label} must occur exactly once")
    marker_index = job.index(marker)
    starts = [match.start() for match in re.finditer(r"(?m)^      - ", job)]
    start = max((value for value in starts if value <= marker_index), default=-1)
    if start < 0:
        raise WorkflowPolicyError(f"{label} is not inside a workflow step")
    end = next((value for value in starts if value > marker_index), len(job))
    return job[start:end]


def validate_scan_run_workflow_policy(repo_root: Path) -> None:
    """Fail unless every promoted execution remains blocking and same-revision.

    The audit intentionally reads tracked workflow text instead of normalizing it
    through a YAML library: GitHub expressions contain syntax that general YAML
    loaders may reinterpret, while this policy needs exact reviewed job markers.
    """

    root = repo_root.resolve()
    errors: list[str] = []
    sources: dict[str, str] = {}
    for policy in _EXECUTION_POLICIES:
        try:
            source = sources.setdefault(
                policy.workflow,
                (root / policy.workflow).read_text(encoding="utf-8"),
            )
            job = _job_block(source, policy.job_id)
            label = f"{policy.workflow}:{policy.job_id}:{policy.participant_id}"
            job_condition = re.search(r"(?m)^    if:\s*(.+)\s*$", job)
            if re.search(r"(?m)^    needs:", job):
                if (
                    job_condition is None
                    or job_condition.group(1).strip() != "${{ !cancelled() }}"
                ):
                    raise WorkflowPolicyError(
                        f"{label} job must run after upstream failures unless cancelled"
                    )
            elif job_condition is not None:
                raise WorkflowPolicyError(
                    f"{label} required job cannot be conditionally skipped"
                )
            if re.search(r"(?m)^    continue-on-error:", job):
                raise WorkflowPolicyError(f"{label} required job must be blocking")
            if policy.job_timeout_minutes is not None and not re.search(
                rf"(?m)^    timeout-minutes: {policy.job_timeout_minutes}\s*$", job
            ):
                raise WorkflowPolicyError(
                    f"{label} must reserve {policy.job_timeout_minutes} minutes for retained and promoted gates"
                )
            if job.count("uses: actions/checkout@v6") != 1:
                raise WorkflowPolicyError(
                    f"{label} must use exactly one default checkout"
                )
            checkout = _step_block(
                job,
                "uses: actions/checkout@v6",
                label=f"{label} checkout",
            )
            if re.search(r"(?m)^\s+ref:", checkout):
                raise WorkflowPolicyError(
                    f"{label} checkout cannot replace the event source revision"
                )
            if policy.matrix_marker is not None and policy.matrix_marker not in job:
                raise WorkflowPolicyError(
                    f"{label} is missing exact required matrix {policy.matrix_marker}"
                )
            if policy.matrix_marker is not None and "fail-fast: false" not in job:
                raise WorkflowPolicyError(f"{label} matrix must keep fail-fast false")
            if policy.matrix_marker is not None and re.search(
                r"(?m)^        exclude:", job
            ):
                raise WorkflowPolicyError(
                    f"{label} matrix cannot exclude required executions"
                )
            legacy_index = job.find(policy.legacy_marker)
            launcher_index = job.find(policy.launcher_marker)
            artifact_index = job.find(policy.artifact_marker)
            if min(legacy_index, launcher_index, artifact_index) < 0:
                raise WorkflowPolicyError(f"{label} is missing a required marker")
            if not legacy_index < launcher_index < artifact_index:
                raise WorkflowPolicyError(
                    f"{label} must run legacy, receipt, and upload steps in order"
                )
            launcher = _step_block(
                job,
                policy.launcher_marker,
                label=f"{label} launcher",
            )
            if "continue-on-error:" in launcher:
                raise WorkflowPolicyError(f"{label} launcher must be blocking")
            if policy.launcher_condition not in launcher:
                raise WorkflowPolicyError(
                    f"{label} launcher must run after earlier failures unless cancelled"
                )
            if "--profile full" in launcher:
                raise WorkflowPolicyError(
                    f"{label} launcher cannot claim full-repository scope"
                )
            upload = _step_block(
                job,
                policy.artifact_marker,
                label=f"{label} upload",
            )
            if policy.upload_condition not in upload:
                raise WorkflowPolicyError(
                    f"{label} diagnostics must upload even on failure"
                )
            if "uses: actions/upload-artifact@v6" not in upload:
                raise WorkflowPolicyError(
                    f"{label} artifact marker is not an upload step"
                )
            if policy.participant_id == "cxx" and "**/run_plan.json" not in upload:
                raise WorkflowPolicyError(
                    f"{label} upload must retain the authenticated run plan"
                )
        except (OSError, WorkflowPolicyError) as error:
            errors.append(str(error))

    try:
        rust_job = _job_block(sources[".github/workflows/ci-rust.yml"], "test")
        variant_marker = "scan_run_contract.py --repo-root ."
        variant_preflight = _step_block(
            rust_job,
            variant_marker,
            label="ci-rust variant preflight",
        )
        if "continue-on-error:" in variant_preflight:
            raise WorkflowPolicyError("ci-rust variant preflight must be blocking")
        if "if: ${{ !cancelled() }}" not in variant_preflight:
            raise WorkflowPolicyError(
                "ci-rust variant preflight must run after earlier failures unless cancelled"
            )
        if rust_job.index(variant_marker) > rust_job.index(
            "run_scan_run_conformance.py --participant rust"
        ):
            raise WorkflowPolicyError(
                "ci-rust variant preflight must run before Rust receipt execution"
            )
    except (KeyError, WorkflowPolicyError) as error:
        errors.append(str(error))
    if errors:
        raise WorkflowPolicyError("; ".join(errors))
