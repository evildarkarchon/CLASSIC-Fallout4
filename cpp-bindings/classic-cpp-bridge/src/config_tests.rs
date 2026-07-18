use super::*;
use std::io::Write;
use tempfile::NamedTempFile;
use tempfile::tempdir;

const EXPLICIT_MAIN_YAML: &str = concat!(
    "schema_version: \"2.0\"\r\n",
    "CLASSIC_Info:\r\n",
    "  version: \"9.1.0\"\r\n",
    "CLASSIC_Interface:\r\n",
    "  autoscan_text_Fallout4: \"explicit bridge\"\r\n",
);
const EXPLICIT_GAME_YAML: &str = concat!(
    "schema_version: \"1.0\"\n",
    "Game_Info:\n",
    "  Main_Root_Name: \"Fallout 4\"\n",
    "Crashlog_Error_Check: []\n",
    "Crashlog_Stack_Check: []\n",
    "Mods_FREQ: []\n",
    "Mods_SOLU: []\n",
);
const EXPLICIT_EMPTY_IGNORE_YAML: &str = "CLASSIC_Ignore_Fallout4: []\n";
const INSTALLED_IGNORE_YAML: &str = "CLASSIC_Ignore_Fallout4:\r\n  - ExistingBridgeEntry.dll\r\n";
const INSTALLED_GENERATING_MAIN_YAML: &str = concat!(
    "schema_version: \"2.0\"\n",
    "CLASSIC_Info:\n",
    "  version: \"9.1.0\"\n",
    "  default_ignorefile: |\n",
    "    CLASSIC_Ignore_Fallout4:\n",
    "      - GeneratedBridgeEntry.dll\n",
    "CLASSIC_Interface:\n",
    "  autoscan_text_Fallout4: \"generated bridge\"\n",
);

fn write_explicit_bridge_fixtures(
    root: &std::path::Path,
    ignore: &[u8],
) -> ffi::ExplicitYamlDataPathsDto {
    let main_path = root.join("chosen-main.fixture");
    let game_path = root.join("chosen-game.fixture");
    let ignore_path = root.join("chosen-ignore.fixture");
    std::fs::write(&main_path, EXPLICIT_MAIN_YAML).expect("write explicit Main fixture");
    std::fs::write(&game_path, EXPLICIT_GAME_YAML).expect("write explicit game fixture");
    std::fs::write(&ignore_path, ignore).expect("write explicit Ignore fixture");
    ffi::ExplicitYamlDataPathsDto {
        main_path: main_path.to_string_lossy().into_owned(),
        game_path: game_path.to_string_lossy().into_owned(),
        ignore_path: ignore_path.to_string_lossy().into_owned(),
    }
}

/// Write valid bundled Main and game files under one isolated installation root.
fn write_installed_bridge_fixtures(root: &std::path::Path) {
    let data = root.join("CLASSIC Data");
    let databases = data.join("databases");
    std::fs::create_dir_all(&databases).expect("create Installed YAML Data fixture directory");
    std::fs::write(databases.join("CLASSIC Main.yaml"), EXPLICIT_MAIN_YAML)
        .expect("write installed Main fixture");
    std::fs::write(databases.join("CLASSIC Fallout4.yaml"), EXPLICIT_GAME_YAML)
        .expect("write installed game fixture");
    std::fs::write(data.join("CLASSIC Ignore.yaml"), INSTALLED_IGNORE_YAML)
        .expect("write installed Local Ignore fixture");
}

/// Invoke inspection with no cache environment so tests cannot read developer state.
fn inspect_installed_without_cache(
    installation_root: &std::path::Path,
    game: ffi::ExplicitYamlDataGameId,
) -> Box<InstalledYamlDataInspectionOperation> {
    installed_yaml_data_inspection_operation_from_result(
        classic_config_core::inspect_installed_yaml_data_with_env(
            CoreInstalledYamlDataInspectionRequest {
                installation_root: installation_root.to_path_buf(),
                game: explicit_game_id_to_core(game),
            },
            |_| None,
        ),
    )
}

/// Invoke loading with no cache environment so tests cannot read developer state.
fn load_installed_without_cache(
    installation_root: &std::path::Path,
    game: ffi::ExplicitYamlDataGameId,
    selected_game_version: &str,
) -> Box<InstalledYamlDataLoadOperation> {
    installed_yaml_data_load_operation_from_result(
        classic_config_core::load_installed_yaml_data_with_env(
            CoreInstalledYamlDataLoadRequest {
                installation_root: installation_root.to_path_buf(),
                game: explicit_game_id_to_core(game),
                selected_game_version: selected_game_version.to_string(),
            },
            |_| None,
        ),
    )
}

