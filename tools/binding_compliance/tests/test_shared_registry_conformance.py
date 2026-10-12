"""Executable ownership checks at the pack and receipt compliance seam."""

import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from conformance.applicability import derive_applicability
from conformance.families.shared_registry import coverage_policy, validate_pack
from conformance.packs import load_and_validate_pack, materialize_run_plan
from conformance.participants import load_participants
from conformance.receipts import validate_prepared_run
from receipt_test_support import copy_participant_catalog

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
        ("string-operations", {"rust"}),
        ("registry-operations", {"rust", "cxx"}),
    ],
)
def test_shared_registry_receipts_fail_closed_at_public_receipt_seam(
        tmp_path: Path, family: str, participants: set[str]
) -> None:
    """Only complete current receipts from enrolled adapters validate and derive facts.

    Authored observations stand in for a transport at this tooling boundary;
    separate native participant runs prove the real API calls. Every mutation
    reaches the same materialization and receipt validation interfaces used
    by CI.
    """
    pack_path = Path("tests/conformance/packs") / family.replace("-", "_") / "v1.json"
    original = _pack(family)
    for relative in (pack_path.parent, Path(original["fixtureRoot"])):
        shutil.copytree(ROOT / relative, tmp_path / relative)
    copy_participant_catalog(ROOT, tmp_path)
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
    matrix = derive_applicability(document, load_participants(ROOT))
    assert {participant.id for participant in matrix.participants} == participants
    assert all(
        set(participant.scenario_ids) == {case["id"] for case in document["scenarios"]}
        for participant in matrix.participants
    )
    for participant in matrix.participants:
        if participant.id == "rust":
            # Canonical Rust observations are validated in native runs; the
            # receipt boundary below belongs to the catalog-enrolled adapters.
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
            assert all(scenario.observed_fact_ids for scenario in report.scenarios)
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
