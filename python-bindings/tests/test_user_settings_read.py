"""Runtime coverage for the typed, read-only User Settings Python adapter."""

from pathlib import Path

import classic_user_settings
import pytest


def user_settings_fixture_root() -> Path:
    """Return the repository-level User Settings compatibility corpus."""
    return (
        Path(__file__).parents[2]
        / "tests"
        / "fixtures"
        / "user_settings_compatibility"
    )


def test_user_settings_read_only_open(tmp_path: Path) -> None:
    """Expose safe typed preferences and retain unknown source content without writing."""
    fixture_root = user_settings_fixture_root()
    content = (fixture_root / "invalid_known_values.yaml").read_bytes()
    settings_path = tmp_path / "CLASSIC Settings.yaml"
    settings_path.write_bytes(content)

    snapshot = classic_user_settings.open_user_settings(str(tmp_path))

    assert snapshot.update_preferences.update_check is False
    assert snapshot.update_preferences.origin == "degraded_fallback"
    assert snapshot.source_location == "canonical"
    assert snapshot.source_path == str(settings_path)
    assert snapshot.classification == "current"
    assert snapshot.schema_major == 1
    assert snapshot.schema_minor == 0
    assert snapshot.commit_eligibility == "eligible"
    assert [diagnostic.code for diagnostic in snapshot.diagnostics] == [
        "invalid_type_update_check",
        "invalid_enum_game_version",
        "invalid_type_move_unsolved_logs",
        "invalid_path_unsolved_logs_destination",
        "invalid_path_custom_scan_input",
        "invalid_range_max_concurrent_scans",
        "invalid_value_formid_databases",
        "invalid_type_gui_geometry_width",
        "invalid_type_gui_geometry_maximized",
    ]
    assert snapshot.diagnostics[0].message
    assert snapshot.revision.startswith("sha256:")
    assert snapshot.original_content == content
    assert settings_path.read_bytes() == content

    variants = [
        ("canonical_current_nested.yaml", "current", True, "document", "eligible"),
        ("flat_classic_config.yaml", "legacy_flat", False, "document", "requires_migration"),
        (
            "newer_major_schema.yaml",
            "future_major",
            False,
            "degraded_fallback",
            "blocked_untrusted",
        ),
        (
            "malformed.yaml",
            "malformed",
            False,
            "degraded_fallback",
            "blocked_untrusted",
        ),
    ]
    for index, (name, classification, update_check, origin, eligibility) in enumerate(
        variants
    ):
        case_root = tmp_path / f"case-{index}"
        case_root.mkdir()
        (case_root / "CLASSIC Settings.yaml").write_bytes(
            (fixture_root / name).read_bytes()
        )
        case_snapshot = classic_user_settings.open_user_settings(str(case_root))
        assert case_snapshot.classification == classification
        assert case_snapshot.update_preferences.update_check is update_check
        assert case_snapshot.update_preferences.origin == origin
        assert case_snapshot.commit_eligibility == eligibility

    legacy_root = tmp_path / "legacy"
    legacy_path = legacy_root / "CLASSIC Data" / "CLASSIC Settings.yaml"
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_bytes((fixture_root / "previous_location_nested.yaml").read_bytes())
    legacy = classic_user_settings.open_user_settings(str(legacy_root))
    assert legacy.source_location == "legacy"
    assert legacy.commit_eligibility == "requires_migration"

    missing_root = tmp_path / "missing"
    missing_root.mkdir()
    missing = classic_user_settings.open_user_settings(str(missing_root))
    assert missing.source_location == "missing"
    assert missing.source_path is None
    assert missing.classification == "missing"
    assert missing.schema_major is None
    assert missing.schema_minor is None
    assert missing.revision == "missing"
    assert missing.update_preferences.update_check is True
    assert missing.update_preferences.origin == "default"
    assert missing.original_content is None

    invalid_bytes_root = tmp_path / "invalid-bytes"
    invalid_bytes_root.mkdir()
    invalid_bytes = b"\xff\xfe\xfd"
    (invalid_bytes_root / "CLASSIC Settings.yaml").write_bytes(invalid_bytes)
    invalid_bytes_snapshot = classic_user_settings.open_user_settings(
        str(invalid_bytes_root)
    )
    assert invalid_bytes_snapshot.classification == "malformed"
    assert invalid_bytes_snapshot.original_content == invalid_bytes


