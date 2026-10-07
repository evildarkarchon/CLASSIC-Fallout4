//! Behavioral checks for the game-aware FormID database save in a User Settings Update.
//!
//! The save is the write-side twin of `CrashLogScanSettings::formid_databases_for_game`:
//! Fallout 4 VR shares the Fallout 4 corpus, so its rows are saved under `Fallout4` and a
//! legacy `Fallout4VR` key is removed with a diagnostic that is visible before and after commit.

use classic_shared_core::GameId;
use classic_user_settings_core::{
    AcceptedUserSettingsUpdate, UpdateDiagnostic, UserSettings, UserSettingsCommitOutcome,
    UserSettingsUpdate, UserSettingsUpdateField, UserSettingsUpdatePreview,
};
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

const FORMID_DATABASES_POINTER: &str = "/CLASSIC_Settings/FormID Databases";
const LEGACY_KEY_REMOVED: &str = "legacy_formid_databases_key_removed";

/// Returns a checked-in User Settings compatibility fixture.
fn fixture_path(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join("tests/fixtures/user_settings_compatibility")
        .join(name)
}

/// Installs one fixture at the canonical settings location.
fn install_fixture(root: &Path, name: &str) {
    std::fs::copy(fixture_path(name), root.join("CLASSIC Settings.yaml")).unwrap();
}

/// Builds an owned row list from string literals.
fn rows(paths: &[&str]) -> Vec<String> {
    paths.iter().map(|path| (*path).to_string()).collect()
}

/// Builds an owned raw FormID Databases mapping from literals.
fn mapping(entries: &[(&str, &[&str])]) -> BTreeMap<String, Vec<String>> {
    entries
        .iter()
        .map(|(game, paths)| ((*game).to_string(), rows(paths)))
        .collect()
}

/// Previews one game-aware save and returns the accepted artifact.
fn accepted_save(
    settings: &UserSettings,
    game: &str,
    paths: &[&str],
) -> AcceptedUserSettingsUpdate {
    match settings
        .preview_update(UserSettingsUpdate::new().with_formid_databases_for_game(game, rows(paths)))
    {
        UserSettingsUpdatePreview::Accepted(accepted) => accepted,
        UserSettingsUpdatePreview::Rejected(diagnostics) => {
            panic!("a valid FormID database save must be accepted: {diagnostics:?}")
        }
    }
}

/// Returns the single raw mapping the accepted artifact will publish.
fn published_mapping(accepted: &AcceptedUserSettingsUpdate) -> &BTreeMap<String, Vec<String>> {
    let [UserSettingsUpdateField::FormIdDatabases(databases)] = accepted.fields() else {
        panic!(
            "a FormID database save publishes exactly one FormID Databases field: {:?}",
            accepted.fields()
        );
    };
    databases
}

/// Returns `(field_path, code)` pairs so assertions stay independent of message wording.
fn codes(diagnostics: &[UpdateDiagnostic]) -> Vec<(Option<&str>, &str)> {
    diagnostics
        .iter()
        .map(|diagnostic| (diagnostic.field_path(), diagnostic.code()))
        .collect()
}

/// Commits `accepted` and returns the diagnostics reported by the committed outcome.
fn commit_diagnostics(root: &Path, accepted: &AcceptedUserSettingsUpdate) -> Vec<UpdateDiagnostic> {
    match accepted.commit(root).unwrap() {
        UserSettingsCommitOutcome::Committed { diagnostics, .. } => diagnostics,
        outcome @ UserSettingsCommitOutcome::Conflict { .. } => {
            panic!("an unchanged document must commit: {outcome:?}")
        }
    }
}

