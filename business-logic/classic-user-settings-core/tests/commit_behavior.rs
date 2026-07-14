//! Behavioral checks for explicit, conflict-safe User Settings commits.

use classic_settings_core::{Yaml, parse_yaml_content};
use classic_user_settings_core::{
    UserSettings, UserSettingsCommitOutcome, UserSettingsUpdate, UserSettingsUpdatePreview,
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
fn missing_document_commit_creates_current_yaml_but_loses_to_a_concurrent_creator() {
    let committed_root = tempfile::tempdir().unwrap();
    let committed = accepted_update(&UserSettings::open(committed_root.path()), false);

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
    let stale = accepted_update(&UserSettings::open(conflict_root.path()), false);
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
