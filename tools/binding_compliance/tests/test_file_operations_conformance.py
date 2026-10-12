"""File operation packs prove public results and actual durable effects."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from conformance.coverage import derive_observed_fact_ids
from conformance.families.file_operations import FILE_OPERATIONS_COVERAGE_POLICY
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


@pytest.mark.parametrize("participant", ("cxx",))
def test_file_receipts_fail_closed(
        tmp_path: Path, participant: str
) -> None:
    """Public receipt validation rejects replay, missing work and drift."""
    (tmp_path / PACK).parent.mkdir(parents=True)
    shutil.copyfile(ROOT / PACK, tmp_path / PACK)
    fixtures = Path("tests/fixtures/file_operations")
    shutil.copytree(ROOT / fixtures, tmp_path / fixtures)
    from receipt_test_support import copy_participant_catalog

    copy_participant_catalog(ROOT, tmp_path)
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
    # CXX runs only the write scenarios since `file-operations.read-text` left it (#309).
    planned = {scenario["id"] for scenario in plan["scenarios"]}
    receipt["scenarios"] = [
        {
            "id": scenario["id"],
            "executionStatus": "completed",
            "capabilityIds": scenario["capabilityIds"],
            "observation": scenario["expected"],
            "failure": None,
        }
        for scenario in document["scenarios"]
        if scenario["id"] in planned
    ]
    run.receipt_path.write_text(json.dumps(receipt))
    report = validate_prepared_run(pack, run, coverage_policy=policy)
    assert not report.failures
    assert all(scenario.result == "pass" for scenario in report.scenarios)
    assert all(scenario.observed_fact_ids for scenario in report.scenarios)

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
