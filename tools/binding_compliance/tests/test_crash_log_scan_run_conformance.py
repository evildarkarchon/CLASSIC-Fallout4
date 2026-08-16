"""Behavior tests for the real Crash Log Scan Run conformance family."""

from __future__ import annotations

import copy
import json
import shutil
import sys
import time
from pathlib import Path

import pytest
import run_scan_run_conformance as scan_run_launcher
from conformance.applicability import derive_applicability, load_policy_exceptions
from conformance.coverage import (
    derive_observed_fact_ids,
    derive_row_coverage,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
)
from conformance.families.crash_log_scan_run import (
    CRASH_LOG_SCAN_RUN_COVERAGE_POLICY,
    REQUIRED_OBSERVATION_FACT_IDS,
)
from conformance.packs import (
    MaterializedRun,
    ValidatedPack,
    discover_pack_paths,
    load_and_validate_pack,
    materialize_run_plan,
)
from conformance.receipts import PreparedRunReport, validate_prepared_run
from conformance.reports import build_scoped_report

REPO_ROOT = Path(__file__).resolve().parents[3]
PACK_PATH = (
    REPO_ROOT / "tests" / "conformance" / "packs" / "crash_log_scan_run" / "v1.json"
)
PARTICIPANT_SOURCES = {
    "rust": (
        REPO_ROOT
        / "business-logic"
        / "classic-scan-presentation"
        / "tests"
        / "scan_run_conformance.rs",
    ),
    "node": (
        REPO_ROOT
        / "node-bindings"
        / "classic-node"
        / "__test__"
        / "scan_run_conformance_runner.ts",
    ),
    "python": (
        REPO_ROOT / "python-bindings" / "tests" / "scan_run_conformance_runner.py",
    ),
}


def test_live_pack_is_input_only_for_all_three_base_adapters(tmp_path: Path) -> None:
    """Fresh Rust, Node, and Python plans share scenarios but never the oracle."""

    pack = load_and_validate_pack(REPO_ROOT, PACK_PATH)
    discovered = [
        path
        for path in discover_pack_paths(REPO_ROOT)
        if load_and_validate_pack(REPO_ROOT, path).document()["familyId"]
        == "crash-log-scan-run"
    ]

    assert discovered == [PACK_PATH]
    pack_document = pack.document()
    assert set(pack_document["fixtures"]) == {
        "validCrashLog",
        "mainYaml",
        "gameYaml",
        "localIgnoreYaml",
    }
    assert "manifest.json" not in str(pack_document)
    assert [scenario["id"] for scenario in pack_document["scenarios"]] == [
        "standard-happy-path",
        "targeted-happy-path",
    ]

    artifact_root = (
        REPO_ROOT
        / "tools"
        / "binding_compliance"
        / "artifacts"
        / "test-scan-run-pack"
        / tmp_path.name
    )
    plans = {}
    try:
        for participant_id, source_paths in PARTICIPANT_SOURCES.items():
            prepared = materialize_run_plan(
                pack,
                participant_id=participant_id,
                participant_role="semantic-adapter",
                execution_instance_id=participant_id,
                source_paths=source_paths,
                artifact_root=artifact_root,
            )
            plan = prepared.document()
            plans[participant_id] = plan
            assert not prepared.receipt_path.exists()
            assert all("expected" not in scenario for scenario in plan["scenarios"])
            assert [scenario["id"] for scenario in plan["scenarios"]] == [
                "standard-happy-path",
                "targeted-happy-path",
            ]
    finally:
        if artifact_root.exists():
            shutil.rmtree(artifact_root)

    assert len({plan["expectationDigest"] for plan in plans.values()}) == 1
    assert len({plan["invocation"]["id"] for plan in plans.values()}) == 3
    assert len({plan["invocation"]["sourceIdentity"] for plan in plans.values()}) == 3


def test_cxx_preparation_materializes_fresh_input_only_toolchain_instances(
    tmp_path: Path,
) -> None:
    """MSVC and clang-cl receive distinct current plans without the tracked oracle."""

    from conformance.adapters.prepare_cxx_conformance import prepare_cxx_run

    artifact_root = (
        REPO_ROOT
        / "tools"
        / "binding_compliance"
        / "artifacts"
        / "test-cxx-preparation"
        / tmp_path.name
    )
    plans = {}
    try:
        for compiler in ("msvc", "clang-cl"):
            prepared = prepare_cxx_run(
                REPO_ROOT,
                compiler=compiler,
                artifact_root=artifact_root,
            )
            plan = prepared.document()
            plans[compiler] = plan

            assert prepared.artifact_dir.parent.name == f"windows-{compiler}"
            assert prepared.artifact_dir.parent.parent.name == "cxx"
            assert not prepared.receipt_path.exists()
            assert plan["participant"] == {
                "id": "cxx",
                "role": "semantic-adapter",
                "executionInstanceId": f"windows-{compiler}",
            }
            assert all("expected" not in scenario for scenario in plan["scenarios"])
            assert [scenario["id"] for scenario in plan["scenarios"]] == [
                "standard-happy-path",
                "targeted-happy-path",
            ]
    finally:
        if artifact_root.exists():
            shutil.rmtree(artifact_root)

    assert plans["msvc"]["expectationDigest"] == plans["clang-cl"]["expectationDigest"]
    assert plans["msvc"]["invocation"]["id"] != plans["clang-cl"]["invocation"]["id"]


