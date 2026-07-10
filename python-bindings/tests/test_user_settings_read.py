"""Runtime coverage for the typed, read-only User Settings Python adapter."""

from pathlib import Path

import classic_user_settings


def test_user_settings_read_only_open(tmp_path: Path) -> None:
    """Expose safe typed preferences and retain unknown source content without writing."""
    fixture_root = (
        Path(__file__).parents[2]
        / "tests"
        / "fixtures"
        / "user_settings_compatibility"
    )
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


def test_user_settings_scan_snapshot_exposes_typed_values_and_alias_policy(
    tmp_path: Path,
) -> None:
    """Project scan choices, provenance, aliases, and safe fallbacks as typed values."""
    fixture_root = (
        Path(__file__).parents[2]
        / "tests"
        / "fixtures"
        / "user_settings_compatibility"
    )
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
        "canonical_alias_conflict_custom_scan_folder"
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


def test_user_settings_preview_accepts_or_rejects_an_update_without_writing(
    tmp_path: Path,
) -> None:
    """Return one complete accepted preview or field-specific rejection diagnostics."""
    fixture_root = (
        Path(__file__).parents[2]
        / "tests"
        / "fixtures"
        / "user_settings_compatibility"
    )
    settings_path = tmp_path / "CLASSIC Settings.yaml"
    source_bytes = (fixture_root / "unknown_entries.yaml").read_bytes()
    settings_path.write_bytes(source_bytes)
    snapshot = classic_user_settings.open_user_settings(str(tmp_path))

    accepted_update = classic_user_settings.UserSettingsUpdate()
    accepted_update.set_update_check(False)
    accepted_update.set_game_version_selection("VR")
    accepted_update.set_fcx_mode(True)
    accepted_update.set_simplify_logs(True)
    accepted_update.set_show_statistics(True)
    accepted_update.set_formid_value_lookup(True)
    accepted_update.set_formid_databases({"Fallout4": ["Z:/Forms.db"]})
    accepted_update.set_move_unsolved_logs(False)
    accepted_update.set_unsolved_logs_destination("C:/CLASSIC/Unsolved")
    accepted_update.set_custom_scan_input("D:/Crash Logs")
    accepted_update.set_max_concurrent_scans(4)
    accepted = snapshot.preview_update(accepted_update)

    assert accepted.accepted is True
    assert accepted.base_revision == snapshot.revision
    assert accepted.diagnostics == []
    assert [field.canonical_path for field in accepted.fields] == [
        "/CLASSIC_Settings/Update Check",
        "/CLASSIC_Settings/Game Version",
        "/CLASSIC_Settings/FCX Mode",
        "/CLASSIC_Settings/Simplify Logs",
        "/CLASSIC_Settings/Show Statistics",
        "/CLASSIC_Settings/Show FormID Values",
        "/CLASSIC_Settings/FormID Databases",
        "/CLASSIC_Settings/Move Unsolved Logs",
        "/CLASSIC_Settings/Unsolved Logs Destination",
        "/CLASSIC_Settings/SCAN Custom Path",
        "/CLASSIC_Settings/Max Concurrent Scans",
    ]
    assert [field.value for field in accepted.fields] == [
        False,
        "VR",
        True,
        True,
        True,
        True,
        {"Fallout4": ["Z:/Forms.db"]},
        False,
        "C:/CLASSIC/Unsolved",
        "D:/Crash Logs",
        4,
    ]
    assert snapshot.update_preferences.update_check is True
    assert snapshot.crash_log_scan_settings.max_concurrent_scans == 0
    assert settings_path.read_bytes() == source_bytes

    rejected_update = classic_user_settings.UserSettingsUpdate()
    rejected_update.set_update_check(False)
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
            "/CLASSIC_Settings/Game Version",
            "invalid_enum_game_version",
        ),
        (
            "/CLASSIC_Settings/Max Concurrent Scans",
            "invalid_range_max_concurrent_scans",
        ),
    ]
    assert settings_path.read_bytes() == source_bytes
