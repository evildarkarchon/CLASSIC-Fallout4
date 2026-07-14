//! Behavioral checks for explicit legacy TUI remembered-state imports.

use classic_settings_core::{Yaml, parse_yaml_content};
use classic_user_settings_core::{
    DocumentClassification, LegacyTuiStateImportOutcome, LegacyTuiStateImportRestoreOutcome,
    Revision, UserSettings, import_legacy_tui_state,
};
use std::path::Path;

/// Parses the single YAML document at `path` for semantic assertions.
fn parsed_document(path: &Path) -> Yaml {
    let content = std::fs::read_to_string(path).expect("read User Settings YAML");
    let mut documents =
        parse_yaml_content(path.display().to_string(), &content).expect("parse User Settings YAML");
    assert_eq!(documents.len(), 1);
    documents.remove(0)
}

#[test]
fn explicit_import_updates_current_settings_and_retains_an_exact_content_addressed_backup() {
    let root = tempfile::tempdir().expect("create CLASSIC root");
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    std::fs::write(
        &settings_path,
        br#"schema_version: "1.0"
CLASSIC_Settings:
  Update Check: true
UI:
  tui:
    active_tab: 0
    results_panel_width: 30
    sort_ascending: false
    future_layout: compact
  community_frontend:
    theme: amber
"#,
    )
    .expect("write current User Settings");
    let original_settings = std::fs::read(&settings_path).unwrap();
    let legacy_path = root.path().join("state.json");
    let legacy_bytes = br#"{
  "active_tab": 3,
  "results_panel_width": 0,
  "sort_ascending": true,
  "future_tui_field": {"retained_only_in_backup": true}
}
"#;
    std::fs::write(&legacy_path, legacy_bytes).expect("write legacy TUI state");

    let LegacyTuiStateImportOutcome::Applied(receipt) =
        import_legacy_tui_state(root.path(), &legacy_path).expect("import legacy TUI state")
    else {
        panic!("an unchanged current base and valid legacy source must apply");
    };

    assert_eq!(receipt.source_path(), legacy_path);
    assert_eq!(
        receipt.backup_path().parent(),
        Some(
            root.path()
                .join("CLASSIC Backup/User Settings/TUI State Imports")
                .as_path()
        )
    );
    assert_eq!(
        receipt
            .backup_path()
            .extension()
            .and_then(|value| value.to_str()),
        Some("json")
    );
    assert_eq!(std::fs::read(receipt.backup_path()).unwrap(), legacy_bytes);
    assert_eq!(
        std::fs::read(
            receipt
                .settings_backup_path()
                .expect("current settings base must be backed up")
        )
        .unwrap(),
        original_settings
    );
    assert_eq!(std::fs::read(&legacy_path).unwrap(), legacy_bytes);
    assert_eq!(receipt.source_revision(), receipt.backup_revision());

    let current = UserSettings::open(root.path());
    assert_eq!(current.revision(), receipt.published_settings_revision());
    let tui = current.frontend_state().tui();
    assert_eq!(tui.active_tab(), 3);
    assert_eq!(tui.results_panel_width(), 0);
    assert!(tui.sort_ascending());
    let document = parsed_document(&settings_path);
    assert_eq!(
        document["UI"]["tui"]["future_layout"],
        Yaml::String("compact".to_string())
    );
    assert_eq!(
        document["UI"]["community_frontend"]["theme"],
        Yaml::String("amber".to_string())
    );

    let LegacyTuiStateImportRestoreOutcome::Restored { revision } =
        receipt.restore(root.path()).expect("restore import")
    else {
        panic!("an unchanged import must restore");
    };
    assert_eq!(&revision, receipt.base_settings_revision());
    assert_eq!(std::fs::read(&settings_path).unwrap(), original_settings);
    assert_eq!(std::fs::read(receipt.backup_path()).unwrap(), legacy_bytes);
    assert_eq!(std::fs::read(&legacy_path).unwrap(), legacy_bytes);
}

#[test]
fn explicit_import_bootstraps_missing_settings_from_published_defaults() {
    let root = tempfile::tempdir().expect("create CLASSIC root");
    let legacy_path = root.path().join("legacy/state.json");
    std::fs::create_dir_all(legacy_path.parent().unwrap()).unwrap();
    std::fs::write(
        &legacy_path,
        br#"{"active_tab":1,"results_panel_width":65535,"sort_ascending":false}"#,
    )
    .unwrap();

    let LegacyTuiStateImportOutcome::Applied(receipt) =
        import_legacy_tui_state(root.path(), &legacy_path).expect("bootstrap import")
    else {
        panic!("missing User Settings must use the explicit bootstrap seam");
    };

    assert_eq!(receipt.base_settings_revision(), &Revision::Missing);
    let current = UserSettings::open(root.path());
    assert_eq!(current.classification(), DocumentClassification::Current);
    assert!(current.update_preferences().update_check());
    assert_eq!(current.frontend_state().tui().active_tab(), 1);
    assert_eq!(
        current.frontend_state().tui().results_panel_width(),
        u16::MAX
    );
    assert!(!current.frontend_state().tui().sort_ascending());

    assert!(receipt.settings_backup_path().is_none());
    let legacy_backup_path = receipt.backup_path().to_path_buf();
    let LegacyTuiStateImportRestoreOutcome::Restored { revision } =
        receipt.restore(root.path()).expect("restore missing base")
    else {
        panic!("an unchanged bootstrap import must restore the missing base");
    };
    assert_eq!(revision, Revision::Missing);
    assert!(!root.path().join("CLASSIC Settings.yaml").exists());
    assert_eq!(
        std::fs::read(legacy_backup_path).unwrap(),
        std::fs::read(legacy_path).unwrap()
    );
}

