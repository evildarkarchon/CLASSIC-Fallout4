"""Field-specific runtime credit for typed settings update builders."""

from collections.abc import Mapping
from functools import partial

from ..coverage import CoveragePredicate

UPDATE_FIELDS = (
    ("/CLASSIC_Settings/Update Check", "update_check", "bool"),
    ("/CLASSIC_Settings/Update Source", "update_source", "string"),
    ("/UI/preferences/auto_switch_after_scan", "auto_switch_after_scan", "bool"),
    ("/CLASSIC_Settings/Managed Game", "managed_game", "string"),
    ("/CLASSIC_Settings/Game Version", "game_version_selection", "string"),
    ("/CLASSIC_Settings/Game Folder Path", "game_root", "optional"),
    ("/CLASSIC_Settings/Game EXE Path", "game_executable", "optional"),
    ("/CLASSIC_Settings/Documents Folder Path", "documents_root", "optional"),
    ("/CLASSIC_Settings/INI Folder Path", "ini_folder", "optional"),
    ("/CLASSIC_Settings/MODS Folder Path", "mods_folder", "optional"),
    ("/CLASSIC_Settings/FCX Mode", "fcx_mode", "bool"),
    ("/CLASSIC_Settings/Simplify Logs", "simplify_logs", "bool"),
    ("/CLASSIC_Settings/Show Statistics", "show_statistics", "bool"),
    ("/CLASSIC_Settings/Show FormID Values", "formid_value_lookup", "bool"),
    ("/CLASSIC_Settings/FormID Databases", "formid_databases", "mapping"),
    ("/CLASSIC_Settings/Move Unsolved Logs", "move_unsolved_logs", "bool"),
    (
        "/CLASSIC_Settings/Unsolved Logs Destination",
        "unsolved_logs_destination",
        "optional",
    ),
    ("/CLASSIC_Settings/SCAN Custom Path", "custom_scan_input", "optional"),
    ("/CLASSIC_Settings/Papyrus Log Path", "papyrus_log_path", "optional"),
    ("/CLASSIC_Settings/Max Concurrent Scans", "max_concurrent_scans", "int"),
)


def accepted_setter(path, kind, observation):
    """Require the setter's own typed accepted value, never an unrelated preview."""
    preview = observation.get("preview", {})
    if preview.get("status") != "accepted" or preview.get("diagnostics") != []:
        return False
    fields = preview.get("acceptedFields", [])
    selected = [
        field
        for field in fields
        if isinstance(field, Mapping) and field.get("fieldPath") == path
    ]
    if len(selected) != 1 or set(selected[0]) != {"fieldPath", "value"}:
        return False
    value = selected[0]["value"]
    return {
        "bool": type(value) is bool,
        "int": type(value) is int,
        "string": isinstance(value, str),
        "optional": value is None or isinstance(value, str),
        "mapping": isinstance(value, Mapping),
    }[kind]


def setter_predicates():
    """Map each builder operation only to its corresponding native accepted field."""
    return tuple(
        CoveragePredicate(
            "user-settings.setter." + method.replace("_", "-"),
            "user-settings.update",
            "user-settings.update",
            "projection",
            ("with_" + method,),
            partial(accepted_setter, path, kind),
            runtime_operations=(
                None,
                "UserSettingsUpdate.set_" + method,
                "set_" + method,
            ),
        )
        for path, method, kind in UPDATE_FIELDS
    )


FORMID_DATABASES_POINTER = "/CLASSIC_Settings/FormID Databases"
# A request selector below the mapping names a game-aware save for that game.
FORMID_DATABASE_SAVE_PREFIX = FORMID_DATABASES_POINTER + "/"
LEGACY_FORMID_KEY_REMOVED = "legacy_formid_databases_key_removed"


def accepted_formid_database_save(observation):
    """Require the Fallout 4 VR save rule: shared-key mapping plus the legacy-key notice.

    Only ``with_formid_databases_for_game`` can produce an accepted preview whose
    published mapping drops ``Fallout4VR`` while reporting the removal, so a
    whole-mapping write can never earn this credit.
    """
    preview = observation.get("preview", {})
    if preview.get("status") != "accepted":
        return False
    fields = [
        field
        for field in preview.get("acceptedFields", [])
        if isinstance(field, Mapping) and field.get("fieldPath") == FORMID_DATABASES_POINTER
    ]
    diagnostics = preview.get("diagnostics")
    commit = observation.get("commit", {})
    return (
        len(fields) == 1
        and isinstance(fields[0].get("value"), Mapping)
        and "Fallout4" in fields[0]["value"]
        and "Fallout4VR" not in fields[0]["value"]
        and isinstance(diagnostics, list)
        and [
            diagnostic.get("code")
            for diagnostic in diagnostics
            if isinstance(diagnostic, Mapping)
        ]
        == [LEGACY_FORMID_KEY_REMOVED]
        and isinstance(commit, Mapping)
        and commit.get("status") == "committed"
        and commit.get("diagnostics") == diagnostics
    )


FORMID_DATABASE_SAVE_PREDICATE = CoveragePredicate(
    "user-settings.setter.formid-databases-for-game",
    "user-settings.update",
    "user-settings.update",
    "projection",
    ("with_formid_databases_for_game",),
    accepted_formid_database_save,
    runtime_operations=(
        None,
        "UserSettingsUpdate.set_formid_databases_for_game",
        "set_formid_databases_for_game",
    ),
)


GROUPED_FIELDS = (
    "/UI/window_geometry/main_tab/maximized",
    "/UI/window_geometry/main_tab/width",
    "/UI/window_geometry/main_tab/height",
    "/UI/tui/active_tab",
    "/UI/tui/results_panel_width",
    "/UI/tui/sort_ascending",
)
UPDATE_FIELD_ORDER = (
    tuple(path for path, _, _ in UPDATE_FIELDS[:3])
    + GROUPED_FIELDS
    + tuple(path for path, _, _ in UPDATE_FIELDS[3:])
)


def accepted_group(paths, observation):
    """Require every typed component of a single grouped native update."""
    return all(
        accepted_setter(
            path,
            "bool" if path.endswith(("/maximized", "/sort_ascending")) else "int",
            observation,
        )
        for path in paths
    )


def grouped_setter_predicates():
    """Credit window/TUI grouped builders only when all accepted components agree."""
    return tuple(
        CoveragePredicate(
            "user-settings.setter." + name.replace("_", "-"),
            "user-settings.update",
            "user-settings.update",
            "projection",
            ("with_" + name,),
            partial(accepted_group, paths),
            runtime_operations=(None, "UserSettingsUpdate.set_" + name, "set_" + name),
        )
        for name, paths in (
            ("window_geometry", GROUPED_FIELDS[:3]),
            ("tui_remembered_state", GROUPED_FIELDS[3:]),
        )
    )