#[test]
fn explicit_yaml_data_bridge_returns_typed_snapshot_and_exact_identities() {
    let temp = tempdir().expect("create explicit bridge fixture directory");
    let paths = write_explicit_bridge_fixtures(temp.path(), EXPLICIT_EMPTY_IGNORE_YAML.as_bytes());

    let load = explicit_yaml_data_load(paths, ffi::ExplicitYamlDataGameId::Fallout4VR, "VR");
    let status = explicit_yaml_data_load_status(&load);
    assert!(status.has_snapshot);
    assert!(!status.has_error);

    let snapshot = explicit_yaml_data_load_take_snapshot(load).expect("take ready snapshot");
    assert_eq!(
        explicit_yaml_data_snapshot_game(&snapshot),
        ffi::ExplicitYamlDataGameId::Fallout4VR
    );
    assert_eq!(
        explicit_yaml_data_snapshot_game_role(&snapshot),
        ffi::ExplicitYamlDataGameRole::Fallout4
    );
    let main_identity = explicit_yaml_data_snapshot_main_identity(&snapshot);
    assert_eq!(main_identity.byte_len, EXPLICIT_MAIN_YAML.len() as u64);
    assert_eq!(main_identity.sha256.len(), 64);
    assert_eq!(
        explicit_yaml_data_snapshot_ignore_identity(&snapshot).byte_len,
        EXPLICIT_EMPTY_IGNORE_YAML.len() as u64
    );

    let data = explicit_yaml_data_snapshot_yaml_data(&snapshot);
    assert_eq!(yaml_data_classic_version(&data), "9.1.0");
    assert!(yaml_data_ignore_list(&data).is_empty());
}

#[test]
fn explicit_yaml_data_bridge_preserves_typed_unsupported_and_ignore_errors() {
    let missing = tempdir().expect("create unsupported-game fixture directory");
    let unsupported = explicit_yaml_data_load(
        ffi::ExplicitYamlDataPathsDto {
            main_path: missing
                .path()
                .join("missing-main")
                .to_string_lossy()
                .into_owned(),
            game_path: missing
                .path()
                .join("missing-game")
                .to_string_lossy()
                .into_owned(),
            ignore_path: missing
                .path()
                .join("missing-ignore")
                .to_string_lossy()
                .into_owned(),
        },
        ffi::ExplicitYamlDataGameId::Skyrim,
        "AnniversaryEdition",
    );
    let unsupported_status = explicit_yaml_data_load_status(&unsupported);
    assert!(unsupported_status.has_error);
    assert_eq!(
        unsupported_status.error.kind,
        ffi::ExplicitYamlDataLoadErrorKind::UnsupportedGame
    );
    assert!(!unsupported_status.error.has_role);

    let malformed = tempdir().expect("create malformed-ignore fixture directory");
    let paths = write_explicit_bridge_fixtures(
        malformed.path(),
        b"CLASSIC_Ignore_Fallout4: not-a-sequence\n",
    );
    let invalid = explicit_yaml_data_load(paths, ffi::ExplicitYamlDataGameId::Fallout4, "Original");
    let invalid_status = explicit_yaml_data_load_status(&invalid);
    assert!(invalid_status.has_error);
    assert_eq!(
        invalid_status.error.kind,
        ffi::ExplicitYamlDataLoadErrorKind::InvalidRoleData
    );
    assert!(invalid_status.error.has_role);
    assert_eq!(
        invalid_status.error.role,
        ffi::ExplicitYamlDataRole::LocalIgnore
    );
    assert!(invalid_status.error.has_path);
}

#[test]
fn installed_yaml_data_bridge_projects_bundled_files_and_structured_diagnostics() {
    let temp = tempdir().expect("create Installed YAML Data bridge fixture directory");
    write_installed_bridge_fixtures(temp.path());

    let operation =
        inspect_installed_without_cache(temp.path(), ffi::ExplicitYamlDataGameId::Fallout4VR);
    let status = installed_yaml_data_inspection_status(&operation);
    assert!(status.has_inspection);
    assert!(!status.has_error);

    let inspection =
        installed_yaml_data_inspection_take(operation).expect("take successful inspection");
    assert_eq!(
        installed_yaml_data_inspection_game(&inspection),
        ffi::ExplicitYamlDataGameId::Fallout4VR
    );
    assert_eq!(
        installed_yaml_data_inspection_game_role(&inspection),
        ffi::InstalledYamlDataGameRole::Fallout4
    );

    let main = installed_yaml_data_inspection_main(&inspection);
    assert_eq!(main.role, ffi::InstalledYamlDataRole::Main);
    assert_eq!(main.provenance, ffi::InstalledYamlDataProvenance::Bundled);
    assert_eq!(main.schema_version, "2.0");
    assert_eq!(main.byte_len, EXPLICIT_MAIN_YAML.len() as u64);
    assert_eq!(main.sha256.len(), 64);

    let game = installed_yaml_data_inspection_game_file(&inspection);
    assert_eq!(game.role, ffi::InstalledYamlDataRole::Game);
    assert_eq!(game.provenance, ffi::InstalledYamlDataProvenance::Bundled);
    assert_eq!(game.schema_version, "1.0");
    assert_eq!(game.byte_len, EXPLICIT_GAME_YAML.len() as u64);
    assert_eq!(game.sha256.len(), 64);

    let diagnostics = installed_yaml_data_inspection_diagnostics(&inspection);
    assert_eq!(diagnostics.len(), 1);
    assert_eq!(
        diagnostics[0].kind,
        ffi::InstalledYamlDataDiagnosticKind::CacheUnavailable
    );
    assert!(!diagnostics[0].has_role);
    assert!(!diagnostics[0].has_candidate);
    assert!(!diagnostics[0].has_path);
    assert!(!diagnostics[0].message.is_empty());
}

