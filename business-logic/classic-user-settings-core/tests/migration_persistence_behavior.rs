//! Behavioral checks for explicit, conflict-safe User Settings migration persistence.

use classic_settings_core::parse_yaml_content;
use classic_user_settings_core::{
    MigrationPlanningOutcome, UserSettings, UserSettingsMigrationApplyOutcome,
    UserSettingsMigrationRestoreOutcome,
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

/// Parses one YAML document so semantic equality is independent of emitter formatting.
fn parse_one(label: &str, bytes: &[u8]) -> classic_settings_core::Yaml {
    let content = std::str::from_utf8(bytes).expect("User Settings YAML must be UTF-8");
    let mut documents = parse_yaml_content(label, content).expect("User Settings YAML must parse");
    assert_eq!(documents.len(), 1, "expected exactly one YAML document");
    documents.remove(0)
}

#[test]
fn explicit_flat_migration_retains_verified_backup_and_reports_reopened_publication() {
    let root = tempfile::tempdir().unwrap();
    let source_path = install_fixture(
        root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "flat_classic_config.yaml",
    );
    let original = std::fs::read(&source_path).unwrap();
    let settings = UserSettings::open(root.path());
    let MigrationPlanningOutcome::Planned(plan) = settings.plan_migration() else {
        panic!("the supported flat shape must produce a migration plan");
    };

    let UserSettingsMigrationApplyOutcome::Applied(receipt) = plan.apply(root.path()).unwrap()
    else {
        panic!("an unchanged approved plan must apply");
    };

    assert_eq!(receipt.source_path(), source_path);
    assert_eq!(receipt.destination_path(), source_path);
    assert_eq!(receipt.source(), plan.source());
    assert_eq!(receipt.target(), plan.target());
    assert_eq!(std::fs::read(receipt.backup_path()).unwrap(), original);
    assert_eq!(receipt.backup_revision(), plan.base_revision());

    let published = std::fs::read(receipt.destination_path()).unwrap();
    assert_eq!(
        parse_one("applied flat migration", &published),
        parse_one(
            "golden flat migration",
            &std::fs::read(fixture_path("flat_migrated.yaml")).unwrap(),
        )
    );
    let reopened = UserSettings::open(root.path());
    assert_eq!(reopened.revision(), receipt.published_revision());
    assert_eq!(reopened.original_bytes(), Some(published.as_slice()));
}

#[test]
fn explicit_restore_republishes_verified_backup_byte_for_byte_and_retains_it() {
    let root = tempfile::tempdir().unwrap();
    let settings_path = install_fixture(
        root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "flat_classic_config.yaml",
    );
    let original = std::fs::read(&settings_path).unwrap();
    let MigrationPlanningOutcome::Planned(plan) = UserSettings::open(root.path()).plan_migration()
    else {
        panic!("the supported flat shape must produce a migration plan");
    };
    let UserSettingsMigrationApplyOutcome::Applied(receipt) = plan.apply(root.path()).unwrap()
    else {
        panic!("an unchanged approved plan must apply");
    };
    let backup_path = receipt.backup_path().to_path_buf();

    let UserSettingsMigrationRestoreOutcome::Restored { revision } =
        receipt.restore(root.path()).unwrap()
    else {
        panic!("an unchanged migrated document must restore");
    };

    assert_eq!(std::fs::read(&settings_path).unwrap(), original);
    assert_eq!(std::fs::read(&backup_path).unwrap(), original);
    let reopened = UserSettings::open(root.path());
    assert_eq!(reopened.revision(), &revision);
    assert_eq!(reopened.original_bytes(), Some(original.as_slice()));
}

#[test]
fn legacy_location_restore_reactivates_the_verified_legacy_source() {
    let root = tempfile::tempdir().unwrap();
    let legacy_path = install_fixture(
        root.path(),
        Path::new("CLASSIC Data/CLASSIC Settings.yaml"),
        "previous_location_nested.yaml",
    );
    let original = std::fs::read(&legacy_path).unwrap();
    let MigrationPlanningOutcome::Planned(plan) = UserSettings::open(root.path()).plan_migration()
    else {
        panic!("the supported previous location must produce a migration plan");
    };
    let UserSettingsMigrationApplyOutcome::Applied(receipt) = plan.apply(root.path()).unwrap()
    else {
        panic!("an unchanged approved location migration must apply");
    };
    let canonical_path = root.path().join("CLASSIC Settings.yaml");
    assert!(canonical_path.exists());
    assert_eq!(
        UserSettings::open(root.path()).source().location(),
        receipt.target().location()
    );

    let UserSettingsMigrationRestoreOutcome::Restored { revision } =
        receipt.restore(root.path()).unwrap()
    else {
        panic!("an unchanged location migration must restore");
    };

    assert!(!canonical_path.exists());
    assert_eq!(std::fs::read(&legacy_path).unwrap(), original);
    assert_eq!(std::fs::read(receipt.backup_path()).unwrap(), original);
    let reopened = UserSettings::open(root.path());
    assert_eq!(reopened.source().location(), receipt.source().location());
    assert_eq!(reopened.revision(), &revision);
}

#[test]
fn stale_plan_conflicts_before_backup_or_publication_and_preserves_newer_bytes() {
    let root = tempfile::tempdir().unwrap();
    let settings_path = install_fixture(
        root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "flat_classic_config.yaml",
    );
    let MigrationPlanningOutcome::Planned(plan) = UserSettings::open(root.path()).plan_migration()
    else {
        panic!("the supported flat shape must produce a migration plan");
    };
    let newer = b"schema_version: \"1.0\"\nCLASSIC_Settings:\n  Update Check: false\nExternal:\n  edit: newer\n";
    std::fs::write(&settings_path, newer).unwrap();

    let outcome = plan.apply(root.path()).unwrap();

    assert!(matches!(
        outcome,
        UserSettingsMigrationApplyOutcome::Conflict { .. }
    ));
    assert_eq!(std::fs::read(&settings_path).unwrap(), newer);
    assert!(
        !root
            .path()
            .join("CLASSIC Backup/User Settings/Migrations")
            .exists()
    );
}

#[test]
fn explicit_alias_migration_publishes_only_the_approved_canonicalization_plan() {
    let root = tempfile::tempdir().unwrap();
    let settings_path = install_fixture(
        root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "alias_only.yaml",
    );
    let MigrationPlanningOutcome::Planned(plan) = UserSettings::open(root.path()).plan_migration()
    else {
        panic!("the supported alias must produce a migration plan");
    };
    let approved = plan.proposed_bytes().to_vec();

    let UserSettingsMigrationApplyOutcome::Applied(_) = plan.apply(root.path()).unwrap() else {
        panic!("an unchanged approved alias plan must apply");
    };

    assert_eq!(std::fs::read(settings_path).unwrap(), approved);
}

#[test]
fn stale_restore_conflicts_and_preserves_both_newer_document_and_verified_backup() {
    let root = tempfile::tempdir().unwrap();
    let settings_path = install_fixture(
        root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "flat_classic_config.yaml",
    );
    let MigrationPlanningOutcome::Planned(plan) = UserSettings::open(root.path()).plan_migration()
    else {
        panic!("the supported flat shape must produce a migration plan");
    };
    let UserSettingsMigrationApplyOutcome::Applied(receipt) = plan.apply(root.path()).unwrap()
    else {
        panic!("an unchanged approved plan must apply");
    };
    let backup = std::fs::read(receipt.backup_path()).unwrap();
    let newer = b"schema_version: \"1.0\"\nCLASSIC_Settings:\n  Update Check: true\nExternal:\n  edit: after-migration\n";
    std::fs::write(&settings_path, newer).unwrap();

    let outcome = receipt.restore(root.path()).unwrap();

    assert!(matches!(
        outcome,
        UserSettingsMigrationRestoreOutcome::Conflict { .. }
    ));
    assert_eq!(std::fs::read(settings_path).unwrap(), newer);
    assert_eq!(std::fs::read(receipt.backup_path()).unwrap(), backup);
}

#[test]
fn corrupted_backup_blocks_restore_without_changing_the_migrated_document() {
    let root = tempfile::tempdir().unwrap();
    install_fixture(
        root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "flat_classic_config.yaml",
    );
    let MigrationPlanningOutcome::Planned(plan) = UserSettings::open(root.path()).plan_migration()
    else {
        panic!("the supported flat shape must produce a migration plan");
    };
    let UserSettingsMigrationApplyOutcome::Applied(receipt) = plan.apply(root.path()).unwrap()
    else {
        panic!("an unchanged approved plan must apply");
    };
    let migrated = std::fs::read(receipt.destination_path()).unwrap();
    std::fs::write(receipt.backup_path(), b"corrupted backup").unwrap();

    let error = receipt.restore(root.path()).unwrap_err();

    assert_eq!(error.code(), "migration_restore_backup_verify_failed");
    assert_eq!(std::fs::read(receipt.destination_path()).unwrap(), migrated);
}
