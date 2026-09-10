"""Import and restoration facts anchored to exact source and backup bytes."""

import hashlib
from collections.abc import Mapping

from ..coverage import CoveragePredicate


def compile_legacy_import(pack, fixture_root) -> None:
    """Compile byte-preservation expectations from authored source fixtures, never runtime output."""
    for scenario in pack["scenarios"]:
        if scenario["action"] != "user-settings.legacy-import":
            continue
        if scenario["expected"] != {"legacyImportCase": "restore-existing"}:
            raise ValueError("unsupported legacy import expectation")
        placements = scenario["input"]["installationData"]
        if {item["path"] for item in placements} != {
            "CLASSIC Settings.yaml",
            "state.json",
        }:
            raise ValueError("legacy import fixture placements are incomplete")
        contents = {
            item["path"]: (
                fixture_root / pack["fixtures"][item["fixtureRef"]]
            ).read_bytes()
            for item in placements
        }
        original, source = contents["CLASSIC Settings.yaml"], contents["state.json"]
        prefix = "CLASSIC Backup/User Settings/TUI State Imports/"
        backup = prefix + hashlib.sha256(source).hexdigest() + ".json"
        settings_backup = prefix + hashlib.sha256(original).hexdigest() + ".yaml"
        contents.update(
            {
                backup: source,
                settings_backup: original,
                "CLASSIC Settings.yaml.commit.lock": b"",
            }
        )
        scenario["expected"] = {
            "import": {
                "status": "applied",
                "sourcePath": "state.json",
                "backupPath": backup,
                "settingsPath": "CLASSIC Settings.yaml",
                "settingsBackupPath": settings_backup,
                "sourceRevisionMatches": True,
                "backupRevisionMatches": True,
                "baseRevisionMatches": True,
                "publishedRevisionMatches": True,
                "inapplicable": {
                    "classification": None,
                    "revision": None,
                    "expectedRevision": None,
                    "actualRevision": None,
                },
                "tui": {
                    "activeTab": 2,
                    "resultsPanelWidth": 42,
                    "sortAscending": True,
                    "origins": ["document"] * 3,
                },
            },
            "restore": {
                "status": "restored",
                "revisionMatches": True,
                "expectedRevision": None,
                "actualRevision": None,
            },
            "files": [
                {"path": path, "bytesHex": value.hex()}
                for path, value in sorted(contents.items())
            ],
        }


def legacy_restored(observation: Mapping) -> bool:
    """Verify retained content-addressed backups and byte-exact base restoration."""
    if set(observation) != {"import", "restore", "files"}:
        return False
    imported = observation["import"]
    files = observation["files"]
    if not isinstance(imported, Mapping) or not isinstance(files, list):
        return False
    try:
        contents = {file["path"]: bytes.fromhex(file["bytesHex"]) for file in files}
        original = contents["CLASSIC Settings.yaml"]
        source = contents["state.json"]
        prefix = "CLASSIC Backup/User Settings/TUI State Imports/"
        backup = prefix + hashlib.sha256(source).hexdigest() + ".json"
        settings_backup = prefix + hashlib.sha256(original).hexdigest() + ".yaml"
        return (
            len(contents) == len(files)
            and contents[backup] == source
            and contents[settings_backup] == original
            and imported
            == {
                "status": "applied",
                "sourcePath": "state.json",
                "backupPath": backup,
                "settingsPath": "CLASSIC Settings.yaml",
                "settingsBackupPath": settings_backup,
                "sourceRevisionMatches": True,
                "backupRevisionMatches": True,
                "baseRevisionMatches": True,
                "publishedRevisionMatches": True,
                "inapplicable": {
                    "classification": None,
                    "revision": None,
                    "expectedRevision": None,
                    "actualRevision": None,
                },
                "tui": {
                    "activeTab": 2,
                    "resultsPanelWidth": 42,
                    "sortAscending": True,
                    "origins": ["document"] * 3,
                },
            }
            and observation["restore"]
            == {
                "status": "restored",
                "revisionMatches": True,
                "expectedRevision": None,
                "actualRevision": None,
            }
        )
    except (KeyError, TypeError, ValueError):
        return False


LEGACY_IMPORT_PREDICATE = CoveragePredicate(
    "user-settings.legacy-import-restored",
    "user-settings.legacy-import",
    "user-settings.legacy-import",
    "durable-effects",
    (
        "import_legacy_tui_state",
        "LegacyTuiStateImportOutcome",
        "LegacyTuiStateImportReceipt",
        "LegacyTuiStateImportRestoreOutcome",
        "restore",
    ),
    legacy_restored,
    runtime_operations=(
        None,
        "user_settings_import_legacy_tui_state",
        "user_settings_legacy_tui_import_outcome",
        "user_settings_restore_legacy_tui_import",
        "importLegacyTuiStateIntoUserSettings",
        "import_legacy_tui_state_into_user_settings",
        "LegacyTuiStateImportReceipt.restore",
        "JsLegacyTuiStateImportReceipt.restore",
        "restore",
    ),
)
