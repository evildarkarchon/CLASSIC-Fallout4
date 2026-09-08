"""Backup coverage requires actual copy effects and version ownership."""

from pathlib import Path

from conformance.command import FAMILY_COVERAGE_POLICIES
from conformance.families.path_backups import matches_versioned
from conformance.packs import load_and_validate_pack
from conformance.receipts import validate_prepared_run
from receipt_test_support import prepare_receipt_case

ROOT = Path(__file__).resolve().parents[3]


def test_backup_facts_reject_missing_or_uncopied_bytes():
    """A directory name or constructor alone cannot prove file backup behavior."""
    assert not matches_versioned({})
    assert not matches_versioned(
        {
            "version": "1.10.163.0",
            "initial": [],
            "firstHex": "00",
            "replacementHex": "01",
        }
    )


def test_backup_receipt_requires_each_lifecycle_field(tmp_path):
    """The exact fixture receipt passes, while missing effects lose all evidence."""
    path = Path("tests/conformance/packs/path_backups/v1.json")
    pack = load_and_validate_pack(ROOT, path)
    policy = FAMILY_COVERAGE_POLICIES["path-backups"]
    for case in pack.document()["scenarios"]:
        predicate = next(p for p in policy.predicates if p.action == case["action"])
        assert predicate.matches(case["expected"])
        for field in case["expected"]:
            changed = dict(case["expected"])
            changed.pop(field)
            assert not predicate.matches(changed)
    pack, run, _ = prepare_receipt_case(
        ROOT, tmp_path, path, "rust", runner_id="backup-policy-test"
    )
    assert not validate_prepared_run(pack, run, coverage_policy=policy).failures
