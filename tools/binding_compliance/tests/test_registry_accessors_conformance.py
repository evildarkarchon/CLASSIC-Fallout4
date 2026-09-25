"""Registry owner behavior at the authenticated compliance boundary."""

import copy
import json
from pathlib import Path

import pytest
from conformance.applicability import derive_applicability
from conformance.command import FAMILY_COVERAGE_POLICIES
from conformance.coverage import load_source_parity_rows
from conformance.packs import load_and_validate_pack
from conformance.receipts import validate_prepared_run

from receipt_test_support import prepare_receipt_case

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    "family,participants",
    [
        ("registry-game", {"rust", "node", "cxx", "python"}),
        ("registry-gui", {"rust", "cxx", "python"}),
        ("registry-context", {"rust", "python"}),
        ("registry-paths", {"rust", "node", "python"}),
    ],
)
def test_registry_accessor_receipts_require_owned_state(tmp_path, family, participants):
    """Missing observations, changed effects and stale receipts cannot earn credit."""
    path = Path("tests/conformance/packs") / family.replace("-", "_") / "v1.json"
    pack = load_and_validate_pack(ROOT, path)
    assert {
               p.id
               for p in derive_applicability(
            pack.document(), load_source_parity_rows(ROOT)
        ).participants
           } == participants
    policy = FAMILY_COVERAGE_POLICIES[family]
    for predicate in policy.predicates:
        assert not predicate.covers_runtime_operation("future_owner_alias")
        assert any(
            predicate.matches(s["expected"]) for s in pack.document()["scenarios"]
        )
    pack, run, receipt = prepare_receipt_case(
        ROOT, tmp_path, path, "rust", runner_id="registry-owner-test"
    )
    assert not validate_prepared_run(pack, run, coverage_policy=policy).failures
    for mutation in ("missing", "changed", "stale", "extra"):
        changed = copy.deepcopy(receipt)
        observation = changed["scenarios"][0]["observation"]
        if mutation == "missing":
            observation.pop(next(iter(observation)))
        elif mutation == "changed":
            observation[next(iter(observation))] = "adapter-drift"
        elif mutation == "extra":
            observation["unexpectedWrite"] = True
        else:
            changed["invocation"]["id"] = "stale"
        run.receipt_path.write_text(json.dumps(changed))
        assert validate_prepared_run(pack, run, coverage_policy=policy).failures
