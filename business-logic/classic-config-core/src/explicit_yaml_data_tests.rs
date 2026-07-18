use super::{
    ExplicitYamlDataLoadError, ExplicitYamlDataRequest, ExplicitYamlDataRole, GameDataRole,
    load_explicit_yaml_data,
};
use classic_shared_core::GameId;
use std::path::PathBuf;
use tempfile::tempdir;

const MAIN_YAML: &str = r#"schema_version: "2.0"
CLASSIC_Info:
  version: "9.1.0"
  version_date: "2026-07-17"
CLASSIC_Interface:
  autoscan_text_Fallout4: "Explicit autoscan"
catch_log_records: []
"#;

const GAME_YAML: &str = r#"schema_version: "1.0"
Game_Info:
  Main_Root_Name: "Fallout 4"
  XSE_Acronym: "F4SE"
  GameVersion: "1.10.163"
Crashlog_Error_Check: []
Crashlog_Stack_Check: []
Mods_FREQ: []
Mods_SOLU: []
"#;

const EMPTY_IGNORE_YAML: &str = "CLASSIC_Ignore_Fallout4: []\n";

fn write_explicit_files(
    root: &std::path::Path,
    main: &[u8],
    game: &[u8],
    ignore: &[u8],
) -> (PathBuf, PathBuf, PathBuf) {
    let main_path = root.join("tool-selected-main.fixture");
    let game_path = root.join("tool-selected-game.fixture");
    let ignore_path = root.join("tool-selected-ignore.fixture");
    std::fs::write(&main_path, main).expect("main fixture should be written");
    std::fs::write(&game_path, game).expect("game fixture should be written");
    std::fs::write(&ignore_path, ignore).expect("ignore fixture should be written");
    (main_path, game_path, ignore_path)
}

#[tokio::test]
async fn explicit_loader_uses_caller_selected_files_and_accepts_empty_local_ignore() {
    let temp = tempdir().expect("temporary directory should be created");
    let (main_path, game_path, ignore_path) = write_explicit_files(
        temp.path(),
        MAIN_YAML.as_bytes(),
        GAME_YAML.as_bytes(),
        EMPTY_IGNORE_YAML.as_bytes(),
    );

    let snapshot = load_explicit_yaml_data(ExplicitYamlDataRequest {
        main_path,
        game_path,
        ignore_path,
        game: GameId::Fallout4,
        selected_game_version: "Original".to_string(),
    })
    .await
    .expect("strict explicit YAML Data should load");

    assert_eq!(snapshot.game_data_role(), GameDataRole::Fallout4);
    assert_eq!(snapshot.yaml_data().classic_version, "9.1.0");
    assert_eq!(snapshot.yaml_data().autoscan_text, "Explicit autoscan");
    assert!(snapshot.yaml_data().ignore_list.is_empty());
    assert_eq!(snapshot.main_identity().byte_len(), MAIN_YAML.len() as u64);
    assert_eq!(snapshot.game_identity().byte_len(), GAME_YAML.len() as u64);
    assert_eq!(
        snapshot.ignore_identity().byte_len(),
        EMPTY_IGNORE_YAML.len() as u64,
    );
}

#[tokio::test]
async fn fallout4_vr_selects_the_shared_fallout4_game_data_role() {
    let temp = tempdir().expect("temporary directory should be created");
    let ignore = "CLASSIC_Ignore_Fallout4:\n  - shared-entry\n";
    let (main_path, game_path, ignore_path) = write_explicit_files(
        temp.path(),
        MAIN_YAML.as_bytes(),
        GAME_YAML.as_bytes(),
        ignore.as_bytes(),
    );

    let snapshot = load_explicit_yaml_data(ExplicitYamlDataRequest {
        main_path,
        game_path,
        ignore_path,
        game: GameId::Fallout4VR,
        selected_game_version: "VR".to_string(),
    })
    .await
    .expect("Fallout 4 VR should use the shared Fallout 4 role");

    assert_eq!(snapshot.game(), GameId::Fallout4VR);
    assert_eq!(snapshot.game_data_role(), GameDataRole::Fallout4);
    assert_eq!(snapshot.yaml_data().ignore_list, ["shared-entry"]);
}