def test_family_policy_derives_every_required_fact_from_each_exact_oracle() -> None:
    """Coverage facts come from semantic observation predicates, not runner claims."""

    pack = load_and_validate_pack(REPO_ROOT, PACK_PATH).document()

    for scenario in pack["scenarios"]:
        facts = derive_observed_fact_ids(
            pack,
            scenario,
            scenario["expected"],
            CRASH_LOG_SCAN_RUN_COVERAGE_POLICY,
        )
        assert facts == REQUIRED_OBSERVATION_FACT_IDS


def test_family_policy_loses_the_corresponding_fact_when_each_family_changes() -> None:
    """Every advertised observation family has a fail-closed semantic predicate."""

    pack = load_and_validate_pack(REPO_ROOT, PACK_PATH).document()
    scenario = pack["scenarios"][0]
    mutations = {
        "scan-run.status": lambda value: value["run"].__setitem__(
            "status", "cancelled"
        ),
        "scan-run.discovery": lambda value: value["discovery"][
            "acceptedLogs"
        ].reverse(),
        "scan-run.setup": lambda value: value["run"].__setitem__(
            "setup", {"status": "unexpected"}
        ),
        "scan-run.effective-concurrency": lambda value: value["run"].__setitem__(
            "effectiveConcurrency", 1
        ),
        "scan-run.installed-yaml-data": lambda value: value["installedYamlData"][
            "main"
        ]["identity"].__setitem__("byteLength", 0),
        "scan-run.log-outcomes": lambda value: value["logs"][0].__setitem__(
            "disposition", "failed"
        ),
        "scan-run.events": lambda value: value["events"]["logs"][0]["trace"].pop(),
        "scan-run.display-content": lambda value: value["displayContent"].pop(),
        "scan-run.durable-effects": lambda value: value["durableEffects"]["reports"][
            0
        ].__setitem__("exists", False),
    }

    for fact_id, mutate in mutations.items():
        changed = copy.deepcopy(scenario["expected"])
        mutate(changed)
        facts = derive_observed_fact_ids(
            pack,
            scenario,
            changed,
            CRASH_LOG_SCAN_RUN_COVERAGE_POLICY,
        )
        assert fact_id not in facts

    malformed_log = copy.deepcopy(scenario["expected"])
    malformed_log["logs"][0]["crashLog"] = {}
    malformed_facts = derive_observed_fact_ids(
        pack,
        scenario,
        malformed_log,
        CRASH_LOG_SCAN_RUN_COVERAGE_POLICY,
    )
    assert "scan-run.log-outcomes" not in malformed_facts


def test_native_workflows_publish_participant_shadow_artifacts_separately() -> None:
    """Runtime jobs keep legacy gates blocking and upload each new slice always."""

    workflow_expectations = {
        ".github/workflows/ci-cpp.yml": (
            "Build and test CLI",
            "run_cxx_conformance.ps1",
            "name: cxx-conformance-${{ matrix.compiler }}",
        ),
        ".github/workflows/ci-rust.yml": (
            "Run Rust tests with all features",
            "--participant rust",
            "name: rust-scan-run-shadow-conformance",
        ),
        ".github/workflows/ci-typescript.yml": (
            "Run Node runtime smoke tests",
            "--participant node",
            "name: node-scan-run-shadow-conformance",
        ),
        ".github/workflows/ci-python-bindings.yml": (
            "Run Python bindings smoke tests",
            "--participant python",
            "name: python-scan-run-shadow-conformance",
        ),
    }

    for relative_path, (
        blocking_step,
        participant,
        artifact_name,
    ) in workflow_expectations.items():
        source = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        blocking_index = source.index(blocking_step)
        shadow_index = source.index(participant)
        artifact_index = source.index(artifact_name)
        assert blocking_index < shadow_index < artifact_index
        shadow_block = source[shadow_index - 160 : artifact_index]
        assert "continue-on-error: true" in shadow_block
        upload_block = source[artifact_index - 160 : artifact_index + 160]
        assert "always()" in upload_block

    assert "--participant cxx" not in "\n".join(
        (REPO_ROOT / path).read_text(encoding="utf-8") for path in workflow_expectations
    )
    cpp_workflow = (REPO_ROOT / ".github/workflows/ci-cpp.yml").read_text(
        encoding="utf-8"
    )
    cli_job = cpp_workflow[cpp_workflow.index("cli-tests:") :]
    assert "timeout-minutes: 120" in cli_job
    full_suite = cli_job[
        cli_job.index("- name: Build and test CLI") : cli_job.index(
            "- name: Run native CXX scan conformance"
        )
    ]
    assert "timeout-minutes: 90" in full_suite