def test_user_settings_frontend_state_exposes_nested_values_and_origins(
    tmp_path: Path,
) -> None:
    """Expose shared preferences, GUI geometry, and namespaced TUI remembered state."""
    fixture_root = user_settings_fixture_root()
    settings_path = tmp_path / "CLASSIC Settings.yaml"
    source_bytes = (fixture_root / "gui_geometry.yaml").read_bytes()
    settings_path.write_bytes(source_bytes)

    snapshot = classic_user_settings.open_user_settings(str(tmp_path))
    frontend = snapshot.frontend_state

    assert isinstance(frontend, classic_user_settings.FrontendState)
    assert isinstance(frontend.preferences, classic_user_settings.FrontendPreferences)
    assert frontend.preferences.auto_switch_after_scan is True
    assert frontend.preferences.auto_switch_after_scan_origin == "document"
    assert frontend.preferences.auto_refresh_interval_ms == 5000
    assert frontend.preferences.auto_refresh_interval_ms_origin == "document"

    geometry = frontend.window_geometry
    assert isinstance(geometry, classic_user_settings.GuiWindowGeometry)
    expected_tabs = {
        "main_tab": (False, 705, 641),
        "backups_tab": (False, 750, 580),
        "articles_tab": (False, 550, 350),
        "results_tab": (True, 750, 450),
    }
    for tab_name, expected in expected_tabs.items():
        tab = getattr(geometry, tab_name)
        assert isinstance(tab, classic_user_settings.WindowGeometry)
        assert (tab.maximized, tab.width, tab.height) == expected
        assert {
            tab.maximized_origin,
            tab.width_origin,
            tab.height_origin,
        } == {"document"}

    assert isinstance(frontend.tui, classic_user_settings.TuiRememberedState)
    assert frontend.tui.active_tab == 0
    assert frontend.tui.results_panel_width == 30
    assert frontend.tui.sort_ascending is False
    assert {
        frontend.tui.active_tab_origin,
        frontend.tui.results_panel_width_origin,
        frontend.tui.sort_ascending_origin,
    } == {"default"}
    assert snapshot.original_content == source_bytes
    assert settings_path.read_bytes() == source_bytes

    invalid_root = tmp_path / "invalid-frontend"
    invalid_root.mkdir()
    invalid_path = invalid_root / "CLASSIC Settings.yaml"
    invalid_bytes = (fixture_root / "invalid_known_values.yaml").read_bytes()
    invalid_path.write_bytes(invalid_bytes)

    invalid = classic_user_settings.open_user_settings(str(invalid_root))
    invalid_main = invalid.frontend_state.window_geometry.main_tab
    assert (invalid_main.maximized, invalid_main.width, invalid_main.height) == (
        False,
        640,
        500,
    )
    assert invalid_main.maximized_origin == "degraded_fallback"
    assert invalid_main.width_origin == "degraded_fallback"
    assert invalid_main.height_origin == "document"
    assert invalid.original_content == invalid_bytes
    assert invalid_path.read_bytes() == invalid_bytes


