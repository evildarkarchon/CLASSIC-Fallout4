//! Behavioral checks for Game Setup User Settings through the public snapshot interface.

use classic_user_settings_core::{GameVersionSelection, PreferenceOrigin, UserSettings};
use std::path::PathBuf;

/// Returns one shared User Settings compatibility fixture through the repository root.
fn fixture_path(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join("tests/fixtures/user_settings_compatibility")
        .join(name)
}

#[test]
fn open_projects_complete_game_setup_settings_without_rewriting_paths() {
    let root = tempfile::tempdir().expect("temporary CLASSIC root");
    let path = root.path().join("CLASSIC Settings.yaml");
    let content = concat!(
        "schema_version: \"1.0\"\n",
        "CLASSIC_Settings:\n",
        "  Managed Game: Fallout 4\n",
        "  Game Version: NextGen\n",
        "  Game Folder Path: 'C:\\Games\\Fallout 4'\n",
        "  Game EXE Path: 'C:\\Games\\Fallout 4\\Fallout4Custom.exe'\n",
        "  Documents Folder Path: /home/deck/.local/share/Steam/steamapps/compatdata/377160/pfx/drive_c/users/steamuser/My Documents/My Games/Fallout4\n",
        "  INI Folder Path: /home/deck/.local/share/Steam/steamapps/compatdata/377160/pfx/drive_c/users/steamuser/My Documents/My Games/Fallout4\n",
        "  MODS Folder Path: 'Z:/Mod Organizer 2/Fallout 4/mods'\n",
        "  SCAN Custom Path: /home/deck/CLASSIC/Crash Logs\n",
        "  Papyrus Log Path: 'C:/Users/Test/Documents/My Games/Fallout4/Logs/Script/Papyrus.0.log'\n",
    );
    std::fs::write(&path, content).expect("write User Settings fixture");
    let modified_before = std::fs::metadata(&path)
        .expect("settings metadata")
        .modified()
        .expect("settings modified time");

    let settings = UserSettings::open(root.path());
    let game_setup = settings.game_setup_settings();

    assert_eq!(game_setup.managed_game().as_str(), "Fallout4");
    assert_eq!(game_setup.managed_game_origin(), PreferenceOrigin::Document);
    assert_eq!(
        game_setup.game_version_selection(),
        GameVersionSelection::NextGen
    );
    assert_eq!(game_setup.game_root(), Some("C:\\Games\\Fallout 4"));
    assert_eq!(
        game_setup.game_executable(),
        Some("C:\\Games\\Fallout 4\\Fallout4Custom.exe")
    );
    assert_eq!(
        game_setup.documents_root(),
        Some(
            "/home/deck/.local/share/Steam/steamapps/compatdata/377160/pfx/drive_c/users/steamuser/My Documents/My Games/Fallout4"
        )
    );
    assert_eq!(
        game_setup.ini_folder(),
        Some(
            "/home/deck/.local/share/Steam/steamapps/compatdata/377160/pfx/drive_c/users/steamuser/My Documents/My Games/Fallout4"
        )
    );
    assert_eq!(
        game_setup.mods_root(),
        Some("Z:/Mod Organizer 2/Fallout 4/mods")
    );
    assert_eq!(
        game_setup.custom_scan_input(),
        Some("/home/deck/CLASSIC/Crash Logs")
    );
    assert_eq!(
        game_setup.papyrus_log(),
        Some("C:/Users/Test/Documents/My Games/Fallout4/Logs/Script/Papyrus.0.log")
    );
    assert!(settings.diagnostics().is_empty());
    assert_eq!(settings.original_bytes(), Some(content.as_bytes()));
    assert_eq!(
        std::fs::read_to_string(&path).expect("read unchanged User Settings"),
        content
    );
    assert_eq!(
        std::fs::metadata(&path)
            .expect("settings metadata after open")
            .modified()
            .expect("settings modified time after open"),
        modified_before
    );
}

#[test]
fn documents_path_obeys_canonical_alias_precedence_including_explicit_clear() {
    let root = tempfile::tempdir().expect("temporary CLASSIC root");
    let path = root.path().join("CLASSIC Settings.yaml");
    let content = concat!(
        "schema_version: \"1.0\"\n",
        "CLASSIC_Settings:\n",
        "  Documents Folder Path: null\n",
        "  INI Folder Path: 'D:/Stale Documents'\n",
    );
    std::fs::write(&path, content).expect("write documents conflict fixture");

    let settings = UserSettings::open(root.path());
    let game_setup = settings.game_setup_settings();

    assert_eq!(game_setup.documents_root(), None);
    assert_eq!(
        game_setup.documents_root_origin(),
        PreferenceOrigin::Document
    );
    assert_eq!(game_setup.ini_folder(), Some("D:/Stale Documents"));
    assert_eq!(
        settings
            .diagnostics()
            .iter()
            .map(|diagnostic| diagnostic.code())
            .collect::<Vec<_>>(),
        vec!["canonical_alias_conflict_ini_folder"]
    );
    assert_eq!(
        std::fs::read_to_string(path).expect("read unchanged documents conflict"),
        content
    );
}

