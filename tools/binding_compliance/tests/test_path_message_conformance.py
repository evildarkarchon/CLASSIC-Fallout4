"""Regression checks for input isolation, exact domain observations and narrow credit."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from conformance.applicability import derive_applicability
from conformance.command import FAMILY_COVERAGE_POLICIES
from conformance.coverage import (
    derive_row_coverage,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
)
from conformance.families.message_operations import (
    message_operations_coverage_policy,
    validate_message_operations_pack,
)
from conformance.families.path_operations import (
    path_normalization_coverage_policy,
    path_operations_coverage_policy,
    validate_path_operations_pack,
)
from conformance.packs import load_and_validate_pack, materialize_run_plan
from conformance.receipts import validate_prepared_run

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("root_prefix", ["", "\\\\?\\"])
@pytest.mark.parametrize(
    "value",
    [
        "C:/Temp/scenario/game/Fallout4.exe",
        r"C:\Temp\scenario\game\Fallout4.exe",
        r"\\?\C:\Temp\scenario\game\Fallout4.exe",
        "//?/C:/Temp/scenario/game/Fallout4.exe",
    ],
)
def test_python_portable_path_strips_windows_root_before_receipt_comparison(
    root_prefix: str,
    value: str,
) -> None:
    """Canonicalized paths and temporary roots may use different Windows spellings."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "path_message_conformance",
        ROOT / "python-bindings/tests/path_message_conformance.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = Path(root_prefix + r"C:\Temp\scenario")
    assert module._portable(value, root) == "game/Fallout4.exe"
    assert module._portable("Path does not exist: C:/Temp/scenario/missing", root) == (
        "Path does not exist: missing"
    )
    assert module._portable(r"Missing \\?\C:\Temp\scenario\game", root) == "Missing game"
    assert module._portable("C:/Temp/scenario-other/game", root) == "C:/Temp/scenario-other/game"


def test_same_named_validator_in_a_new_bridge_namespace_cannot_borrow_proof(tmp_path):
    """Public namespace identity matters even when core owner and function name match."""
    from receipt_test_support import prepare_receipt_case

    pack, run, _ = prepare_receipt_case(
        ROOT,
        tmp_path,
        Path("tests/conformance/packs/path_operations/v1.json"),
        "cxx",
        runner_id="namespace-scope-regression",
    )
    policy = path_operations_coverage_policy()
    report = validate_prepared_run(pack, run, coverage_policy=policy)
    assert not report.failures
    rows = load_source_parity_rows(ROOT)
    original = next(
        row for row in rows if row.obligation_id == "parity:cxx:5318454026bb9a08"
    )
    future = replace(
        original,
        obligation_id="parity:cxx:new-namespace-validate-path",
        locator="/entries/new-namespace",
    )
    coverage = derive_row_coverage(
        pack.document(),
        (*rows, future),
        policy,
        (report,),
        scope_participant_id="cxx",
        retained_analyzers=load_retained_analyzer_kinds(ROOT),
    )
    assert [failure.obligation_id for failure in coverage.failures] == [
        future.obligation_id
    ]


def test_message_mutation_and_routing_methods_have_executable_ownership() -> None:
    """Mutation, title builders, enum values and routing decisions have real calls."""
    policy = message_operations_coverage_policy()
    for operation in (
        "__init__",
        "set_content",
        "set_title",
        "set_target",
        "set_msg_type",
        "set_details",
        "with_title",
        "__int__",
        "name",
        "should_display",
        "should_display_in_cli",
        "should_display_in_gui",
    ):
        assert any(
            predicate.covers_runtime_operation(operation)
            for predicate in policy.predicates
        )


def test_python_path_wrapper_methods_have_their_core_owner_and_predicates() -> None:
    """Every foundation path wrapper operation retains its own executed boundary."""
    rows = [
        row
        for row in load_source_parity_rows(ROOT)
        if row.obligation_id.startswith("parity:python:shared.path.PathHandler")
    ]
    assert rows
    assert all(
        row.rust_crate == "classic-shared-core" and row.rust_symbol == "PathHandler"
        for row in rows
    )
    policy = path_normalization_coverage_policy()
    assert all(
        any(
            predicate.covers_runtime_operation(row.runtime_operation)
            for predicate in policy.predicates
        )
        for row in rows
    )


