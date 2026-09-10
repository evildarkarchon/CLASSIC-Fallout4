"""Managed game-file backups preserve exact copies, restoration and removal."""

from collections.abc import Mapping

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def matches_backup(value: Mapping) -> bool:
    """Require an existing native backup and restoration of overwritten source bytes."""
    return (
        set(value)
        == {"initial", "exists", "created", "restored", "copy", "source", "files"}
        and value["initial"] is False
        and value["exists"] is True
        and value["created"] == "Backed up 1 files"
        and value["restored"] == 1
        and value["copy"] == "original bytes\n"
        and value["source"] == value["copy"]
        and value["files"]
        == {
            "f4se_fixture.dll": value["copy"],
            "sentinel.txt": "keep\n",
            "CLASSIC_Backups/XSE_Backup/f4se_fixture.dll": value["copy"],
        }
    )


def matches_removed(value: Mapping) -> bool:
    """Backup removal must preserve the restored game file and unrelated sentinel."""
    return value == {
        "exists": False,
        "files": {"f4se_fixture.dll": "original bytes\n", "sentinel.txt": "keep\n"},
    }


def matches_game_files(value: Mapping) -> bool:
    """Require all three public operations with intermediate restored source bytes."""
    return value == {
        "backup": "1 files affected, 0 errors",
        "restore": "1 files affected, 0 errors",
        "remove": "1 files affected, 0 errors",
        "restored": "original bytes\n",
        "files": {
            "backups/fixture/f4se_fixture.dll": "original bytes\n",
            "game/sentinel.txt": "keep\n",
        },
    }


FILE_BACKUPS_COVERAGE_POLICY = FamilyCoveragePolicy(
    "file-backups",
    (
        CoveragePredicate(
            "file-backups.managed",
            "file-backups.managed",
            "file-backups.managed",
            "durable-effects",
            ("BackupManager", "create_backup", "restore_backup", "backup_exists"),
            matches_backup,
            runtime_operations=(
                None,
                "backup_manager_new",
                "backup_manager_create",
                "backup_manager_restore",
                "backup_manager_exists",
            ),
        ),
        CoveragePredicate(
            "file-backups.remove",
            "file-backups.remove",
            "file-backups.remove",
            "durable-effects",
            ("remove_backup",),
            matches_removed,
            runtime_operations=("backup_manager_remove",),
        ),
        CoveragePredicate(
            "file-backups.game-files",
            "file-backups.game-files",
            "file-backups.game-files",
            "durable-effects",
            ("GameFilesManager", "backup", "restore", "remove"),
            matches_game_files,
            runtime_operations=(
                None,
                "game_files_manager_new",
                "game_files_backup",
                "game_files_restore",
                "game_files_remove",
            ),
        ),
    ),
)
