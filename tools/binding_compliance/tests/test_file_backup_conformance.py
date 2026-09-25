"""Managed file backups must prove replacement restoration and scoped removal."""

from pathlib import Path

from conformance.command import FAMILY_COVERAGE_POLICIES
from conformance.families.file_backups import matches_backup
from conformance.packs import load_and_validate_pack


def test_managed_backup_requires_durable_bytes():
    """Lifecycle labels alone do not prove a backup operation occurred."""
    assert not matches_backup({})
    assert not matches_backup({"initial": False, "exists": True, "restored": 1})


def test_file_backup_facts_require_each_copy_and_removal_field():
    """Validate complete expected facts and reject each deleted field independently."""
    root = Path(__file__).resolve().parents[3]
    pack = load_and_validate_pack(
        root, Path("tests/conformance/packs/file_backups/v1.json")
    )
    policy = FAMILY_COVERAGE_POLICIES["file-backups"]
    for case in pack.document()["scenarios"]:
        predicate = next(p for p in policy.predicates if p.action == case["action"])
        assert predicate.matches(case["expected"])
        for field in case["expected"]:
            changed = dict(case["expected"])
            changed.pop(field)
            assert not predicate.matches(changed)
