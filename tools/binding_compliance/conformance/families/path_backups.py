"""Versioned backups require retained byte copies and public directory results."""

from collections.abc import Mapping

from ..coverage import CoveragePredicate, FamilyCoveragePolicy


def matches_versioned(value: Mapping) -> bool:
    """Require creation, overwrite, extraction and listing evidence together."""
    return (
        set(value)
        == {
            "version",
            "sanitized",
            "initial",
            "versions",
            "root",
            "directory",
            "created",
            "firstHex",
            "replacementHex",
            "files",
        }
        and value["version"] == "1.10.163.0"
        and value["sanitized"] == "1_10_163_0"
        and value["initial"] == []
        and value["versions"] == ["1_10_163_0"]
        and value["root"] == "backups"
        and value["directory"] == "backups/1_10_163_0"
        and value["created"] == "backups/1_10_163_0/settings.ini"
        and value["firstHex"] == "006669727374ff"
        and value["replacementHex"] == "007365636f6e64fe"
        and value["files"]
        == {
            "backups/1_10_163_0/settings.ini": value["replacementHex"],
            "settings.ini": value["replacementHex"],
            "xse.log": "72756e74696d652076657273696f6e203d20312e31302e3136332e300a",
        }
    )


def matches_timestamp(value: Mapping) -> bool:
    """Only normalized, bounded native timestamps with byte-exact copies earn facts."""
    return value == {
        "initial": [],
        "listed": ["<timestamp>"],
        "created": "CLASSIC Backups/Fallout4/<timestamp>/settings.ini",
        "sourceHex": "006669727374ff",
        "copyHex": "006669727374ff",
        "files": ["CLASSIC Backups/Fallout4/<timestamp>/settings.ini", "settings.ini"],
    }


PATH_BACKUPS_COVERAGE_POLICY = FamilyCoveragePolicy(
    "path-backups",
    (
        CoveragePredicate(
            "path-backups.versioned",
            "path-backups.versioned",
            "path-backups.versioned",
            "durable-effects",
            ("BackupManager", "XseVersion"),
            matches_versioned,
            runtime_operations=(
                None,
                "__init__",
                "new",
                "extract_version_from_xse_log",
                "extractVersionFromXseLog",
                "create_backup",
                "createBackup",
                "backup_root",
                "backupRoot",
                "list_versions",
                "listVersions",
                "get_version_path",
                "getVersionPath",
                "full_version",
                "fullVersion",
                "sanitized",
                "__repr__",
                "__str__",
                "toString",
            ),
        ),
        CoveragePredicate(
            "path-backups.timestamp",
            "path-backups.timestamp",
            "path-backups.timestamp",
            "durable-effects",
            ("create_backup", "list_versions"),
            matches_timestamp,
            runtime_operations=("backup_create_timestamped", "backup_list_existing"),
        ),
    ),
)