def test_user_settings_scan_snapshot_exposes_typed_values_and_alias_policy(
    tmp_path: Path,
) -> None:
    """Project scan choices, provenance, aliases, and safe fallbacks as typed values."""
    fixture_root = user_settings_fixture_root()
    current_path = tmp_path / "CLASSIC Settings.yaml"
    current_path.write_bytes((fixture_root / "canonical_current_nested.yaml").read_bytes())

    current = classic_user_settings.open_user_settings(str(tmp_path))
    scan = current.crash_log_scan_settings

    assert scan.fcx_mode is False
    assert scan.simplify_logs is False
    assert scan.show_statistics is False
    assert scan.formid_value_lookup is False
    assert scan.formid_databases == {
        "Fallout4": ["databases/Fallout4 FormIDs.db"]
    }
    assert scan.move_unsolved_logs is True
    assert scan.unsolved_logs_destination is None
    assert scan.custom_scan_input is None
    assert scan.game_version_selection == "auto"
    assert scan.max_concurrent_scans == 0
    assert scan.fcx_mode_origin == "document"
    assert scan.formid_databases_origin == "document"

    alias_root = tmp_path / "alias"
    alias_root.mkdir()
    alias_bytes = (fixture_root / "alias_only.yaml").read_bytes()
    alias_path = alias_root / "CLASSIC Settings.yaml"
    alias_path.write_bytes(alias_bytes)
    alias = classic_user_settings.open_user_settings(str(alias_root))
    assert alias.crash_log_scan_settings.custom_scan_input == "E:/Alias Crash Logs"
    assert alias.crash_log_scan_settings.custom_scan_input_origin == "document"
    assert alias.diagnostics == []
    assert alias_path.read_bytes() == alias_bytes

    conflict_root = tmp_path / "conflict"
    conflict_root.mkdir()
    conflict_bytes = (fixture_root / "canonical_alias_conflict.yaml").read_bytes()
    conflict_path = conflict_root / "CLASSIC Settings.yaml"
    conflict_path.write_bytes(conflict_bytes)
    conflict = classic_user_settings.open_user_settings(str(conflict_root))
    assert conflict.crash_log_scan_settings.custom_scan_input == "D:/Canonical Crash Logs"
    assert [diagnostic.code for diagnostic in conflict.diagnostics] == [
        "canonical_alias_conflict_mods_folder",
        "canonical_alias_conflict_custom_scan_folder",
    ]
    assert conflict_path.read_bytes() == conflict_bytes

    invalid_root = tmp_path / "invalid"
    invalid_root.mkdir()
    invalid_bytes = (fixture_root / "invalid_known_values.yaml").read_bytes()
    invalid_path = invalid_root / "CLASSIC Settings.yaml"
    invalid_path.write_bytes(invalid_bytes)
    invalid = classic_user_settings.open_user_settings(str(invalid_root))
    invalid_scan = invalid.crash_log_scan_settings
    assert invalid_scan.game_version_selection == "auto"
    assert invalid_scan.game_version_selection_origin == "degraded_fallback"
    assert invalid_scan.move_unsolved_logs is False
    assert invalid_scan.move_unsolved_logs_origin == "degraded_fallback"
    assert invalid_scan.unsolved_logs_destination is None
    assert invalid_scan.unsolved_logs_destination_origin == "degraded_fallback"
    assert invalid_scan.custom_scan_input is None
    assert invalid_scan.custom_scan_input_origin == "degraded_fallback"
    assert invalid_scan.formid_databases == {}
    assert invalid_scan.formid_databases_origin == "degraded_fallback"
    assert invalid_scan.max_concurrent_scans == 0
    assert invalid_scan.max_concurrent_scans_origin == "degraded_fallback"
    assert invalid_path.read_bytes() == invalid_bytes

    game_setup_root = tmp_path / "game-setup"
    game_setup_root.mkdir()
    game_setup_bytes = b"""schema_version: \"1.0\"
CLASSIC_Settings:
  Managed Game: Fallout 4 VR
  Game Version: VR
  Game Folder Path: 'Z:\\Games\\Fallout 4 VR'
  Game EXE Path: 'Z:\\Games\\Fallout 4 VR\\Fallout4VR.exe'
  Documents Folder Path: /home/deck/Documents/My Games/Fallout4VR
  INI Folder Path: /home/deck/compatdata/fallout4vr/ini
  MODS Folder Path: /home/deck/Games/Fallout4VR/mods
  SCAN Custom Path: /home/deck/CLASSIC/crash-logs
  Papyrus Log Path: /home/deck/Documents/My Games/Fallout4VR/Logs/Script/Papyrus.0.log
"""
    (game_setup_root / "CLASSIC Settings.yaml").write_bytes(game_setup_bytes)

    setup_snapshot = classic_user_settings.open_user_settings(str(game_setup_root))
    setup = setup_snapshot.game_setup_settings
    assert isinstance(setup, classic_user_settings.GameSetupSettings)
    assert setup.managed_game == "Fallout4VR"
    assert setup.game_version_selection == "VR"
    assert setup.game_root == r"Z:\Games\Fallout 4 VR"
    assert setup.game_executable == r"Z:\Games\Fallout 4 VR\Fallout4VR.exe"
    assert setup.documents_root == "/home/deck/Documents/My Games/Fallout4VR"
    assert setup.ini_folder == "/home/deck/compatdata/fallout4vr/ini"
    assert setup.mods_root == "/home/deck/Games/Fallout4VR/mods"
    assert setup.custom_scan_input == "/home/deck/CLASSIC/crash-logs"
    assert setup.papyrus_log == (
        "/home/deck/Documents/My Games/Fallout4VR/Logs/Script/Papyrus.0.log"
    )
    assert {
        setup.managed_game_origin,
        setup.game_version_selection_origin,
        setup.game_root_origin,
        setup.game_executable_origin,
        setup.documents_root_origin,
        setup.ini_folder_origin,
        setup.mods_root_origin,
        setup.custom_scan_input_origin,
        setup.papyrus_log_origin,
    } == {"document"}