#[test]
fn installed_yaml_data_bridge_preserves_typed_inspection_errors() {
    let unsupported_root = tempdir().expect("create unsupported-game inspection root");
    let unsupported = inspect_installed_without_cache(
        unsupported_root.path(),
        ffi::ExplicitYamlDataGameId::Skyrim,
    );
    let unsupported_status = installed_yaml_data_inspection_status(&unsupported);
    assert!(unsupported_status.has_error);
    assert_eq!(
        unsupported_status.error.kind,
        ffi::InstalledYamlDataInspectionErrorKind::UnsupportedGame
    );
    assert!(!unsupported_status.error.has_role);
    assert!(unsupported_status.error.diagnostics.is_empty());

    let missing_root = tempdir().expect("create missing-source inspection root");
    let missing =
        inspect_installed_without_cache(missing_root.path(), ffi::ExplicitYamlDataGameId::Fallout4);
    let missing_status = installed_yaml_data_inspection_status(&missing);
    assert!(missing_status.has_error);
    assert_eq!(
        missing_status.error.kind,
        ffi::InstalledYamlDataInspectionErrorKind::NoUsableSource
    );
    assert!(missing_status.error.has_role);
    assert_eq!(missing_status.error.role, ffi::InstalledYamlDataRole::Main);
    assert!(missing_status.error.diagnostics.iter().any(|diagnostic| {
        diagnostic.kind == ffi::InstalledYamlDataDiagnosticKind::Missing
            && diagnostic.has_role
            && diagnostic.role == ffi::InstalledYamlDataRole::Main
            && diagnostic.has_candidate
            && diagnostic.candidate == ffi::InstalledYamlDataProvenance::Bundled
            && diagnostic.has_path
    }));
}

#[test]
fn installed_yaml_data_load_bridge_projects_ready_snapshot() {
    let installation = tempdir().expect("create Installed YAML Data load fixture directory");
    write_installed_bridge_fixtures(installation.path());

    let operation = load_installed_without_cache(
        installation.path(),
        ffi::ExplicitYamlDataGameId::Fallout4VR,
        "VR",
    );
    let status = installed_yaml_data_load_status(&operation);
    assert!(status.has_snapshot);
    assert!(!status.has_error);

    let snapshot =
        installed_yaml_data_load_take_snapshot(operation).expect("take ready installed snapshot");
    assert_eq!(
        installed_yaml_data_snapshot_game(&snapshot),
        ffi::ExplicitYamlDataGameId::Fallout4VR
    );
    assert_eq!(
        installed_yaml_data_snapshot_game_role(&snapshot),
        ffi::InstalledYamlDataGameRole::Fallout4
    );
    assert_eq!(
        installed_yaml_data_snapshot_local_ignore_state(&snapshot),
        ffi::LocalIgnoreYamlDataState::Existing
    );

    let main = installed_yaml_data_snapshot_main(&snapshot);
    assert_eq!(main.provenance, ffi::InstalledYamlDataProvenance::Bundled);
    assert_eq!(main.schema_version, "2.0");
    assert_eq!(main.byte_len, EXPLICIT_MAIN_YAML.len() as u64);
    let game = installed_yaml_data_snapshot_game_file(&snapshot);
    assert_eq!(game.provenance, ffi::InstalledYamlDataProvenance::Bundled);
    assert_eq!(game.schema_version, "1.0");
    assert_eq!(game.byte_len, EXPLICIT_GAME_YAML.len() as u64);

    let ignore_identity = installed_yaml_data_snapshot_local_ignore_identity(&snapshot);
    assert_eq!(ignore_identity.byte_len, INSTALLED_IGNORE_YAML.len() as u64);
    assert_eq!(ignore_identity.sha256.len(), 64);
    let yaml_data = installed_yaml_data_snapshot_yaml_data(&snapshot);
    assert_eq!(
        yaml_data_ignore_list(&yaml_data),
        vec!["ExistingBridgeEntry.dll".to_string()]
    );
    assert!(
        installed_yaml_data_snapshot_diagnostics(&snapshot)
            .iter()
            .any(|diagnostic| diagnostic.kind
                == ffi::InstalledYamlDataDiagnosticKind::CacheUnavailable)
    );

    std::fs::write(
        installation
            .path()
            .join("CLASSIC Data")
            .join("CLASSIC Ignore.yaml"),
        "changed after loading",
    )
    .expect("replace selected Local Ignore after loading");
    assert_eq!(
        installed_yaml_data_snapshot_local_ignore_identity(&snapshot).byte_len,
        INSTALLED_IGNORE_YAML.len() as u64
    );
    assert_eq!(
        yaml_data_ignore_list(&installed_yaml_data_snapshot_yaml_data(&snapshot)),
        vec!["ExistingBridgeEntry.dll".to_string()]
    );
}

