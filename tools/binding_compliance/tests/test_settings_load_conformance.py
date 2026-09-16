"""Settings loader pack validation at the executable compliance seam."""

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
from conformance.families.settings_load import (
    settings_load_coverage_policy,
    settings_yaml_batch_coverage_policy,
    settings_yaml_coverage_policy,
    validate_settings_load_pack,
)
from conformance.packs import load_and_validate_pack, materialize_run_plan
from conformance.receipts import validate_prepared_run

from receipt_test_support import copy_source_inventory

ROOT = Path(__file__).resolve().parents[3]


def test_settings_load_inputs_and_observations_fail_closed() -> None:
    """The four actual loader outcomes and cache effects are all required."""
    pack = json.loads(
        (ROOT / "tests/conformance/packs/settings_load/v1.json").read_text()
    )
    assert len(validate_settings_load_pack(pack, ROOT)) == 4
    for predicate in settings_load_coverage_policy().predicates:
        assert any(predicate.matches(case["expected"]) for case in pack["scenarios"])
        assert not predicate.matches({})
        assert not predicate.covers_runtime_operation("unexecuted_future_method")


def _pack(family: str) -> dict:
    """Read authored settings observations for receipt mutation checks."""
    return json.loads(
        (
                ROOT / "tests/conformance/packs" / family.replace("-", "_") / "v1.json"
        ).read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    "family,participants",
    [
        ("settings-load", {"rust", "cxx", "node", "python"}),
        ("settings-yaml", {"rust", "cxx", "node", "python"}),
        ("settings-yaml-batch", {"rust", "node"}),
    ],
)
def test_settings_load_receipts_fail_closed_at_public_coverage_seam(
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
    policy = {
        "settings-load": settings_load_coverage_policy,
        "settings-yaml": settings_yaml_coverage_policy,
        "settings-yaml-batch": settings_yaml_batch_coverage_policy,
    }[family]()
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
            # A family scope excludes unimplemented siblings; the full owner
            # denominator must still reject every newly exported operation.
            full_owner = copy.deepcopy(document)
            for capability in full_owner["capabilities"]:
                capability.pop("operationScoped", None)
            assert derive_row_coverage(
                full_owner,
                (future,),
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
                    if family == "settings-load":
                        observation["sync"]["count"] = 999
                    elif family == "settings-yaml":
                        observation["persisted"]["name"] = "corrupted"
                    else:
                        observation["ordered"].reverse()
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


def test_settings_cache_lifecycle_is_required_for_credit() -> None:
    """Removing invalidation or cache statistics invalidates executable evidence."""
    pack = _pack("settings-load")
    predicate = settings_load_coverage_policy().predicates[0]
    observed = pack["scenarios"][0]["expected"]
    assert "cacheState" in observed["sync"]
    for field in (
            "keys",
            "size",
            "invalidated",
            "invalidatedAgain",
            "afterInvalidate",
            "stats",
            "resetStats",
    ):
        changed = copy.deepcopy(observed)
        del changed["sync"]["cacheState"][field]
        assert not predicate.matches(changed)


def test_settings_yaml_persistence_and_cache_facts_are_required() -> None:
    """The YAML receipt must retain mutation, persisted bytes and cache reuse."""
    from conformance.families.settings_load import (
        settings_yaml_coverage_policy,
        validate_settings_yaml_pack,
    )

    pack = _pack("settings-yaml")
    assert validate_settings_yaml_pack(pack, ROOT)
    for predicate in settings_yaml_coverage_policy().predicates:
        observation = pack["scenarios"][0]["expected"]
        assert predicate.matches(observation)
        for key in ("before", "after", "persisted", "files", "cache"):
            changed = copy.deepcopy(observation)
            del changed[key]
            assert not predicate.matches(changed)


def test_settings_yaml_batch_requires_order_and_typed_results() -> None:
    """An adapter cannot replace ordered entries or omit a batch result."""
    from conformance.families.settings_load import (
        settings_yaml_batch_coverage_policy,
        validate_settings_yaml_batch_pack,
    )

    pack = _pack("settings-yaml-batch")
    assert validate_settings_yaml_batch_pack(pack, ROOT)
    predicate = settings_yaml_batch_coverage_policy().predicates[0]
    observed = pack["scenarios"][0]["expected"]
    assert predicate.matches(observed)
    for key in ("before", "ordered", "vectors", "after"):
        changed = copy.deepcopy(observed)
        del changed[key]
        assert not predicate.matches(changed)
