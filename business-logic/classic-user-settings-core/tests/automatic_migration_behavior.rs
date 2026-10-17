//! Behavioral checks for the silent startup migration of User Settings.

use classic_user_settings_core::{
    AutomaticMigrationOutcome, CommitEligibility, SourceLocation, UserSettings, migrate_if_required,
};
use std::path::{Path, PathBuf};

/// Returns one checked-in User Settings compatibility fixture.
fn fixture_path(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join("tests/fixtures/user_settings_compatibility")
        .join(name)
}

/// Installs a compatibility fixture at one root-relative source location.
fn install_fixture(root: &Path, relative_path: &Path, fixture: &str) -> PathBuf {
    let destination = root.join(relative_path);
    std::fs::create_dir_all(destination.parent().expect("fixture must have a parent")).unwrap();
    std::fs::copy(fixture_path(fixture), &destination).unwrap();
    destination
}

#[test]
fn flat_document_is_migrated_in_place_with_a_verified_backup() {
    let root = tempfile::tempdir().unwrap();
    let settings_path = install_fixture(
        root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "flat_classic_config.yaml",
    );
    let original = std::fs::read(&settings_path).unwrap();

    let AutomaticMigrationOutcome::Applied(receipt) = migrate_if_required(root.path()) else {
        panic!("a flat document requires and supports migration");
    };

    assert_eq!(std::fs::read(receipt.backup_path()).unwrap(), original);
    let reopened = UserSettings::open(root.path());
    assert_eq!(reopened.commit_eligibility(), CommitEligibility::Eligible);
    assert_eq!(reopened.revision(), receipt.published_revision());
}

#[test]
fn previous_location_document_moves_to_the_canonical_location() {
    let root = tempfile::tempdir().unwrap();
    let legacy_path = install_fixture(
        root.path(),
        Path::new("CLASSIC Data/CLASSIC Settings.yaml"),
        "previous_location_nested.yaml",
    );
    let original = std::fs::read(&legacy_path).unwrap();

    let AutomaticMigrationOutcome::Applied(receipt) = migrate_if_required(root.path()) else {
        panic!("a previous-location document requires and supports migration");
    };

    assert!(root.path().join("CLASSIC Settings.yaml").exists());
    assert_eq!(std::fs::read(receipt.backup_path()).unwrap(), original);
    let reopened = UserSettings::open(root.path());
    assert_eq!(reopened.source().location(), SourceLocation::Canonical);
    assert_eq!(reopened.commit_eligibility(), CommitEligibility::Eligible);
}

#[test]
fn a_second_startup_has_nothing_left_to_migrate() {
    let root = tempfile::tempdir().unwrap();
    install_fixture(
        root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "flat_classic_config.yaml",
    );
    assert!(matches!(
        migrate_if_required(root.path()),
        AutomaticMigrationOutcome::Applied(_)
    ));

    assert_eq!(
        migrate_if_required(root.path()),
        AutomaticMigrationOutcome::NotRequired
    );
}

#[test]
fn missing_document_is_not_created() {
    let root = tempfile::tempdir().unwrap();

    assert_eq!(
        migrate_if_required(root.path()),
        AutomaticMigrationOutcome::NotRequired
    );
    assert!(!root.path().join("CLASSIC Settings.yaml").exists());
    assert!(!root.path().join("CLASSIC Backup").exists());
}

#[test]
fn documents_without_a_migration_requirement_are_left_byte_for_byte() {
    // `alias_only.yaml` is current but has an optional canonicalization plan; only a
    // requirement may trigger a silent write. `malformed.yaml` is untrusted, not migratable.
    for fixture in [
        "canonical_current_nested.yaml",
        "alias_only.yaml",
        "malformed.yaml",
    ] {
        let root = tempfile::tempdir().unwrap();
        let settings_path =
            install_fixture(root.path(), Path::new("CLASSIC Settings.yaml"), fixture);
        let original = std::fs::read(&settings_path).unwrap();

        assert_eq!(
            migrate_if_required(root.path()),
            AutomaticMigrationOutcome::NotRequired,
            "{fixture}"
        );
        assert_eq!(
            std::fs::read(&settings_path).unwrap(),
            original,
            "{fixture}"
        );
        assert!(!root.path().join("CLASSIC Backup").exists(), "{fixture}");
    }
}