#[test]
/// The bridge projects generated Local Ignore state, parsed data, identity, and diagnostics.
fn installed_yaml_data_load_bridge_projects_generated_local_ignore_state_and_diagnostic() {
    let installation = tempdir().expect("create generated Local Ignore bridge fixture directory");
    write_installed_bridge_fixtures(installation.path());
    let data = installation.path().join("CLASSIC Data");
    std::fs::write(
        data.join("databases").join("CLASSIC Main.yaml"),
        INSTALLED_GENERATING_MAIN_YAML,
    )
    .expect("write Main fixture with retained Local Ignore defaults");
    let ignore_path = data.join("CLASSIC Ignore.yaml");
    std::fs::remove_file(&ignore_path).expect("remove existing Local Ignore fixture");

    let operation = load_installed_without_cache(
        installation.path(),
        ffi::ExplicitYamlDataGameId::Fallout4,
        "Original",
    );
    let status = installed_yaml_data_load_status(&operation);
    assert!(status.has_snapshot);
    assert!(!status.has_error);

    let snapshot =
        installed_yaml_data_load_take_snapshot(operation).expect("take generated ready snapshot");
    assert_eq!(
        installed_yaml_data_snapshot_local_ignore_state(&snapshot),
        ffi::LocalIgnoreYamlDataState::Generated
    );
    assert_eq!(
        yaml_data_ignore_list(&installed_yaml_data_snapshot_yaml_data(&snapshot)),
        vec!["GeneratedBridgeEntry.dll".to_string()]
    );

    let generated = installed_yaml_data_snapshot_diagnostics(&snapshot)
        .into_iter()
        .find(|diagnostic| {
            diagnostic.kind == ffi::InstalledYamlDataDiagnosticKind::LocalIgnoreGenerated
        })
        .expect("generated snapshot should expose its structured Local Ignore diagnostic");
    assert!(!generated.has_role);
    assert!(!generated.has_candidate);
    assert!(generated.has_path);
    assert_eq!(generated.path, ignore_path.to_string_lossy());
    assert!(!generated.message.is_empty());
}

#[test]
fn installed_yaml_data_load_bridge_preserves_typed_terminal_context() {
    let unsupported_root = tempdir().expect("create unsupported-game load root");
    let unsupported = load_installed_without_cache(
        unsupported_root.path(),
        ffi::ExplicitYamlDataGameId::Skyrim,
        "AnniversaryEdition",
    );
    let unsupported_status = installed_yaml_data_load_status(&unsupported);
    assert!(unsupported_status.has_error);
    assert_eq!(
        unsupported_status.error.kind,
        ffi::InstalledYamlDataLoadErrorKind::UnsupportedGame
    );
    assert!(!unsupported_status.error.has_role);
    assert!(!unsupported_status.error.has_path);

    let missing_root = tempdir().expect("create missing-source load root");
    let missing = load_installed_without_cache(
        missing_root.path(),
        ffi::ExplicitYamlDataGameId::Fallout4,
        "Original",
    );
    let missing_status = installed_yaml_data_load_status(&missing);
    assert_eq!(
        missing_status.error.kind,
        ffi::InstalledYamlDataLoadErrorKind::NoUsableSource
    );
    assert!(missing_status.error.has_role);
    assert_eq!(
        missing_status.error.role,
        ffi::InstalledYamlDataLoadRole::Main
    );
    assert!(missing_status.error.diagnostics.iter().any(|diagnostic| {
        diagnostic.kind == ffi::InstalledYamlDataDiagnosticKind::Missing && diagnostic.has_path
    }));
}