def test_user_settings_preview_accepts_or_rejects_an_update_without_writing(
    tmp_path: Path,
) -> None:
    """Return one complete accepted preview or field-specific rejection diagnostics."""
    fixture_root = user_settings_fixture_root()
    settings_path = tmp_path / "CLASSIC Settings.yaml"
    source_bytes = (fixture_root / "unknown_entries.yaml").read_bytes()
    settings_path.write_bytes(source_bytes)
    snapshot = classic_user_settings.open_user_settings(str(tmp_path))

    accepted_update = classic_user_settings.UserSettingsUpdate()
    accepted_update.set_update_check(False)
    accepted_update.set_managed_game("Fallout4VR")
    accepted_update.set_game_version_selection("VR")
    accepted_update.set_game_root(r"Z:\Games\Fallout 4 VR")
    accepted_update.set_game_executable(r"Z:\Games\Fallout 4 VR\Fallout4VR.exe")
    accepted_update.set_documents_root("/home/deck/Documents/My Games/Fallout4VR")
    accepted_update.set_ini_folder("/home/deck/compatdata/fallout4vr/ini")
    accepted_update.set_mods_folder("/home/deck/Games/Fallout4VR/mods")
    accepted_update.set_fcx_mode(True)
    accepted_update.set_simplify_logs(True)
    accepted_update.set_show_statistics(True)
    accepted_update.set_formid_value_lookup(True)
    accepted_update.set_formid_databases({"Fallout4": ["Z:/Forms.db"]})
    accepted_update.set_move_unsolved_logs(False)
    accepted_update.set_unsolved_logs_destination("C:/CLASSIC/Unsolved")
    accepted_update.set_custom_scan_input("D:/Crash Logs")
    accepted_update.set_papyrus_log_path(
        "/home/deck/Documents/My Games/Fallout4VR/Logs/Script/Papyrus.0.log"
    )
    accepted_update.set_max_concurrent_scans(4)
    accepted = snapshot.preview_update(accepted_update)

    assert accepted.accepted is True
    assert accepted.base_revision == snapshot.revision
    assert accepted.diagnostics == []
    assert [field.canonical_path for field in accepted.fields] == [
        "/CLASSIC_Settings/Update Check",
        "/CLASSIC_Settings/Managed Game",
        "/CLASSIC_Settings/Game Version",
        "/CLASSIC_Settings/Game Folder Path",
        "/CLASSIC_Settings/Game EXE Path",
        "/CLASSIC_Settings/Documents Folder Path",
        "/CLASSIC_Settings/INI Folder Path",
        "/CLASSIC_Settings/MODS Folder Path",
        "/CLASSIC_Settings/FCX Mode",
        "/CLASSIC_Settings/Simplify Logs",
        "/CLASSIC_Settings/Show Statistics",
        "/CLASSIC_Settings/Show FormID Values",
        "/CLASSIC_Settings/FormID Databases",
        "/CLASSIC_Settings/Move Unsolved Logs",
        "/CLASSIC_Settings/Unsolved Logs Destination",
        "/CLASSIC_Settings/SCAN Custom Path",
        "/CLASSIC_Settings/Papyrus Log Path",
        "/CLASSIC_Settings/Max Concurrent Scans",
    ]
    assert [field.value for field in accepted.fields] == [
        False,
        "Fallout4VR",
        "VR",
        r"Z:\Games\Fallout 4 VR",
        r"Z:\Games\Fallout 4 VR\Fallout4VR.exe",
        "/home/deck/Documents/My Games/Fallout4VR",
        "/home/deck/compatdata/fallout4vr/ini",
        "/home/deck/Games/Fallout4VR/mods",
        True,
        True,
        True,
        True,
        {"Fallout4": ["Z:/Forms.db"]},
        False,
        "C:/CLASSIC/Unsolved",
        "D:/Crash Logs",
        "/home/deck/Documents/My Games/Fallout4VR/Logs/Script/Papyrus.0.log",
        4,
    ]
    assert snapshot.update_preferences.update_check is True
    assert snapshot.crash_log_scan_settings.max_concurrent_scans == 0
    assert settings_path.read_bytes() == source_bytes

    rejected_update = classic_user_settings.UserSettingsUpdate()
    rejected_update.set_update_check(False)
    rejected_update.set_managed_game("Morrowind")
    rejected_update.set_game_version_selection("Future")
    rejected_update.set_max_concurrent_scans(-9)
    rejected = snapshot.preview_update(rejected_update)

    assert rejected.accepted is False
    assert rejected.base_revision is None
    assert rejected.fields == []
    assert [
        (diagnostic.field_path, diagnostic.code)
        for diagnostic in rejected.diagnostics
    ] == [
        (
            "/CLASSIC_Settings/Managed Game",
            "invalid_enum_managed_game",
        ),
        (
            "/CLASSIC_Settings/Game Version",
            "invalid_enum_game_version",
        ),
        (
            "/CLASSIC_Settings/Max Concurrent Scans",
            "invalid_range_max_concurrent_scans",
        ),
    ]
    assert settings_path.read_bytes() == source_bytes


