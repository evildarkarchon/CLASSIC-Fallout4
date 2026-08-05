use super::*;
// Imported here rather than in `config.rs`: the module itself only projects
// labels through `crate::vocabulary::display_label`, so the trait is in scope
// only where the tests read `label()` off a core variant to derive their
// expectation from.
use classic_vocabulary::Vocabulary;
use std::io::Write;
use tempfile::NamedTempFile;
use tempfile::tempdir;

const EXPLICIT_MAIN_YAML: &str = concat!(
    "schema_version: \"2.0\"\r\n",
    "CLASSIC_Info:\r\n",
    "  version: \"9.1.0\"\r\n",
    "CLASSIC_Interface:\r\n",
    "  autoscan_text_Fallout4: \"explicit bridge\"\r\n",
    "exclude_log_records:\r\n",
    "  - '(void*)'\r\n",
    "  - 'kernel32.dll'\r\n",
);
const EXPLICIT_GAME_YAML: &str = concat!(
    "schema_version: \"1.0\"\n",
    "Game_Info:\n",
    "  Main_Root_Name: \"Fallout 4\"\n",
    "Crashlog_Error_Check: []\n",
    "Crashlog_Stack_Check: []\n",
    "Mods_CONF:\n",
    "  - mod_a: Upscaling.dll\n",
    "    mod_b: FSR3_AA.dll\n",
    "    name_a: Upscaling\n",
    "    name_b: FSR 3 Antialiasing\n",
    "    description: The mods are redundant with each other.\n",
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

/// Build a `YamlData` handle from three caller-selected files.
///
/// The bridge no longer exposes a positional directory-pair loader, so bridge
/// tests that need a `YamlData` handle acquire one the same way C++ does: load
/// exactly the files they wrote, then take the snapshot's YAML Data. Because
/// explicit loading gates on `schema_version` and role-specific semantics, the
/// caller's fixtures must be valid — that is the point of the retained seam.
fn yaml_data_from_explicit_files(
    root: &std::path::Path,
    main: &str,
    game: &str,
    ignore: &str,
    game_id: ffi::ExplicitYamlDataGameId,
    selected_game_version: &str,
) -> Box<YamlData> {
    let main_path = root.join("selected-main.yaml");
    let game_path = root.join("selected-game.yaml");
    let ignore_path = root.join("selected-ignore.yaml");
    std::fs::write(&main_path, main).expect("write Main fixture");
    std::fs::write(&game_path, game).expect("write game fixture");
    std::fs::write(&ignore_path, ignore).expect("write Local Ignore fixture");

    let load = explicit_yaml_data_load(
        ffi::ExplicitYamlDataPathsDto {
            main_path: main_path.to_string_lossy().into_owned(),
            game_path: game_path.to_string_lossy().into_owned(),
            ignore_path: ignore_path.to_string_lossy().into_owned(),
        },
        game_id,
        selected_game_version,
    );
    let snapshot =
        explicit_yaml_data_load_take_snapshot(load).expect("explicit fixture load should succeed");
    explicit_yaml_data_snapshot_yaml_data(&snapshot)
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
    assert_eq!(yaml_data_mods_conf_count(&data), 1);
    assert_eq!(yaml_data_mods_conf_fixes(&data), [""]);
    assert_eq!(yaml_data_mods_conf_has_fixes(&data), [false]);
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
    assert!(!status.has_recovery_plan);
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
    assert_eq!(
        installed_yaml_data_snapshot_simplify_remove_list(&snapshot),
        vec!["(void*)".to_string(), "kernel32.dll".to_string()]
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
    assert!(!status.has_recovery_plan);
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
fn installed_yaml_data_load_bridge_projects_and_consumes_local_ignore_recovery_plan_without_writes()
{
    let installation = tempdir().expect("create recovery bridge fixture directory");
    write_installed_bridge_fixtures(installation.path());
    let databases = installation.path().join("CLASSIC Data").join("databases");
    let main_path = databases.join("CLASSIC Main.yaml");
    let game_path = databases.join("CLASSIC Fallout4.yaml");
    let ignore_path = installation
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");
    let malformed_ignore = b"CLASSIC_Ignore_Fallout4: not-a-sequence\r\n";
    std::fs::write(&main_path, INSTALLED_GENERATING_MAIN_YAML)
        .expect("write Main fixture with retained Local Ignore defaults");
    std::fs::write(&ignore_path, malformed_ignore).expect("write malformed Local Ignore fixture");
    let before_main = std::fs::read(&main_path).expect("read Main before recovery operation");
    let before_game = std::fs::read(&game_path).expect("read game before recovery operation");
    let before_ignore =
        std::fs::read(&ignore_path).expect("read Local Ignore before recovery operation");

    let operation = load_installed_without_cache(
        installation.path(),
        ffi::ExplicitYamlDataGameId::Fallout4,
        "Original",
    );
    let status = installed_yaml_data_load_status(&operation);
    assert!(!status.has_snapshot);
    assert!(status.has_recovery_plan);
    assert!(!status.has_error);

    let plan = installed_yaml_data_load_take_recovery_plan(operation)
        .expect("take retained Local Ignore recovery plan");
    assert_eq!(
        local_ignore_recovery_plan_game(&plan),
        ffi::ExplicitYamlDataGameId::Fallout4
    );
    assert_eq!(
        local_ignore_recovery_plan_game_role(&plan),
        ffi::InstalledYamlDataGameRole::Fallout4
    );
    let retained_main = local_ignore_recovery_plan_main(&plan);
    assert_eq!(
        retained_main.byte_len,
        INSTALLED_GENERATING_MAIN_YAML.len() as u64
    );
    let retained_game = local_ignore_recovery_plan_game_file(&plan);
    assert_eq!(retained_game.byte_len, EXPLICIT_GAME_YAML.len() as u64);
    assert_eq!(
        local_ignore_recovery_plan_local_ignore_path(&plan),
        ignore_path.to_string_lossy()
    );
    let malformed_identity = local_ignore_recovery_plan_malformed_local_ignore_identity(&plan);
    assert_eq!(malformed_identity.byte_len, malformed_ignore.len() as u64);
    assert_eq!(malformed_identity.sha256.len(), 64);
    assert!(local_ignore_recovery_plan_has_default_local_ignore_identity(&plan));
    let default_identity = local_ignore_recovery_plan_default_local_ignore_identity(&plan);
    assert_eq!(
        default_identity.byte_len,
        "CLASSIC_Ignore_Fallout4:\n  - GeneratedBridgeEntry.dll\n".len() as u64
    );
    assert_eq!(default_identity.sha256.len(), 64);
    assert_eq!(
        local_ignore_recovery_plan_selected_game_version(&plan),
        "Original"
    );
    assert!(
        local_ignore_recovery_plan_diagnostics(&plan)
            .iter()
            .any(|diagnostic| {
                diagnostic.kind == ffi::InstalledYamlDataDiagnosticKind::InvalidRoleData
                    && diagnostic.has_path
                    && diagnostic.path == ignore_path.to_string_lossy()
            })
    );

    let snapshot = local_ignore_recovery_plan_proceed_without_ignore(plan);
    assert_eq!(
        installed_yaml_data_snapshot_local_ignore_state(&snapshot),
        ffi::LocalIgnoreYamlDataState::ProceedWithoutIgnore
    );
    let snapshot_identity = installed_yaml_data_snapshot_local_ignore_identity(&snapshot);
    assert_eq!(snapshot_identity.sha256, malformed_identity.sha256);
    assert_eq!(snapshot_identity.byte_len, malformed_identity.byte_len);
    let snapshot_main = installed_yaml_data_snapshot_main(&snapshot);
    assert_eq!(snapshot_main.sha256, retained_main.sha256);
    assert_eq!(snapshot_main.byte_len, retained_main.byte_len);
    let snapshot_game = installed_yaml_data_snapshot_game_file(&snapshot);
    assert_eq!(snapshot_game.sha256, retained_game.sha256);
    assert_eq!(snapshot_game.byte_len, retained_game.byte_len);
    assert!(yaml_data_ignore_list(&installed_yaml_data_snapshot_yaml_data(&snapshot)).is_empty());

    assert_eq!(
        std::fs::read(&main_path).expect("read Main after recovery operation"),
        before_main
    );
    assert_eq!(
        std::fs::read(&game_path).expect("read game after recovery operation"),
        before_game
    );
    assert_eq!(
        std::fs::read(&ignore_path).expect("read Local Ignore after recovery operation"),
        before_ignore
    );

    let later_operation = load_installed_without_cache(
        installation.path(),
        ffi::ExplicitYamlDataGameId::Fallout4,
        "Original",
    );
    let later_status = installed_yaml_data_load_status(&later_operation);
    assert!(!later_status.has_snapshot);
    assert!(later_status.has_recovery_plan);
    assert!(!later_status.has_error);
}

#[test]
fn installed_yaml_data_load_bridge_recovers_from_malformed_ignore_without_valid_defaults() {
    let installation = tempdir().expect("create recovery bridge fixture directory");
    write_installed_bridge_fixtures(installation.path());
    let databases = installation.path().join("CLASSIC Data").join("databases");
    let main_path = databases.join("CLASSIC Main.yaml");
    let game_path = databases.join("CLASSIC Fallout4.yaml");
    let ignore_path = installation
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");
    let malformed_ignore = b"CLASSIC_Ignore_Fallout4: not-a-sequence\r\n";
    std::fs::write(&ignore_path, malformed_ignore).expect("write malformed Local Ignore fixture");
    let before_main = std::fs::read(&main_path).expect("read Main before recovery operation");
    let before_game = std::fs::read(&game_path).expect("read game before recovery operation");
    let before_ignore =
        std::fs::read(&ignore_path).expect("read Local Ignore before recovery operation");

    let operation = load_installed_without_cache(
        installation.path(),
        ffi::ExplicitYamlDataGameId::Fallout4,
        "Original",
    );
    let status = installed_yaml_data_load_status(&operation);
    assert!(!status.has_snapshot);
    assert!(status.has_recovery_plan);
    assert!(!status.has_error);

    let plan = installed_yaml_data_load_take_recovery_plan(operation)
        .expect("take recovery plan without selected-Main defaults");
    assert!(!local_ignore_recovery_plan_has_default_local_ignore_identity(&plan));
    let unavailable_identity = local_ignore_recovery_plan_default_local_ignore_identity(&plan);
    assert!(unavailable_identity.sha256.is_empty());
    assert_eq!(unavailable_identity.byte_len, 0);

    let snapshot = local_ignore_recovery_plan_proceed_without_ignore(plan);
    assert_eq!(
        installed_yaml_data_snapshot_local_ignore_state(&snapshot),
        ffi::LocalIgnoreYamlDataState::ProceedWithoutIgnore
    );
    assert!(yaml_data_ignore_list(&installed_yaml_data_snapshot_yaml_data(&snapshot)).is_empty());
    assert_eq!(
        std::fs::read(&main_path).expect("read Main after recovery operation"),
        before_main
    );
    assert_eq!(
        std::fs::read(&game_path).expect("read game after recovery operation"),
        before_game
    );
    assert_eq!(
        std::fs::read(&ignore_path).expect("read Local Ignore after recovery operation"),
        before_ignore
    );

    let later_operation = load_installed_without_cache(
        installation.path(),
        ffi::ExplicitYamlDataGameId::Fallout4,
        "Original",
    );
    let later_status = installed_yaml_data_load_status(&later_operation);
    assert!(!later_status.has_snapshot);
    assert!(later_status.has_recovery_plan);
    assert!(!later_status.has_error);
}

#[test]
/// The consuming reset bridge exposes durable success metadata and its retained snapshot.
fn local_ignore_reset_bridge_projects_success_metadata_and_snapshot() {
    let installation = tempdir().expect("create successful reset bridge fixture directory");
    write_installed_bridge_fixtures(installation.path());
    let data = installation.path().join("CLASSIC Data");
    let ignore_path = data.join("CLASSIC Ignore.yaml");
    let malformed_ignore = b"CLASSIC_Ignore_Fallout4: not-a-sequence\r\n";
    let replacement = b"CLASSIC_Ignore_Fallout4:\n  - GeneratedBridgeEntry.dll\n";
    std::fs::write(
        data.join("databases").join("CLASSIC Main.yaml"),
        INSTALLED_GENERATING_MAIN_YAML,
    )
    .expect("write Main fixture with reset defaults");
    std::fs::write(&ignore_path, malformed_ignore).expect("write malformed Local Ignore fixture");

    let operation = load_installed_without_cache(
        installation.path(),
        ffi::ExplicitYamlDataGameId::Fallout4,
        "Original",
    );
    let plan = installed_yaml_data_load_take_recovery_plan(operation)
        .expect("take reset-ready recovery plan");
    let malformed_identity = local_ignore_recovery_plan_malformed_local_ignore_identity(&plan);
    let replacement_identity = local_ignore_recovery_plan_default_local_ignore_identity(&plan);

    let reset = local_ignore_recovery_plan_reset_to_default(plan);
    let status = local_ignore_reset_status(&reset);
    assert!(status.has_reset);
    assert!(!status.has_conflict);
    assert!(!status.has_error);

    let result = local_ignore_reset_take_result(reset).expect("take successful reset result");
    assert_eq!(
        local_ignore_reset_result_local_ignore_path(&result),
        ignore_path.to_string_lossy()
    );
    let backup_path = local_ignore_reset_result_backup_path(&result);
    assert_eq!(
        std::fs::read(&backup_path).expect("read durable reset backup"),
        malformed_ignore
    );
    assert_eq!(
        std::fs::read(&ignore_path).expect("read reset Local Ignore"),
        replacement
    );
    assert_eq!(
        local_ignore_reset_result_malformed_local_ignore_identity(&result).sha256,
        malformed_identity.sha256
    );
    assert_eq!(
        local_ignore_reset_result_backup_identity(&result).sha256,
        malformed_identity.sha256
    );
    assert_eq!(
        local_ignore_reset_result_replacement_identity(&result).sha256,
        replacement_identity.sha256
    );
    assert!(
        local_ignore_reset_result_diagnostics(&result)
            .iter()
            .any(|diagnostic| {
                diagnostic.kind == ffi::InstalledYamlDataDiagnosticKind::LocalIgnoreReset
                    && diagnostic.has_path
                    && diagnostic.path == ignore_path.to_string_lossy()
            })
    );

    let snapshot = local_ignore_reset_result_take_snapshot(result);
    assert_eq!(
        installed_yaml_data_snapshot_local_ignore_state(&snapshot),
        ffi::LocalIgnoreYamlDataState::ResetToDefault
    );
    assert_eq!(
        installed_yaml_data_snapshot_local_ignore_identity(&snapshot).sha256,
        replacement_identity.sha256
    );
    assert_eq!(
        yaml_data_ignore_list(&installed_yaml_data_snapshot_yaml_data(&snapshot)),
        vec!["GeneratedBridgeEntry.dll".to_string()]
    );
}

#[test]
/// The reset bridge preserves typed identity conflict data without overwriting newer bytes.
fn local_ignore_reset_bridge_projects_conflict_identities_and_optional_backup() {
    let installation = tempdir().expect("create reset conflict bridge fixture directory");
    write_installed_bridge_fixtures(installation.path());
    let data = installation.path().join("CLASSIC Data");
    let ignore_path = data.join("CLASSIC Ignore.yaml");
    let malformed_ignore = b"CLASSIC_Ignore_Fallout4: not-a-sequence\r\n";
    let changed_ignore = b"changed while the caller was deciding";
    std::fs::write(
        data.join("databases").join("CLASSIC Main.yaml"),
        INSTALLED_GENERATING_MAIN_YAML,
    )
    .expect("write Main fixture with reset defaults");
    std::fs::write(&ignore_path, malformed_ignore).expect("write malformed Local Ignore fixture");

    let operation = load_installed_without_cache(
        installation.path(),
        ffi::ExplicitYamlDataGameId::Fallout4,
        "Original",
    );
    let plan = installed_yaml_data_load_take_recovery_plan(operation)
        .expect("take conflict-tested recovery plan");
    let expected = local_ignore_recovery_plan_malformed_local_ignore_identity(&plan);
    std::fs::write(&ignore_path, changed_ignore).expect("replace Local Ignore before reset");

    let reset = local_ignore_recovery_plan_reset_to_default(plan);
    let status = local_ignore_reset_status(&reset);
    assert!(!status.has_reset);
    assert!(status.has_conflict);
    assert!(!status.has_error);

    let conflict = local_ignore_reset_take_conflict(reset).expect("take typed reset conflict");
    assert_eq!(
        local_ignore_reset_conflict_expected_identity(&conflict).sha256,
        expected.sha256
    );
    assert!(local_ignore_reset_conflict_has_actual_identity(&conflict));
    let actual = local_ignore_reset_conflict_actual_identity(&conflict);
    assert_eq!(actual.byte_len, changed_ignore.len() as u64);
    assert_ne!(actual.sha256, expected.sha256);
    assert!(!local_ignore_reset_conflict_has_backup_path(&conflict));
    assert!(local_ignore_reset_conflict_backup_path(&conflict).is_empty());
    assert_eq!(
        std::fs::read(&ignore_path).expect("read conflict-preserved Local Ignore"),
        changed_ignore
    );
}

#[test]
/// The reset bridge keeps every core error kind and durable publication stage typed.
fn local_ignore_reset_bridge_maps_every_error_kind_and_publication_stage() {
    let path = std::path::PathBuf::from("isolated/CLASSIC Ignore.yaml");
    let io_error = || std::io::Error::other("reset fixture");
    let errors = [
        CoreLocalIgnoreResetError::DefaultsUnavailable {
            path: path.clone(),
            reason: "defaults fixture".to_string(),
        },
        CoreLocalIgnoreResetError::Lock {
            path: path.clone(),
            source: io_error(),
        },
        CoreLocalIgnoreResetError::Read {
            path: path.clone(),
            source: io_error(),
        },
        CoreLocalIgnoreResetError::BackupDirectory {
            path: path.clone(),
            source: io_error(),
        },
        CoreLocalIgnoreResetError::BackupVerification {
            path: path.clone(),
            reason: "verification fixture".to_string(),
        },
        CoreLocalIgnoreResetError::BackupPublication {
            path: path.clone(),
            stage: CoreLocalIgnoreResetPublicationStage::Create,
            source: io_error(),
        },
        CoreLocalIgnoreResetError::BackupPublication {
            path: path.clone(),
            stage: CoreLocalIgnoreResetPublicationStage::Write,
            source: io_error(),
        },
        CoreLocalIgnoreResetError::ReplacementPublication {
            path: path.clone(),
            stage: CoreLocalIgnoreResetPublicationStage::Flush,
            source: io_error(),
        },
        CoreLocalIgnoreResetError::ReplacementPublication {
            path: path.clone(),
            stage: CoreLocalIgnoreResetPublicationStage::Sync,
            source: io_error(),
        },
        CoreLocalIgnoreResetError::ReplacementPublication {
            path,
            stage: CoreLocalIgnoreResetPublicationStage::Publish,
            source: io_error(),
        },
    ];
    let dtos = errors
        .iter()
        .map(local_ignore_reset_error_to_dto)
        .collect::<Vec<_>>();

    assert_eq!(
        dtos[..5].iter().map(|error| error.kind).collect::<Vec<_>>(),
        vec![
            ffi::LocalIgnoreResetErrorKind::DefaultsUnavailable,
            ffi::LocalIgnoreResetErrorKind::Lock,
            ffi::LocalIgnoreResetErrorKind::Read,
            ffi::LocalIgnoreResetErrorKind::BackupDirectory,
            ffi::LocalIgnoreResetErrorKind::BackupVerification,
        ]
    );
    assert!(
        dtos[..5]
            .iter()
            .all(|error| error.has_path && !error.has_stage && !error.message.is_empty())
    );
    assert_eq!(
        dtos[5..]
            .iter()
            .map(|error| error.stage)
            .collect::<Vec<_>>(),
        vec![
            ffi::LocalIgnoreResetPublicationStage::Create,
            ffi::LocalIgnoreResetPublicationStage::Write,
            ffi::LocalIgnoreResetPublicationStage::Flush,
            ffi::LocalIgnoreResetPublicationStage::Sync,
            ffi::LocalIgnoreResetPublicationStage::Publish,
        ]
    );
    assert_eq!(
        dtos[5..].iter().map(|error| error.kind).collect::<Vec<_>>(),
        vec![
            ffi::LocalIgnoreResetErrorKind::BackupPublication,
            ffi::LocalIgnoreResetErrorKind::BackupPublication,
            ffi::LocalIgnoreResetErrorKind::ReplacementPublication,
            ffi::LocalIgnoreResetErrorKind::ReplacementPublication,
            ffi::LocalIgnoreResetErrorKind::ReplacementPublication,
        ]
    );
    assert!(dtos[5..].iter().all(|error| error.has_stage));

    let malformed_identity = YamlDataContentIdentity::from_bytes(b"malformed");
    let backup_identity = malformed_identity.clone();
    let replacement_identity = YamlDataContentIdentity::from_bytes(b"defaults");
    let durability_error = CoreLocalIgnoreResetError::ReplacementDurabilityUnknown {
        receipt: Box::new(classic_config_core::LocalIgnoreResetDurabilityReceipt {
            path: std::path::PathBuf::from("isolated/CLASSIC Ignore.yaml"),
            backup_path: std::path::PathBuf::from("isolated/backup.bak"),
            malformed_identity: malformed_identity.clone(),
            backup_identity: backup_identity.clone(),
            replacement_identity: replacement_identity.clone(),
        }),
        source: io_error(),
    };
    let durability_dto = local_ignore_reset_error_to_dto(&durability_error);
    assert_eq!(
        durability_dto.kind,
        ffi::LocalIgnoreResetErrorKind::ReplacementDurabilityUnknown
    );
    assert!(!durability_dto.has_stage);
    assert!(durability_dto.has_durability_receipt);
    assert_eq!(durability_dto.backup_path, "isolated/backup.bak");
    assert_eq!(
        durability_dto.malformed_identity.sha256,
        malformed_identity.sha256_hex()
    );
    assert_eq!(
        durability_dto.backup_identity.sha256,
        backup_identity.sha256_hex()
    );
    assert_eq!(
        durability_dto.replacement_identity.sha256,
        replacement_identity.sha256_hex()
    );
}

#[test]
/// An unavailable retained default is exposed through the operation's typed error status.
fn local_ignore_reset_bridge_projects_defaults_unavailable_status() {
    let installation = tempdir().expect("create unavailable-default reset fixture directory");
    write_installed_bridge_fixtures(installation.path());
    let ignore_path = installation
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Ignore.yaml");
    std::fs::write(&ignore_path, b"CLASSIC_Ignore_Fallout4: not-a-sequence\r\n")
        .expect("write malformed Local Ignore fixture");

    let operation = load_installed_without_cache(
        installation.path(),
        ffi::ExplicitYamlDataGameId::Fallout4,
        "Original",
    );
    let plan = installed_yaml_data_load_take_recovery_plan(operation)
        .expect("take recovery plan without defaults");
    let reset = local_ignore_recovery_plan_reset_to_default(plan);
    let status = local_ignore_reset_status(&reset);
    assert!(!status.has_reset);
    assert!(!status.has_conflict);
    assert!(status.has_error);
    assert_eq!(
        status.error.kind,
        ffi::LocalIgnoreResetErrorKind::DefaultsUnavailable
    );
    assert!(status.error.has_path);
    assert_eq!(status.error.path, ignore_path.to_string_lossy());
    assert!(!status.error.has_stage);
    assert!(!status.error.message.is_empty());
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
    assert!(!unsupported_status.has_snapshot);
    assert!(!unsupported_status.has_recovery_plan);
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
    assert!(!missing_status.has_snapshot);
    assert!(!missing_status.has_recovery_plan);
    assert!(missing_status.has_error);
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
            ffi::InstalledYamlDataLoadErrorKind::LocalIgnoreDefaultInvalid,
            ffi::InstalledYamlDataLoadErrorKind::LocalIgnoreCreate,
            ffi::InstalledYamlDataLoadErrorKind::InvalidSelectedData,
        ]
    );
    assert!(!error_dtos[0].has_role);
    assert!(error_dtos[1].has_role);
    assert_eq!(error_dtos[1].role, ffi::InstalledYamlDataLoadRole::Game);
    for error in &error_dtos[2..=4] {
        assert!(error.has_role);
        assert_eq!(error.role, ffi::InstalledYamlDataLoadRole::LocalIgnore);
        assert!(error.has_path);
    }
    assert!(!error_dtos[5].has_role);
}

/// An absent caller-selected file surfaces as a typed `Read` status, not a panic.
///
/// This replaces the removed positional loader's "invalid dirs" case: C++ now
/// always receives an operation handle and inspects its status before consuming
/// a snapshot.
#[test]
fn explicit_yaml_data_bridge_reports_absent_files_as_typed_read_errors() {
    let temp = tempdir().expect("failed to create temp dir");
    let load = explicit_yaml_data_load(
        ffi::ExplicitYamlDataPathsDto {
            main_path: temp
                .path()
                .join("absent-main.yaml")
                .to_string_lossy()
                .into_owned(),
            game_path: temp
                .path()
                .join("absent-game.yaml")
                .to_string_lossy()
                .into_owned(),
            ignore_path: temp
                .path()
                .join("absent-ignore.yaml")
                .to_string_lossy()
                .into_owned(),
        },
        ffi::ExplicitYamlDataGameId::Fallout4,
        "auto",
    );

    let status = explicit_yaml_data_load_status(&load);
    assert!(!status.has_snapshot);
    assert!(status.has_error);
    assert_eq!(status.error.kind, ffi::ExplicitYamlDataLoadErrorKind::Read);
    assert!(status.error.has_role);
    assert_eq!(status.error.role, ffi::ExplicitYamlDataRole::Main);
    assert!(status.error.has_path);
}

#[test]
fn test_yaml_data_accessors_fallback_when_game_info_is_minimal() {
    let temp = tempdir().expect("failed to create temp dir");

    // `Game_Info` carries only `Main_Root_Name`, so the Crashgen name, its
    // ignore keys, and the game version must all come from the registry and
    // `Crashgen_Registry` fallbacks rather than from explicit Game_Info fields.
    let game_yaml = concat!(
        "schema_version: \"1.0\"\n",
        "Game_Info:\n",
        "  Main_Root_Name: \"Fallout 4\"\n",
        "Crashlog_Error_Check: []\n",
        "Crashlog_Stack_Check: []\n",
        "Mods_FREQ: []\n",
        "Mods_SOLU: []\n",
        "Crashgen_Registry:\n",
        "  \"Buffout 4\":\n",
        "    ignore_keys:\n",
        "      - \"BuffoutSpecificIgnore\"\n",
        "    checks: []\n",
        "  default:\n",
        "    ignore_keys:\n",
        "      - \"DefaultIgnore\"\n",
        "    checks: []\n",
    );

    let data = yaml_data_from_explicit_files(
        temp.path(),
        EXPLICIT_MAIN_YAML,
        game_yaml,
        EXPLICIT_EMPTY_IGNORE_YAML,
        ffi::ExplicitYamlDataGameId::Fallout4,
        "auto",
    );

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

    let data = yaml_data_from_explicit_files(
        temp.path(),
        EXPLICIT_MAIN_YAML,
        concat!(
            "schema_version: \"1.0\"\n",
            "Game_Info:\n",
            "  Main_Root_Name: Fallout 4\n",
            "Crashlog_Error_Check: []\n",
            "Crashlog_Stack_Check: []\n",
            "Mods_FREQ: []\n",
            "Mods_SOLU: []\n",
        ),
        EXPLICIT_EMPTY_IGNORE_YAML,
        ffi::ExplicitYamlDataGameId::Fallout4VR,
        "VR",
    );

    // The shared Fallout 4 game file declares no VR-specific facts, so both
    // come from the Version Registry keyed by the VR game identity.
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
///
/// The snapshot owns its bytes, so the temporary directory can drop as soon as
/// the load returns — no fixture leak is needed to keep the handle valid.
fn make_yaml_data_with_suspect_rules() -> Box<YamlData> {
    let temp = tempdir().expect("failed to create temp dir");

    let game_yaml = concat!(
        "schema_version: \"1.0\"\n",
        "Game_Info:\n",
        "  Main_Root_Name: \"Fallout 4\"\n",
        "Mods_FREQ: []\n",
        "Mods_SOLU: []\n",
        "Crashgen_Registry:\n",
        "  \"Buffout 4\":\n",
        "    ignore_keys: []\n",
        "    checks: []\n",
        "  default:\n",
        "    ignore_keys: []\n",
        "    checks: []\n",
        "Crashlog_Error_Check:\n",
        "  - id: \"err_test_rule\"\n",
        "    name: \"Test Error Rule\"\n",
        "    severity: 3\n",
        "    main_error_contains_any:\n",
        "      - \"AccessViolation\"\n",
        "      - \"NullPointer\"\n",
        "Crashlog_Stack_Check:\n",
        "  - id: \"stack_test_rule\"\n",
        "    name: \"Test Stack Rule\"\n",
        "    severity: 2\n",
        "    main_error_required_any:\n",
        "      - \"RequiredPattern\"\n",
        "    main_error_optional_any:\n",
        "      - \"OptionalPattern\"\n",
        "    stack_contains_any:\n",
        "      - \"StackPattern1\"\n",
        "      - \"StackPattern2\"\n",
        "    exclude_if_stack_contains_any:\n",
        "      - \"ExcludePattern\"\n",
        "    stack_contains_at_least:\n",
        "      - substring: \"RepeatedFunc\"\n",
        "        count: 2\n",
    );

    yaml_data_from_explicit_files(
        temp.path(),
        EXPLICIT_MAIN_YAML,
        game_yaml,
        EXPLICIT_EMPTY_IGNORE_YAML,
        ffi::ExplicitYamlDataGameId::Fallout4,
        "auto",
    )
}

#[test]
fn test_yaml_data_suspects_error_rules_empty() {
    let temp = tempdir().expect("failed to create temp dir");

    let data = yaml_data_from_explicit_files(
        temp.path(),
        EXPLICIT_MAIN_YAML,
        concat!(
            "schema_version: \"1.0\"\n",
            "Game_Info:\n",
            "  Main_Root_Name: \"Fallout 4\"\n",
            "Crashlog_Error_Check: []\n",
            "Crashlog_Stack_Check: []\n",
            "Mods_FREQ: []\n",
            "Mods_SOLU: []\n",
            "Crashgen_Registry:\n",
            "  default:\n",
            "    ignore_keys: []\n",
            "    checks: []\n",
        ),
        EXPLICIT_EMPTY_IGNORE_YAML,
        ffi::ExplicitYamlDataGameId::Fallout4,
        "auto",
    );

    assert!(yaml_data_suspects_error_rules(&data).is_empty());
}

#[test]
fn test_yaml_data_suspects_error_rules_populated() {
    let data = make_yaml_data_with_suspect_rules();
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

#[test]
fn test_yaml_data_suspects_stack_rules_metadata_no_count_rules_field() {
    let data = make_yaml_data_with_suspect_rules();
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

#[test]
fn test_yaml_data_suspects_stack_count_rules_unknown_id_returns_empty() {
    let data = make_yaml_data_with_suspect_rules();
    let count_rules =
        yaml_data_suspects_stack_count_rules_for_id(&data, "definitely_not_a_real_id_xyz");
    assert!(count_rules.is_empty());
}

#[test]
fn test_yaml_data_suspects_stack_count_rules_known_id_returns_populated() {
    let data = make_yaml_data_with_suspect_rules();
    let count_rules = yaml_data_suspects_stack_count_rules_for_id(&data, "stack_test_rule");
    assert!(
        !count_rules.is_empty(),
        "expected count rules for stack_test_rule"
    );
    assert_eq!(count_rules[0].substring, "RepeatedFunc");
    assert_eq!(count_rules[0].count, 2);
}

#[test]
fn test_yaml_data_suspects_error_keys_still_works_d08_regression() {
    // D-08 regression: existing fn must remain unchanged
    let data = make_yaml_data_with_suspect_rules();
    let keys = yaml_data_suspects_error_keys(&data);
    assert!(
        !keys.is_empty(),
        "yaml_data_suspects_error_keys must still work (D-08)"
    );
}

#[test]
fn test_yaml_data_suspects_stack_keys_still_works_d08_regression() {
    // D-08 regression: existing fn must remain unchanged
    let data = make_yaml_data_with_suspect_rules();
    let keys = yaml_data_suspects_stack_keys(&data);
    assert!(
        !keys.is_empty(),
        "yaml_data_suspects_stack_keys must still work (D-08)"
    );
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

// --- Vocabulary projection ------------------------------------------------
//
// Expectations are derived from `classic-config-core`, never restated. A
// hand-written array here would be another copy of the vocabulary: it would
// pass against a bridge that had already drifted, because it would only be
// comparing this file's copy against itself. Iterating `VARIANTS` also means a
// new variant is covered without anyone remembering to extend these tests.

#[test]
/// Every projected CXX variant resolves back to the core Display Label.
fn every_config_enum_projects_its_core_display_label() {
    for variant in CoreInstalledYamlDataProvenance::VARIANTS.iter().copied() {
        assert_eq!(
            installed_yaml_data_provenance_label(installed_yaml_data_provenance_to_ffi(variant)),
            variant.label(),
        );
    }
    for variant in CoreInstalledYamlDataDiagnosticKind::VARIANTS
        .iter()
        .copied()
    {
        assert_eq!(
            installed_yaml_data_diagnostic_kind_label(installed_yaml_data_diagnostic_kind_to_ffi(
                variant
            )),
            variant.label(),
        );
    }
    for variant in CoreLocalIgnoreYamlDataState::VARIANTS.iter().copied() {
        assert_eq!(
            local_ignore_yaml_data_state_label(local_ignore_yaml_data_state_to_ffi(variant)),
            variant.label(),
        );
    }
}

#[test]
/// A fabricated CXX enum value yields nothing rather than an invented label.
fn an_out_of_range_cxx_enum_value_yields_an_empty_display_label() {
    // CXX shared enums are open at the FFI boundary: C++ can hand back any
    // `u8`. The bridge never produces one of these, but returning some other
    // variant's label - or a hand-written "unknown" string - would put
    // vocabulary back in the adapter, which is what this work removes.
    let fabricated = ffi::InstalledYamlDataDiagnosticKind { repr: u8::MAX };
    assert_eq!(installed_yaml_data_diagnostic_kind_label(fabricated), "");
}