#[test]
fn absent_legacy_source_is_a_noop_outcome() {
    let root = tempfile::tempdir().expect("create CLASSIC root");

    let outcome = import_legacy_tui_state(root.path(), root.path().join("missing-state.json"))
        .expect("missing legacy state is not an operational failure");

    assert_eq!(outcome, LegacyTuiStateImportOutcome::NoLegacySource);
    assert!(!root.path().join("CLASSIC Settings.yaml").exists());
}

#[test]
fn invalid_legacy_json_and_values_fail_before_backup_or_settings_changes() {
    for (source, expected_code) in [
        (b"{".as_slice(), "legacy_tui_state_parse_failed"),
        (b"[]".as_slice(), "legacy_tui_state_root_not_object"),
        (
            br#"{"active_tab":4,"results_panel_width":30,"sort_ascending":false}"#.as_slice(),
            "legacy_tui_state_active_tab_invalid",
        ),
        (
            br#"{"active_tab":0,"results_panel_width":65536,"sort_ascending":false}"#.as_slice(),
            "legacy_tui_state_results_panel_width_invalid",
        ),
        (
            br#"{"active_tab":0,"results_panel_width":30,"sort_ascending":0}"#.as_slice(),
            "legacy_tui_state_sort_ascending_invalid",
        ),
    ] {
        let root = tempfile::tempdir().expect("create CLASSIC root");
        let legacy_path = root.path().join("state.json");
        std::fs::write(&legacy_path, source).unwrap();

        let error = import_legacy_tui_state(root.path(), &legacy_path).unwrap_err();

        assert_eq!(error.code(), expected_code);
        assert!(!root.path().join("CLASSIC Settings.yaml").exists());
        assert!(
            !root
                .path()
                .join("CLASSIC Backup/User Settings/TUI State Imports")
                .exists()
        );
    }
}

#[test]
fn migration_required_and_untrusted_settings_bases_are_distinct_noop_outcomes() {
    let legacy_source = br#"{"active_tab":2,"results_panel_width":44,"sort_ascending":true}"#;

    let migration_root = tempfile::tempdir().expect("create migration root");
    std::fs::write(
        migration_root.path().join("CLASSIC Settings.yaml"),
        b"UI:\n  tui:\n    active_tab: 0\n",
    )
    .unwrap();
    let migration_legacy = migration_root.path().join("state.json");
    std::fs::write(&migration_legacy, legacy_source).unwrap();

    let migration_outcome =
        import_legacy_tui_state(migration_root.path(), &migration_legacy).unwrap();
    assert!(matches!(
        migration_outcome,
        LegacyTuiStateImportOutcome::RequiresSettingsMigration {
            classification: DocumentClassification::Unversioned,
            ..
        }
    ));

    let untrusted_root = tempfile::tempdir().expect("create untrusted root");
    let malformed = b"not: [valid YAML";
    std::fs::write(
        untrusted_root.path().join("CLASSIC Settings.yaml"),
        malformed,
    )
    .unwrap();
    let untrusted_legacy = untrusted_root.path().join("state.json");
    std::fs::write(&untrusted_legacy, legacy_source).unwrap();

    let untrusted_outcome =
        import_legacy_tui_state(untrusted_root.path(), &untrusted_legacy).unwrap();
    assert!(matches!(
        untrusted_outcome,
        LegacyTuiStateImportOutcome::UntrustedSettingsBase {
            classification: DocumentClassification::Malformed,
            ..
        }
    ));
    assert_eq!(
        std::fs::read(untrusted_root.path().join("CLASSIC Settings.yaml")).unwrap(),
        malformed
    );
}

#[test]
fn restore_conflicts_without_overwriting_newer_settings_or_removing_backups() {
    let root = tempfile::tempdir().expect("create CLASSIC root");
    let settings_path = root.path().join("CLASSIC Settings.yaml");
    std::fs::write(
        &settings_path,
        b"schema_version: \"1.0\"\nCLASSIC_Settings:\n  Update Check: true\n",
    )
    .unwrap();
    let legacy_path = root.path().join("state.json");
    std::fs::write(
        &legacy_path,
        br#"{"active_tab":2,"results_panel_width":44,"sort_ascending":true}"#,
    )
    .unwrap();
    let LegacyTuiStateImportOutcome::Applied(receipt) =
        import_legacy_tui_state(root.path(), &legacy_path).unwrap()
    else {
        panic!("valid import must apply");
    };
    let legacy_backup = std::fs::read(receipt.backup_path()).unwrap();
    let settings_backup_path = receipt.settings_backup_path().unwrap().to_path_buf();
    let settings_backup = std::fs::read(&settings_backup_path).unwrap();
    let newer = b"schema_version: \"1.0\"\nCLASSIC_Settings:\n  Update Check: false\nExternal:\n  edit: newer\n";
    std::fs::write(&settings_path, newer).unwrap();

    let outcome = receipt.restore(root.path()).unwrap();

    assert!(matches!(
        outcome,
        LegacyTuiStateImportRestoreOutcome::Conflict { .. }
    ));
    assert_eq!(std::fs::read(settings_path).unwrap(), newer);
    assert_eq!(std::fs::read(receipt.backup_path()).unwrap(), legacy_backup);
    assert_eq!(
        std::fs::read(settings_backup_path).unwrap(),
        settings_backup
    );
}