def _pack(family: str) -> dict:
    """Load independent authored expectations from the repository pack."""
    return json.loads(
        (
            ROOT / "tests/conformance/packs" / family.replace("-", "_") / "v1.json"
        ).read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    "family", ["path-operations", "path-normalization", "message-operations"]
)
def test_authored_packs_have_valid_input_only_fixtures(family: str) -> None:
    """Inputs contain no expected-result oracle and satisfy their domain validator."""
    document = _pack(family)
    validate = (
        validate_message_operations_pack
        if family == "message-operations"
        else validate_path_operations_pack
    )
    paths = validate(document, ROOT)
    assert len(paths) == len(document["scenarios"])
    for path in paths:
        assert '"expected"' not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "family,policy",
    [
        ("path-operations", path_operations_coverage_policy),
        ("path-normalization", path_normalization_coverage_policy),
        ("message-operations", message_operations_coverage_policy),
    ],
)
def test_predicates_reject_missing_domain_fields(family: str, policy) -> None:
    """Incomplete adapter observations cannot earn runtime evidence."""
    observations = [case["expected"] for case in _pack(family)["scenarios"]]
    for predicate in policy().predicates:
        assert any(predicate.matches(value) for value in observations)
        assert not predicate.matches({})
        for observation in observations:
            for field in observation:
                incomplete = {
                    key: value for key, value in observation.items() if key != field
                }
                assert not predicate.matches(incomplete)


def test_unexecuted_methods_cannot_borrow_message_or_path_credit() -> None:
    """A class symbol never silently credits unrelated methods."""
    for policy in (
        message_operations_coverage_policy(),
        path_normalization_coverage_policy(),
    ):
        for operation in (
            "future_set_content",
            "future_set_title",
            "future_set_target",
            "future_clear_cache",
            "future_cache_metrics",
            "future_split_path",
        ):
            assert not any(
                predicate.covers_runtime_operation(operation)
                for predicate in policy.predicates
            )


def test_missing_path_and_required_file_failures_are_distinct() -> None:
    """A required-file failure must not substitute for an existence miss."""
    cases = {
        case["id"]: case["expected"] for case in _pack("path-operations")["scenarios"]
    }
    predicates = {
        predicate.id: predicate
        for predicate in path_operations_coverage_policy().predicates
    }
    missing = predicates["validate-required-files-missing"]
    assert missing.matches(cases["missing-directory"])
    assert not missing.matches(cases["required-file-missing"])
    corrupted = copy.deepcopy(cases["missing-directory"])
    corrupted["exists"] = True
    assert not missing.matches(corrupted)


@pytest.mark.parametrize(
    "escape",
    ["../escape", "C:/outside", "/absolute", "game/../../escape", "game\\outside"],
)
def test_path_fixture_escape_fails_before_execution(
    tmp_path: Path, escape: str
) -> None:
    """Fixture materialization rejects portable and Windows-specific escapes."""
    document = _pack("path-operations")
    document["fixtureRoot"] = "fixtures"
    document["scenarios"] = document["scenarios"][:1]
    reference = document["scenarios"][0]["input"]["fixtureRef"]
    fixture = {
        "directories": [escape],
        "files": {},
        "request": {"path": "game", "requiredFiles": []},
    }
    path = tmp_path / "fixtures" / document["fixtures"][reference]
    path.parent.mkdir()
    path.write_text(json.dumps(fixture), encoding="utf-8")
    with pytest.raises(ValueError, match="contained relative"):
        validate_path_operations_pack(document, tmp_path)