def _write_engine_test_receipt(prepared: MaterializedRun, pack: ValidatedPack) -> None:
    """Publish an oracle-shaped receipt for central aggregation unit tests only."""

    plan = prepared.document()
    pack_document = pack.document()
    expected_by_id = {
        scenario["id"]: scenario["expected"] for scenario in pack_document["scenarios"]
    }
    receipt = {
        "schemaVersion": plan["schemaVersion"],
        "familyId": plan["familyId"],
        "familyVersion": plan["familyVersion"],
        "expectationDigest": plan["expectationDigest"],
        "invocation": plan["invocation"],
        "participant": plan["participant"],
        "runner": {
            "id": "synthetic-engine-test",
            "version": 1,
            "platform": "windows",
            "toolchain": "pytest",
        },
        "scenarios": [
            {
                "id": scenario["id"],
                "executionStatus": "completed",
                "capabilityIds": scenario["capabilityIds"],
                "observation": expected_by_id[scenario["id"]],
                "failure": None,
            }
            for scenario in plan["scenarios"]
        ],
    }
    prepared.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")


def _prepare_base_adapter_reports(
    pack: ValidatedPack, artifact_root: Path
) -> list[PreparedRunReport]:
    """Materialize and centrally validate Rust, Node, and Python test receipts."""

    prepared_reports = []
    for participant_id, source_paths in PARTICIPANT_SOURCES.items():
        prepared = materialize_run_plan(
            pack,
            participant_id=participant_id,
            participant_role="semantic-adapter",
            execution_instance_id=participant_id,
            source_paths=source_paths,
            artifact_root=artifact_root,
        )
        _write_engine_test_receipt(prepared, pack)
        prepared_reports.append(
            validate_prepared_run(
                pack,
                prepared,
                receipt_paths=(prepared.receipt_path,),
                coverage_policy=CRASH_LOG_SCAN_RUN_COVERAGE_POLICY,
            )
        )
    return prepared_reports


def test_three_base_receipts_pass_their_scopes_but_not_full_repository(
    tmp_path: Path,
) -> None:
    """Rust/Node/Python are exact shadow slices while the CXX denominator remains."""

    pack = load_and_validate_pack(REPO_ROOT, PACK_PATH)
    artifact_root = (
        REPO_ROOT
        / "tools"
        / "binding_compliance"
        / "artifacts"
        / "test-scan-run-report"
        / tmp_path.name
    )
    try:
        prepared_reports = _prepare_base_adapter_reports(pack, artifact_root)

        pack_document = pack.document()
        parity_rows = load_source_parity_rows(REPO_ROOT)
        retained = load_retained_analyzer_kinds(REPO_ROOT)
        exceptions = load_policy_exceptions(REPO_ROOT)
        applicability = derive_applicability(
            pack_document,
            parity_rows,
            policy_exceptions=exceptions,
        )
        for prepared_report in prepared_reports:
            participant_id = str(prepared_report.participant["id"])
            coverage = derive_row_coverage(
                pack_document,
                parity_rows,
                CRASH_LOG_SCAN_RUN_COVERAGE_POLICY,
                (prepared_report,),
                scope_participant_id=participant_id,
                retained_analyzers=retained,
                policy_exceptions=exceptions,
            )
            scoped = build_scoped_report(
                family_id="crash-log-scan-run",
                profile="conformance",
                applicability=applicability,
                prepared_reports=(prepared_report,),
                participant_id=participant_id,
                execution_instance_id=participant_id,
                coverage=coverage,
            ).document()
            assert scoped["result"] == "pass"
            assert scoped["repositoryComplete"] is False

        full_coverage = derive_row_coverage(
            pack_document,
            parity_rows,
            CRASH_LOG_SCAN_RUN_COVERAGE_POLICY,
            tuple(prepared_reports),
            retained_analyzers=retained,
            policy_exceptions=exceptions,
        )
        full = build_scoped_report(
            family_id="crash-log-scan-run",
            profile="full",
            applicability=applicability,
            prepared_reports=tuple(prepared_reports),
            coverage=full_coverage,
        ).document()
        assert full["result"] == "fail"
        assert full["repositoryComplete"] is False
        assert any(
            execution["participantId"] == "cxx"
            for execution in full["missingExecutions"]
        )
    finally:
        if artifact_root.exists():
            shutil.rmtree(artifact_root)


