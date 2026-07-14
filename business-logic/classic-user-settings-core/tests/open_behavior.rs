//! Behavioral checks for the public read-only User Settings interface.

use classic_settings_core::parse_yaml_content;
use classic_user_settings_core::{
    CommitEligibility, DocumentClassification, PreferenceOrigin, Revision, SourceLocation,
    UpdateSource, UserSettings,
};
use std::path::{Path, PathBuf};

/// Returns a checked-in compatibility fixture through the repository root.
fn fixture_path(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join("tests/fixtures/user_settings_compatibility")
        .join(name)
}

#[test]
fn open_missing_document_uses_published_defaults_without_creating_files() {
    let root = tempfile::tempdir().unwrap();

    let settings = UserSettings::open(root.path());

    assert_eq!(settings.source().location(), SourceLocation::Missing);
    assert_eq!(settings.source().path(), None);
    assert_eq!(settings.classification(), DocumentClassification::Missing);
    assert!(settings.update_preferences().update_check());
    assert_eq!(
        settings.update_preferences().update_check_origin(),
        PreferenceOrigin::Default
    );
    assert_eq!(settings.revision(), &Revision::Missing);
    assert_eq!(settings.original_bytes(), None);
    assert_eq!(settings.commit_eligibility(), CommitEligibility::Eligible);
    assert!(settings.diagnostics().is_empty());
    assert!(!root.path().join("CLASSIC Settings.yaml").exists());
    assert!(!root.path().join("CLASSIC Data").exists());
}

#[test]
fn published_defaults_match_the_missing_projection_without_filesystem_access() {
    let defaults = UserSettings::published_defaults();

    assert_eq!(defaults.source().location(), SourceLocation::Missing);
    assert_eq!(defaults.classification(), DocumentClassification::Missing);
    assert_eq!(defaults.revision(), &Revision::Missing);
    assert!(defaults.update_preferences().update_check());
    assert_eq!(
        defaults.update_preferences().update_source(),
        UpdateSource::GitHub
    );
    assert!(defaults.crash_log_scan_settings().move_unsolved_logs());
    assert!(
        defaults
            .frontend_state()
            .preferences()
            .auto_switch_after_scan()
    );
    assert_eq!(defaults.commit_eligibility(), CommitEligibility::Eligible);
}

#[test]
fn canonical_update_source_is_exposed_as_a_typed_preference() {
    let root = tempfile::tempdir().unwrap();
    install_fixture(
        root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "canonical_current_nested.yaml",
    );

    let settings = UserSettings::open(root.path());

    assert_eq!(
        settings.update_preferences().update_source(),
        UpdateSource::GitHub
    );
    assert_eq!(
        settings.update_preferences().update_source_origin(),
        PreferenceOrigin::Document
    );
}

#[test]
fn open_legacy_location_reads_typed_preferences_without_moving_the_document() {
    let root = tempfile::tempdir().unwrap();
    let path = install_fixture(
        root.path(),
        Path::new("CLASSIC Data/CLASSIC Settings.yaml"),
        "previous_location_nested.yaml",
    );
    let bytes_before = std::fs::read(&path).unwrap();
    let modified_before = std::fs::metadata(&path).unwrap().modified().unwrap();

    let settings = UserSettings::open(root.path());

    assert_eq!(settings.source().location(), SourceLocation::Legacy);
    assert_eq!(settings.source().path(), Some(path.as_path()));
    assert_eq!(
        settings.classification(),
        DocumentClassification::Unversioned
    );
    assert!(!settings.update_preferences().update_check());
    assert_eq!(
        settings.update_preferences().update_check_origin(),
        PreferenceOrigin::Document
    );
    assert_eq!(
        settings.commit_eligibility(),
        CommitEligibility::RequiresMigration
    );
    assert_eq!(
        settings
            .diagnostics()
            .iter()
            .map(|diagnostic| diagnostic.code())
            .collect::<Vec<_>>(),
        vec!["migration_required_previous_location"]
    );
    assert_eq!(settings.original_bytes(), Some(bytes_before.as_slice()));
    assert!(!root.path().join("CLASSIC Settings.yaml").exists());
    assert_eq!(std::fs::read(&path).unwrap(), bytes_before);
    assert_eq!(
        std::fs::metadata(&path).unwrap().modified().unwrap(),
        modified_before
    );
}

