//! Behavioral checks for explicit, conflict-safe User Settings commits.

use classic_settings_core::{Yaml, parse_yaml_content};
use classic_user_settings_core::{
    GuiWindow, UserSettings, UserSettingsCommitOutcome, UserSettingsFrontendTransitionOutcome,
    UserSettingsUpdate, UserSettingsUpdatePreview,
};
use std::path::{Path, PathBuf};

/// Returns a checked-in User Settings compatibility fixture.
fn fixture_path(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join("tests/fixtures/user_settings_compatibility")
        .join(name)
}

/// Installs one fixture at the canonical settings location.
fn install_fixture(root: &Path, name: &str) -> PathBuf {
    let destination = root.join("CLASSIC Settings.yaml");
    std::fs::copy(fixture_path(name), &destination).unwrap();
    destination
}

/// Parses the single YAML document at `path` for semantic comparisons.
fn parsed_document(path: &Path) -> Yaml {
    let content = std::fs::read_to_string(path).unwrap();
    let mut documents = parse_yaml_content(path.display().to_string(), &content).unwrap();
    assert_eq!(documents.len(), 1);
    documents.remove(0)
}

/// Parses the checked-in compatibility mirror generated from the Rust-owned default registry.
fn published_defaults_document() -> Yaml {
    let main_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join("CLASSIC Data/databases/CLASSIC Main.yaml");
    let main = parsed_document(&main_path);
    let defaults = main["CLASSIC_Info"]["default_settings"]
        .as_str()
        .expect("default_settings must remain a YAML document literal");
    let mut documents = parse_yaml_content("published User Settings defaults", defaults).unwrap();
    assert_eq!(documents.len(), 1);
    documents.remove(0)
}

/// Returns the accepted artifact for one valid Update Check change.
fn accepted_update(
    settings: &UserSettings,
    value: bool,
) -> classic_user_settings_core::AcceptedUserSettingsUpdate {
    let UserSettingsUpdatePreview::Accepted(accepted) =
        settings.preview_update(UserSettingsUpdate::new().with_update_check(value))
    else {
        panic!("valid Update Check change should be accepted");
    };
    accepted
}

/// Returns an accepted first-run artifact for one explicit Update Check override.
fn accepted_bootstrap(
    settings: &UserSettings,
    value: bool,
) -> classic_user_settings_core::AcceptedUserSettingsUpdate {
    let UserSettingsUpdatePreview::Accepted(accepted) =
        settings.preview_bootstrap(UserSettingsUpdate::new().with_update_check(value))
    else {
        panic!("a missing trusted snapshot should accept an explicit bootstrap preview");
    };
    accepted
}

#[test]
fn concurrent_commits_allow_one_publication_and_report_one_revision_conflict() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("CLASSIC Settings.yaml");
    std::fs::write(
        &path,
        "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Update Check: true\n",
    )
    .unwrap();
    let first = accepted_update(&UserSettings::open(root.path()), false);
    let second = accepted_update(&UserSettings::open(root.path()), false);

    let barrier = std::sync::Arc::new(std::sync::Barrier::new(2));
    let root_path = root.path();
    let (first_outcome, second_outcome) = std::thread::scope(|scope| {
        let first_barrier = std::sync::Arc::clone(&barrier);
        let first_commit = scope.spawn(move || {
            first_barrier.wait();
            first.commit(root_path).unwrap()
        });
        let second_commit = scope.spawn(move || {
            barrier.wait();
            second.commit(root_path).unwrap()
        });
        (first_commit.join().unwrap(), second_commit.join().unwrap())
    });

    let outcomes = [first_outcome, second_outcome];
    assert_eq!(
        outcomes
            .iter()
            .filter(|outcome| matches!(outcome, UserSettingsCommitOutcome::Committed { .. }))
            .count(),
        1
    );
    assert_eq!(
        outcomes
            .iter()
            .filter(|outcome| matches!(outcome, UserSettingsCommitOutcome::Conflict { .. }))
            .count(),
        1
    );
    assert!(
        !UserSettings::open(root.path())
            .update_preferences()
            .update_check()
    );
}

#[test]
fn stale_commit_leaves_a_newer_external_document_byte_for_byte_unchanged() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("CLASSIC Settings.yaml");
    std::fs::write(
        &path,
        "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Update Check: true\n",
    )
    .unwrap();
    let accepted = accepted_update(&UserSettings::open(root.path()), false);
    let external = concat!(
        "schema_version: \"1.0\"\n",
        "CLASSIC_Settings:\n",
        "  Update Check: true\n",
        "ExternalEditor:\n",
        "  changed_after_preview: true\n",
    );
    std::fs::write(&path, external).unwrap();

    let outcome = accepted.commit(root.path()).unwrap();

    assert!(matches!(
        outcome,
        UserSettingsCommitOutcome::Conflict { .. }
    ));
    assert_eq!(std::fs::read(&path).unwrap(), external.as_bytes());
}

