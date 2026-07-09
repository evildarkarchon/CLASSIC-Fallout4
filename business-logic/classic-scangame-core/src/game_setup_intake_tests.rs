use super::*;
use std::fs;
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