def test_all_base_adapter_instances_complete_full_repository_scope(
    tmp_path: Path,
) -> None:
    """Rust, Node, Python, MSVC, and clang-cl satisfy the semantic denominator."""

    from conformance.adapters.prepare_cxx_conformance import prepare_cxx_run

    pack = load_and_validate_pack(REPO_ROOT, PACK_PATH)
    artifact_root = (
        REPO_ROOT
        / "tools"
        / "binding_compliance"
        / "artifacts"
        / "test-full-scan-run-report"
        / tmp_path.name
    )
    try:
        prepared_reports = _prepare_base_adapter_reports(pack, artifact_root)

        for compiler in ("msvc", "clang-cl"):
            prepared = prepare_cxx_run(
                REPO_ROOT,
                compiler=compiler,
                artifact_root=artifact_root,
            )
            _write_engine_test_receipt(prepared, pack)
            prepared_reports.append(
                validate_prepared_run(
                    pack,
                    prepared,
                    receipt_paths=(prepared.receipt_path,),
                    coverage_policy=CRASH_LOG_SCAN_RUN_COVERAGE_POLICY,
                )
            )

        pack_document = pack.document()
        parity_rows = load_source_parity_rows(REPO_ROOT)
        retained = load_retained_analyzer_kinds(REPO_ROOT)
        exceptions = load_policy_exceptions(REPO_ROOT)
        applicability = derive_applicability(
            pack_document,
            parity_rows,
            policy_exceptions=exceptions,
        )
        coverage = derive_row_coverage(
            pack_document,
            parity_rows,
            CRASH_LOG_SCAN_RUN_COVERAGE_POLICY,
            tuple(prepared_reports),
            retained_analyzers=retained,
            policy_exceptions=exceptions,
        )
        report = build_scoped_report(
            family_id="crash-log-scan-run",
            profile="full",
            applicability=applicability,
            prepared_reports=tuple(prepared_reports),
            coverage=coverage,
        ).document()

        assert report["result"] == "pass"
        assert report["repositoryComplete"] is True
        assert report["missingExecutions"] == []
    finally:
        if artifact_root.exists():
            shutil.rmtree(artifact_root)


def test_cxx_runner_and_launcher_stay_bridge_only_and_oracle_blind() -> None:
    """Native evidence uses the generated bridge and only the approved wrapper."""

    runner_path = (
        REPO_ROOT
        / "classic-cli"
        / "tests"
        / "conformance"
        / "classic_cxx_conformance.cpp"
    )
    runner = runner_path.read_text(encoding="utf-8")
    assert '"classic_cxx_bridge/scanner.h"' in runner
    assert "ScanRunObserver" in runner
    assert "scan_run_contract_execute" in runner
    assert 'scenario.contains("expected")' in runner
    assert "scan_run_fixture_config" not in runner
    assert "manifest.json" not in runner
    assert "tests/conformance/packs" not in runner.replace("\\", "/")
    assert "scan_run_cli" not in runner

    cmake = (REPO_ROOT / "classic-cli" / "CMakeLists.txt").read_text(encoding="utf-8")
    target_start = cmake.index("add_executable(classic-cxx-conformance")
    target_end = cmake.index("add_test(NAME classic-cxx-conformance", target_start)
    target_block = cmake[target_start:target_end]
    assert "classic_cxx_bridge" in target_block
    assert "nlohmann_json::nlohmann_json" in target_block
    assert "src/scan_run_cli.cpp" not in target_block
    assert "src/scanner.cpp" not in target_block

    launcher = (
        REPO_ROOT
        / "tools"
        / "binding_compliance"
        / "conformance"
        / "adapters"
        / "run_cxx_conformance.ps1"
    ).read_text(encoding="utf-8")
    assert "15 * 60 * 1000" in launcher
    wrapper_start = launcher.index("$WrapperArguments = @(")
    wrapper_end = launcher.index("$RecordedCommand", wrapper_start)
    wrapper_block = launcher[wrapper_start:wrapper_end]
    required_tokens = (
        '"-File"',
        '"classic-cli/build_cli.ps1"',
        '"-Test"',
        '"-CTestName"',
        '"classic-cxx-conformance"',
        '"-Compiler"',
        "$Compiler",
        '"-CTestArgs"',
        '"--output-junit"',
        "$JunitPath",
    )
    positions = tuple(wrapper_block.index(token) for token in required_tokens)
    assert positions == tuple(sorted(positions))
    assert wrapper_block.rstrip().endswith(")")
    assert "$Process.Kill($true)" in launcher
    assert '--execution-instance "windows-$Compiler"' in launcher
    assert "--attempt $AttemptPath" in launcher
    assert "--junit $JunitPath" in launcher
    assert "Get-FileSha256" in launcher