#[test]
fn open_malformed_document_returns_a_fail_closed_read_only_view() {
    let root = tempfile::tempdir().unwrap();
    let path = install_fixture(
        root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "malformed.yaml",
    );
    let bytes_before = std::fs::read(&path).unwrap();
    let modified_before = std::fs::metadata(&path).unwrap().modified().unwrap();

    let settings = UserSettings::open(root.path());

    assert_eq!(settings.source().location(), SourceLocation::Canonical);
    assert_eq!(settings.classification(), DocumentClassification::Malformed);
    assert!(!settings.update_preferences().update_check());
    assert_eq!(
        settings.update_preferences().update_check_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert_eq!(
        settings.commit_eligibility(),
        CommitEligibility::BlockedUntrusted
    );
    assert_eq!(
        settings
            .diagnostics()
            .iter()
            .map(|diagnostic| diagnostic.code())
            .collect::<Vec<_>>(),
        vec!["malformed_document", "commit_blocked_untrusted_document"]
    );
    assert_eq!(settings.original_bytes(), Some(bytes_before.as_slice()));
    assert!(matches!(settings.revision(), Revision::ContentSha256(_)));
    assert_eq!(std::fs::read(&path).unwrap(), bytes_before);
    assert_eq!(
        std::fs::metadata(&path).unwrap().modified().unwrap(),
        modified_before
    );
}

#[test]
fn open_invalid_known_values_fall_back_safely_without_blocking_later_updates() {
    let root = tempfile::tempdir().unwrap();
    let path = install_fixture(
        root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "invalid_known_values.yaml",
    );
    let bytes_before = std::fs::read(&path).unwrap();

    let settings = UserSettings::open(root.path());

    assert_eq!(settings.classification(), DocumentClassification::Current);
    assert!(!settings.update_preferences().update_check());
    assert_eq!(
        settings.update_preferences().update_check_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert_eq!(settings.commit_eligibility(), CommitEligibility::Eligible);
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
    assert_eq!(std::fs::read(&path).unwrap(), bytes_before);
}

#[test]
fn open_future_major_document_blocks_commits_and_update_checks() {
    let root = tempfile::tempdir().unwrap();
    let path = install_fixture(
        root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "newer_major_schema.yaml",
    );
    let bytes_before = std::fs::read(&path).unwrap();

    let settings = UserSettings::open(root.path());

    assert_eq!(
        settings.classification(),
        DocumentClassification::FutureMajor
    );
    assert!(!settings.update_preferences().update_check());
    assert_eq!(
        settings.update_preferences().update_check_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert_eq!(
        settings.commit_eligibility(),
        CommitEligibility::BlockedUntrusted
    );
    assert_eq!(
        settings
            .diagnostics()
            .iter()
            .map(|diagnostic| diagnostic.code())
            .collect::<Vec<_>>(),
        vec![
            "unsupported_future_major_schema",
            "commit_blocked_untrusted_document"
        ]
    );
    assert_eq!(settings.original_bytes(), Some(bytes_before.as_slice()));
    assert_eq!(std::fs::read(&path).unwrap(), bytes_before);
}

#[test]
fn open_older_schema_returns_a_degraded_incompatible_view() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("CLASSIC Settings.yaml");
    let content = b"schema_version: \"0.9\"\nCLASSIC_Settings:\n  Update Check: true\n";
    std::fs::write(&path, content).unwrap();

    let settings = UserSettings::open(root.path());

    assert_eq!(settings.classification(), DocumentClassification::Older);
    assert_eq!(settings.schema_version(), Some((0, 9)));
    assert!(!settings.update_preferences().update_check());
    assert_eq!(
        settings.commit_eligibility(),
        CommitEligibility::BlockedUntrusted
    );
    assert_eq!(
        settings
            .diagnostics()
            .iter()
            .map(|diagnostic| diagnostic.code())
            .collect::<Vec<_>>(),
        vec![
            "unsupported_older_schema",
            "commit_blocked_untrusted_document"
        ]
    );
    assert_eq!(settings.original_bytes(), Some(content.as_slice()));
    assert_eq!(std::fs::read(path).unwrap(), content);
}

#[test]
fn open_flat_legacy_document_projects_update_preferences_without_rewriting() {
    let root = tempfile::tempdir().unwrap();
    let path = install_fixture(
        root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "flat_classic_config.yaml",
    );
    let bytes_before = std::fs::read(&path).unwrap();

    let settings = UserSettings::open(root.path());

    assert_eq!(
        settings.classification(),
        DocumentClassification::LegacyFlat
    );
    assert!(!settings.update_preferences().update_check());
    assert_eq!(
        settings.update_preferences().update_check_origin(),
        PreferenceOrigin::Document
    );
    assert_eq!(
        settings.commit_eligibility(),
        CommitEligibility::RequiresMigration
    );
    assert_eq!(
        settings
            .diagnostics()
            .iter()
            .map(|diagnostic| diagnostic.code())
            .collect::<Vec<_>>(),
        vec!["migration_required_flat_classic_config"]
    );
    assert_eq!(settings.original_bytes(), Some(bytes_before.as_slice()));
    assert_eq!(std::fs::read(path).unwrap(), bytes_before);
}

#[test]
fn canonical_source_wins_even_when_a_valid_legacy_document_exists() {
    let root = tempfile::tempdir().unwrap();
    let canonical = install_fixture(
        root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "malformed.yaml",
    );
    let legacy = install_fixture(
        root.path(),
        Path::new("CLASSIC Data/CLASSIC Settings.yaml"),
        "previous_location_nested.yaml",
    );
    let canonical_before = std::fs::read(&canonical).unwrap();
    let legacy_before = std::fs::read(&legacy).unwrap();

    let settings = UserSettings::open(root.path());

    assert_eq!(settings.source().location(), SourceLocation::Canonical);
    assert_eq!(settings.source().path(), Some(canonical.as_path()));
    assert_eq!(settings.classification(), DocumentClassification::Malformed);
    assert!(!settings.update_preferences().update_check());
    assert_eq!(std::fs::read(canonical).unwrap(), canonical_before);
    assert_eq!(std::fs::read(legacy).unwrap(), legacy_before);
}

#[test]
fn open_unversioned_canonical_document_requires_migration_but_reads_known_values() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("CLASSIC Settings.yaml");
    let content = b"CLASSIC_Settings:\n  Update Check: false\n";
    std::fs::write(&path, content).unwrap();

    let settings = UserSettings::open(root.path());

    assert_eq!(
        settings.classification(),
        DocumentClassification::Unversioned
    );
    assert_eq!(settings.schema_version(), None);
    assert!(!settings.update_preferences().update_check());
    assert_eq!(
        settings.commit_eligibility(),
        CommitEligibility::RequiresMigration
    );
    assert_eq!(
        settings.diagnostics()[0].code(),
        "migration_required_unversioned_document"
    );
    assert_eq!(std::fs::read(path).unwrap(), content);
}

#[test]
fn open_same_major_newer_document_accepts_additive_schema_content() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("CLASSIC Settings.yaml");
    let content = b"schema_version: \"1.7\"\nCLASSIC_Settings:\n  Update Check: true\nFuture:\n  additive: value\n";
    std::fs::write(&path, content).unwrap();

    let settings = UserSettings::open(root.path());

    assert_eq!(
        settings.classification(),
        DocumentClassification::NewerCompatible
    );
    assert_eq!(settings.schema_version(), Some((1, 7)));
    assert!(settings.update_preferences().update_check());
    assert_eq!(settings.commit_eligibility(), CommitEligibility::Eligible);
    assert!(settings.diagnostics().is_empty());
    assert_eq!(settings.original_bytes(), Some(content.as_slice()));
    assert_eq!(std::fs::read(path).unwrap(), content);
}

