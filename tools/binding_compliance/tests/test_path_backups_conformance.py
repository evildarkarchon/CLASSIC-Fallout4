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


# The version-labelled backup moved from classic-path-core to
# classic-resource-core (#251) and its Rust owner type became
# VersionBackupManager so it cannot be confused with resource core's
# game-target BackupManager. Binding exports keep their names, so each row keeps
# its ID and public operation; only the Rust owner and symbol change.
_MOVED_VERSION_BACKUP_ROWS = {
    "parity:cxx:12499068ea3118fb": ("create_backup", "backup_create_timestamped"),
    "parity:cxx:31c8949e2bfdacaf": ("list_versions", "backup_list_existing"),
    "parity:node:aux-phase4a-backup-manager": ("VersionBackupManager", None),
    "parity:node:version-registry-promote-xse-version": ("XseVersion", None),
    "parity:python:path.lib.BackupManager": ("VersionBackupManager", None),
    "parity:python:path.lib.BackupManager.__init__": (
        "VersionBackupManager",
        "__init__",
    ),
    "parity:python:path.lib.BackupManager.create_backup": (
        "VersionBackupManager",
        "create_backup",
    ),
    "parity:python:path.lib.BackupManager.extract_version_from_xse_log": (
        "VersionBackupManager",
        "extract_version_from_xse_log",
    ),
    "parity:python:path.lib.BackupManager.get_version_path": (
        "VersionBackupManager",
        "get_version_path",
    ),
    "parity:python:path.lib.BackupManager.list_versions": (
        "VersionBackupManager",
        "list_versions",
    ),
    "parity:python:path.lib.XseVersion": ("XseVersion", None),
    "parity:python:path.lib.XseVersion.__init__": ("XseVersion", "__init__"),
    "parity:python:path.lib.XseVersion.full_version": ("XseVersion", "full_version"),
    "parity:python:path.lib.XseVersion.sanitized": ("XseVersion", "sanitized"),
}


def _rows():
    from conformance.coverage import load_source_parity_rows

    return {row.obligation_id: row for row in load_source_parity_rows(ROOT)}


def test_version_backup_rows_name_resource_core_and_keep_operation_identity():
    """Moved rows name resource core without re-keying their public operation.

    Path core no longer exports the backup, so no row may still claim
    classic-path-core owns any part of it.
    """
    rows = _rows()
    for obligation, (symbol, operation) in _MOVED_VERSION_BACKUP_ROWS.items():
        row = rows[obligation]
        assert row.rust_crate == "classic-resource-core", obligation
        assert row.rust_symbol == symbol, obligation
        assert row.runtime_operation == operation, obligation
    moved = {"BackupManager", "BackupError", "BackupResult", "XseVersion"}
    assert not [
        key
        for key, row in rows.items()
        if row.rust_crate == "classic-path-core"
        and (row.rust_symbol or "").removesuffix("@rust") in moved
    ]


def test_version_backup_rows_keep_executable_predicate_candidates():
    """Every moved binding row still finds its path-backups predicate."""
    from retirement_readiness import candidate_predicates

    pack = load_and_validate_pack(
        ROOT, Path("tests/conformance/packs/path_backups/v1.json")
    ).document()
    policy = FAMILY_COVERAGE_POLICIES["path-backups"]
    assert pack["domainOwner"]["rustCrate"] == "classic-resource-core"
    rows = _rows()
    for obligation in _MOVED_VERSION_BACKUP_ROWS:
        assert candidate_predicates(rows[obligation], pack, policy), obligation


def test_two_backup_operations_stay_independently_identifiable():
    """The version-labelled and game-target backups never share a Rust owner symbol.

    Both live in resource core once #250 lands, and parity rows resolve by crate
    and bare symbol, so a shared type name would let one backup's mapping pass
    against the other's implementation.
    """
    version_pack = load_and_validate_pack(
        ROOT, Path("tests/conformance/packs/path_backups/v1.json")
    ).document()
    game_target_pack = load_and_validate_pack(
        ROOT, Path("tests/conformance/packs/file_backups/v1.json")
    ).document()
    version_types = {
        symbol
        for capability in version_pack["capabilities"]
        for symbol in capability["rustSymbols"]
        if symbol[:1].isupper()
    }
    game_target_types = {
        symbol
        for capability in game_target_pack["capabilities"]
        for symbol in capability["rustSymbols"]
        if symbol[:1].isupper()
    }
    assert "VersionBackupManager" in version_types
    assert "BackupManager" in game_target_types
    assert not version_types & game_target_types
    rows = _rows()
    for obligation in (
        "parity:node:aux-phase4a-js-backup-manager",
        "parity:python:file_io.core.BackupManager@rust",
    ):
        assert rows[obligation].rust_symbol in {"BackupManager", "BackupManager@rust"}
