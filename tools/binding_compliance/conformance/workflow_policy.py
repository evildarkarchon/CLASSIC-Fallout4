"""Static policy audit for all promoted semantic and consumer receipt jobs."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path

from .applicability import derive_applicability, load_policy_exceptions
from .consumers import load_consumer_obligations
from .coverage import load_source_parity_rows
from .packs import discover_pack_paths, load_and_validate_pack


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
    family_id: str = "crash-log-scan-run"
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

# Both promoted families retain the same native denominator and predecessor
# gates. Family selection precedes compiler selection so markers stay unique.
_EXECUTION_POLICIES += tuple(
    replace(
        policy,
        family_id="user-settings",
        launcher_marker=(
            policy.launcher_marker.replace(
                "run_scan_run_conformance.py", "run_user_settings_conformance.py"
            )
            if policy.participant_id in {"rust", "node", "python"}
            else policy.launcher_marker.replace(
                " --participant", " --family user-settings --participant"
            ).replace(" -Compiler", " -Family user-settings -Compiler")
        ),
        artifact_marker=(
            "name: "
            + policy.participant_id
            + "-user-settings-"
            + (
                "consumer-conformance"
                if policy.participant_id in {"cli", "gui", "tui"}
                else "conformance"
            )
            + (
                "-${{ matrix.compiler }}"
                if policy.matrix_marker == "compiler: [msvc, clang-cl]"
                else ""
            )
        ),
    )
    for policy in _EXECUTION_POLICIES
)


# Focused analyzers share four semantic adapters, with no fabricated frontend
# obligations. Every family has its own blocking step and diagnostic artifact.
_EXECUTION_POLICIES += tuple(
    replace(
        policy,
        family_id=family,
        launcher_marker=(
            f"run_semantic_conformance.py --family {family} --participant {policy.participant_id}"
            if policy.participant_id != "cxx"
            else f"run_cxx_conformance.ps1 -Family {family} -Compiler ${{{{ matrix.compiler }}}}"
        ),
        artifact_marker=(
            f"name: {policy.participant_id}-{family}-conformance"
            + ("-${{ matrix.compiler }}" if policy.participant_id == "cxx" else "")
        ),
    )
    for family in (
        "crash-suspect",
        "crashgen-settings",
        "mod-guidance",
        "formid-lookup",
        "named-record",
        "plugin-evidence",
        "installed-yaml-data",
        "config-vocabulary",
        "scan-run-vocabulary",
        "config-operations",
        "file-operations",
        "database-operations",
        "version-registry",
        "scan-game",
        "path-operations",
        "path-normalization",
        "message-operations",
        "file-fingerprint",
        "performance",
        "update-decisions",
        "update-services",
        "string-operations",
        "registry-operations",
        "registry-game",
        "registry-gui",
        "registry-context",
        "registry-keys",
        "game-version-parse",
        "game-version-distance",
        "game-version-order",
        "fallout4-identity",
        "fallout4-paths",
        "fallout4-metadata",
        "version-registry-values",
        "settings-yaml-batch",
        "registry-paths",
        "web-operations",
        "resource-operations",
        "version-operations",
        "version-extraction",
        "version-f4se",
        "version-pe",
        "version-pe-path",
        "xse-operations",
        "xse-folder",
        "installation-paths",
        "game-identity",
        "runtime-access",
        "settings-load",
        "settings-yaml",
        "settings-validation",
        "settings-cached-docs",
        "version-registry-details",
    )
    for policy in _EXECUTION_POLICIES[:7]
    if policy.participant_id in {"rust", "node", "python", "cxx"}
    and not (
        family
        in {
            "path-normalization",
            "message-operations",
            "file-fingerprint",
            "string-operations",
            "resource-operations",
            "version-operations",
        }
        and policy.participant_id == "cxx"
    )
    and not (
        family in {"version-extraction", "version-f4se", "version-pe-path"}
        and policy.participant_id == "cxx"
    )
    and not (family == "xse-folder" and policy.participant_id in {"node", "python"})
    and not (family == "version-f4se" and policy.participant_id == "node")
    and not (
        family in {"settings-cached-docs", "version-registry-details"}
        and policy.participant_id == "cxx"
    )
    and not (family == "settings-validation" and policy.participant_id == "node")
    and not (
        family in {"registry-keys", "settings-yaml-batch"}
        and policy.participant_id == "cxx"
    )
    and not (family == "registry-keys" and policy.participant_id == "node")
    and not (family == "settings-yaml-batch" and policy.participant_id == "python")
    and not (
        family
        in {
            "fallout4-metadata",
            "game-version-order",
            "version-registry-values",
            "game-version-distance",
        }
        and policy.participant_id == "cxx"
    )
    and not (
        family
        in {
            "fallout4-metadata",
            "fallout4-paths",
            "game-version-order",
            "version-registry-values",
        }
        and policy.participant_id == "node"
    )
    and not (family == "runtime-access" and policy.participant_id == "python")
    and not (
        family in {"registry-context", "registry-paths"}
        and policy.participant_id == "cxx"
    )
    and not (
        family in {"registry-context", "registry-gui"}
        and policy.participant_id == "node"
    )
)
# Autoscan Reports use the shared scan-run launcher while retaining the same
# four semantic adapters and separate diagnostics as the focused families.
_EXECUTION_POLICIES += tuple(
    replace(
        policy,
        family_id="autoscan-report",
        launcher_marker=(
            f"run_scan_run_conformance.py --family autoscan-report --participant {policy.participant_id}"
            if policy.participant_id != "cxx"
            else "run_cxx_conformance.ps1 -Family autoscan-report -Compiler ${{ matrix.compiler }}"
        ),
        artifact_marker=(
            f"name: {policy.participant_id}-autoscan-report-conformance"
            + ("-${{ matrix.compiler }}" if policy.participant_id == "cxx" else "")
        ),
    )
    for policy in _EXECUTION_POLICIES[:7]
    if policy.participant_id in {"rust", "node", "python", "cxx"}
)
# The CLI job retains its original suite and the bounded family launches.
_EXECUTION_POLICIES = tuple(
    replace(policy, job_timeout_minutes=360) if policy.job_id == "cli-tests" else policy
    for policy in _EXECUTION_POLICIES
)


def _required_execution_keys(repo_root: Path) -> set[tuple[str, str, str]]:
    """Derive every required family, adapter and compiler from tracked contracts.

    Workflow markers describe how CI executes a participant; they cannot define
    which participants are required, or new source mappings could silently skip CI.
    """

    rows = load_source_parity_rows(repo_root)
    exceptions = load_policy_exceptions(repo_root)
    consumers = load_consumer_obligations(repo_root)
    required: set[tuple[str, str, str]] = set()
    for path in discover_pack_paths(repo_root):
        document = load_and_validate_pack(repo_root, path).document()
        matrix = derive_applicability(
            document, rows, policy_exceptions=exceptions, consumer_catalog=consumers
        )
        required.update(
            (document["familyId"], participant.id, instance)
            for participant in matrix.participants
            for instance in participant.execution_instance_ids
        )
    if not required:
        raise WorkflowPolicyError("required execution denominator is empty")
    return required


def _validate_execution_denominator(repo_root: Path) -> None:
    """Reject missing or duplicate CI policies for source-derived executions."""

    required = _required_execution_keys(repo_root)
    enforced: set[tuple[str, str, str]] = set()
    for policy in _EXECUTION_POLICIES:
        instances = (
            ("windows-clang-cl", "windows-msvc")
            if policy.matrix_marker == "compiler: [msvc, clang-cl]"
            else (policy.participant_id,)
        )
        for instance in instances:
            key = (policy.family_id, policy.participant_id, instance)
            if key in enforced:
                raise WorkflowPolicyError(f"duplicate required execution policy: {key}")
            enforced.add(key)
    missing = required - enforced
    if missing:
        raise WorkflowPolicyError(
            f"missing required execution policies: {sorted(missing)}"
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
    try:
        _validate_execution_denominator(root)
    except (OSError, ValueError) as error:
        errors.append(str(error))
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
            if policy.participant_id == "gui":
                legacy = _step_block(
                    job, policy.legacy_marker, label=f"{label} legacy build"
                )
                # A different preset rebuilds Qt through vcpkg and consumes the bounded
                # receipt window before the consumer can execute.
                if any(
                    re.findall(r"(?<!\S)-Preset\s+(\S+)", step) != ["ci-system-qt"]
                    for step in (legacy, launcher)
                ):
                    raise WorkflowPolicyError(
                        f"{label} must reuse the preceding GUI build preset ci-system-qt"
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