#[test]
fn open_retains_unknown_entries_for_later_semantic_preservation() {
    let root = tempfile::tempdir().unwrap();
    let path = install_fixture(
        root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "unknown_entries.yaml",
    );
    let bytes_before = std::fs::read(&path).unwrap();

    let settings = UserSettings::open(root.path());

    let retained = std::str::from_utf8(settings.original_bytes().unwrap()).unwrap();
    let documents = parse_yaml_content("retained User Settings", retained).unwrap();
    assert_eq!(
        documents[0]["ThirdPartyPlugin"]["enabled"].as_bool(),
        Some(true)
    );
    assert_eq!(
        documents[0]["ThirdPartyPlugin"]["retry_count"].as_i64(),
        Some(3)
    );
    assert_eq!(
        documents[0]["ThirdPartyPlugin"]["tags"][1].as_str(),
        Some("beta")
    );
    assert_eq!(
        documents[0]["CLASSIC_Settings"]["Future Scan Knob"]["weight"].as_i64(),
        Some(7)
    );
    assert_eq!(settings.original_bytes(), Some(bytes_before.as_slice()));
    assert_eq!(std::fs::read(path).unwrap(), bytes_before);
}

#[test]
fn revisions_are_stable_for_equal_content_and_change_after_an_external_edit() {
    let first_root = tempfile::tempdir().unwrap();
    let second_root = tempfile::tempdir().unwrap();
    let first_path = install_fixture(
        first_root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "canonical_current_nested.yaml",
    );
    install_fixture(
        second_root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "canonical_current_nested.yaml",
    );

    let first = UserSettings::open(first_root.path());
    let equal_content = UserSettings::open(second_root.path());
    assert_eq!(first.revision(), equal_content.revision());

    std::fs::write(
        &first_path,
        b"schema_version: \"1.0\"\nCLASSIC_Settings:\n  Update Check: false\n",
    )
    .unwrap();
    let externally_edited = UserSettings::open(first_root.path());
    assert_ne!(first.revision(), externally_edited.revision());
}