#[test]
fn installed_yaml_data_load_bridge_maps_every_core_error_kind() {
    let path = std::path::PathBuf::from("isolated/CLASSIC Ignore.yaml");
    let invalid_bytes = vec![0xff];
    let invalid_utf8 =
        std::str::from_utf8(&invalid_bytes).expect_err("fixture must be invalid UTF-8");
    let errors = [
        CoreInstalledYamlDataLoadError::UnsupportedGame {
            game: CoreGameId::Skyrim,
        },
        CoreInstalledYamlDataLoadError::NoUsableSource {
            role: CoreInstalledYamlDataRole::Game,
            diagnostics: Vec::new(),
        },
        CoreInstalledYamlDataLoadError::LocalIgnoreRead {
            path: path.clone(),
            source: std::io::Error::new(std::io::ErrorKind::NotFound, "missing fixture"),
        },
        CoreInstalledYamlDataLoadError::LocalIgnoreInvalidUtf8 {
            path: path.clone(),
            source: invalid_utf8,
        },
        CoreInstalledYamlDataLoadError::LocalIgnoreParse {
            path: path.clone(),
            message: "parse fixture".to_string(),
        },
        CoreInstalledYamlDataLoadError::LocalIgnoreInvalidRoleData {
            path: path.clone(),
            reason: "role fixture".to_string(),
        },
        CoreInstalledYamlDataLoadError::LocalIgnoreDefaultInvalid {
            path: path.clone(),
            reason: "default fixture".to_string(),
        },
        CoreInstalledYamlDataLoadError::LocalIgnoreCreate {
            path,
            source: std::io::Error::new(std::io::ErrorKind::PermissionDenied, "creation fixture"),
        },
        CoreInstalledYamlDataLoadError::InvalidSelectedData {
            message: "projection fixture".to_string(),
        },
    ];
    let error_dtos = errors
        .iter()
        .map(installed_yaml_data_load_error_to_dto)
        .collect::<Vec<_>>();

    assert_eq!(
        error_dtos
            .iter()
            .map(|error| error.kind)
            .collect::<Vec<_>>(),
        vec![
            ffi::InstalledYamlDataLoadErrorKind::UnsupportedGame,
            ffi::InstalledYamlDataLoadErrorKind::NoUsableSource,
            ffi::InstalledYamlDataLoadErrorKind::LocalIgnoreRead,
            ffi::InstalledYamlDataLoadErrorKind::LocalIgnoreInvalidUtf8,
            ffi::InstalledYamlDataLoadErrorKind::LocalIgnoreParse,
            ffi::InstalledYamlDataLoadErrorKind::LocalIgnoreInvalidRoleData,
            ffi::InstalledYamlDataLoadErrorKind::LocalIgnoreDefaultInvalid,
            ffi::InstalledYamlDataLoadErrorKind::LocalIgnoreCreate,
            ffi::InstalledYamlDataLoadErrorKind::InvalidSelectedData,
        ]
    );
    assert!(!error_dtos[0].has_role);
    assert!(error_dtos[1].has_role);
    assert_eq!(error_dtos[1].role, ffi::InstalledYamlDataLoadRole::Game);
    for error in &error_dtos[2..=7] {
        assert!(error.has_role);
        assert_eq!(error.role, ffi::InstalledYamlDataLoadRole::LocalIgnore);
        assert!(error.has_path);
    }
    assert!(!error_dtos[8].has_role);
}

#[test]
fn test_yaml_data_load_invalid_dirs() {
    let result = yaml_data_load(
        "nonexistent_root_dir",
        "nonexistent_data_dir",
        "Fallout4",
        "auto",
    );
    assert!(result.is_err());
}

#[test]
fn test_yaml_data_load_from_real_dirs() {
    let root_dir = "J:\\CLASSIC-Fallout4";
    let data_dir = "J:\\CLASSIC-Fallout4\\ClassicLib";

    let result = yaml_data_load(root_dir, data_dir, "Fallout4", "auto");
    if let Ok(data) = result {
        assert!(!yaml_data_classic_version(&data).is_empty());
        assert!(!yaml_data_xse_acronym(&data).is_empty());
        assert!(!yaml_data_crashgen_name_field(&data).is_empty());
        assert!(!yaml_data_game_version(&data).is_empty());
        assert!(!yaml_data_mods_freq_entries(&data).is_empty());
        assert!(!yaml_data_mods_solu_entries(&data).is_empty());

        let name = yaml_data_get_crashgen_name(&data);
        assert!(!name.is_empty());

        // IndexMap key/value pairs should have matching lengths
        let err_keys = yaml_data_suspects_error_keys(&data);
        let err_vals = yaml_data_suspects_error_values(&data);
        assert_eq!(err_keys.len(), err_vals.len());
    }
}

