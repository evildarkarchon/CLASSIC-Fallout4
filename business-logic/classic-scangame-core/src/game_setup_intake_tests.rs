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
