"""Scan Game receipts prove findings, game selection and read-only durable effects."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from conformance.coverage import derive_observed_fact_ids
from conformance.families.scan_game import SCAN_GAME_COVERAGE_POLICY
from conformance.packs import load_and_validate_pack, materialize_run_plan
from conformance.receipts import validate_prepared_run

from receipt_test_support import prepare_receipt_case

ROOT = Path(__file__).resolve().parents[3]
PACK = Path("tests/conformance/packs/scan_game/v1.json")


def test_scan_game_facts_require_complete_native_results_and_no_writes() -> None:
    """Missing results and unexpected filesystem mutations earn no coverage."""
    pack = load_and_validate_pack(ROOT, PACK)
    document = pack.document()
    for scenario in document["scenarios"]:
        fixture = json.loads(
            (
                    pack.fixture_root
                    / document["fixtures"][scenario["input"]["fixtureRef"]]
            ).read_text()
        )
        assert "expected" not in fixture
        if fixture["operation"] in {"validate-ini", "validate-enb"}:
            assert set(fixture) == {"operation", "game", "files", "directories"}
        elif fixture["operation"] == "process-logs":
            assert set(fixture) == {
                "operation",
                "game",
                "files",
                "directories",
                "catch",
                "excludeFiles",
                "excludeErrors",
            }
        else:
            assert set(fixture) == {"operation", "xse", "unpacked", "archived"}
        expected = scenario["expected"]
        assert derive_observed_fact_ids(
            document, scenario, expected, SCAN_GAME_COVERAGE_POLICY
        )
        for field in expected:
            changed = copy.deepcopy(expected)
            del changed[field]
            assert not derive_observed_fact_ids(
                document, scenario, changed, SCAN_GAME_COVERAGE_POLICY
            )
        for field in ("files", "directories"):
            if field not in expected:
                continue
            changed = copy.deepcopy(expected)
            changed[field].append(
                {"path": "unexpected", "content": "write"}
                if field == "files"
                else "unexpected"
            )
            assert not derive_observed_fact_ids(
                document, scenario, changed, SCAN_GAME_COVERAGE_POLICY
            )
        assert not derive_observed_fact_ids(
            document,
            {**scenario, "action": "unrelated"},
            expected,
            SCAN_GAME_COVERAGE_POLICY,
        )


# Rust-only since the #308 bridge trim: CXX is no longer enrolled for this family.
@pytest.mark.parametrize("participant", ("rust",))
def test_scan_game_receipts_reject_stale_partial_or_mutated_evidence(
        tmp_path: Path, participant: str
) -> None:
    """Central validation accepts only complete, current, invocation-owned receipts."""
    pack, run, receipt = prepare_receipt_case(
        ROOT, tmp_path, PACK, participant, runner_id="scan-game-boundary-test"
    )
    plan = run.document()
    assert all("expected" not in scenario for scenario in plan["scenarios"])
    policy = SCAN_GAME_COVERAGE_POLICY
    report = validate_prepared_run(pack, run, coverage_policy=policy)
    assert not report.failures
    assert all(item.result == "pass" for item in report.scenarios)
    for mutation in (
            "missing",
            "skipped",
            "wrong-result",
            "write",
            "directory",
            "stale-expectation",
            "stale-source",
    ):
        changed = copy.deepcopy(receipt)
        if mutation == "missing":
            changed["scenarios"].pop()
        elif mutation == "skipped":
            changed["scenarios"][0].update(
                executionStatus="not_applicable",
                observation=None,
                policyExceptionId="invented-skip",
            )
        elif mutation == "wrong-result":
            enb = next(
                item for item in changed["scenarios"] if item["id"] == "enb-absent"
            )
            enb["observation"]["result"]["config"] = "Valid"
        elif mutation == "write":
            changed["scenarios"][0]["observation"]["files"].append(
                {"path": "unexpected.txt", "content": "write"}
            )
        elif mutation == "directory":
            changed["scenarios"][0]["observation"]["directories"].append("unexpected")
        elif mutation == "stale-expectation":
            changed["expectationDigest"] = "sha256:" + "0" * 64
        else:
            changed["invocation"]["sourceIdentity"] = (
                    "git:" + "0" * 40 + ":sha256:" + "0" * 64
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
