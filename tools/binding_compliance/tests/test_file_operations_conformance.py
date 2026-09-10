"""File operation packs prove public results and actual durable effects."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest
from conformance.coverage import (
    derive_observed_fact_ids,
    derive_row_coverage,
    load_retained_analyzer_kinds,
    load_source_parity_rows,
)
from conformance.families.file_operations import FILE_OPERATIONS_COVERAGE_POLICY
from conformance.families.operation_scope import is_retained_operation
from conformance.packs import load_and_validate_pack, materialize_run_plan
from conformance.receipts import validate_prepared_run

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("tests/conformance/packs/file_operations/v1.json")


def test_file_operations_have_complete_independent_observations() -> None:
    """Missing carriers and unauthorized writes cannot earn semantic coverage."""
    pack = load_and_validate_pack(ROOT, PACK)
    document = pack.document()
    for scenario in document["scenarios"]:
        fixture = json.loads(
            (
                pack.fixture_root
                / document["fixtures"][scenario["input"]["fixtureRef"]]
            ).read_text()
        )
        assert set(fixture) == (
            {"operation", "path", "files", "content"}
            if fixture["operation"] == "write-text"
            else {"operation", "path", "files"}
        )
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            document, scenario, expected, FILE_OPERATIONS_COVERAGE_POLICY
        )
        for field in expected:
            changed = copy.deepcopy(expected)
            del changed[field]
            assert not derive_observed_fact_ids(
                document, scenario, changed, FILE_OPERATIONS_COVERAGE_POLICY
            )
        changed = copy.deepcopy(expected)
        changed["files"].append({"path": "unexpected.txt", "content": "side effect"})
        changed["files"].sort(key=lambda item: item["path"])
        assert not derive_observed_fact_ids(
            document, scenario, changed, FILE_OPERATIONS_COVERAGE_POLICY
        )
        assert not derive_observed_fact_ids(
            document,
            {**scenario, "action": "unrelated"},
            expected,
            FILE_OPERATIONS_COVERAGE_POLICY,
        )


def test_scoped_migration_retains_only_known_deferred_methods() -> None:
    """New methods and unrelated participant identities cannot inherit old coverage."""
    rows = load_source_parity_rows(ROOT)
    retained = next(
        row
        for row in rows
        if row.participant_id == "python"
        and row.rust_symbol == "FileIOCore"
        and row.runtime_operation == "read_dds_header"
    )
    assert is_retained_operation("file-operations", retained)
    for change in (
        {"runtime_operation": "new_future_method"},
        {"runtime_operation": "read_file"},
        {"runtime_operation": None},
        {"runtime_operation": "__init__"},
        {"participant_id": "node"},
        {"rust_symbol": "Unrelated"},
    ):
        assert not is_retained_operation("file-operations", replace(retained, **change))


@pytest.mark.parametrize("participant", ("cxx", "node", "python"))
def test_file_receipts_fail_closed_and_preserve_migration_scope(
    tmp_path: Path, participant: str
) -> None:
    """Public receipt validation rejects replay, missing work, drift and future APIs."""
    (tmp_path / PACK).parent.mkdir(parents=True)
    shutil.copyfile(ROOT / PACK, tmp_path / PACK)
    fixtures = Path("tests/fixtures/file_operations")
    shutil.copytree(ROOT / fixtures, tmp_path / fixtures)
    from receipt_test_support import copy_source_inventory

    copy_source_inventory(ROOT, tmp_path)
    for arguments in (
        ("init",),
        ("config", "user.email", "conformance@example.invalid"),
        ("config", "user.name", "Conformance Tests"),
        ("add", "."),
        ("commit", "-m", "fixture"),
    ):
        subprocess.run(
            ["git", "-C", str(tmp_path), *arguments], check=True, capture_output=True
        )
    pack = load_and_validate_pack(tmp_path, PACK)
    document = pack.document()
    policy = FILE_OPERATIONS_COVERAGE_POLICY
    run = materialize_run_plan(
        pack,
        participant_id=participant,
        participant_role="semantic-adapter",
        execution_instance_id=participant,
        source_paths=(PACK,),
    )
    plan = run.document()
    assert all("expected" not in scenario for scenario in plan["scenarios"])
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
        "id": "file-operations-boundary-test",
        "version": 1,
        "platform": "windows",
        "toolchain": participant,
    }
    # Authored expectations are synthetic receipt input only at this central test
    # seam; the executable native adapters receive the input-only run plan above.
    receipt["scenarios"] = [
        {
            "id": scenario["id"],
            "executionStatus": "completed",
            "capabilityIds": scenario["capabilityIds"],
            "observation": scenario["expected"],
            "failure": None,
        }
        for scenario in document["scenarios"]
    ]
    run.receipt_path.write_text(json.dumps(receipt))
    report = validate_prepared_run(pack, run, coverage_policy=policy)
    assert not report.failures
    assert all(scenario.result == "pass" for scenario in report.scenarios)
    rows = load_source_parity_rows(ROOT)
    coverage = derive_row_coverage(
        document,
        rows,
        policy,
        (report,),
        scope_participant_id=participant,
        retained_analyzers=load_retained_analyzer_kinds(ROOT),
    )
    assert coverage.rows
    assert not coverage.failures
    assert all(
        row.evidence_kind in {"executable", "structural"} for row in coverage.rows
    )
    if participant == "python":
        covered_ids = {row.obligation_id for row in coverage.rows}
        for stream in ("PyLineStreamer", "PySyncLineStreamer"):
            assert f"parity:python:file_io.log_collection.{stream}" in covered_ids
        assert "parity:python:file_io.log_collection.PyLogCollector" not in covered_ids
        retained = next(
            row
            for row in rows
            if row.participant_id == "python"
            and row.rust_symbol == "FileIOCore"
            and row.runtime_operation == "read_dds_header"
        )
        assert retained.obligation_id not in {
            row.obligation_id for row in coverage.rows
        }
        for operation in (
            "read_bytes",
            "read_lines",
            "read_file_mmap",
            "stream_lines",
            "stream_lines_sync",
            "file_exists",
            "get_file_size",
            "get_file_info",
            "clear_cache",
            "py_read_multiple_files",
            "py_walk_directory",
            "write_bytes",
            "write_lines",
            "append_file",
            "py_write_multiple_files",
        ):
            migrated = next(
                row
                for row in rows
                if row.participant_id == "python"
                and row.rust_symbol == "FileIOCore"
                and row.runtime_operation == operation
            )
            assert migrated.obligation_id in {
                row.obligation_id for row in coverage.rows
            }
    prototype = next(
        row
        for row in rows
        if row.participant_id == participant
        and row.rust_crate == "classic-file-io-core"
        and row.rust_symbol in {"FileIOCore", "read_file"}
    )
    added = replace(
        prototype,
        obligation_id="parity:test:future-file-operation",
        rust_symbol="FileIOCore",
        runtime_operation="future_file_operation",
    )
    expanded = derive_row_coverage(
        document,
        (*rows, added),
        policy,
        (report,),
        scope_participant_id=participant,
        retained_analyzers=load_retained_analyzer_kinds(ROOT),
    )
    assert [failure.obligation_id for failure in expanded.failures] == [
        added.obligation_id
    ]

    for mutation in ("missing", "skipped", "wrong-value", "forbidden-file"):
        changed = copy.deepcopy(receipt)
        if mutation == "missing":
            changed["scenarios"].pop(0)
        elif mutation == "skipped":
            changed["scenarios"][0].update(
                executionStatus="not_applicable",
                observation=None,
                policyExceptionId="invented-skip",
            )
        elif mutation == "wrong-value":
            changed["scenarios"][0]["observation"]["content"] = "wrong text"
        else:
            changed["scenarios"][-1]["observation"]["files"].insert(
                0, {"path": "absent/output.txt", "content": "unauthorized write"}
            )
        run.receipt_path.write_text(json.dumps(changed))
        rejected = validate_prepared_run(pack, run, coverage_policy=policy)
        assert rejected.failures or any(
            item.result != "pass" for item in rejected.scenarios
        ), mutation

    fresh_run = materialize_run_plan(
        pack,
        participant_id=participant,
        participant_role="semantic-adapter",
        execution_instance_id=participant,
        source_paths=(PACK,),
    )
    fresh_run.receipt_path.write_text(json.dumps(receipt))
    assert validate_prepared_run(pack, fresh_run, coverage_policy=policy).failures