#[test]
fn absent_update_check_uses_the_published_default_but_null_fails_closed() {
    let absent_root = tempfile::tempdir().unwrap();
    std::fs::write(
        absent_root.path().join("CLASSIC Settings.yaml"),
        b"schema_version: \"1.0\"\nCLASSIC_Settings:\n  FCX Mode: false\n",
    )
    .unwrap();
    let null_root = tempfile::tempdir().unwrap();
    std::fs::write(
        null_root.path().join("CLASSIC Settings.yaml"),
        b"schema_version: \"1.0\"\nCLASSIC_Settings:\n  Update Check: null\n",
    )
    .unwrap();

    let absent = UserSettings::open(absent_root.path());
    let null = UserSettings::open(null_root.path());

    assert!(absent.update_preferences().update_check());
    assert_eq!(
        absent.update_preferences().update_check_origin(),
        PreferenceOrigin::Default
    );
    assert!(!null.update_preferences().update_check());
    assert_eq!(
        null.update_preferences().update_check_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert_eq!(null.diagnostics()[0].code(), "invalid_type_update_check");
}

#[test]
fn unreadable_selected_source_returns_a_degraded_view_without_falling_back() {
    let root = tempfile::tempdir().unwrap();
    std::fs::create_dir(root.path().join("CLASSIC Settings.yaml")).unwrap();
    install_fixture(
        root.path(),
        Path::new("CLASSIC Data/CLASSIC Settings.yaml"),
        "previous_location_nested.yaml",
    );

    let settings = UserSettings::open(root.path());

    assert_eq!(settings.source().location(), SourceLocation::Canonical);
    assert_eq!(settings.classification(), DocumentClassification::Malformed);
    assert_eq!(settings.revision(), &Revision::Unavailable);
    assert!(!settings.update_preferences().update_check());
    assert_eq!(
        settings
            .diagnostics()
            .iter()
            .map(|diagnostic| diagnostic.code())
            .collect::<Vec<_>>(),
        vec!["unreadable_document", "commit_blocked_untrusted_document"]
    );
}

#[test]
fn unrecognized_or_structurally_invalid_documents_fail_closed() {
    for content in ["arbitrary: yaml\n", "42\n", "CLASSIC_Settings: broken\n"] {
        let root = tempfile::tempdir().unwrap();
        let path = root.path().join("CLASSIC Settings.yaml");
        std::fs::write(&path, content).unwrap();

        let settings = UserSettings::open(root.path());

        assert_eq!(
            settings.classification(),
            DocumentClassification::Malformed,
            "content must be structurally untrusted: {content:?}"
        );
        assert!(!settings.update_preferences().update_check());
        assert_eq!(
            settings.commit_eligibility(),
            CommitEligibility::BlockedUntrusted
        );
        assert_eq!(settings.diagnostics()[0].code(), "malformed_document");
        assert_eq!(std::fs::read_to_string(path).unwrap(), content);
    }
}

#[test]
fn present_null_schema_version_is_malformed_instead_of_unversioned() {
    for content in [
        "schema_version: null\nCLASSIC_Settings:\n  Update Check: true\n",
        "schema_version: null\nupdate_check: true\n",
    ] {
        let root = tempfile::tempdir().unwrap();
        let path = root.path().join("CLASSIC Settings.yaml");
        std::fs::write(&path, content).unwrap();

        let settings = UserSettings::open(root.path());

        assert_eq!(settings.classification(), DocumentClassification::Malformed);
        assert!(!settings.update_preferences().update_check());
        assert_eq!(
            settings.commit_eligibility(),
            CommitEligibility::BlockedUntrusted
        );
        assert_eq!(settings.diagnostics()[0].code(), "invalid_schema_version");
        assert_eq!(std::fs::read_to_string(path).unwrap(), content);
    }
}

/// Copies one compatibility fixture to its requested root-relative path.
fn install_fixture(root: &Path, relative_path: &Path, fixture: &str) -> PathBuf {
    let destination = root.join(relative_path);
    std::fs::create_dir_all(destination.parent().expect("fixture must have a parent")).unwrap();
    std::fs::copy(fixture_path(fixture), &destination).unwrap();
    destination
}

#[test]
fn open_current_document_exposes_typed_preferences_without_writing() {
    let root = tempfile::tempdir().unwrap();
    let path = install_fixture(
        root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "canonical_current_nested.yaml",
    );
    let bytes_before = std::fs::read(&path).unwrap();
    let modified_before = std::fs::metadata(&path).unwrap().modified().unwrap();

    let settings = UserSettings::open(root.path());

    assert_eq!(settings.source().location(), SourceLocation::Canonical);
    assert_eq!(settings.classification(), DocumentClassification::Current);
    assert!(settings.update_preferences().update_check());
    assert_eq!(
        settings.update_preferences().update_check_origin(),
        PreferenceOrigin::Document
    );
    assert_eq!(settings.commit_eligibility(), CommitEligibility::Eligible);
    assert!(settings.diagnostics().is_empty());
    assert_eq!(settings.original_bytes(), Some(bytes_before.as_slice()));
    assert!(matches!(settings.revision(), Revision::ContentSha256(_)));
    assert_eq!(std::fs::read(&path).unwrap(), bytes_before);
    assert_eq!(
        std::fs::metadata(&path).unwrap().modified().unwrap(),
        modified_before
    );
}
