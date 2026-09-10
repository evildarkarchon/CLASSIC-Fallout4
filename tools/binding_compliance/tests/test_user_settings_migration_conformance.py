"""Migration scenarios must prove public planning and durable restoration facts."""

import copy
import json

import pytest
from conformance.packs import (
    MaterializationError,
    PackValidationError,
    load_and_validate_pack,
    load_prepared_run,
)
from conformance.receipts import validate_prepared_run
from test_user_settings_conformance import (
    PACK_PATH,
    REPO_ROOT,
    _prepared_copy,
    _receipt,
)


def test_migration_pack_covers_planning_approval_conflicts_and_restoration() -> None:
    """The shared independent corpus supplies the full migration scenario matrix."""
    pack = load_and_validate_pack(REPO_ROOT, PACK_PATH)
    scenarios = {
        item["id"]: item["expected"]
        for item in pack.document()["scenarios"]
        if item["action"] == "user-settings.migrate"
    }
    assert scenarios["migration-current"]["planning"]["status"] == "not-required"
    assert scenarios["migration-unsupported"]["planning"]["status"] == "unsupported"
    assert scenarios["migration-review-only"]["apply"]["status"] == "not-attempted"
    assert scenarios["migration-flat-restore"]["restore"]["status"] == "restored"
    assert scenarios["migration-previous-restore"]["restore"]["status"] == "restored"
    assert scenarios["migration-alias-conflict"]["apply"]["status"] == "applied"
    assert scenarios["migration-stale-apply"]["apply"]["status"] == "conflict"
    assert scenarios["migration-stale-restore"]["restore"]["status"] == "conflict"
    assert scenarios["migration-tampered-backup"]["restore"]["errorCode"] == (
        "migration_restore_backup_verify_failed"
    )
    assert scenarios["migration-blocked-backup"]["apply"]["errorCode"] == (
        "migration_backup_directory_failed"
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "repeat",
        "inverse",
        "round-trip",
        "base-revision",
        "plan-row",
        "proposal",
        "publication",
        "backup",
        "restored",
        "receipt",
        "error-code",
        "conflict-revision",
        "extra-file",
        "missing-scenario",
        "self-attestation",
        "nonempty-lock",
    ],
)
def test_migration_receipts_fail_closed_on_changed_evidence(tmp_path, mutation) -> None:
    """Passing envelopes cannot mask forged plans, byte evidence, or recovery outcomes."""
    pack, run = _prepared_copy(tmp_path)
    receipt = _receipt(pack, run)
    # First prove this independent fixture reaches the comparator successfully.
    run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert not validate_prepared_run(pack, run).failures
    observations = {item["id"]: item["observation"] for item in receipt["scenarios"]}
    observed = observations["migration-flat-restore"]
    if mutation == "repeat":
        observed["repeatedPlanning"]["plan"]["required"] = False
    elif mutation == "inverse":
        observed["reversedPlan"]["changes"].reverse()
    elif mutation == "round-trip":
        observed["roundTripPlan"]["proposedHex"] = "00"
    elif mutation == "base-revision":
        observed["planning"]["plan"]["baseRevision"] = "missing"
    elif mutation == "plan-row":
        # Change all copies coherently: exact oracle rows must still reject it.
        for key in ("planning", "repeatedPlanning"):
            observed[key]["plan"]["changes"][1]["kind"] = "alias_canonicalization"
        observed["roundTripPlan"]["changes"][1]["kind"] = "alias_canonicalization"
        observed["reversedPlan"]["changes"][-2]["kind"] = "alias_canonicalization"
    elif mutation == "proposal":
        observed["planning"]["plan"]["proposedHex"] = "00"
    elif mutation in {"publication", "backup", "restored"}:
        checkpoint = "finalTree" if mutation == "restored" else "afterApplyTree"
        path = (
            observed["apply"]["receipt"]["backupPath"]
            if mutation == "backup"
            else {"path": "CLASSIC Settings.yaml"}
        )
        next(entry for entry in observed[checkpoint] if entry["path"] == path)[
            "bytesHex"
        ] += "0a"
    elif mutation == "receipt":
        observed["apply"]["receipt"]["publishedRevision"] = "sha256:" + "0" * 64
    elif mutation == "error-code":
        observations["migration-tampered-backup"]["restore"]["errorCode"] = (
            "adapter_error"
        )
    elif mutation == "conflict-revision":
        observations["migration-stale-restore"]["restore"]["actualRevision"] = "missing"
    elif mutation == "extra-file":
        observed["finalTree"].append(
            {"path": {"path": "unexpected"}, "kind": "file", "bytesHex": ""}
        )
    elif mutation == "missing-scenario":
        receipt["scenarios"] = [
            item
            for item in receipt["scenarios"]
            if item["id"] != "migration-flat-restore"
        ]
    elif mutation == "self-attestation":
        observed["reversedPlan"] = {"verifiedInverse": True}
    else:
        observations["migration-stale-apply"]["afterApplyTree"].append(
            {
                "path": {"path": "CLASSIC Settings.yaml.commit.lock"},
                "kind": "file",
                "bytesHex": "00",
            }
        )
    run.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert validate_prepared_run(pack, run).failures


def test_migration_plans_are_input_only_and_expected_bytes_are_digest_bound(
    tmp_path,
) -> None:
    """Expected documents never reach adapters, and changing one invalidates prepared work."""
    pack, run = _prepared_copy(tmp_path)
    text = run.run_plan_path.read_text(encoding="utf-8")
    assert "migrationScenario" not in text
    assert "expected_document" not in text
    assert "flat_migrated.yaml" not in json.dumps(run.document()["fixtures"])
    before = pack.expectation_digest
    path = pack.fixture_root / "flat_migrated.yaml"
    path.write_bytes(path.read_bytes() + b"\n# changed oracle\n")
    assert load_and_validate_pack(tmp_path, PACK_PATH).expectation_digest != before
    with pytest.raises(MaterializationError):
        load_prepared_run(
            load_and_validate_pack(tmp_path, PACK_PATH), run.run_plan_path
        )


def test_migration_pack_rejects_missing_operations_and_changed_approval(
    tmp_path,
) -> None:
    """Applicability and caller approval cannot be weakened by editing a run scenario."""
    _prepared_copy(tmp_path)
    path = tmp_path / PACK_PATH
    original = json.loads(path.read_text(encoding="utf-8"))
    for mutation in ("missing", "approval", "normalization"):
        pack = copy.deepcopy(original)
        scenario = next(
            item for item in pack["scenarios"] if item["id"] == "migration-review-only"
        )
        if mutation == "missing":
            pack["scenarios"].remove(scenario)
        elif mutation == "approval":
            scenario["input"]["apply"] = True
        else:
            conflict = next(
                item
                for item in pack["scenarios"]
                if item["id"] == "migration-stale-apply"
            )
            del conflict["normalization"]["optionalEmptyFiles"]
        path.write_text(json.dumps(pack), encoding="utf-8")
        with pytest.raises(PackValidationError, match="migration"):
            load_and_validate_pack(tmp_path, PACK_PATH)
