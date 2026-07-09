use super::*;
use std::fs;
use std::path::Path;
use tempfile::TempDir;

fn setup_roots() -> (TempDir, PathBuf, PathBuf) {
    let temp = TempDir::new().expect("temp dir");
    let game_root = temp.path().join("Fallout4");
    let docs_root = temp.path().join("Docs");
    fs::create_dir_all(&game_root).expect("game root");
    fs::create_dir_all(&docs_root).expect("docs root");
    fs::write(game_root.join("Fallout4.exe"), b"not a real pe").expect("fake exe");
    (temp, game_root, docs_root)
}

fn write_valid_docs_inis(docs_root: &Path) {
    fs::write(docs_root.join("Fallout4.ini"), "[General]\n").expect("main ini");
    fs::write(docs_root.join("Fallout4Custom.ini"), "[Archive]\n").expect("custom ini");
    fs::write(docs_root.join("Fallout4Prefs.ini"), "[General]\n").expect("prefs ini");
}

#[test]
fn normalizes_game_setup_version_selection_aliases() {
    assert_eq!(normalize_game_setup_version_selection(""), "auto");
    assert_eq!(normalize_game_setup_version_selection("og"), "Original");
    assert_eq!(normalize_game_setup_version_selection("NG"), "NextGen");
    assert_eq!(
        normalize_game_setup_version_selection("Anniversary Edition"),
        "AnniversaryEdition"
    );
    assert_eq!(normalize_game_setup_version_selection("VR"), "VR");
    assert_eq!(normalize_game_setup_version_selection("nonsense"), "auto");
}

#[test]
fn game_setup_path_detection_treats_blank_values_as_missing() {
    assert_eq!(game_setup_needs_path_detection(None, None), (true, true));
    assert_eq!(
        game_setup_needs_path_detection(Some("C:/Games/Fallout4"), Some("")),
        (false, true)
    );
    assert_eq!(
        game_setup_needs_path_detection(Some("C:/Games/Fallout4"), Some("C:/Docs")),
        (false, false)
    );
}

#[test]
fn docs_relative_path_uses_proton_safe_separator() {
    assert_eq!(docs_relative_path("Fallout4"), "My Games/Fallout4");
    assert_eq!(docs_relative_path("Fallout4VR"), "My Games/Fallout4VR");
}

#[test]
fn from_config_requires_saved_game_root() {
    let config = classic_config_core::ClassicConfig::default();

    assert!(GameSetupIntake::from_config(&config, GameId::Fallout4).is_none());
}

#[test]
fn from_config_prefers_docs_root_over_ini_folder() {
    let (_temp, game_root, docs_root) = setup_roots();
    let ini_folder = docs_root.with_file_name("IniFallback");
    let mut config = classic_config_core::ClassicConfig {
        game_version: "NextGen".to_string(),
        ..classic_config_core::ClassicConfig::default()
    };
    config.paths.game_root = game_root.clone();
    config.paths.docs_root = Some(docs_root.clone());
    config.paths.ini_folder = Some(ini_folder);

    let intake = GameSetupIntake::from_config(&config, GameId::Fallout4)
        .expect("saved game root should build intake");

    assert_eq!(intake.selected_game_version, "NextGen");
    assert_eq!(intake.game_root.as_deref(), Some(game_root.as_path()));
    assert_eq!(intake.docs_root.as_deref(), Some(docs_root.as_path()));
}

#[test]
fn from_config_uses_ini_folder_as_legacy_docs_fallback() {
    let (_temp, game_root, docs_root) = setup_roots();
    let mut config = classic_config_core::ClassicConfig::default();
    config.paths.game_root = game_root;
    config.paths.ini_folder = Some(docs_root.clone());

    let intake = GameSetupIntake::from_config(&config, GameId::Fallout4)
        .expect("saved game root should build intake");

    assert_eq!(intake.docs_root.as_deref(), Some(docs_root.as_path()));
}

#[test]
fn registry_auto_candidates_keep_fallout4_non_vr() {
    let candidates = registry_auto_candidates(get_version_registry(), GameId::Fallout4);

    assert!(
        candidates.iter().any(|info| info.id == "FO4_OG"),
        "expected classic Fallout 4 candidates"
    );
    assert!(
        candidates.iter().all(|info| info.id != "FO4_VR"),
        "Fallout 4 auto detection must not include the VR registry entry"
    );
}