#[tokio::test]
async fn unregistered_game_returns_typed_unsupported_game_without_reading_paths() {
    let missing = PathBuf::from("paths-must-not-be-read-for-an-unsupported-game");
    let error = load_explicit_yaml_data(ExplicitYamlDataRequest {
        main_path: missing.join("main.yaml"),
        game_path: missing.join("game.yaml"),
        ignore_path: missing.join("ignore.yaml"),
        game: GameId::Skyrim,
        selected_game_version: "AnniversaryEdition".to_string(),
    })
    .await
    .expect_err("an unregistered YAML Data role must be rejected");

    assert!(matches!(
        error,
        ExplicitYamlDataLoadError::UnsupportedGame {
            game: GameId::Skyrim
        }
    ));
}

#[tokio::test]
async fn malformed_local_ignore_is_distinct_from_a_valid_empty_sequence() {
    let temp = tempdir().expect("temporary directory should be created");
    let malformed_ignore = "CLASSIC_Ignore_Fallout4: not-a-sequence\n";
    let (main_path, game_path, ignore_path) = write_explicit_files(
        temp.path(),
        MAIN_YAML.as_bytes(),
        GAME_YAML.as_bytes(),
        malformed_ignore.as_bytes(),
    );

    let error = load_explicit_yaml_data(ExplicitYamlDataRequest {
        main_path,
        game_path,
        ignore_path: ignore_path.clone(),
        game: GameId::Fallout4,
        selected_game_version: "Original".to_string(),
    })
    .await
    .expect_err("a scalar Local Ignore value must be rejected");

    assert!(matches!(
        error,
        ExplicitYamlDataLoadError::InvalidRoleData {
            role: ExplicitYamlDataRole::LocalIgnore,
            path,
            ..
        } if path == ignore_path
    ));
}

#[tokio::test]
async fn snapshot_data_and_identity_remain_bound_to_the_original_owned_bytes() {
    let temp = tempdir().expect("temporary directory should be created");
    let (main_path, game_path, ignore_path) = write_explicit_files(
        temp.path(),
        MAIN_YAML.as_bytes(),
        GAME_YAML.as_bytes(),
        EMPTY_IGNORE_YAML.as_bytes(),
    );

    let snapshot = load_explicit_yaml_data(ExplicitYamlDataRequest {
        main_path: main_path.clone(),
        game_path: game_path.clone(),
        ignore_path: ignore_path.clone(),
        game: GameId::Fallout4,
        selected_game_version: "Original".to_string(),
    })
    .await
    .expect("explicit snapshot should load");
    let original_identities = (
        snapshot.main_identity().clone(),
        snapshot.game_identity().clone(),
        snapshot.ignore_identity().clone(),
    );

    std::fs::write(&main_path, b"replacement main bytes").expect("main source should be replaced");
    std::fs::write(&game_path, b"replacement game bytes").expect("game source should be replaced");
    std::fs::write(&ignore_path, b"replacement ignore bytes")
        .expect("ignore source should be replaced");

    assert_eq!(snapshot.yaml_data().classic_version, "9.1.0");
    assert_eq!(snapshot.main_identity(), &original_identities.0);
    assert_eq!(snapshot.game_identity(), &original_identities.1);
    assert_eq!(snapshot.ignore_identity(), &original_identities.2);
    assert_eq!(snapshot.main_identity().sha256_hex().len(), 64);
}

#[tokio::test]
async fn explicit_loading_does_not_fallback_generate_or_self_heal() {
    let temp = tempdir().expect("temporary directory should be created");
    let explicit_root = temp.path().join("explicit");
    let installed_databases = temp.path().join("CLASSIC Data").join("databases");
    let cache_root = temp.path().join("yaml-cache");
    std::fs::create_dir_all(&explicit_root).expect("explicit root should be created");
    std::fs::create_dir_all(&installed_databases)
        .expect("installed decoy directory should be created");
    std::fs::create_dir_all(&cache_root).expect("cache decoy directory should be created");

    let missing_main = explicit_root.join("missing-main.yaml");
    let explicit_game = explicit_root.join("game.yaml");
    let missing_ignore = explicit_root.join("missing-ignore.yaml");
    std::fs::write(&explicit_game, GAME_YAML).expect("explicit game should be written");
    std::fs::write(installed_databases.join("CLASSIC Main.yaml"), MAIN_YAML)
        .expect("bundled decoy should be written");
    let previous_cache = cache_root.join("CLASSIC Main.yaml.prev");
    std::fs::write(&previous_cache, b"previous-cache-sentinel")
        .expect("previous cache decoy should be written");

    let error = load_explicit_yaml_data(ExplicitYamlDataRequest {
        main_path: missing_main.clone(),
        game_path: explicit_game,
        ignore_path: missing_ignore.clone(),
        game: GameId::Fallout4,
        selected_game_version: "Original".to_string(),
    })
    .await
    .expect_err("missing explicit inputs must not fall back to installed data");

    assert!(matches!(
        error,
        ExplicitYamlDataLoadError::Read {
            role: ExplicitYamlDataRole::Main,
            path,
            ..
        } if path == missing_main
    ));
    assert!(
        !missing_ignore.exists(),
        "Local Ignore must not be generated"
    );
    assert_eq!(
        std::fs::read(&previous_cache).expect("previous cache decoy should remain"),
        b"previous-cache-sentinel",
    );
    assert!(
        !cache_root.join("CLASSIC Main.yaml").exists(),
        ".prev must not be promoted by explicit loading",
    );
    assert!(
        !explicit_root.join("missing-main.yaml.bak").exists(),
        "explicit loading must not create backups",
    );
}