@pytest.mark.parametrize(
    "family,participants",
    [
        ("path-operations", {"rust", "cxx", "node", "python"}),
        ("path-normalization", {"rust", "node", "python"}),
        ("message-operations", {"rust", "node", "python"}),
    ],
)
def test_path_message_receipts_fail_closed_at_public_coverage_seam(
    tmp_path: Path, family: str, participants: set[str]
) -> None:
    """Only complete current receipts cover source-selected public operations.

    Authored observations stand in for a transport at this tooling boundary;
    separate native participant runs prove the real API calls. Every mutation
    reaches the same materialization, receipt validation and row derivation
    interfaces used by CI.
    """
    pack_path = Path("tests/conformance/packs") / family.replace("-", "_") / "v1.json"
    original = _pack(family)
    for relative in (pack_path.parent, Path(original["fixtureRoot"])):
        shutil.copytree(ROOT / relative, tmp_path / relative)
    for args in (
        ("init",),
        ("config", "user.email", "conformance@example.invalid"),
        ("config", "user.name", "Conformance Tests"),
        ("add", "."),
        ("commit", "-m", "fixture"),
    ):
        subprocess.run(
            ["git", "-C", str(tmp_path), *args], check=True, capture_output=True
        )
    pack = load_and_validate_pack(tmp_path, pack_path)
    document = pack.document()
    policy = FAMILY_COVERAGE_POLICIES[family]
    rows = load_source_parity_rows(ROOT)
    retained = load_retained_analyzer_kinds(ROOT)
    matrix = derive_applicability(document, rows)
    assert {participant.id for participant in matrix.participants} == participants
    assert all(
        set(participant.scenario_ids) == {case["id"] for case in document["scenarios"]}
        for participant in matrix.participants
    )
    for participant in matrix.participants:
        if participant.id == "rust":
            # Canonical Rust observations are validated in native runs; parity
            # row accounting below belongs to the source-selected adapters.
            continue
        for execution in participant.execution_instance_ids:
            run = materialize_run_plan(
                pack,
                participant_id=participant.id,
                participant_role=participant.role,
                execution_instance_id=execution,
                source_paths=(pack_path,),
            )
            plan = run.document()
            assert all(
                set(case["input"]) == {"fixtureRef"} and "expected" not in case
                for case in plan["scenarios"]
            )
            receipt = {
                key: plan[key]
                for key in (
                    "schemaVersion",
                    "familyId",
                    "familyVersion",
                    "expectationDigest",
                    "invocation",
                    "participant",
                )
            }
            receipt["runner"] = {
                "id": "test-path-message-boundary",
                "version": 1,
                "platform": "windows",
                "toolchain": execution,
            }
            receipt["scenarios"] = [
                {
                    "id": case["id"],
                    "capabilityIds": case["capabilityIds"],
                    "executionStatus": "completed",
                    "observation": copy.deepcopy(case["expected"]),
                    "failure": None,
                }
                for case in document["scenarios"]
            ]
            run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            report = validate_prepared_run(pack, run, coverage_policy=policy)
            assert not report.failures
            covered = derive_row_coverage(
                document,
                rows,
                policy,
                (report,),
                scope_participant_id=participant.id,
                retained_analyzers=retained,
            )
            assert covered.rows and not covered.failures
            prototype = next(
                row
                for row in rows
                if row.participant_id == participant.id
                and row.rust_crate == document["domainOwner"]["rustCrate"]
                and row.rust_symbol in document["capabilities"][0]["rustSymbols"]
            )
            future = replace(
                prototype,
                obligation_id="future-path-message-operation",
                runtime_operation="future_public_method",
                required_evidence_kind="runtime",
            )
            assert derive_row_coverage(
                document,
                (*rows, future),
                policy,
                (report,),
                scope_participant_id=participant.id,
                retained_analyzers=retained,
            ).failures
            for mutation in (
                "changed",
                "missing-scenario",
                "skipped",
                "stale",
                "missing-receipt",
            ):
                changed = copy.deepcopy(receipt)
                if mutation == "changed":
                    observation = changed["scenarios"][0]["observation"]
                    field = {
                        "path-operations": "path",
                        "path-normalization": "normalizedPath",
                        "message-operations": "content",
                    }[family]
                    observation[field] += "-adapter-drift"
                elif mutation == "missing-scenario":
                    changed["scenarios"].pop()
                elif mutation == "skipped":
                    for case in changed["scenarios"]:
                        case["executionStatus"] = "skipped"
                elif mutation == "stale":
                    changed["invocation"]["id"] = "stale-invocation"
                if mutation == "missing-receipt":
                    run.receipt_path.unlink()
                else:
                    run.receipt_path.write_text(json.dumps(changed), encoding="utf-8")
                rejected = validate_prepared_run(pack, run, coverage_policy=policy)
                assert rejected.failures, mutation
                assert derive_row_coverage(
                    document,
                    rows,
                    policy,
                    (rejected,),
                    scope_participant_id=participant.id,
                    retained_analyzers=retained,
                ).failures, mutation


def test_node_message_aliases_keep_their_actual_public_operation_names():
    """Camel-case Node callables must not lose facts after correcting their source owners."""
    from pathlib import Path

    from conformance.coverage import load_source_parity_rows
    from conformance.families.message_operations import (
        message_operations_coverage_policy,
    )
    from conformance.packs import load_and_validate_pack
    from retirement_readiness import candidate_predicates

    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/message_operations/v1.json")
    ).document()
    policy = message_operations_coverage_policy()
    for row in load_source_parity_rows(root):
        if row.obligation_id in {
            "parity:node:aux-phase4a-create-message",
            "parity:node:aux-phase4a-format-message",
        }:
            assert candidate_predicates(row, pack, policy), row.obligation_id