def test_runners_are_private_and_call_only_their_public_scan_run_seams() -> None:
    """No adapter runner imports the tracked oracle or the legacy manifest."""

    seam_markers = {
        "rust": ("contract::execute", "render_run_result"),
        "node": ("scanRunExecute", 'from "../index.js"'),
        "python": ("scan_run_execute", "import classic_scanlog"),
    }
    for participant_id, source_paths in PARTICIPANT_SOURCES.items():
        source = source_paths[0].read_text(encoding="utf-8")
        assert "manifest.json" not in source
        assert "tests/conformance/packs" not in source.replace("\\", "/")
        assert all(marker in source for marker in seam_markers[participant_id])


def test_launcher_records_spawn_failures_as_structured_shadow_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing adapter executable still produces an attempt and shadow report."""

    def fail_to_spawn(*_args: object, **_kwargs: object) -> tuple[None, None, OSError]:
        """Simulate an unavailable native runner executable."""

        return None, None, FileNotFoundError("adapter executable is unavailable")

    artifact_root = (
        REPO_ROOT
        / "tools"
        / "binding_compliance"
        / "artifacts"
        / "test-launcher-failure"
        / tmp_path.name
    )
    monkeypatch.setattr(scan_run_launcher, "_run_adapter_command", fail_to_spawn)
    try:
        result, artifact_dir = scan_run_launcher.run_participant(
            "rust",
            artifact_root=artifact_root,
        )

        attempt = json.loads(
            (artifact_dir / "attempt.json").read_text(encoding="utf-8")
        )
        report = json.loads(
            (artifact_dir / "shadow_report.json").read_text(encoding="utf-8")
        )
        assert result == 1
        assert attempt["exitCode"] is None
        assert attempt["timedOut"] is False
        assert "adapter executable is unavailable" in attempt["launchError"]
        assert report["result"] == "fail"
        environment_failures = [
            failure
            for failure in report["failures"]
            if failure["kind"] == "local_environment_failure"
        ]
        assert len(environment_failures) == 1
        assert "adapter executable is unavailable" in environment_failures[0]["message"]
        assert not (artifact_dir / "receipt.json").exists()
    finally:
        if artifact_root.exists():
            shutil.rmtree(artifact_root)


def test_launcher_terminates_descendants_before_finalizing_a_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A timed-out child cannot publish a receipt after central validation."""

    child_code = (
        "import os,time; from pathlib import Path; time.sleep(2); "
        "Path(os.environ['CLASSIC_CONFORMANCE_OUTPUT']).write_text"
        "('{}', encoding='utf-8')"
    )
    parent_code = (
        "import subprocess,sys,time; "
        f"subprocess.Popen((sys.executable, '-c', {child_code!r})); "
        "time.sleep(60)"
    )
    command = scan_run_launcher.ParticipantCommand(
        arguments=(sys.executable, "-c", parent_code),
        working_directory=REPO_ROOT,
        source_paths=(Path(__file__).resolve(),),
    )
    monkeypatch.setitem(scan_run_launcher.PARTICIPANT_COMMANDS, "rust", command)

    artifact_root = (
        REPO_ROOT
        / "tools"
        / "binding_compliance"
        / "artifacts"
        / "test-launcher-timeout"
        / tmp_path.name
    )
    try:
        result, artifact_dir = scan_run_launcher.run_participant(
            "rust",
            artifact_root=artifact_root,
            timeout_seconds=1,
        )
        time.sleep(3)

        attempt = json.loads(
            (artifact_dir / "attempt.json").read_text(encoding="utf-8")
        )
        report = json.loads(
            (artifact_dir / "shadow_report.json").read_text(encoding="utf-8")
        )
        assert result == 1
        assert attempt["timedOut"] is True
        assert attempt["launchError"] is None
        assert report["result"] == "fail"
        assert not (artifact_dir / "receipt.json").exists()
    finally:
        if artifact_root.exists():
            shutil.rmtree(artifact_root)