#[tokio::test]
async fn local_ignore_syntax_failure_reports_the_local_ignore_role() {
    let temp = tempdir().expect("temporary directory should be created");
    let (main_path, game_path, ignore_path) = write_explicit_files(
        temp.path(),
        MAIN_YAML.as_bytes(),
        GAME_YAML.as_bytes(),
        b"CLASSIC_Ignore_Fallout4: [unterminated",
    );

    let error = load_explicit_yaml_data(ExplicitYamlDataRequest {
        main_path,
        game_path,
        ignore_path: ignore_path.clone(),
        game: GameId::Fallout4,
        selected_game_version: "Original".to_string(),
    })
    .await
    .expect_err("malformed Local Ignore syntax must be rejected");

    assert!(matches!(
        error,
        ExplicitYamlDataLoadError::Parse {
            role: ExplicitYamlDataRole::LocalIgnore,
            path,
            ..
        } if path == ignore_path
    ));
}

#[tokio::test]
async fn game_file_must_semantically_match_the_selected_game_data_role() {
    let temp = tempdir().expect("temporary directory should be created");
    let wrong_game = GAME_YAML.replace(
        "Main_Root_Name: \"Fallout 4\"",
        "Main_Root_Name: \"Skyrim\"",
    );
    let (main_path, game_path, ignore_path) = write_explicit_files(
        temp.path(),
        MAIN_YAML.as_bytes(),
        wrong_game.as_bytes(),
        EMPTY_IGNORE_YAML.as_bytes(),
    );

    let error = load_explicit_yaml_data(ExplicitYamlDataRequest {
        main_path,
        game_path: game_path.clone(),
        ignore_path,
        game: GameId::Fallout4,
        selected_game_version: "Original".to_string(),
    })
    .await
    .expect_err("the game document must match the registered Fallout 4 role");

    assert!(matches!(
        error,
        ExplicitYamlDataLoadError::InvalidRoleData {
            role: ExplicitYamlDataRole::Game,
            path,
            ..
        } if path == game_path
    ));
}

#[tokio::test]
async fn local_ignore_rejects_missing_null_and_non_string_entries() {
    let invalid_documents = [
        "unrelated: []\n",
        "CLASSIC_Ignore_Fallout4: null\n",
        "CLASSIC_Ignore_Fallout4:\n  - valid\n  - 42\n",
    ];

    for invalid_ignore in invalid_documents {
        let temp = tempdir().expect("temporary directory should be created");
        let (main_path, game_path, ignore_path) = write_explicit_files(
            temp.path(),
            MAIN_YAML.as_bytes(),
            GAME_YAML.as_bytes(),
            invalid_ignore.as_bytes(),
        );
        let error = load_explicit_yaml_data(ExplicitYamlDataRequest {
            main_path,
            game_path,
            ignore_path: ignore_path.clone(),
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        })
        .await
        .expect_err("malformed Local Ignore shape must be rejected");

        assert!(matches!(
            error,
            ExplicitYamlDataLoadError::InvalidRoleData {
                role: ExplicitYamlDataRole::LocalIgnore,
                path,
                ..
            } if path == ignore_path
        ));
    }
}

#[tokio::test]
async fn invalid_utf8_is_attributed_to_the_exact_role_and_path() {
    let temp = tempdir().expect("temporary directory should be created");
    let (main_path, game_path, ignore_path) = write_explicit_files(
        temp.path(),
        MAIN_YAML.as_bytes(),
        &[0xff, 0xfe, 0xfd],
        EMPTY_IGNORE_YAML.as_bytes(),
    );

    let error = load_explicit_yaml_data(ExplicitYamlDataRequest {
        main_path,
        game_path: game_path.clone(),
        ignore_path,
        game: GameId::Fallout4,
        selected_game_version: "Original".to_string(),
    })
    .await
    .expect_err("invalid UTF-8 must be rejected before YAML parsing");

    assert!(matches!(
        error,
        ExplicitYamlDataLoadError::InvalidUtf8 {
            role: ExplicitYamlDataRole::Game,
            path,
            ..
        } if path == game_path
    ));
}

