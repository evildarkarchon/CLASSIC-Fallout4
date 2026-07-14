//! Behavioral checks for deterministic, side-effect-free User Settings migration planning.

use classic_settings_core::parse_yaml_content;
use classic_user_settings_core::{
    CURRENT_USER_SETTINGS_SCHEMA_VERSION, MigrationChangeKind, MigrationPlanningOutcome,
    SourceLocation, UserSettings, UserSettingsSchemaVersion,
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
    let content = std::str::from_utf8(bytes).expect("planned YAML must be UTF-8");
    let mut documents = parse_yaml_content(label, content).expect("planned YAML must parse");
    assert_eq!(documents.len(), 1, "planned YAML must contain one document");
    documents.remove(0)
}

#[test]
fn current_schema_version_exposes_explicit_major_and_minor_components() {
    assert_eq!(
        CURRENT_USER_SETTINGS_SCHEMA_VERSION,
        UserSettingsSchemaVersion::new(1, 0)
    );
    assert_eq!(CURRENT_USER_SETTINGS_SCHEMA_VERSION.major(), 1);
    assert_eq!(CURRENT_USER_SETTINGS_SCHEMA_VERSION.minor(), 0);
}

#[test]
fn flat_classic_config_plans_the_golden_canonical_document_and_reverses_in_memory() {
    let root = tempfile::tempdir().unwrap();
    let path = install_fixture(
        root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "flat_classic_config.yaml",
    );
    let original = std::fs::read(&path).unwrap();
    let settings = UserSettings::open(root.path());

    let first = settings.plan_migration();
    let second = settings.plan_migration();
    assert_eq!(first, second, "repeated planning must be byte-stable");
    let MigrationPlanningOutcome::Planned(plan) = first else {
        panic!("the supported flat ClassicConfig shape must produce a plan");
    };

    assert!(plan.required());
    assert_eq!(plan.source().location(), SourceLocation::Canonical);
    assert_eq!(plan.source().schema_version(), None);
    assert_eq!(plan.target().location(), SourceLocation::Canonical);
    assert_eq!(
        plan.target().schema_version(),
        Some(CURRENT_USER_SETTINGS_SCHEMA_VERSION)
    );
    assert_eq!(plan.original_bytes(), original);
    assert_eq!(plan.base_revision(), settings.revision());
    assert_eq!(
        parse_one("planned flat migration", plan.proposed_bytes()),
        parse_one(
            "golden flat migration",
            &std::fs::read(fixture_path("flat_migrated.yaml")).unwrap()
        )
    );
    assert!(
        plan.changes()
            .iter()
            .any(|change| change.kind() == MigrationChangeKind::SchemaVersionTransition)
    );
    assert!(plan.changes().iter().any(|change| {
        change.source_path() == Some("/update_check")
            && change.target_path() == Some("/CLASSIC_Settings/Update Check")
    }));

    let reversed = plan.reverse_in_memory();
    assert_eq!(reversed.original_bytes(), plan.proposed_bytes());
    assert_eq!(reversed.proposed_bytes(), plan.original_bytes());
    assert_eq!(reversed.source(), plan.target());
    assert_eq!(reversed.target(), plan.source());
    assert_ne!(
        reversed.base_revision(),
        plan.base_revision(),
        "the inverse must be anchored to the proposed bytes it would restore from"
    );
    assert_eq!(reversed.reverse_in_memory(), plan);
}

#[test]
fn unversioned_legacy_location_plans_both_version_and_location_transitions() {
    let root = tempfile::tempdir().unwrap();
    install_fixture(
        root.path(),
        Path::new("CLASSIC Data/CLASSIC Settings.yaml"),
        "previous_location_nested.yaml",
    );
    let settings = UserSettings::open(root.path());

    let MigrationPlanningOutcome::Planned(plan) = settings.plan_migration() else {
        panic!("the supported previous location must produce a plan");
    };

    assert!(plan.required());
    assert_eq!(plan.source().location(), SourceLocation::Legacy);
    assert_eq!(plan.source().schema_version(), None);
    assert_eq!(plan.target().location(), SourceLocation::Canonical);
    assert_eq!(
        plan.target().schema_version(),
        Some(CURRENT_USER_SETTINGS_SCHEMA_VERSION)
    );
    assert!(plan.changes().iter().any(|change| {
        change.kind() == MigrationChangeKind::LocationTransition
            && change.source_path() == Some("CLASSIC Data/CLASSIC Settings.yaml")
            && change.target_path() == Some("CLASSIC Settings.yaml")
    }));
    assert!(plan.changes().iter().any(|change| {
        change.kind() == MigrationChangeKind::SchemaVersionTransition
            && change.source_path().is_none()
            && change.target_path() == Some("/schema_version")
    }));
}

