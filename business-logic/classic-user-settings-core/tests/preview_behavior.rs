//! Behavioral checks for non-persisting User Settings Update previews.

use classic_user_settings_core::{
    GameVersionSelection, UserSettings, UserSettingsUpdate, UserSettingsUpdateField,
    UserSettingsUpdatePreview,
};
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

/// Returns a checked-in compatibility fixture through the repository root.
fn fixture_path(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join("tests/fixtures/user_settings_compatibility")
        .join(name)
}

/// Copies one compatibility fixture to the canonical User Settings path.
fn install_fixture(root: &Path, fixture: &str) -> PathBuf {
    let destination = root.join("CLASSIC Settings.yaml");
    std::fs::copy(fixture_path(fixture), &destination).unwrap();
    destination
}

#[test]
fn preview_accepts_a_multi_field_update_without_changing_unknown_entries_or_snapshot_values() {
    let root = tempfile::tempdir().unwrap();
    let path = install_fixture(root.path(), "unknown_entries.yaml");
    let bytes_before = std::fs::read(&path).unwrap();
    let modified_before = std::fs::metadata(&path).unwrap().modified().unwrap();
    let settings = UserSettings::open(root.path());
    let update = UserSettingsUpdate::new()
        .with_update_check(false)
        .with_max_concurrent_scans(4);

    let preview = settings.preview_update(update);

    let UserSettingsUpdatePreview::Accepted(accepted) = preview else {
        panic!("valid requested fields should produce one accepted preview");
    };
    assert_eq!(accepted.base_revision(), settings.revision());
    assert_eq!(
        accepted.fields(),
        &[
            UserSettingsUpdateField::UpdateCheck(false),
            UserSettingsUpdateField::MaxConcurrentScans(4),
        ]
    );
    assert_eq!(
        accepted
            .fields()
            .iter()
            .map(UserSettingsUpdateField::canonical_path)
            .collect::<Vec<_>>(),
        vec![
            "/CLASSIC_Settings/Update Check",
            "/CLASSIC_Settings/Max Concurrent Scans",
        ]
    );
    assert!(settings.update_preferences().update_check());
    assert_eq!(settings.crash_log_scan_settings().max_concurrent_scans(), 0);
    assert_eq!(settings.original_bytes(), Some(bytes_before.as_slice()));
    assert_eq!(std::fs::read(&path).unwrap(), bytes_before);
    assert_eq!(
        std::fs::metadata(&path).unwrap().modified().unwrap(),
        modified_before
    );
}

#[test]
fn preview_rejects_all_requested_fields_as_one_unit_with_field_specific_diagnostics() {
    let root = tempfile::tempdir().unwrap();
    let path = install_fixture(root.path(), "invalid_known_values.yaml");
    let bytes_before = std::fs::read(&path).unwrap();
    let settings = UserSettings::open(root.path());
    let update = UserSettingsUpdate::new()
        .with_update_check(true)
        .with_game_version_selection("Future")
        .with_max_concurrent_scans(-9);

    let preview = settings.preview_update(update);

    let UserSettingsUpdatePreview::Rejected(diagnostics) = preview else {
        panic!("one invalid requested field must prevent a partial accepted preview");
    };
    assert_eq!(
        diagnostics
            .iter()
            .map(|diagnostic| (diagnostic.field_path(), diagnostic.code()))
            .collect::<Vec<_>>(),
        vec![
            (
                Some("/CLASSIC_Settings/Game Version"),
                "invalid_enum_game_version",
            ),
            (
                Some("/CLASSIC_Settings/Max Concurrent Scans"),
                "invalid_range_max_concurrent_scans",
            ),
        ]
    );
    assert_eq!(settings.original_bytes(), Some(bytes_before.as_slice()));
    assert_eq!(std::fs::read(path).unwrap(), bytes_before);
}

#[test]
fn preview_does_not_include_or_repair_an_unrelated_conflicting_alias() {
    let root = tempfile::tempdir().unwrap();
    let path = install_fixture(root.path(), "canonical_alias_conflict.yaml");
    let bytes_before = std::fs::read(&path).unwrap();
    let settings = UserSettings::open(root.path());

    let preview = settings.preview_update(UserSettingsUpdate::new().with_max_concurrent_scans(4));

    let UserSettingsUpdatePreview::Accepted(accepted) = preview else {
        panic!("an unrelated alias conflict must not reject a valid requested field");
    };
    assert_eq!(
        accepted.fields(),
        &[UserSettingsUpdateField::MaxConcurrentScans(4)]
    );
    assert_eq!(std::fs::read(path).unwrap(), bytes_before);
}

#[test]
fn preview_carries_every_requested_scan_field_without_normalizing_values() {
    let root = tempfile::tempdir().unwrap();
    let settings = UserSettings::open(root.path());
    let databases = BTreeMap::from([(
        "Fallout4".to_string(),
        vec!["databases/custom.db".to_string()],
    )]);
    let update = UserSettingsUpdate::new()
        .with_game_version_selection("VR")
        .with_fcx_mode(true)
        .with_simplify_logs(true)
        .with_show_statistics(true)
        .with_formid_value_lookup(true)
        .with_formid_databases(databases.clone())
        .with_move_unsolved_logs(false)
        .with_unsolved_logs_destination(Some("C:/CLASSIC/Unsolved".to_string()))
        .with_custom_scan_input(Some("D:/Crash Logs".to_string()))
        .with_max_concurrent_scans(8);

    let UserSettingsUpdatePreview::Accepted(accepted) = settings.preview_update(update) else {
        panic!("canonical scan values should produce an accepted preview");
    };

    assert_eq!(
        accepted.fields(),
        &[
            UserSettingsUpdateField::GameVersionSelection(GameVersionSelection::Vr),
            UserSettingsUpdateField::FcxMode(true),
            UserSettingsUpdateField::SimplifyLogs(true),
            UserSettingsUpdateField::ShowStatistics(true),
            UserSettingsUpdateField::FormIdValueLookup(true),
            UserSettingsUpdateField::FormIdDatabases(databases),
            UserSettingsUpdateField::MoveUnsolvedLogs(false),
            UserSettingsUpdateField::UnsolvedLogsDestination(Some(
                "C:/CLASSIC/Unsolved".to_string(),
            )),
            UserSettingsUpdateField::CustomScanInput(Some("D:/Crash Logs".to_string())),
            UserSettingsUpdateField::MaxConcurrentScans(8),
        ]
    );
    assert!(!root.path().join("CLASSIC Settings.yaml").exists());
}

#[test]
fn preview_rejects_an_untrusted_base_without_exposing_requested_fields() {
    let root = tempfile::tempdir().unwrap();
    let path = install_fixture(root.path(), "malformed.yaml");
    let bytes_before = std::fs::read(&path).unwrap();
    let settings = UserSettings::open(root.path());

    let preview = settings.preview_update(UserSettingsUpdate::new().with_update_check(true));

    let UserSettingsUpdatePreview::Rejected(diagnostics) = preview else {
        panic!("an untrusted source cannot produce an accepted update preview");
    };
    assert_eq!(diagnostics.len(), 1);
    assert_eq!(diagnostics[0].field_path(), None);
    assert_eq!(diagnostics[0].code(), "update_base_not_commit_eligible");
    assert_eq!(std::fs::read(path).unwrap(), bytes_before);
}