#[test]
fn frontend_geometry_transition_replays_once_without_losing_a_newer_setting() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("CLASSIC Settings.yaml");
    std::fs::write(
        &path,
        concat!(
            "schema_version: \"1.0\"\n",
            "CLASSIC_Settings:\n",
            "  Update Check: true\n",
            "UI:\n",
            "  window_geometry:\n",
            "    main_tab:\n",
            "      maximized: false\n",
            "      width: 640\n",
            "      height: 500\n",
        ),
    )
    .unwrap();
    let displayed = UserSettings::open(root.path());
    let newer = accepted_update(&displayed, false);
    assert!(matches!(
        newer.commit(root.path()).unwrap(),
        UserSettingsCommitOutcome::Committed { .. }
    ));

    let outcome = UserSettings::commit_frontend_geometry_transition(
        root.path(),
        displayed.revision(),
        GuiWindow::Main,
        true,
        1440,
        900,
    )
    .unwrap();

    assert!(matches!(
        outcome,
        UserSettingsFrontendTransitionOutcome::Committed { .. }
    ));
    let current = UserSettings::open(root.path());
    assert!(!current.update_preferences().update_check());
    let geometry = current.frontend_state().window_geometry().main_tab();
    assert!(geometry.maximized());
    assert_eq!(geometry.width(), 1440);
    assert_eq!(geometry.height(), 900);
}

#[test]
fn commit_patches_only_the_requested_node_in_a_document_with_unrelated_external_content() {
    let root = tempfile::tempdir().unwrap();
    let path = install_fixture(root.path(), "unknown_entries.yaml");
    let accepted = accepted_update(&UserSettings::open(root.path()), false);

    let outcome = accepted.commit(root.path()).unwrap();

    assert!(matches!(
        outcome,
        UserSettingsCommitOutcome::Committed { .. }
    ));
    let actual = parsed_document(&path);
    let expected = parsed_document(&fixture_path("unknown_entries_after_update.yaml"));
    assert_eq!(actual["ThirdPartyPlugin"], expected["ThirdPartyPlugin"]);
    assert_eq!(actual["UI"], expected["UI"]);
    assert_eq!(
        actual["CLASSIC_Settings"]["Future Scan Knob"],
        expected["CLASSIC_Settings"]["Future Scan Knob"]
    );
    assert_eq!(
        actual["CLASSIC_Settings"]["Update Check"],
        Yaml::Boolean(false)
    );
}

#[test]
fn geometry_commit_updates_only_the_selected_window_and_preserves_unknown_frontend_content() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("CLASSIC Settings.yaml");
    let source = br#"schema_version: "1.0"
CLASSIC_Settings:
  Update Check: true
UI:
  window_geometry:
    main_tab:
      maximized: false
      width: 640
      height: 500
    future_tab:
      layout: ultrawide
  community_frontend:
    theme: amber
"#;
    std::fs::write(&path, source).unwrap();
    let settings = UserSettings::open(root.path());
    let UserSettingsUpdatePreview::Accepted(accepted) = settings.preview_update(
        UserSettingsUpdate::new().with_window_geometry(GuiWindow::Main, true, 1024, 768),
    ) else {
        panic!("valid geometry should be accepted");
    };

    let outcome = accepted.commit(root.path()).unwrap();

    assert!(matches!(
        outcome,
        UserSettingsCommitOutcome::Committed { .. }
    ));
    let actual = parsed_document(&path);
    assert_eq!(
        actual["UI"]["window_geometry"]["main_tab"]["maximized"],
        Yaml::Boolean(true)
    );
    assert_eq!(
        actual["UI"]["window_geometry"]["main_tab"]["width"],
        Yaml::Integer(1024)
    );
    assert_eq!(
        actual["UI"]["window_geometry"]["main_tab"]["height"],
        Yaml::Integer(768)
    );
    assert_eq!(
        actual["UI"]["window_geometry"]["future_tab"]["layout"],
        Yaml::String("ultrawide".to_string())
    );
    assert_eq!(
        actual["UI"]["community_frontend"]["theme"],
        Yaml::String("amber".to_string())
    );
    assert_eq!(
        actual["CLASSIC_Settings"]["Update Check"],
        Yaml::Boolean(true)
    );
}

#[test]
fn tui_state_commit_updates_one_complete_transition_and_preserves_unknown_frontend_content() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("CLASSIC Settings.yaml");
    std::fs::write(
        &path,
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
    .unwrap();
    let settings = UserSettings::open(root.path());
    let UserSettingsUpdatePreview::Accepted(accepted) =
        settings.preview_update(UserSettingsUpdate::new().with_tui_remembered_state(2, 42, true))
    else {
        panic!("valid TUI remembered state should be accepted");
    };

    let outcome = accepted.commit(root.path()).unwrap();

    assert!(matches!(
        outcome,
        UserSettingsCommitOutcome::Committed { .. }
    ));
    let actual = parsed_document(&path);
    assert_eq!(actual["UI"]["tui"]["active_tab"], Yaml::Integer(2));
    assert_eq!(
        actual["UI"]["tui"]["results_panel_width"],
        Yaml::Integer(42)
    );
    assert_eq!(actual["UI"]["tui"]["sort_ascending"], Yaml::Boolean(true));
    assert_eq!(
        actual["UI"]["tui"]["future_layout"],
        Yaml::String("compact".to_string())
    );
    assert_eq!(
        actual["UI"]["community_frontend"]["theme"],
        Yaml::String("amber".to_string())
    );
}