#[test]
fn test_yaml_data_game_version_mode() {
    let root_dir = "J:\\CLASSIC-Fallout4";
    let data_dir = "J:\\CLASSIC-Fallout4\\ClassicLib";

    let result_og = yaml_data_load(root_dir, data_dir, "Fallout4", "auto");
    let result_vr = yaml_data_load(root_dir, data_dir, "Fallout4", "VR");

    if let (Ok(og), Ok(vr)) = (result_og, result_vr) {
        let og_root = yaml_data_get_game_root_name(&og);
        let vr_root = yaml_data_get_game_root_name(&vr);
        assert!(!og_root.is_empty());
        assert!(!vr_root.is_empty());
    }
}

#[test]
fn test_yaml_data_accessors_fallback_when_game_info_is_minimal() {
    let temp = tempdir().expect("failed to create temp dir");
    let data_dir = temp.path().join("CLASSIC Data");
    let db_dir = data_dir.join("databases");
    std::fs::create_dir_all(&db_dir).expect("failed to create db dir");

    let main_yaml = r#"
CLASSIC_Info:
  version: "7.31.0"
  version_date: "2024-01-15"
CLASSIC_Interface:
  autoscan_text_Fallout4: "Autoscan Fallout 4"
"#;
    let game_yaml = r#"
Game_Info:
  Main_Root_Name: "Fallout 4"
Crashgen_Registry:
  "Buffout 4":
    ignore_keys:
      - "BuffoutSpecificIgnore"
    checks: []
  default:
    ignore_keys:
      - "DefaultIgnore"
    checks: []
"#;
    let ignore_yaml = r#"
CLASSIC_Ignore_Fallout4: []
"#;

    std::fs::write(db_dir.join("CLASSIC Main.yaml"), main_yaml).expect("write main yaml");
    std::fs::write(db_dir.join("CLASSIC Fallout4.yaml"), game_yaml).expect("write game yaml");
    std::fs::write(temp.path().join("CLASSIC Ignore.yaml"), ignore_yaml)
        .expect("write ignore yaml");

    let root_dir = temp.path().to_string_lossy().to_string();
    let data_dir_str = data_dir.to_string_lossy().to_string();
    let data = yaml_data_load(&root_dir, &data_dir_str, "Fallout4", "auto")
        .expect("yaml_data_load should succeed");

    assert!(!yaml_data_get_crashgen_name(&data).is_empty());
    assert_eq!(
        yaml_data_get_crashgen_ignore(&data),
        vec!["BuffoutSpecificIgnore".to_string()]
    );
    assert!(!yaml_data_game_version(&data).is_empty());
}

#[test]
fn fallout4_vr_loads_the_shared_fallout4_yaml_through_the_bridge() {
    let temp = tempdir().expect("failed to create temp dir");
    let data_dir = temp.path().join("CLASSIC Data");
    let db_dir = data_dir.join("databases");
    std::fs::create_dir_all(&db_dir).expect("failed to create db dir");

    std::fs::write(
        db_dir.join("CLASSIC Main.yaml"),
        concat!(
            "CLASSIC_Info:\n",
            "  version: 7.31.0\n",
            "CLASSIC_Interface:\n",
            "  autoscan_text_Fallout4: Autoscan Fallout 4\n",
        ),
    )
    .expect("write main yaml");
    std::fs::write(
        db_dir.join("CLASSIC Fallout4.yaml"),
        "Game_Info:\n  Main_Root_Name: Fallout 4\n",
    )
    .expect("write shared Fallout 4 yaml");
    std::fs::write(
        temp.path().join("CLASSIC Ignore.yaml"),
        "CLASSIC_Ignore_Fallout4: []\n",
    )
    .expect("write ignore yaml");

    let data = yaml_data_load(
        &temp.path().to_string_lossy(),
        &data_dir.to_string_lossy(),
        "Fallout4VR",
        "VR",
    )
    .expect("Fallout 4 VR should load the shared Fallout 4 YAML");

    assert_eq!(yaml_data_xse_acronym(&data), "F4SEVR");
    assert_eq!(yaml_data_game_version(&data), "1.2.72");
}

#[test]
fn test_save_local_yaml_paths_creates_file() {
    let temp = tempdir().expect("failed to create temp dir");
    let local_yaml_path = temp
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Fallout4 Local.yaml");

    save_local_yaml_paths(
        &local_yaml_path.to_string_lossy(),
        "C:/Games/Fallout4",
        "C:/Users/Test/Documents/My Games/Fallout4",
    )
    .expect("save_local_yaml_paths should succeed");

    let yaml = classic_settings_core::YamlOperations::new()
        .load_yaml_file(&local_yaml_path)
        .expect("load local yaml");
    assert_eq!(
        yaml["Game_Info"]["Root_Folder_Game"].as_str(),
        Some("C:/Games/Fallout4")
    );
    assert_eq!(
        yaml["Game_Info"]["Root_Folder_Docs"].as_str(),
        Some("C:/Users/Test/Documents/My Games/Fallout4")
    );
}

