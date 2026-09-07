"""Executable ownership checks at the pack and receipt compliance seam."""

import copy
import json
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from conformance.applicability import derive_applicability
from conformance.coverage import (
    derive_row_coverage,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
)
from conformance.families.shared_registry import coverage_policy, validate_pack
from conformance.packs import load_and_validate_pack, materialize_run_plan
from conformance.receipts import validate_prepared_run

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("family", ["string-operations", "registry-operations"])
def test_inputs_and_observation_predicates_fail_closed(family: str) -> None:
    """Authored inputs are oracle-free and missing actual fields earn no credit."""
    document = json.loads(
        (
            ROOT / "tests/conformance/packs" / family.replace("-", "_") / "v1.json"
        ).read_text(encoding="utf-8")
    )
    paths = validate_pack(document, ROOT)
    assert len(paths) == len(document["scenarios"])
    for path in paths:
        assert set(json.loads(path.read_text(encoding="utf-8"))) == {"request"}
    for predicate in coverage_policy(family).predicates:
        assert any(
            predicate.matches(case["expected"]) for case in document["scenarios"]
        )
        assert not predicate.covers_runtime_operation("unexecuted_future_method")
        for case in document["scenarios"]:
            for field in case["expected"]:
                incomplete = dict(case["expected"])
                del incomplete[field]
                assert not predicate.matches(incomplete)


def _pack(family: str) -> dict:
    """Load independent authored expectations for receipt mutation checks."""
    return json.loads(
        (
            ROOT / "tests/conformance/packs" / family.replace("-", "_") / "v1.json"
        ).read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    "family,participants",
    [
        ("string-operations", {"rust", "node", "python"}),
        ("registry-operations", {"rust", "cxx", "node", "python"}),
    ],
)
def test_shared_registry_receipts_fail_closed_at_public_coverage_seam(
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
    policy = coverage_policy(family)
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
                    if family == "string-operations":
                        observation["normalized"][0] += "-adapter-drift"
                    else:
                        observation["afterRemovePresent"] = True
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