def test_accepted_user_settings_update_commit_publishes_preserved_document(
    tmp_path: Path,
) -> None:
    """Commit requested fields while retaining unrelated document content."""
    fixture_root = user_settings_fixture_root()
    settings_path = tmp_path / "CLASSIC Settings.yaml"
    settings_path.write_bytes((fixture_root / "unknown_entries.yaml").read_bytes())
    snapshot = classic_user_settings.open_user_settings(str(tmp_path))
    update = classic_user_settings.UserSettingsUpdate()
    update.set_update_check(False)
    update.set_unsolved_logs_destination("D:/CLASSIC/Unsolved")

    accepted = snapshot.preview_update(update)
    outcome = accepted.commit(str(tmp_path))

    assert outcome.status == "committed"
    assert outcome.revision is not None
    assert outcome.revision.startswith("sha256:")
    assert outcome.expected_revision is None
    assert outcome.actual_revision is None
    committed = classic_user_settings.open_user_settings(str(tmp_path))
    assert committed.revision == outcome.revision
    assert committed.update_preferences.update_check is False
    assert (
        committed.crash_log_scan_settings.unsolved_logs_destination
        == "D:/CLASSIC/Unsolved"
    )
    committed_content = settings_path.read_text(encoding="utf-8")
    assert "ThirdPartyPlugin:" in committed_content
    assert "community_frontend:" in committed_content


