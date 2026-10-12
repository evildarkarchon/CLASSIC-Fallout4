"""Static policy audit for all promoted semantic and consumer receipt jobs."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path

from .applicability import derive_applicability, load_policy_exceptions
from .consumers import load_consumer_obligations
from .packs import discover_pack_paths, load_and_validate_pack
from .participants import load_participants


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
# The derived families below expand only these base participant policies.
_BASE_POLICY_COUNT = len(_EXECUTION_POLICIES)

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
            if policy.participant_id == "rust"
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


# Focused analyzers share the semantic adapters, with no fabricated frontend
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
        "file-generation",
        "yaml-source-values",
        "yaml-file-values",
        "mod-ini",
        "message-logging",
        "wrye-report",
        "log-collection",
        "game-integrity",
        "game-orchestration",
        "game-setup-intake",
        "formid-finding",
        "markdown-rendering",
        "report-discovery",
        "shared-performance",
        "crashgen-check",
        "xse-plugin-validation",
        "hash-cache-controls",
        "ba2-scan",
        "unpacked-scan",
        "windows-platform-paths",
        "path-backups",
        "file-backups",
        "yaml-update-operations",
        "crash-pattern",
        "update-rejection",
        "database-operations",
        "version-registry",
        "scan-game",
        "path-operations",
        "path-normalization",
        "message-operations",
        "file-fingerprint",
        "dds-header",
        "log-parsing",
        "papyrus-monitor",
        "performance-timers",
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
    for policy in _EXECUTION_POLICIES[:_BASE_POLICY_COUNT]
    if policy.participant_id in {"rust", "cxx"}
    and not (family == "windows-platform-paths" and policy.participant_id == "cxx")
    and not (
        family in {"unpacked-scan", "xse-plugin-validation"}
        and policy.participant_id == "cxx"
    )
    and not (family == "shared-performance" and policy.participant_id == "cxx")
    and not (
        family
        in {"file-generation", "yaml-source-values", "mod-ini", "game-orchestration"}
        and policy.participant_id == "cxx"
    )
    and not (family == "performance-timers" and policy.participant_id == "cxx")
    and not (family == "dds-header" and policy.participant_id == "cxx")
    and not (family == "log-parsing" and policy.participant_id == "cxx")
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
    and not (
        family in {"settings-cached-docs", "version-registry-details"}
        and policy.participant_id == "cxx"
    )
    and not (
        family in {"registry-keys", "settings-yaml-batch"}
        and policy.participant_id == "cxx"
    )
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
        family in {"registry-context", "registry-paths"}
        and policy.participant_id == "cxx"
    )
    # Served only by bridge modules removed for having no production caller (#307).
    and not (
        family
        in {
            "database-operations",
            "fallout4-identity",
            "fallout4-paths",
            "formid-lookup",
            "game-version-parse",
            "performance",
            "version-pe",
            "version-registry",
        }
        and policy.participant_id == "cxx"
    )
    # Rust-only since the consumer-driven config/scangame bridge trim (#308):
    # no CLI or GUI production code calls the exports these families exercised.
    and not (
        family
        in {
            "ba2-scan",
            "config-vocabulary",
            "crashgen-check",
            "game-integrity",
            "installed-yaml-data",
            "scan-game",
            "wrye-report",
        }
        and policy.participant_id == "cxx"
    )
)
# Autoscan Reports use the shared scan-run launcher while retaining the same
# semantic adapters and separate diagnostics as the focused families.
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
    for policy in _EXECUTION_POLICIES[:_BASE_POLICY_COUNT]
    if policy.participant_id in {"rust", "cxx"}
)
# Crash Log Scan Launch (ADR-0009) also uses the shared scan-run launcher, with
# its own per-adapter runners, the same semantic adapters, and separate
# diagnostics. Frontends consume it through their own consumer launchers.
_EXECUTION_POLICIES += tuple(
    replace(
        policy,
        family_id="crash-log-scan-launch",
        launcher_marker=(
            f"run_scan_run_conformance.py --family crash-log-scan-launch --participant {policy.participant_id}"
            if policy.participant_id != "cxx"
            else "run_cxx_conformance.ps1 -Family crash-log-scan-launch -Compiler ${{ matrix.compiler }}"
        ),
        artifact_marker=(
            f"name: {policy.participant_id}-crash-log-scan-launch-conformance"
            + ("-${{ matrix.compiler }}" if policy.participant_id == "cxx" else "")
        ),
    )
    for policy in _EXECUTION_POLICIES[:_BASE_POLICY_COUNT]
    if policy.participant_id in {"rust", "cxx"}
)
# The native CLI launches through Crash Log Scan Launch (#289) and proves it with
# its own consumer receipt, on the same compiler matrix as its other families.
_EXECUTION_POLICIES += tuple(
    replace(
        policy,
        family_id="crash-log-scan-launch",
        launcher_marker=(
            "run_cli_consumer_conformance.ps1 -Family crash-log-scan-launch"
            " -Compiler ${{ matrix.compiler }}"
        ),
        artifact_marker=(
            "name: cli-crash-log-scan-launch-consumer-conformance-${{ matrix.compiler }}"
        ),
    )
    for policy in _EXECUTION_POLICIES[:_BASE_POLICY_COUNT]
    if policy.participant_id == "cli"
)
# The GUI launches every Crash Log Scan through Crash Log Scan Launch (#288), so
# its launch receipt is a blocking step of the GUI job with its own artifact,
# after the build that step reuses.
_EXECUTION_POLICIES += tuple(
    replace(
        policy,
        family_id="crash-log-scan-launch",
        launcher_marker=(
            "run_gui_consumer_conformance.ps1 -Family crash-log-scan-launch -Compiler ${{ matrix.compiler }}"
        ),
        artifact_marker=(
            "name: gui-crash-log-scan-launch-consumer-conformance-${{ matrix.compiler }}"
        ),
    )
    for policy in _EXECUTION_POLICIES[:_BASE_POLICY_COUNT]
    if policy.participant_id == "gui"
)
# The TUI launches its Crash Logs scans through Crash Log Scan Launch (#287).
_EXECUTION_POLICIES += tuple(
    replace(
        policy,
        family_id="crash-log-scan-launch",
        launcher_marker=(
            "run_scan_run_consumer_conformance.py --family crash-log-scan-launch --participant tui"
        ),
        artifact_marker="name: tui-crash-log-scan-launch-consumer-conformance",
    )
    for policy in _EXECUTION_POLICIES[:_BASE_POLICY_COUNT]
    if policy.participant_id == "tui"
)
# The CLI job retains its original suite and the bounded family launches.
_EXECUTION_POLICIES = tuple(
    replace(policy, job_timeout_minutes=360) if policy.job_id == "cli-tests" else policy
    for policy in _EXECUTION_POLICIES
)
# Families whose CXX runner needed bridge exports no frontend calls left CXX in
# #309; `participants.json` enrols them Rust-only, so their CI steps are gone.
# The filter runs last because the base CXX policy is the crash-log-scan-run
# family, and the derived families above still copy it.
_T2C_RUST_ONLY_FAMILIES = frozenset(
    {
        "autoscan-report",
        "crash-log-scan-run",
        "crash-pattern",
        "crash-suspect",
        "crashgen-settings",
        "formid-finding",
        "hash-cache-controls",
        "log-collection",
        "markdown-rendering",
        "message-logging",
        "mod-guidance",
        "named-record",
        "papyrus-monitor",
        "path-backups",
        "path-operations",
        "plugin-evidence",
        "registry-game",
        "registry-gui",
        "registry-operations",
        "runtime-access",
        "scan-run-vocabulary",
        "settings-load",
        "settings-validation",
        "settings-yaml",
        "update-decisions",
        "update-services",
        "web-operations",
        "xse-operations",
        "yaml-file-values",
        "yaml-update-operations",
    }
)
_EXECUTION_POLICIES = tuple(
    policy
    for policy in _EXECUTION_POLICIES
    if not (
        policy.participant_id == "cxx" and policy.family_id in _T2C_RUST_ONLY_FAMILIES
    )
)


def _required_execution_keys(repo_root: Path) -> set[tuple[str, str, str]]:
    """Derive every required family, adapter and compiler from tracked contracts.

    Workflow markers describe how CI executes a participant; they cannot define
    which participants are required, or new source mappings could silently skip CI.
    """

    participants = load_participants(repo_root)
    exceptions = load_policy_exceptions(repo_root)
    consumers = load_consumer_obligations(repo_root)
    required: set[tuple[str, str, str]] = set()
    tracked_families: set[str] = set()
    for path in discover_pack_paths(repo_root):
        document = load_and_validate_pack(repo_root, path).document()
        tracked_families.add(document["familyId"])
        matrix = derive_applicability(
            document,
            participants,
            policy_exceptions=exceptions,
            consumer_catalog=consumers,
        )
        required.update(
            (document["familyId"], participant.id, instance)
            for participant in matrix.participants
            for instance in participant.execution_instance_ids
        )
    # An enrolment for a family with no pack would never run, so a renamed or
    # deleted pack must not leave a silently dead participants.json entry.
    untracked = sorted(set(participants.family_ids) - tracked_families)
    if untracked:
        raise WorkflowPolicyError(
            "participants.json enrols untracked families: " + ", ".join(untracked)
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


def _has_exact_step_condition(step: str, expected: str) -> bool:
    """Require one reviewed step condition without extra execution restrictions."""

    # Matching a prefix admits `&& false`; only the YAML step key establishes
    # execution, so comments and command strings must not satisfy this policy.
    conditions = re.findall(r"(?m)^        (if:[^\r\n]*)$", step)
    return [condition.rstrip() for condition in conditions] == [expected]


def _validate_corrosion_source_workflow(repo_root: Path) -> None:
    """Bind native builds to one verified current-run Corrosion checkout."""
    source = (repo_root / ".github" / "workflows" / "ci-cpp.yml").read_text(
        encoding="utf-8"
    )
    revision = "1499b14e4906a2890f5cee1547c8848db261753d"
    artifact_name = "corrosion-source-v0.6.1"
    fetch = _job_block(source, "corrosion-source")
    archive = _step_block(
        fetch,
        "Archive verified Corrosion v0.6.1 source",
        label="Corrosion source archive",
    )
    for marker in (
        "git clone --depth 1 --branch v0.6.1",
        revision,
        "git -C $sourceDir archive --format=zip",
        "Get-FileHash -LiteralPath $archivePath -Algorithm SHA256",
    ):
        if marker not in archive:
            raise WorkflowPolicyError("Corrosion source must be pinned and archived once")
    upload = _step_block(fetch, "Upload pinned Corrosion source", label="Corrosion source upload")
    for line in (
        "        uses: actions/upload-artifact@v6",
        f"          name: {artifact_name}",
        "          path: ${{ runner.temp }}/classic-corrosion-artifact/",
        "          if-no-files-found: error",
    ):
        if line not in upload.splitlines():
            raise WorkflowPolicyError("Corrosion source archive must be uploaded")
    if "    continue-on-error:" in fetch or "matrix:" in fetch:
        raise WorkflowPolicyError("Corrosion source fetch must be one blocking job")

    for job_id, build_step in (
        ("cli-tests", "Build and test CLI"),
        ("gui-tests", "Build and test GUI"),
    ):
        job = _job_block(source, job_id)
        if "    needs: [corrosion-source]" not in job.splitlines():
            raise WorkflowPolicyError("Corrosion source must gate each native build")
        download = _step_block(
            job, "Download pinned Corrosion source", label="Corrosion source download"
        )
        for line in (
            "        uses: actions/download-artifact@v8",
            f"          name: {artifact_name}",
            "          path: ${{ runner.temp }}/classic-corrosion-artifact",
        ):
            if line not in download.splitlines():
                raise WorkflowPolicyError("Corrosion source must come from this run")
        if re.search(
            r"(?m)^\s+(run-id|repository|github-token|artifact-ids):",
            "\n".join(download.splitlines()[1:]),
        ):
            raise WorkflowPolicyError("Corrosion source must come from this run")
        verify = _step_block(
            job,
            "Verify and extract pinned Corrosion source",
            label="Corrosion source verification",
        )
        for marker in (
            revision,
            "Get-FileHash -LiteralPath $archivePath -Algorithm SHA256",
            "Expand-Archive -LiteralPath $archivePath",
            "CLASSIC_CORROSION_SOURCE_DIR=$sourceDir",
        ):
            if marker not in verify:
                raise WorkflowPolicyError("Corrosion source verification was weakened")
        if not job.index("Verify and extract pinned Corrosion source") < job.index(build_step):
            raise WorkflowPolicyError("Corrosion source must be verified before build")


def _validate_full_aggregation(repo_root: Path) -> None:
    """Keep the repository gate bound to every current-run native participant.

    Local reusable workflow references share the caller revision. Downloading
    separate artifact directories preserves immutable receipt/plan pairs; a
    cross-run download cannot certify this checkout.
    """
    source = (repo_root / ".github/workflows/ci-binding-compliance.yml").read_text(
        encoding="utf-8"
    )
    callers = {
        "rust": ".github/workflows/ci-rust.yml",
        "native": ".github/workflows/ci-cpp.yml",
    }
    for job_id, workflow in callers.items():
        job = _job_block(source, job_id)
        if not re.search(rf"(?m)^    uses: \./{re.escape(workflow)}$", job):
            raise WorkflowPolicyError(
                "full aggregation requires same-revision reusable jobs"
            )
        if re.search(r"(?m)^    (if|continue-on-error|needs):", job):
            raise WorkflowPolicyError(
                "full aggregation cannot skip required reusable jobs"
            )
        reusable = (repo_root / workflow).read_text(encoding="utf-8")
        if not re.search(r"(?m)^  workflow_call:\s*$", reusable):
            raise WorkflowPolicyError(
                "full aggregation participants must support workflow_call"
            )
    full = _job_block(source, "full")
    for line in (
        "    needs: [rust, native]",
        "    if: ${{ !cancelled() }}",
        "    runs-on: windows-latest",
    ):
        if line not in full.splitlines():
            raise WorkflowPolicyError(
                "full aggregation must await every Windows participant"
            )
    if re.search(r"(?m)^    continue-on-error:", full):
        raise WorkflowPolicyError("full aggregation must be blocking")
    checkout = _step_block(
        full, "uses: actions/checkout@v6", label="full aggregation checkout"
    )
    if re.search(r"(?m)^\s+(ref|path|repository):", checkout):
        raise WorkflowPolicyError(
            "full aggregation must preserve event checkout identity"
        )
    download = _step_block(
        full,
        "Download current-run conformance artifacts",
        label="full aggregation download",
    )
    for line in (
        "        uses: actions/download-artifact@v8",
        "          pattern: '*conformance*'",
        "          path: tools/binding_compliance/artifacts/downloaded",
        "          merge-multiple: false",
    ):
        if line not in download.splitlines():
            raise WorkflowPolicyError(
                "full aggregation requires every unmerged receipt artifact"
            )
    if re.search(
        r"(?m)^\s+(run-id|repository|github-token|name|artifact-ids):",
        "\n".join(download.splitlines()[1:]),
    ):
        raise WorkflowPolicyError(
            "full aggregation artifacts must come from the current workflow run"
        )
    upstream = _step_block(
        full,
        "Require every retained participant job to pass",
        label="full aggregation upstream results",
    )
    if (
        "          PARTICIPANT_RESULTS: ${{ toJSON(needs) }}"
        not in upstream.splitlines()
        or "continue-on-error:" in upstream
        or not _has_exact_step_condition(upstream, "if: ${{ !cancelled() }}")
    ):
        raise WorkflowPolicyError(
            "full aggregation must require actual upstream job results"
        )
    command = "python tools/binding_compliance/check_compliance.py --repo-root . --profile full --receipt-directory tools/binding_compliance/artifacts/downloaded --output-dir tools/binding_compliance/artifacts/full"
    launcher = _step_block(
        full,
        "tools/binding_compliance/check_compliance.py",
        label="full aggregation launcher",
    )
    if (
        f"        run: {command}" not in launcher.splitlines()
        or "continue-on-error:" in launcher
    ):
        raise WorkflowPolicyError(
            "full aggregation must execute the complete full profile"
        )
    if not _has_exact_step_condition(launcher, "if: ${{ !cancelled() }}"):
        raise WorkflowPolicyError("full aggregation must report upstream failures")
    _validate_corrosion_source_workflow(repo_root)


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
    try:
        _validate_full_aggregation(root)
    except (OSError, WorkflowPolicyError) as error:
        errors.append(f"full aggregation: {error}")
    sources: dict[str, str] = {}
    for policy in _EXECUTION_POLICIES:
        try:
            source = sources.setdefault(
                policy.workflow,
                (root / policy.workflow).read_text(encoding="utf-8"),
            )
            job = _job_block(source, policy.job_id)
            label = f"{policy.workflow}:{policy.job_id}:{policy.participant_id}"
            if "    runs-on: windows-latest" not in job.splitlines():
                raise WorkflowPolicyError(
                    f"{label} must preserve the Windows receipt checkout layout"
                )
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
            if re.search(r"(?m)^\s+(path|repository):", checkout):
                raise WorkflowPolicyError(
                    f"{label} must preserve the default receipt checkout layout"
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
            if not _has_exact_step_condition(launcher, policy.launcher_condition):
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
            if not _has_exact_step_condition(upload, policy.upload_condition):
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
        if not _has_exact_step_condition(variant_preflight, "if: ${{ !cancelled() }}"):
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
