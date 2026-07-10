//! Behavioral checks for Crash Log Scan User Settings through the public interface.

use classic_user_settings_core::{GameVersionSelection, PreferenceOrigin, UserSettings};
use std::path::{Path, PathBuf};

/// Returns a checked-in compatibility fixture through the repository root.
fn fixture_path(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join("tests/fixtures/user_settings_compatibility")
        .join(name)
}

/// Copies one compatibility fixture to its requested root-relative path.
fn install_fixture(root: &Path, fixture: &str) -> PathBuf {
    let destination = root.join("CLASSIC Settings.yaml");
    std::fs::copy(fixture_path(fixture), &destination).unwrap();
    destination
}

#[test]
fn open_current_document_projects_complete_crash_log_scan_settings_without_writing() {
    let root = tempfile::tempdir().unwrap();
    let path = install_fixture(root.path(), "canonical_current_nested.yaml");
    let bytes_before = std::fs::read(&path).unwrap();
    let modified_before = std::fs::metadata(&path).unwrap().modified().unwrap();

    let settings = UserSettings::open(root.path());
    let scan = settings.crash_log_scan_settings();

    assert!(!scan.fcx_mode());
    assert!(!scan.simplify_logs());
    assert!(!scan.show_statistics());
    assert!(!scan.formid_value_lookup());
    assert!(scan.move_unsolved_logs());
    assert_eq!(scan.unsolved_logs_destination(), None);
    assert_eq!(scan.custom_scan_input(), None);
    assert_eq!(scan.game_version_selection(), GameVersionSelection::Auto);
    assert_eq!(scan.max_concurrent_scans(), 0);
    assert_eq!(
        scan.formid_databases().get("Fallout4").unwrap(),
        &["databases/Fallout4 FormIDs.db"]
    );
    assert_eq!(scan.fcx_mode_origin(), PreferenceOrigin::Document);
    assert_eq!(scan.formid_databases_origin(), PreferenceOrigin::Document);
    assert_eq!(std::fs::read(&path).unwrap(), bytes_before);
    assert_eq!(
        std::fs::metadata(&path).unwrap().modified().unwrap(),
        modified_before
    );
}

#[test]
fn open_alias_only_document_projects_custom_scan_input_without_rewriting_the_alias() {
    let root = tempfile::tempdir().unwrap();
    let path = install_fixture(root.path(), "alias_only.yaml");
    let bytes_before = std::fs::read(&path).unwrap();

    let settings = UserSettings::open(root.path());

    assert_eq!(
        settings.crash_log_scan_settings().custom_scan_input(),
        Some("E:/Alias Crash Logs")
    );
    assert_eq!(
        settings
            .crash_log_scan_settings()
            .custom_scan_input_origin(),
        PreferenceOrigin::Document
    );
    assert!(settings.diagnostics().is_empty());
    assert_eq!(settings.original_bytes(), Some(bytes_before.as_slice()));
    assert_eq!(std::fs::read(path).unwrap(), bytes_before);
}

#[test]
fn open_conflicting_alias_document_prefers_the_valid_canonical_label_with_a_diagnostic() {
    let root = tempfile::tempdir().unwrap();
    let path = install_fixture(root.path(), "canonical_alias_conflict.yaml");
    let bytes_before = std::fs::read(&path).unwrap();

    let settings = UserSettings::open(root.path());

    assert_eq!(
        settings.crash_log_scan_settings().custom_scan_input(),
        Some("D:/Canonical Crash Logs")
    );
    assert_eq!(
        settings
            .diagnostics()
            .iter()
            .map(|diagnostic| diagnostic.code())
            .collect::<Vec<_>>(),
        vec![
            "canonical_alias_conflict_mods_folder",
            "canonical_alias_conflict_custom_scan_folder",
        ]
    );
    assert_eq!(settings.original_bytes(), Some(bytes_before.as_slice()));
    assert_eq!(std::fs::read(path).unwrap(), bytes_before);
}