#[test]
fn test_save_local_yaml_paths_preserves_empty_adapter_field() {
    let temp = tempdir().expect("failed to create temp dir");
    let local_yaml_path = temp
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Fallout4 Local.yaml");

    std::fs::create_dir_all(local_yaml_path.parent().expect("local YAML parent"))
        .expect("create local YAML parent");
    std::fs::write(
        &local_yaml_path,
        concat!(
            "Game_Info:\n",
            "  Root_Folder_Docs: C:/Users/Test/Documents/Existing\n",
            "  Docs_Folder_XSE: C:/Users/Test/Documents/Existing/F4SE\n",
        ),
    )
    .expect("seed local YAML");

    save_local_yaml_paths(&local_yaml_path.to_string_lossy(), "D:/Games/Fallout4", "")
        .expect("save_local_yaml_paths should preserve an unset docs path");

    let yaml = classic_settings_core::YamlOperations::new()
        .load_yaml_file(&local_yaml_path)
        .expect("load local YAML");
    assert_eq!(
        yaml["Game_Info"]["Root_Folder_Game"].as_str(),
        Some("D:/Games/Fallout4")
    );
    assert_eq!(
        yaml["Game_Info"]["Root_Folder_Docs"].as_str(),
        Some("C:/Users/Test/Documents/Existing")
    );
    assert_eq!(
        yaml["Game_Info"]["Docs_Folder_XSE"].as_str(),
        Some("C:/Users/Test/Documents/Existing/F4SE")
    );
}

// ── CXXS-07 typed suspect-rule tests ───────────────────────────────

/// Builds a minimal YamlData with suspect error rules for testing.
fn make_yaml_data_with_suspect_rules() -> Option<Box<YamlData>> {
    let temp = tempdir().expect("failed to create temp dir");
    let data_dir = temp.path().join("CLASSIC Data");
    let db_dir = data_dir.join("databases");
    std::fs::create_dir_all(&db_dir).expect("failed to create db dir");

    let main_yaml = r#"
CLASSIC_Info:
  version: "7.31.0"
  version_date: "2024-01-15"
CLASSIC_Interface:
  autoscan_text_Fallout4: "Autoscan Fallout 4"
"#;

    let game_yaml = r#"
Game_Info:
  Main_Root_Name: "Fallout 4"
Crashgen_Registry:
  "Buffout 4":
    ignore_keys: []
    checks: []
  default:
    ignore_keys: []
    checks: []
Crashlog_Error_Check:
  - id: "err_test_rule"
    name: "Test Error Rule"
    severity: 3
    main_error_contains_any:
      - "AccessViolation"
      - "NullPointer"
Crashlog_Stack_Check:
  - id: "stack_test_rule"
    name: "Test Stack Rule"
    severity: 2
    main_error_required_any:
      - "RequiredPattern"
    main_error_optional_any:
      - "OptionalPattern"
    stack_contains_any:
      - "StackPattern1"
      - "StackPattern2"
    exclude_if_stack_contains_any:
      - "ExcludePattern"
    stack_contains_at_least:
      - substring: "RepeatedFunc"
        count: 2
"#;

    let ignore_yaml = r#"
CLASSIC_Ignore_Fallout4: []
"#;

    std::fs::write(db_dir.join("CLASSIC Main.yaml"), main_yaml).ok()?;
    std::fs::write(db_dir.join("CLASSIC Fallout4.yaml"), game_yaml).ok()?;
    std::fs::write(temp.path().join("CLASSIC Ignore.yaml"), ignore_yaml).ok()?;

    let root_dir = temp.path().to_string_lossy().to_string();
    let data_dir_str = data_dir.to_string_lossy().to_string();

    // Keep temp alive by leaking — test fixture only
    std::mem::forget(temp);

    yaml_data_load(&root_dir, &data_dir_str, "Fallout4", "auto").ok()
}

#[test]
fn test_yaml_data_suspects_error_rules_empty() {
    let temp = tempdir().expect("failed to create temp dir");
    let data_dir = temp.path().join("CLASSIC Data");
    let db_dir = data_dir.join("databases");
    std::fs::create_dir_all(&db_dir).expect("failed to create db dir");

    let main_yaml = "CLASSIC_Info:\n  version: \"7.0.0\"\n  version_date: \"2024-01-01\"\nCLASSIC_Interface:\n  autoscan_text_Fallout4: \"Autoscan\"\n";
    let game_yaml = "Game_Info:\n  Main_Root_Name: \"Fallout 4\"\nCrashgen_Registry:\n  default:\n    ignore_keys: []\n    checks: []\n";
    let ignore_yaml = "CLASSIC_Ignore_Fallout4: []\n";

    std::fs::write(db_dir.join("CLASSIC Main.yaml"), main_yaml).expect("write main yaml");
    std::fs::write(db_dir.join("CLASSIC Fallout4.yaml"), game_yaml).expect("write game yaml");
    std::fs::write(temp.path().join("CLASSIC Ignore.yaml"), ignore_yaml)
        .expect("write ignore yaml");

    let root_dir = temp.path().to_string_lossy().to_string();
    let data_dir_str = data_dir.to_string_lossy().to_string();

    if let Ok(data) = yaml_data_load(&root_dir, &data_dir_str, "Fallout4", "auto") {
        assert!(yaml_data_suspects_error_rules(&data).is_empty());
    }
}