def test_missing_user_settings_requires_explicit_bootstrap_preview(
    tmp_path: Path,
) -> None:
    """Create the complete Rust-owned defaults only through explicit bootstrap."""
    settings_path = tmp_path / "CLASSIC Settings.yaml"
    snapshot = classic_user_settings.open_user_settings(str(tmp_path))
    update = classic_user_settings.UserSettingsUpdate()
    update.set_game_version_selection("VR")

    ordinary = snapshot.preview_update(update)

    assert ordinary.accepted is False
    assert [diagnostic.code for diagnostic in ordinary.diagnostics] == [
        "update_base_requires_bootstrap"
    ]
    assert not settings_path.exists()

    bootstrap = snapshot.preview_bootstrap(update)

    assert bootstrap.accepted is True
    assert bootstrap.base_revision == "missing"
    assert not settings_path.exists()

    outcome = bootstrap.commit(str(tmp_path))

    assert outcome.status == "committed"
    document = settings_path.read_text(encoding="utf-8")
    assert "schema_version:" in document
    assert "CLASSIC_Settings:" in document
    assert "Game Version: VR" in document
    assert "FormID Databases:" in document
    assert "UI:" in document
    assert "window_geometry:" in document
    assert "tui:" in document


def test_accepted_user_settings_update_commit_reports_stale_conflict(
    tmp_path: Path,
) -> None:
    """Return revision details without overwriting a concurrent external edit."""
    fixture_root = user_settings_fixture_root()
    settings_path = tmp_path / "CLASSIC Settings.yaml"
    source_bytes = (fixture_root / "unknown_entries.yaml").read_bytes()
    settings_path.write_bytes(source_bytes)
    snapshot = classic_user_settings.open_user_settings(str(tmp_path))
    update = classic_user_settings.UserSettingsUpdate()
    update.set_update_check(False)
    accepted = snapshot.preview_update(update)
    externally_edited = source_bytes + b"\nExternalOwner:\n  generation: 2\n"
    settings_path.write_bytes(externally_edited)

    outcome = accepted.commit(str(tmp_path))

    assert outcome.status == "conflict"
    assert outcome.revision is None
    assert outcome.expected_revision == snapshot.revision
    assert outcome.actual_revision is not None
    assert outcome.actual_revision.startswith("sha256:")
    assert outcome.actual_revision != outcome.expected_revision
    assert settings_path.read_bytes() == externally_edited


def test_user_settings_update_commit_rejects_unaccepted_and_operational_failures(
    tmp_path: Path,
) -> None:
    """Reject invalid previews and raise the typed commit error for I/O failures."""
    snapshot = classic_user_settings.open_user_settings(str(tmp_path))
    invalid_update = classic_user_settings.UserSettingsUpdate()
    invalid_update.set_max_concurrent_scans(-1)
    rejected = snapshot.preview_update(invalid_update)
    with pytest.raises(ValueError, match="only an accepted"):
        rejected.commit(str(tmp_path))

    update = classic_user_settings.UserSettingsUpdate()
    update.set_update_check(False)
    accepted = snapshot.preview_bootstrap(update)
    tmp_path.rmdir()

    with pytest.raises(
        classic_user_settings.UserSettingsCommitError,
        match="commit_lock_open_failed",
    ):
        accepted.commit(str(tmp_path))
