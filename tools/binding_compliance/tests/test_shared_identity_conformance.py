"""Fail-closed public pack validation for stable game tokens and runtime access."""

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
from conformance.families.shared_identity import coverage_policy, validate_pack
from conformance.packs import load_and_validate_pack, materialize_run_plan
from conformance.receipts import validate_prepared_run
from receipt_test_support import copy_source_inventory

ROOT = Path(__file__).resolve().parents[3]


def test_game_metadata_and_python_value_methods_are_source_scoped():
    """Pretty labels use the shared getter while unavailable CXX/Node value methods stay out."""
    document = _pack("game-identity")
    matrix = derive_applicability(document, load_source_parity_rows(ROOT))
    metadata = next(
        (case for case in document["scenarios"] if case["id"] == "metadata"), None
    )
    assert metadata is not None
    assert {p.id for p in matrix.participants if "metadata" in p.scenario_ids} == {
        "rust",
        "python",
        "node",
        "cxx",
    }
    assert {p.id for p in matrix.participants if "details" in p.scenario_ids} == {
        "rust",
        "python",
    }
    from retirement_readiness import candidate_predicates

    selected = {
        "__eq__",
        "__hash__",
        "__repr__",
        "__str__",
        "exe_name",
        "is_vr",
        "getGameName",
    }
    for row in load_source_parity_rows(ROOT):
        if (
            row.rust_crate == "classic-shared-core"
            and row.rust_symbol == "GameId"
            and row.runtime_operation in selected
        ):
            assert candidate_predicates(
                row, document, coverage_policy("game-identity")
            ), row.obligation_id


def test_runtime_access_includes_python_and_explicit_shutdown_intent() -> None:
    """Health diagnostics and no-op shutdown must be backed by actual calls."""
    pack = _pack("runtime-access")
    matrix = derive_applicability(pack, load_source_parity_rows(ROOT))
    assert {participant.id for participant in matrix.participants} == {
        "rust",
        "cxx",
        "node",
        "python",
    }
    assert any(
        "parity:cxx:b0a1036b892934c2" in predicate.binding_obligation_ids
        for predicate in coverage_policy("runtime-access").predicates
    )


@pytest.mark.parametrize("family", ["game-identity", "runtime-access"])
def test_identity_observations_reject_missing_fields(family: str) -> None:
    """Missing tokens or access outcomes cannot credit a public operation."""
    document = json.loads(
        (
            ROOT / "tests/conformance/packs" / family.replace("-", "_") / "v1.json"
        ).read_text(encoding="utf-8")
    )
    assert validate_pack(document, ROOT)
    for predicate in coverage_policy(family).predicates:
        assert any(
            predicate.matches(case["expected"]) for case in document["scenarios"]
        )
        assert not predicate.matches({})
        assert not predicate.covers_runtime_operation("future_public_method")


def _pack(family: str) -> dict:
    """Read authored expectations for receipt mutation checks."""
    return json.loads(
        (
            ROOT / "tests/conformance/packs" / family.replace("-", "_") / "v1.json"
        ).read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    "family,participants",
    [
        ("game-identity", {"rust", "cxx", "node", "python"}),
        ("runtime-access", {"rust", "cxx", "node", "python"}),
    ],
)
def test_shared_identity_receipts_fail_closed_at_public_coverage_seam(
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
    if any(
        capability.get("operationScoped", False)
        for capability in original["capabilities"]
    ):
        copy_source_inventory(ROOT, tmp_path)
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
    if family == "runtime-access":
        assert all(
            set(participant.scenario_ids)
            == {case["id"] for case in document["scenarios"]}
            for participant in matrix.participants
        )
    else:
        assert all(
            {"stable", "metadata"} <= set(participant.scenario_ids)
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
                if case["id"] in {item["id"] for item in plan["scenarios"]}
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
                    if family == "game-identity":
                        observation["tokens"][0] += "-adapter-drift"
                    else:
                        observation["available"][0] = False
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