#[test]
fn fallout4_vr_save_moves_rows_under_fallout4_and_reports_the_legacy_key_removal() {
    let root = tempfile::tempdir().unwrap();
    install_fixture(root.path(), "vr_shared_and_legacy_formid_databases.yaml");
    let settings = UserSettings::open(root.path());
    let saved = [
        "databases/Fallout4 FormIDs.db",
        "databases/Legacy VR FormIDs.db",
        "D:/Added/VR Extra.db",
    ];

    let accepted = accepted_save(&settings, "Fallout4VR", &saved);

    assert_eq!(
        published_mapping(&accepted),
        &mapping(&[
            ("Fallout4", &saved),
            ("Skyrim", &["databases/Skyrim FormIDs.db"]),
        ]),
        "VR rows are saved under Fallout4, the legacy key is dropped, other games are preserved"
    );
    assert_eq!(
        codes(accepted.diagnostics()),
        vec![(Some(FORMID_DATABASES_POINTER), LEGACY_KEY_REMOVED)],
        "the legacy key removal is visible in the preview before commit"
    );
    assert!(
        accepted.diagnostics()[0].message().contains("Fallout4VR"),
        "the removal message names the legacy key"
    );

    let committed = commit_diagnostics(root.path(), &accepted);
    assert_eq!(
        codes(&committed),
        vec![(Some(FORMID_DATABASES_POINTER), LEGACY_KEY_REMOVED)],
        "the committed outcome reports the same removal"
    );

    let reopened = UserSettings::open(root.path());
    let scan = reopened.crash_log_scan_settings();
    assert_eq!(
        scan.formid_databases(),
        &mapping(&[
            ("Fallout4", &saved),
            ("Skyrim", &["databases/Skyrim FormIDs.db"]),
        ]),
        "the raw keyed map stays readable with the stored document shape unchanged"
    );
    assert_eq!(scan.formid_databases_for_game(GameId::Fallout4VR), saved);
    assert_eq!(scan.formid_databases_for_game(GameId::Fallout4), saved);
    assert!(
        reopened.diagnostics().is_empty(),
        "the published document reopens without open diagnostics: {:?}",
        reopened.diagnostics()
    );
}

#[test]
fn fallout4_vr_save_accepts_the_human_facing_managed_game_label() {
    let root = tempfile::tempdir().unwrap();
    install_fixture(root.path(), "vr_legacy_formid_databases.yaml");
    let settings = UserSettings::open(root.path());

    let accepted = accepted_save(
        &settings,
        "Fallout 4 VR",
        &["databases/Legacy VR FormIDs.db"],
    );

    assert_eq!(
        published_mapping(&accepted),
        &mapping(&[("Fallout4", &["databases/Legacy VR FormIDs.db"])])
    );
    assert_eq!(
        codes(accepted.diagnostics()),
        vec![(Some(FORMID_DATABASES_POINTER), LEGACY_KEY_REMOVED)]
    );
}

#[test]
fn fallout4_vr_save_without_a_legacy_key_reports_no_diagnostic() {
    let root = tempfile::tempdir().unwrap();
    install_fixture(root.path(), "canonical_current_nested.yaml");
    let settings = UserSettings::open(root.path());

    let accepted = accepted_save(&settings, "Fallout4VR", &["D:/VR.db"]);

    assert_eq!(
        published_mapping(&accepted),
        &mapping(&[("Fallout4", &["D:/VR.db"])])
    );
    assert!(accepted.diagnostics().is_empty());
    assert!(commit_diagnostics(root.path(), &accepted).is_empty());
}

#[test]
fn fallout4_save_touches_only_its_own_key_and_keeps_legacy_vr_rows() {
    let root = tempfile::tempdir().unwrap();
    install_fixture(root.path(), "vr_shared_and_legacy_formid_databases.yaml");
    let settings = UserSettings::open(root.path());

    let accepted = accepted_save(&settings, "Fallout4", &["D:/Only Fallout4.db"]);

    assert_eq!(
        published_mapping(&accepted),
        &mapping(&[
            ("Fallout4", &["D:/Only Fallout4.db"]),
            (
                "Fallout4VR",
                &[
                    "databases/Fallout4 FormIDs.db",
                    "databases/Legacy VR FormIDs.db"
                ],
            ),
            ("Skyrim", &["databases/Skyrim FormIDs.db"]),
        ])
    );
    assert!(accepted.diagnostics().is_empty());
}