#[test]
fn registry_auto_candidates_prefer_fallout4vr_registry_identity() {
    let candidates = registry_auto_candidates(get_version_registry(), GameId::Fallout4VR);

    assert_eq!(registry_game_names(GameId::Fallout4VR)[0], "Fallout4VR");
    assert!(
        candidates.iter().any(|info| info.id == "FO4_VR"),
        "expected the Fallout 4 VR registry entry"
    );
    assert!(
        candidates.iter().all(|info| info.id == "FO4_VR"),
        "Fallout 4 VR auto detection should only consider VR registry metadata"
    );
}

#[test]
fn executable_hash_matching_uses_registry_candidates() {
    let temp = TempDir::new().expect("temp dir");
    let exe_path = temp.path().join("Fallout4VR.exe");
    fs::write(&exe_path, b"registered by hash").expect("fake exe");
    let exe_hash = FileHasher::hash_file(&exe_path).expect("hash fake exe");
    let candidate = VersionInfo {
        id: "FO4_VR".to_string(),
        game: "Fallout4VR".to_string(),
        is_vr: true,
        version: RegistryGameVersion::new(1, 2, 72, 0),
        display_name: "Fallout 4 VR".to_string(),
        short_name: "VR".to_string(),
        description: "Virtual Reality version".to_string(),
        docs_name: "Fallout4VR".to_string(),
        steam_id: 611660,
        address_library: None,
        xse: None,
        compatible_range: None,
        priority: 100,
        deprecated: false,
        exe_hash: Some(exe_hash),
        crashgen_versions: Vec::new(),
    };
    let mut facts = GameSetupVersionFacts::default();

    let matched =
        detect_registry_info_from_exe(&exe_path, &[candidate], &mut facts).expect("hash match");

    assert_eq!(matched.id, "FO4_VR");
    assert_eq!(facts.match_confidence.as_deref(), Some("exact"));
}

#[test]
fn explicit_vr_selection_from_fallout4_uses_vr_executable_docs_and_xse() {
    let temp = TempDir::new().expect("temp dir");
    let game_root = temp.path().join("Fallout4VR");
    let docs_root = temp.path().join("Docs").join("Fallout4VR");
    fs::create_dir_all(&game_root).expect("game root");
    fs::create_dir_all(&docs_root).expect("docs root");
    fs::write(game_root.join("Fallout4VR.exe"), b"not a real pe").expect("fake vr exe");
    fs::write(game_root.join("f4sevr_loader.exe"), b"loader").expect("vr loader");
    fs::write(game_root.join("f4sevr_0_6_20.dll"), b"dll").expect("vr version dll");

    let result = GameSetupIntake::new(GameId::Fallout4, "VR")
        .with_game_root(&game_root)
        .with_docs_root(&docs_root)
        .run();

    assert_eq!(result.status, GameSetupIntakeStatus::Ready);
    assert!(
        !result
            .actions
            .contains(&GameSetupRequiredAction::ChooseGamePath)
    );
    let expected_exe = game_root.join("Fallout4VR.exe");
    assert_eq!(
        result.paths.game_exe_path.as_deref(),
        Some(expected_exe.as_path())
    );
    assert_eq!(result.version.registry_id.as_deref(), Some("FO4_VR"));

    let xse_loader = result
        .checks
        .iter()
        .find(|check| check.kind == GameSetupCheckKind::XseLoader)
        .expect("xse loader check");
    assert_eq!(xse_loader.state, GameSetupCheckState::Passed);
    assert!(xse_loader.message.contains("F4SEVR loader is installed."));

    let xse_version = result
        .checks
        .iter()
        .find(|check| check.kind == GameSetupCheckKind::XseVersion)
        .expect("xse version check");
    assert_eq!(xse_version.state, GameSetupCheckState::Passed);
    assert!(
        xse_version
            .message
            .contains("Detected F4SEVR version 0.6.20")
    );

    let documents = result
        .checks
        .iter()
        .find(|check| check.kind == GameSetupCheckKind::DocumentsFolder)
        .expect("documents check");
    assert!(
        documents
            .details
            .iter()
            .any(|detail| detail.contains("Fallout4VR.ini")),
        "VR selections should validate Fallout4VR INI names"
    );
}