#[tokio::test]
async fn main_file_requires_the_schema_two_release_semver_shape() {
    let temp = tempdir().expect("temporary directory should be created");
    let decorated_main = MAIN_YAML.replace("version: \"9.1.0\"", "version: \"CLASSIC v9.1.0\"");
    let (main_path, game_path, ignore_path) = write_explicit_files(
        temp.path(),
        decorated_main.as_bytes(),
        GAME_YAML.as_bytes(),
        EMPTY_IGNORE_YAML.as_bytes(),
    );

    let error = load_explicit_yaml_data(ExplicitYamlDataRequest {
        main_path: main_path.clone(),
        game_path,
        ignore_path,
        game: GameId::Fallout4,
        selected_game_version: "Original".to_string(),
    })
    .await
    .expect_err("decorated legacy version text must fail strict Main semantics");

    assert!(matches!(
        error,
        ExplicitYamlDataLoadError::InvalidRoleData {
            role: ExplicitYamlDataRole::Main,
            path,
            ..
        } if path == main_path
    ));
}

#[tokio::test]
async fn explicit_game_validation_rejects_lossy_structured_and_list_entries() {
    let malformed_sections = [
        (
            "Crashlog_Error_Check: []",
            r#"Crashlog_Error_Check:
  - id: malformed-severity
    name: Malformed severity
    severity: high
    main_error_contains_any: [valid]
"#,
        ),
        (
            "Mods_FREQ: []",
            r#"Mods_FREQ:
  - id: malformed-criteria
    name: Malformed criteria
    description: Must not silently discard non-string criteria
    criteria:
      any: [valid, 42]
"#,
        ),
        (
            "Mods_SOLU: []",
            r#"Mods_SOLU: []
Crashlog_Plugins_Exclude:
  - valid.dll
  - 42
"#,
        ),
        (
            "Mods_SOLU: []",
            r#"Mods_SOLU: []
Crashgen_Registry:
  default:
    checks: [valid, 42]
"#,
        ),
        ("XSE_Acronym: \"F4SE\"", "XSE_Acronym: [F4SE]"),
    ];

    for (valid_section, malformed_section) in malformed_sections {
        let temp = tempdir().expect("temporary directory should be created");
        let malformed_game = GAME_YAML.replace(valid_section, malformed_section);
        let (main_path, game_path, ignore_path) = write_explicit_files(
            temp.path(),
            MAIN_YAML.as_bytes(),
            malformed_game.as_bytes(),
            EMPTY_IGNORE_YAML.as_bytes(),
        );

        let error = load_explicit_yaml_data(ExplicitYamlDataRequest {
            main_path,
            game_path: game_path.clone(),
            ignore_path,
            game: GameId::Fallout4,
            selected_game_version: "Original".to_string(),
        })
        .await
        .expect_err("malformed game entries must not be silently discarded");

        assert!(matches!(
            error,
            ExplicitYamlDataLoadError::InvalidRoleData {
                role: ExplicitYamlDataRole::Game,
                path,
                ..
            } if path == game_path
        ));
    }
}

#[tokio::test]
async fn explicit_main_validation_rejects_lossy_consumed_fields() {
    let malformed_main =
        MAIN_YAML.replace("version_date: \"2026-07-17\"", "version_date: [2026-07-17]");
    let temp = tempdir().expect("temporary directory should be created");
    let (main_path, game_path, ignore_path) = write_explicit_files(
        temp.path(),
        malformed_main.as_bytes(),
        GAME_YAML.as_bytes(),
        EMPTY_IGNORE_YAML.as_bytes(),
    );

    let error = load_explicit_yaml_data(ExplicitYamlDataRequest {
        main_path: main_path.clone(),
        game_path,
        ignore_path,
        game: GameId::Fallout4,
        selected_game_version: "Original".to_string(),
    })
    .await
    .expect_err("malformed consumed Main fields must not silently default");

    assert!(matches!(
        error,
        ExplicitYamlDataLoadError::InvalidRoleData {
            role: ExplicitYamlDataRole::Main,
            path,
            ..
        } if path == main_path
    ));
}