#[test]
fn other_game_save_touches_only_its_own_key_and_preserves_every_other_game() {
    let root = tempfile::tempdir().unwrap();
    install_fixture(root.path(), "vr_shared_and_legacy_formid_databases.yaml");
    let settings = UserSettings::open(root.path());

    let accepted = accepted_save(&settings, "Starfield", &["D:/Starfield.db"]);

    assert_eq!(
        published_mapping(&accepted),
        &mapping(&[
            (
                "Fallout4",
                &[
                    "databases/Fallout4 FormIDs.db",
                    "databases/Shared Extra FormIDs.db"
                ],
            ),
            (
                "Fallout4VR",
                &[
                    "databases/Fallout4 FormIDs.db",
                    "databases/Legacy VR FormIDs.db"
                ],
            ),
            ("Skyrim", &["databases/Skyrim FormIDs.db"]),
            ("Starfield", &["D:/Starfield.db"]),
        ])
    );
    assert!(accepted.diagnostics().is_empty());
    assert!(commit_diagnostics(root.path(), &accepted).is_empty());
    assert_eq!(
        UserSettings::open(root.path())
            .crash_log_scan_settings()
            .formid_databases_for_game(GameId::Fallout4VR),
        vec![
            "databases/Fallout4 FormIDs.db",
            "databases/Shared Extra FormIDs.db",
            "databases/Legacy VR FormIDs.db",
        ],
        "an unrelated save leaves the Fallout 4 VR scan read untouched"
    );
}

#[test]
fn save_applies_on_top_of_a_whole_mapping_requested_in_the_same_update() {
    let root = tempfile::tempdir().unwrap();
    install_fixture(root.path(), "canonical_current_nested.yaml");
    let settings = UserSettings::open(root.path());

    let UserSettingsUpdatePreview::Accepted(accepted) = settings.preview_update(
        UserSettingsUpdate::new()
            .with_formid_databases(mapping(&[
                ("Fallout4VR", &["D:/Legacy.db"]),
                ("Skyrim", &["D:/Skyrim.db"]),
            ]))
            .with_formid_databases_for_game("Fallout4VR", rows(&["D:/Shared.db"])),
    ) else {
        panic!("a valid combined FormID update must be accepted");
    };

    assert_eq!(
        published_mapping(&accepted),
        &mapping(&[
            ("Fallout4", &["D:/Shared.db"]),
            ("Skyrim", &["D:/Skyrim.db"])
        ])
    );
    assert_eq!(
        codes(accepted.diagnostics()),
        vec![(Some(FORMID_DATABASES_POINTER), LEGACY_KEY_REMOVED)]
    );
}

#[test]
fn save_for_an_unsupported_game_or_with_an_empty_path_is_rejected() {
    let root = tempfile::tempdir().unwrap();
    install_fixture(root.path(), "canonical_current_nested.yaml");
    let settings = UserSettings::open(root.path());

    for (game, paths, code) in [
        (
            "Oblivion",
            rows(&["D:/x.db"]),
            "invalid_enum_formid_databases_game",
        ),
        ("Fallout4VR", rows(&[""]), "invalid_value_formid_databases"),
    ] {
        let UserSettingsUpdatePreview::Rejected(diagnostics) = settings
            .preview_update(UserSettingsUpdate::new().with_formid_databases_for_game(game, paths))
        else {
            panic!("an invalid FormID database save must be rejected");
        };
        assert_eq!(
            codes(&diagnostics),
            vec![(Some(FORMID_DATABASES_POINTER), code)]
        );
    }
}

#[test]
fn ordinary_updates_carry_no_accepted_diagnostics() {
    let root = tempfile::tempdir().unwrap();
    install_fixture(root.path(), "vr_shared_and_legacy_formid_databases.yaml");
    let settings = UserSettings::open(root.path());

    let UserSettingsUpdatePreview::Accepted(accepted) =
        settings.preview_update(UserSettingsUpdate::new().with_update_check(false))
    else {
        panic!("a valid Update Check change must be accepted");
    };

    assert!(accepted.diagnostics().is_empty());
    assert!(commit_diagnostics(root.path(), &accepted).is_empty());
    assert!(
        UserSettings::open(root.path())
            .crash_log_scan_settings()
            .formid_databases()
            .contains_key("Fallout4VR"),
        "updates that do not save FormID rows never remove the legacy key"
    );
}