#[test]
fn legacy_ini_path_supplies_documents_root_when_canonical_label_is_missing() {
    let root = tempfile::tempdir().expect("temporary CLASSIC root");
    let path = root.path().join("CLASSIC Settings.yaml");
    let content = concat!(
        "schema_version: \"1.0\"\n",
        "CLASSIC_Settings:\n",
        "  INI Folder Path: 'D:/Legacy Documents'\n",
    );
    std::fs::write(&path, content).expect("write legacy INI fixture");

    let settings = UserSettings::open(root.path());
    let game_setup = settings.game_setup_settings();

    assert_eq!(game_setup.documents_root(), Some("D:/Legacy Documents"));
    assert_eq!(
        game_setup.documents_root_origin(),
        PreferenceOrigin::Document
    );
    assert_eq!(game_setup.ini_folder(), Some("D:/Legacy Documents"));
    assert!(settings.diagnostics().is_empty());
    assert_eq!(
        std::fs::read_to_string(path).expect("read unchanged legacy INI"),
        content
    );
}

#[test]
fn canonical_mods_and_custom_paths_win_conflicts_without_rewriting_aliases() {
    let root = tempfile::tempdir().expect("temporary CLASSIC root");
    let path = root.path().join("CLASSIC Settings.yaml");
    std::fs::copy(fixture_path("canonical_alias_conflict.yaml"), &path)
        .expect("install conflict fixture");
    let bytes_before = std::fs::read(&path).expect("read fixture before open");

    let settings = UserSettings::open(root.path());
    let game_setup = settings.game_setup_settings();

    assert_eq!(game_setup.mods_root(), Some("D:/Canonical Mods"));
    assert_eq!(
        game_setup.custom_scan_input(),
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
    assert_eq!(
        std::fs::read(path).expect("read fixture after open"),
        bytes_before
    );
}

#[test]
fn alias_only_mods_and_custom_paths_are_projected_without_rewriting() {
    let root = tempfile::tempdir().expect("temporary CLASSIC root");
    let path = root.path().join("CLASSIC Settings.yaml");
    let content = concat!(
        "schema_version: \"1.0\"\n",
        "CLASSIC_Settings:\n",
        "  Staging Mods Folder: 'D:/Legacy Mods'\n",
        "  Custom Scan Folder: 'D:/Legacy Crash Logs'\n",
    );
    std::fs::write(&path, content).expect("write alias-only fixture");

    let settings = UserSettings::open(root.path());

    assert_eq!(
        settings.game_setup_settings().mods_root(),
        Some("D:/Legacy Mods")
    );
    assert_eq!(
        settings.game_setup_settings().custom_scan_input(),
        Some("D:/Legacy Crash Logs")
    );
    assert_eq!(
        settings.game_setup_settings().mods_root_origin(),
        PreferenceOrigin::Document
    );
    assert!(settings.diagnostics().is_empty());
    assert_eq!(
        std::fs::read_to_string(path).expect("read unchanged aliases"),
        content
    );
}

#[test]
fn invalid_setup_values_use_typed_fallbacks_and_stable_diagnostics() {
    let root = tempfile::tempdir().expect("temporary CLASSIC root");
    let path = root.path().join("CLASSIC Settings.yaml");
    let content = concat!(
        "schema_version: \"1.0\"\n",
        "CLASSIC_Settings:\n",
        "  Managed Game: Future Game\n",
        "  Game Folder Path: relative/game\n",
        "  Game EXE Path: 42\n",
        "  Documents Folder Path: relative/documents\n",
        "  INI Folder Path: false\n",
        "  MODS Folder Path: relative/mods\n",
        "  Staging Mods Folder: 'D:/Usable Alias Mods'\n",
        "  Papyrus Log Path: relative/Papyrus.0.log\n",
    );
    std::fs::write(&path, content).expect("write invalid setup fixture");

    let settings = UserSettings::open(root.path());
    let game_setup = settings.game_setup_settings();

    assert_eq!(game_setup.managed_game().as_str(), "Fallout4");
    assert_eq!(
        game_setup.managed_game_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert_eq!(game_setup.game_root(), None);
    assert_eq!(game_setup.game_executable(), None);
    assert_eq!(game_setup.documents_root(), None);
    assert_eq!(game_setup.ini_folder(), None);
    assert_eq!(game_setup.mods_root(), Some("D:/Usable Alias Mods"));
    assert_eq!(game_setup.papyrus_log(), None);
    assert_eq!(
        settings
            .diagnostics()
            .iter()
            .map(|diagnostic| diagnostic.code())
            .collect::<Vec<_>>(),
        vec![
            "invalid_enum_managed_game",
            "invalid_path_game_root",
            "invalid_type_game_executable",
            "invalid_path_documents_root",
            "invalid_path_mods_folder",
            "invalid_path_papyrus_log",
        ]
    );
    assert_eq!(
        std::fs::read_to_string(path).expect("read unchanged invalid values"),
        content
    );
}

#[test]
fn missing_and_malformed_documents_distinguish_defaults_from_degraded_fallbacks() {
    let missing_root = tempfile::tempdir().expect("missing settings root");
    let malformed_root = tempfile::tempdir().expect("malformed settings root");
    std::fs::write(
        malformed_root.path().join("CLASSIC Settings.yaml"),
        "CLASSIC_Settings: [\n",
    )
    .expect("write malformed fixture");

    let missing = UserSettings::open(missing_root.path());
    let malformed = UserSettings::open(malformed_root.path());

    assert_eq!(
        missing.game_setup_settings().managed_game_origin(),
        PreferenceOrigin::Default
    );
    assert_eq!(
        missing.game_setup_settings().game_root_origin(),
        PreferenceOrigin::Default
    );
    assert_eq!(
        malformed.game_setup_settings().managed_game_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert_eq!(
        malformed.game_setup_settings().game_root_origin(),
        PreferenceOrigin::DegradedFallback
    );
    assert!(!missing_root.path().join("CLASSIC Settings.yaml").exists());
}