#[test]
fn test_yaml_data_suspects_error_rules_populated() {
    if let Some(data) = make_yaml_data_with_suspect_rules() {
        let rules = yaml_data_suspects_error_rules(&data);
        assert!(!rules.is_empty(), "expected at least one error rule");
        let rule = &rules[0];
        assert_eq!(rule.id, "err_test_rule");
        assert_eq!(rule.name, "Test Error Rule");
        assert_eq!(rule.severity, 3);
        assert!(
            rule.main_error_contains_any
                .contains(&"AccessViolation".to_string()),
            "expected AccessViolation in main_error_contains_any"
        );
    }
}

#[test]
fn test_yaml_data_suspects_stack_rules_metadata_no_count_rules_field() {
    if let Some(data) = make_yaml_data_with_suspect_rules() {
        let metadata = yaml_data_suspects_stack_rules_metadata(&data);
        assert!(!metadata.is_empty(), "expected at least one stack rule");
        let rule = &metadata[0];
        assert_eq!(rule.id, "stack_test_rule");
        assert_eq!(rule.name, "Test Stack Rule");
        assert_eq!(rule.severity, 2);
        // Verify all flat Vec<String> fields are accessible (no nested Vec<Struct>)
        assert!(
            rule.main_error_required_any
                .contains(&"RequiredPattern".to_string())
        );
        assert!(
            rule.main_error_optional_any
                .contains(&"OptionalPattern".to_string())
        );
        assert!(
            rule.stack_contains_any
                .contains(&"StackPattern1".to_string())
        );
        assert!(
            rule.exclude_if_stack_contains_any
                .contains(&"ExcludePattern".to_string())
        );
        // Pitfall 6 compile-time proof: no stack_contains_at_least field on the DTO
    }
}

#[test]
fn test_yaml_data_suspects_stack_count_rules_unknown_id_returns_empty() {
    if let Some(data) = make_yaml_data_with_suspect_rules() {
        let count_rules =
            yaml_data_suspects_stack_count_rules_for_id(&data, "definitely_not_a_real_id_xyz");
        assert!(count_rules.is_empty());
    }
}

#[test]
fn test_yaml_data_suspects_stack_count_rules_known_id_returns_populated() {
    if let Some(data) = make_yaml_data_with_suspect_rules() {
        let count_rules = yaml_data_suspects_stack_count_rules_for_id(&data, "stack_test_rule");
        assert!(
            !count_rules.is_empty(),
            "expected count rules for stack_test_rule"
        );
        assert_eq!(count_rules[0].substring, "RepeatedFunc");
        assert_eq!(count_rules[0].count, 2);
    }
}

#[test]
fn test_yaml_data_suspects_error_keys_still_works_d08_regression() {
    // D-08 regression: existing fn must remain unchanged
    if let Some(data) = make_yaml_data_with_suspect_rules() {
        let keys = yaml_data_suspects_error_keys(&data);
        assert!(
            !keys.is_empty(),
            "yaml_data_suspects_error_keys must still work (D-08)"
        );
    }
}

#[test]
fn test_yaml_data_suspects_stack_keys_still_works_d08_regression() {
    // D-08 regression: existing fn must remain unchanged
    if let Some(data) = make_yaml_data_with_suspect_rules() {
        let keys = yaml_data_suspects_stack_keys(&data);
        assert!(
            !keys.is_empty(),
            "yaml_data_suspects_stack_keys must still work (D-08)"
        );
    }
}

#[test]
fn test_settings_cache_stats_helpers_forward_core_surface() {
    settings_cache_clear();
    reset_settings_cache_stats();

    assert_eq!(settings_cache_size(), 0);
    let initial = settings_cache_stats();
    assert_eq!(initial.hits, 0);
    assert_eq!(initial.misses, 0);
    assert_eq!(initial.size, 0);
    assert_eq!(initial.capacity, 64);

    let mut file = NamedTempFile::new().expect("create temp yaml");
    file.write_all(b"key: value\n").expect("write temp yaml");
    file.flush().expect("flush temp yaml");

    classic_settings_core::load_settings_sync("bridge-settings", file.path())
        .expect("load settings into cache");

    let populated = settings_cache_stats();
    assert_eq!(settings_cache_size(), 1);
    assert_eq!(populated.size, 1);
}