#[test]
fn open_invalid_known_values_uses_field_safe_fallbacks_and_preserves_original_nodes() {
    let root = tempfile::tempdir().unwrap();
    let path = install_fixture(root.path(), "invalid_known_values.yaml");
    let bytes_before = std::fs::read(&path).unwrap();

    let settings = UserSettings::open(root.path());
    let scan = settings.crash_log_scan_settings();

    assert_eq!(scan.game_version_selection(), GameVersionSelection::Auto);
    assert_eq!(
        scan.game_version_selection_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert!(!scan.move_unsolved_logs());
    assert_eq!(
        scan.move_unsolved_logs_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert_eq!(scan.unsolved_logs_destination(), None);
    assert_eq!(
        scan.unsolved_logs_destination_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert_eq!(scan.custom_scan_input(), None);
    assert_eq!(
        scan.custom_scan_input_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert_eq!(scan.max_concurrent_scans(), 0);
    assert_eq!(
        scan.max_concurrent_scans_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert!(scan.formid_databases().is_empty());
    assert_eq!(
        scan.formid_databases_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert_eq!(
        settings
            .diagnostics()
            .iter()
            .map(|diagnostic| diagnostic.code())
            .collect::<Vec<_>>(),
        vec![
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
    );
    assert_eq!(settings.original_bytes(), Some(bytes_before.as_slice()));
    assert_eq!(std::fs::read(path).unwrap(), bytes_before);
}

#[test]
fn invalid_canonical_custom_scan_path_falls_back_to_a_valid_alias() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("CLASSIC Settings.yaml");
    let content = b"schema_version: \"1.0\"\nCLASSIC_Settings:\n  SCAN Custom Path: relative/logs\n  Custom Scan Folder: E:/Alias Crash Logs\n";
    std::fs::write(&path, content).unwrap();

    let settings = UserSettings::open(root.path());

    assert_eq!(
        settings.crash_log_scan_settings().custom_scan_input(),
        Some("E:/Alias Crash Logs")
    );
    assert_eq!(
        settings
            .diagnostics()
            .iter()
            .map(|diagnostic| diagnostic.code())
            .collect::<Vec<_>>(),
        vec!["invalid_path_custom_scan_input"]
    );
    assert_eq!(std::fs::read(path).unwrap(), content);
}

#[test]
fn legacy_flat_relative_custom_scan_path_uses_the_same_safe_fallback() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("CLASSIC Settings.yaml");
    let content = b"fcx_mode: false\npaths:\n  scan_custom: relative/logs\n";
    std::fs::write(&path, content).unwrap();

    let settings = UserSettings::open(root.path());

    assert_eq!(settings.crash_log_scan_settings().custom_scan_input(), None);
    assert_eq!(
        settings
            .crash_log_scan_settings()
            .custom_scan_input_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert_eq!(
        settings
            .diagnostics()
            .iter()
            .map(|diagnostic| diagnostic.code())
            .collect::<Vec<_>>(),
        vec![
            "migration_required_flat_classic_config",
            "invalid_path_custom_scan_input",
        ]
    );
    assert_eq!(std::fs::read(path).unwrap(), content);
}

#[test]
fn missing_and_untrusted_documents_use_distinct_scan_defaults_and_safety_fallbacks() {
    let missing_root = tempfile::tempdir().unwrap();
    let malformed_root = tempfile::tempdir().unwrap();
    install_fixture(malformed_root.path(), "malformed.yaml");

    let missing = UserSettings::open(missing_root.path());
    let malformed = UserSettings::open(malformed_root.path());

    assert!(missing.crash_log_scan_settings().move_unsolved_logs());
    assert_eq!(
        missing
            .crash_log_scan_settings()
            .move_unsolved_logs_origin(),
        PreferenceOrigin::Default
    );
    assert!(!malformed.crash_log_scan_settings().move_unsolved_logs());
    assert_eq!(
        malformed
            .crash_log_scan_settings()
            .move_unsolved_logs_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert!(!malformed.crash_log_scan_settings().fcx_mode());
    assert!(!malformed.crash_log_scan_settings().formid_value_lookup());
    assert!(
        malformed
            .crash_log_scan_settings()
            .formid_databases()
            .is_empty()
    );
    assert!(!missing_root.path().join("CLASSIC Settings.yaml").exists());
}