#[test]
fn intake_returns_ready_diagnostics_for_explicit_paths() {
    let (_temp, game_root, docs_root) = setup_roots();
    let result = GameSetupIntake::new(GameId::Fallout4, "Original")
        .with_game_root(&game_root)
        .with_docs_root(&docs_root)
        .run();

    assert_eq!(result.status, GameSetupIntakeStatus::Ready);
    assert_eq!(result.paths.game_root.as_deref(), Some(game_root.as_path()));
    assert_eq!(result.paths.docs_root.as_deref(), Some(docs_root.as_path()));
    assert!(result.path_updates.is_empty());
    assert!(
        result
            .checks
            .iter()
            .any(|check| check.kind == GameSetupCheckKind::ExecutableHash)
    );
    assert!(result.rendered_report.contains("Game Setup Intake"));
}

#[test]
fn auto_without_registry_match_requests_version_choice() {
    let (_temp, game_root, docs_root) = setup_roots();
    let result = GameSetupIntake::new(GameId::Fallout4, "auto")
        .with_game_root(&game_root)
        .with_docs_root(&docs_root)
        .run();

    assert_eq!(result.status, GameSetupIntakeStatus::ActionRequired);
    assert!(
        result
            .actions
            .contains(&GameSetupRequiredAction::ChooseGameVersion)
    );
}

#[test]
fn configured_game_exe_path_allows_non_default_executable_under_root() {
    let temp = TempDir::new().expect("temp dir");
    let game_root = temp.path().join("Fallout4");
    let docs_root = temp.path().join("Docs");
    fs::create_dir_all(&game_root).expect("game root");
    fs::create_dir_all(&docs_root).expect("docs root");
    write_valid_docs_inis(&docs_root);
    let configured_exe = game_root.join("Fallout4Custom.exe");
    fs::write(&configured_exe, b"not a real pe").expect("configured exe");
    fs::write(game_root.join("f4se_loader.exe"), b"loader").expect("loader");

    let result = GameSetupIntake::new(GameId::Fallout4, "auto")
        .with_game_root(&game_root)
        .with_game_exe_path(&configured_exe)
        .with_docs_root(&docs_root)
        .run();

    assert_eq!(result.status, GameSetupIntakeStatus::ActionRequired);
    assert!(!result.has_errors());
    assert_eq!(result.paths.game_root.as_deref(), Some(game_root.as_path()));
    assert_eq!(
        result.paths.game_exe_path.as_deref(),
        Some(configured_exe.as_path())
    );
    assert!(
        !result
            .actions
            .contains(&GameSetupRequiredAction::ChooseGamePath)
    );
    assert!(
        result
            .actions
            .contains(&GameSetupRequiredAction::ChooseGameVersion)
    );
}

#[test]
fn unsupported_game_id_returns_registry_diagnostic() {
    let (_temp, game_root, docs_root) = setup_roots();
    fs::write(game_root.join("Starfield.exe"), b"fake").expect("fake starfield exe");

    let result = GameSetupIntake::new(GameId::Starfield, "auto")
        .with_game_root(&game_root)
        .with_docs_root(&docs_root)
        .run();

    assert!(
        result.checks.iter().any(|check| {
            check.kind == GameSetupCheckKind::RegistryMetadata
                && check.state == GameSetupCheckState::Unsupported
        }),
        "expected unsupported registry metadata diagnostic"
    );
}

#[test]
fn complete_xse_checks_use_registry_expectations() {
    let (_temp, game_root, docs_root) = setup_roots();
    fs::write(game_root.join("f4se_loader.exe"), b"loader").expect("loader");
    fs::write(game_root.join("f4se_0_6_23.dll"), b"dll").expect("version dll");
    let plugins = game_root.join("Data").join("F4SE").join("Plugins");
    fs::create_dir_all(&plugins).expect("plugins");
    fs::write(plugins.join("version-1-10-163-0.bin"), b"address lib").expect("address lib");

    let result = GameSetupIntake::new(GameId::Fallout4, "Original")
        .with_game_root(&game_root)
        .with_docs_root(&docs_root)
        .run();

    assert!(
        result.checks.iter().any(|check| {
            check.kind == GameSetupCheckKind::XseVersion
                && check.state == GameSetupCheckState::Passed
        }),
        "expected XSE version to pass"
    );
    assert!(
        result.checks.iter().any(|check| {
            check.kind == GameSetupCheckKind::AddressLibrary
                && check.state == GameSetupCheckState::Passed
        }),
        "expected Address Library to pass"
    );
    assert!(
        result.checks.iter().any(|check| {
            check.kind == GameSetupCheckKind::XseScriptHashes
                && check.state == GameSetupCheckState::Failed
        }),
        "expected script hashes to fail because scripts are absent"
    );
}