#[test]
fn commit_preserves_untouched_invalid_values_and_legacy_aliases_semantically() {
    let invalid_root = tempfile::tempdir().unwrap();
    let invalid_path = install_fixture(invalid_root.path(), "invalid_known_values.yaml");
    let invalid_before = parsed_document(&invalid_path);
    let invalid_settings = UserSettings::open(invalid_root.path());
    let UserSettingsUpdatePreview::Accepted(invalid_update) = invalid_settings.preview_update(
        UserSettingsUpdate::new()
            .with_simplify_logs(true)
            .with_show_statistics(true),
    ) else {
        panic!("valid fields should be accepted despite unrelated invalid values");
    };

    invalid_update.commit(invalid_root.path()).unwrap();

    let invalid_after = parsed_document(&invalid_path);
    for label in [
        "Update Check",
        "Game Version",
        "Move Unsolved Logs",
        "Unsolved Logs Destination",
        "SCAN Custom Path",
        "Max Concurrent Scans",
        "FormID Databases",
    ] {
        assert_eq!(
            invalid_after["CLASSIC_Settings"][label], invalid_before["CLASSIC_Settings"][label],
            "untouched invalid node {label} changed"
        );
    }
    assert_eq!(invalid_after["UI"], invalid_before["UI"]);
    assert_eq!(
        invalid_after["CLASSIC_Settings"]["Simplify Logs"],
        Yaml::Boolean(true)
    );
    assert_eq!(
        invalid_after["CLASSIC_Settings"]["Show Statistics"],
        Yaml::Boolean(true)
    );

    let alias_root = tempfile::tempdir().unwrap();
    let alias_path = install_fixture(alias_root.path(), "canonical_alias_conflict.yaml");
    let alias_before = parsed_document(&alias_path);
    let alias_settings = UserSettings::open(alias_root.path());
    let UserSettingsUpdatePreview::Accepted(alias_update) =
        alias_settings.preview_update(UserSettingsUpdate::new().with_max_concurrent_scans(4))
    else {
        panic!("unrelated alias conflicts should not reject an update");
    };

    alias_update.commit(alias_root.path()).unwrap();

    let alias_after = parsed_document(&alias_path);
    for label in ["Staging Mods Folder", "Custom Scan Folder"] {
        assert_eq!(
            alias_after["CLASSIC_Settings"][label], alias_before["CLASSIC_Settings"][label],
            "legacy alias {label} changed"
        );
    }
}

#[test]
fn bootstrap_commit_renders_the_complete_published_default_registry() {
    let root = tempfile::tempdir().unwrap();
    let settings = UserSettings::open(root.path());
    let UserSettingsUpdatePreview::Accepted(accepted) =
        settings.preview_bootstrap(UserSettingsUpdate::new())
    else {
        panic!("a missing trusted snapshot should accept an explicit bootstrap preview");
    };

    let outcome = accepted.commit(root.path()).unwrap();

    assert!(matches!(
        outcome,
        UserSettingsCommitOutcome::Committed { .. }
    ));
    assert_eq!(
        parsed_document(&root.path().join("CLASSIC Settings.yaml")),
        published_defaults_document()
    );
}

#[test]
fn bootstrap_commit_applies_requested_fields_but_loses_to_a_concurrent_creator() {
    let committed_root = tempfile::tempdir().unwrap();
    let committed = accepted_bootstrap(&UserSettings::open(committed_root.path()), false);

    let outcome = committed.commit(committed_root.path()).unwrap();

    assert!(matches!(
        outcome,
        UserSettingsCommitOutcome::Committed { .. }
    ));
    let created = parsed_document(&committed_root.path().join("CLASSIC Settings.yaml"));
    assert_eq!(created["schema_version"], Yaml::String("1.0".to_string()));
    assert_eq!(
        created["CLASSIC_Settings"]["Update Check"],
        Yaml::Boolean(false)
    );

    let conflict_root = tempfile::tempdir().unwrap();
    let stale = accepted_bootstrap(&UserSettings::open(conflict_root.path()), false);
    let external = "schema_version: \"1.0\"\nCLASSIC_Settings:\n  Update Check: true\n";
    let path = conflict_root.path().join("CLASSIC Settings.yaml");
    std::fs::write(&path, external).unwrap();

    let conflict = stale.commit(conflict_root.path()).unwrap();

    assert!(matches!(
        conflict,
        UserSettingsCommitOutcome::Conflict { .. }
    ));
    assert_eq!(std::fs::read(&path).unwrap(), external.as_bytes());
}