#[test]
fn explicit_alias_plan_is_optional_and_removes_aliases_without_touching_disk() {
    let root = tempfile::tempdir().unwrap();
    let path = install_fixture(
        root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "canonical_alias_conflict.yaml",
    );
    let original = std::fs::read(&path).unwrap();
    let modified_before = std::fs::metadata(&path).unwrap().modified().unwrap();
    let entries_before = std::fs::read_dir(root.path()).unwrap().count();
    let settings = UserSettings::open(root.path());

    let MigrationPlanningOutcome::Planned(plan) = settings.plan_migration() else {
        panic!("known aliases must produce an explicit canonicalization plan");
    };

    assert!(!plan.required());
    assert!(plan.changes().iter().all(|change| {
        change.kind() == MigrationChangeKind::AliasCanonicalization
            || change.kind() == MigrationChangeKind::KnownValueCanonicalization
    }));
    let proposed = parse_one("alias migration", plan.proposed_bytes());
    assert_eq!(
        proposed["CLASSIC_Settings"]["MODS Folder Path"].as_str(),
        Some("D:/Canonical Mods")
    );
    assert!(matches!(
        proposed["CLASSIC_Settings"]["Staging Mods Folder"],
        classic_settings_core::Yaml::BadValue
    ));
    assert_eq!(
        proposed["CLASSIC_Settings"]["SCAN Custom Path"].as_str(),
        Some("D:/Canonical Crash Logs")
    );
    assert!(matches!(
        proposed["CLASSIC_Settings"]["Custom Scan Folder"],
        classic_settings_core::Yaml::BadValue
    ));
    assert_eq!(std::fs::read(&path).unwrap(), original);
    assert_eq!(
        std::fs::metadata(&path).unwrap().modified().unwrap(),
        modified_before
    );
    assert_eq!(
        std::fs::read_dir(root.path()).unwrap().count(),
        entries_before
    );
    assert!(!root.path().join("CLASSIC Settings.yaml.bak").exists());
}

#[test]
fn alias_only_current_document_has_an_optional_reviewable_plan() {
    let root = tempfile::tempdir().unwrap();
    install_fixture(
        root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "alias_only.yaml",
    );

    let MigrationPlanningOutcome::Planned(plan) = UserSettings::open(root.path()).plan_migration()
    else {
        panic!("the known alias form must be covered by planning");
    };

    assert!(!plan.required());
    assert_eq!(plan.changes().len(), 1);
    assert_eq!(
        plan.changes()[0].kind(),
        MigrationChangeKind::AliasCanonicalization
    );
}

#[test]
fn alias_plan_promotes_the_typed_fallback_when_the_canonical_value_is_invalid() {
    let root = tempfile::tempdir().unwrap();
    std::fs::write(
        root.path().join("CLASSIC Settings.yaml"),
        b"schema_version: \"1.0\"\nCLASSIC_Settings:\n  SCAN Custom Path: relative/logs\n  Custom Scan Folder: E:/Alias Crash Logs\n",
    )
    .unwrap();

    let MigrationPlanningOutcome::Planned(plan) = UserSettings::open(root.path()).plan_migration()
    else {
        panic!("the valid alias fallback must produce a canonicalization plan");
    };
    let proposed = parse_one("fallback alias migration", plan.proposed_bytes());

    assert_eq!(
        proposed["CLASSIC_Settings"]["SCAN Custom Path"].as_str(),
        Some("E:/Alias Crash Logs")
    );
    assert!(matches!(
        proposed["CLASSIC_Settings"]["Custom Scan Folder"],
        classic_settings_core::Yaml::BadValue
    ));
}

#[test]
fn current_and_same_major_newer_documents_need_no_migration_or_downgrade() {
    let current_root = tempfile::tempdir().unwrap();
    install_fixture(
        current_root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "canonical_current_nested.yaml",
    );
    assert_eq!(
        UserSettings::open(current_root.path()).plan_migration(),
        MigrationPlanningOutcome::NotRequired
    );

    let newer_root = tempfile::tempdir().unwrap();
    std::fs::write(
        newer_root.path().join("CLASSIC Settings.yaml"),
        b"schema_version: \"1.7\"\nCLASSIC_Settings:\n  Update Check: true\nFuture:\n  additive: value\n",
    )
    .unwrap();
    assert_eq!(
        UserSettings::open(newer_root.path()).plan_migration(),
        MigrationPlanningOutcome::NotRequired
    );
}

#[test]
fn unsupported_version_gap_and_future_major_return_structured_diagnostics() {
    for (version, expected_code) in [
        ("0.9", "unsupported_schema_version_gap"),
        ("99.0", "future_major_schema_read_only"),
    ] {
        let root = tempfile::tempdir().unwrap();
        std::fs::write(
            root.path().join("CLASSIC Settings.yaml"),
            format!("schema_version: \"{version}\"\nCLASSIC_Settings:\n  Update Check: true\n"),
        )
        .unwrap();

        let MigrationPlanningOutcome::Unsupported(diagnostics) =
            UserSettings::open(root.path()).plan_migration()
        else {
            panic!("schema {version} must remain read-only and unsupported");
        };
        assert_eq!(diagnostics.len(), 1);
        assert_eq!(diagnostics[0].code(), expected_code);
        assert!(!root.path().join("CLASSIC Settings.yaml.bak").exists());
    }
}

#[test]
fn missing_and_untrusted_documents_do_not_produce_migration_plans() {
    let missing_root = tempfile::tempdir().unwrap();
    assert_eq!(
        UserSettings::open(missing_root.path()).plan_migration(),
        MigrationPlanningOutcome::NotRequired
    );

    let malformed_root = tempfile::tempdir().unwrap();
    install_fixture(
        malformed_root.path(),
        Path::new("CLASSIC Settings.yaml"),
        "malformed.yaml",
    );
    let MigrationPlanningOutcome::Unsupported(diagnostics) =
        UserSettings::open(malformed_root.path()).plan_migration()
    else {
        panic!("untrusted input must not produce proposed bytes");
    };
    assert_eq!(diagnostics[0].code(), "migration_source_untrusted");
}
