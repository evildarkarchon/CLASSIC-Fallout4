use super::*;
use classic_settings_core::{merge_yaml_documents, parse_yaml_content};
use serial_test::serial;
use std::sync::{Mutex, OnceLock};
use tempfile::tempdir;

fn current_dir_lock() -> &'static Mutex<()> {
    static LOCK: OnceLock<Mutex<()>> = OnceLock::new();
    LOCK.get_or_init(|| Mutex::new(()))
}

fn parse_yaml_document(yaml_str: &str) -> Yaml {
    let docs = parse_yaml_content("memory://config.rs", yaml_str).unwrap();
    merge_yaml_documents("memory://config.rs", &docs).unwrap()
}

#[test]
#[serial]
fn yamlsource_main_load_routes_through_shippable_loader() {
    // Regression for the Codex adversarial review finding:
    // `YamlSource::Main.load` used to read the bundled path directly,
    // bypassing the yaml-update-delivery cache. This test locks the CWD,
    // writes a bundled copy whose `CLASSIC_Info.version` is distinct from
    // any checked-in fixture, and confirms that calling the public
    // `YamlSource::Main.load` surfaces that content. The routing is the
    // load-time half of the update contract — without it, an installed
    // update can never become the loaded document regardless of what the
    // cache directory contains.
    //
    // Written as a sync test with a local `block_on` so the process-wide
    // CWD mutex is never held across an await point (`clippy::await_holding_lock`).
    let _guard = current_dir_lock().lock().unwrap();
    let original_dir = std::env::current_dir().unwrap();
    let work_dir = tempdir().unwrap();
    let bundled_dir = work_dir.path().join("CLASSIC Data").join("databases");
    std::fs::create_dir_all(&bundled_dir).unwrap();
    let bundled_payload = concat!(
        "schema_version: \"1.0\"\n",
        "CLASSIC_Info:\n",
        "  version: shippable-routing-regression\n",
    );
    std::fs::write(bundled_dir.join("CLASSIC Main.yaml"), bundled_payload).unwrap();

    classic_settings_core::clear_global_yaml_cache();
    std::env::set_current_dir(work_dir.path()).unwrap();

    let runtime = tokio::runtime::Runtime::new().unwrap();
    let result = runtime.block_on(async { YamlSource::Main.load("").await });

    std::env::set_current_dir(original_dir).unwrap();

    let yaml = result.expect("shippable load must succeed for compatible bundled copy");
    assert_eq!(
        yaml["CLASSIC_Info"]["version"].as_str(),
        Some("shippable-routing-regression"),
        "YamlSource::Main.load must surface the bundled document that the \
         shippable loader resolved, proving the cache-aware wiring is live",
    );
}

#[test]
fn test_default_config() {
    let config = ClassicConfig::default();
    assert!(!config.fcx_mode);
    assert!(!config.show_formid_values);
    assert!(!config.stat_logging);
    assert!(!config.move_unsolved_logs);
    assert!(!config.simplify_logs);
    assert!(config.update_check);
    assert_eq!(config.game_version, "auto");
    assert_eq!(config.update_source, "github");
}

#[tokio::test]
async fn test_save_and_load_yaml() {
    let temp_dir = tempdir().unwrap();
    let config_path = temp_dir.path().join("test_config.yaml");

    let mut config = ClassicConfig {
        fcx_mode: true,
        show_formid_values: true,
        ..Default::default()
    };
    config.paths.ini_folder = Some(PathBuf::from("C:\\Test"));

    // Save config
    config.save_to_yaml(&config_path).await.unwrap();
    assert!(config_path.exists());

    // Load config
    let loaded = ClassicConfig::load_from_yaml(&config_path).await.unwrap();
    assert_eq!(loaded.fcx_mode, config.fcx_mode);
    assert_eq!(loaded.show_formid_values, config.show_formid_values);
    assert_eq!(loaded.paths.ini_folder, config.paths.ini_folder);
}

#[tokio::test]
async fn test_load_from_yaml_merges_multiple_documents() {
    let temp_dir = tempdir().unwrap();
    let config_path = temp_dir.path().join("CLASSIC Settings.yaml");

    std::fs::write(
        &config_path,
        concat!(
            "paths:\n",
            "  game_root: C:/Games/Fallout4\n",
            "formid_databases:\n",
            "  Fallout4:\n",
            "    - databases/FOLON FormIDs.db\n",
            "---\n",
            "fcx_mode: true\n",
            "paths:\n",
            "  docs_root: C:/Users/Test/Documents/My Games/Fallout4\n",
        ),
    )
    .unwrap();

    let config = ClassicConfig::load_from_yaml(&config_path).await.unwrap();

    assert!(config.fcx_mode);
    assert_eq!(config.paths.game_root, PathBuf::from("C:/Games/Fallout4"));
    assert_eq!(
        config.paths.docs_root,
        Some(PathBuf::from("C:/Users/Test/Documents/My Games/Fallout4"))
    );
    assert_eq!(
        config.formid_databases.get("Fallout4"),
        Some(&vec![PathBuf::from("databases/FOLON FormIDs.db")])
    );
}

#[test]
fn test_yaml_round_trip() {
    let config = ClassicConfig {
        fcx_mode: true,
        show_formid_values: false,
        stat_logging: true,
        move_unsolved_logs: false,
        simplify_logs: true,
        update_check: false,
        game_version: "NextGen".to_string(),
        update_source: "both".to_string(),
        auto_switch_to_results: false,
        auto_refresh_interval_ms: 1000,
        paths: PathConfig {
            ini_folder: Some(PathBuf::from("C:\\Ini")),
            scan_custom: Some(PathBuf::from("D:\\Logs")),
            mods_folder: Some(PathBuf::from("C:\\Mods")),
            game_root: PathBuf::from("C:\\Game"),
            docs_root: Some(PathBuf::from("C:\\Docs")),
        },
        formid_databases: HashMap::from([(
            "Fallout4".to_string(),
            vec![PathBuf::from("databases/FOLON FormIDs.db")],
        )]),
    };

    let yaml = config.to_yaml();
    let restored = ClassicConfig::from_yaml(&yaml).unwrap();

    assert_eq!(restored.fcx_mode, config.fcx_mode);
    assert_eq!(restored.show_formid_values, config.show_formid_values);
    assert_eq!(restored.stat_logging, config.stat_logging);
    assert_eq!(restored.move_unsolved_logs, config.move_unsolved_logs);
    assert_eq!(restored.simplify_logs, config.simplify_logs);
    assert_eq!(restored.update_check, config.update_check);
    assert_eq!(restored.game_version, config.game_version);
    assert_eq!(restored.update_source, config.update_source);
    assert_eq!(
        restored.auto_switch_to_results,
        config.auto_switch_to_results
    );
    assert_eq!(
        restored.auto_refresh_interval_ms,
        config.auto_refresh_interval_ms
    );
    assert_eq!(restored.paths.ini_folder, config.paths.ini_folder);
    assert_eq!(restored.paths.scan_custom, config.paths.scan_custom);
    assert_eq!(restored.paths.mods_folder, config.paths.mods_folder);
    assert_eq!(restored.paths.game_root, config.paths.game_root);
    assert_eq!(restored.paths.docs_root, config.paths.docs_root);
    assert_eq!(restored.formid_databases, config.formid_databases);
}

#[test]
fn test_missing_game_version_defaults_to_auto() {
    let yaml_str = "fcx_mode: false\n";
    let yaml = parse_yaml_document(yaml_str);

    let config = ClassicConfig::from_yaml(&yaml).unwrap();

    assert_eq!(config.game_version, "auto");
}

#[test]
fn test_game_version_is_loaded_when_set() {
    let yaml_str = "game_version: Original\n";
    let yaml = parse_yaml_document(yaml_str);

    let config = ClassicConfig::from_yaml(&yaml).unwrap();

    assert_eq!(config.game_version, "Original");
}

#[tokio::test]
async fn test_save_creates_parent_directory() {
    let temp_dir = tempdir().unwrap();
    let nested_path = temp_dir.path().join("subdir").join("config.yaml");

    let config = ClassicConfig::default();

    // This should succeed even though subdir doesn't exist
    config.save_to_yaml(&nested_path).await.unwrap();
    assert!(nested_path.exists());
}

#[tokio::test]
async fn test_yaml_empty_paths() {
    let temp_dir = tempdir().unwrap();
    let config_path = temp_dir.path().join("empty_paths.yaml");

    // Config with no optional paths
    let config = ClassicConfig {
        fcx_mode: false,
        show_formid_values: false,
        stat_logging: false,
        move_unsolved_logs: false,
        simplify_logs: false,
        update_check: true,
        game_version: "auto".to_string(),
        update_source: "github".to_string(),
        auto_switch_to_results: true,
        auto_refresh_interval_ms: 5000,
        paths: PathConfig {
            ini_folder: None,
            scan_custom: None,
            mods_folder: None,
            game_root: PathBuf::from("C:\\Game"),
            docs_root: None,
        },
        formid_databases: HashMap::new(),
    };

    config.save_to_yaml(&config_path).await.unwrap();
    let loaded = ClassicConfig::load_from_yaml(&config_path).await.unwrap();

    assert!(loaded.paths.ini_folder.is_none());
    assert!(loaded.paths.scan_custom.is_none());
    assert!(loaded.paths.mods_folder.is_none());
    assert_eq!(loaded.paths.game_root, PathBuf::from("C:\\Game"));
    assert!(loaded.paths.docs_root.is_none());
}

#[test]
fn test_load_local_yaml_paths_merges_multiple_documents() {
    let _guard = current_dir_lock().lock().unwrap();
    let original_dir = std::env::current_dir().unwrap();
    let temp_dir = tempdir().unwrap();
    let local_yaml_dir = temp_dir.path().join("CLASSIC Data");
    let local_yaml_path = local_yaml_dir.join("CLASSIC Task4Merge Local.yaml");

    std::fs::create_dir_all(&local_yaml_dir).unwrap();
    std::fs::write(
        &local_yaml_path,
        concat!(
            "Game_Info:\n",
            "  Root_Folder_Game: C:/Games/Fallout4\n",
            "---\n",
            "Game_Info:\n",
            "  Root_Folder_Docs: C:/Users/Test/Documents/My Games/Fallout4\n",
        ),
    )
    .unwrap();

    std::env::set_current_dir(temp_dir.path()).unwrap();

    let mut config = ClassicConfig::default();
    let runtime = tokio::runtime::Runtime::new().unwrap();
    let result = runtime.block_on(config.load_local_yaml_paths("Task4Merge"));

    std::env::set_current_dir(original_dir).unwrap();

    result.unwrap();
    assert_eq!(config.paths.game_root, PathBuf::from("C:/Games/Fallout4"));
    assert_eq!(
        config.paths.docs_root,
        Some(PathBuf::from("C:/Users/Test/Documents/My Games/Fallout4"))
    );
}

#[tokio::test]
async fn test_save_local_yaml_paths_to_creates_missing_file() {
    let temp_dir = tempdir().unwrap();
    let local_yaml_path = temp_dir
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Fallout4 Local.yaml");

    let config = ClassicConfig {
        paths: PathConfig {
            ini_folder: None,
            scan_custom: None,
            mods_folder: None,
            game_root: PathBuf::from("C:/Games/Fallout4"),
            docs_root: Some(PathBuf::from("C:/Users/Test/Documents/My Games/Fallout4")),
        },
        ..Default::default()
    };

    config
        .save_local_yaml_paths_to(&local_yaml_path)
        .await
        .unwrap();

    assert!(local_yaml_path.exists());

    let yaml = load_yaml_merged_async(&local_yaml_path).await.unwrap();
    assert_eq!(
        yaml["Game_Info"]["Root_Folder_Game"].as_str(),
        Some("C:/Games/Fallout4")
    );
    assert_eq!(
        yaml["Game_Info"]["Root_Folder_Docs"].as_str(),
        Some("C:/Users/Test/Documents/My Games/Fallout4")
    );
}

#[tokio::test]
async fn test_save_local_yaml_paths_to_preserves_existing_keys() {
    let temp_dir = tempdir().unwrap();
    let local_yaml_path = temp_dir
        .path()
        .join("CLASSIC Data")
        .join("CLASSIC Fallout4 Local.yaml");

    std::fs::create_dir_all(local_yaml_path.parent().unwrap()).unwrap();
    std::fs::write(
        &local_yaml_path,
        concat!(
            "Game_Info:\n",
            "  Docs_Folder_XSE: C:/Users/Test/Documents/My Games/Fallout4/F4SE\n",
        ),
    )
    .unwrap();

    let config = ClassicConfig {
        paths: PathConfig {
            ini_folder: None,
            scan_custom: None,
            mods_folder: None,
            game_root: PathBuf::from("C:/Games/Fallout4"),
            docs_root: Some(PathBuf::from("C:/Users/Test/Documents/My Games/Fallout4")),
        },
        ..Default::default()
    };

    config
        .save_local_yaml_paths_to(&local_yaml_path)
        .await
        .unwrap();

    let yaml = load_yaml_merged_async(&local_yaml_path).await.unwrap();
    assert_eq!(
        yaml["Game_Info"]["Root_Folder_Game"].as_str(),
        Some("C:/Games/Fallout4")
    );
    assert_eq!(
        yaml["Game_Info"]["Root_Folder_Docs"].as_str(),
        Some("C:/Users/Test/Documents/My Games/Fallout4")
    );
    assert_eq!(
        yaml["Game_Info"]["Docs_Folder_XSE"].as_str(),
        Some("C:/Users/Test/Documents/My Games/Fallout4/F4SE")
    );
}

#[test]
fn test_path_config_default() {
    let config = PathConfig::default();
    assert!(config.ini_folder.is_none());
    assert!(config.scan_custom.is_none());
    assert!(config.mods_folder.is_none());
    // Default should be empty - must be loaded from config or Local.yaml
    assert_eq!(config.game_root, PathBuf::new());
    assert!(config.docs_root.is_none());
}

#[test]
fn test_resolve_application_dir_returns_none_without_exe_path() {
    assert_eq!(resolve_application_dir(None), None);
}

#[test]
#[serial]
fn test_application_dir_uses_registry_override_when_set() {
    let override_dir = PathBuf::from("C:/my/project");
    classic_registry_core::set_application_dir(override_dir.clone());
    assert_eq!(application_dir(), Some(override_dir));
    // Clean up so other tests are not affected
    classic_registry_core::unregister(classic_registry_core::Keys::APP_DIR);
}

#[test]
#[serial]
fn test_application_dir_falls_back_to_current_exe_without_override() {
    classic_registry_core::unregister(classic_registry_core::Keys::APP_DIR);
    // With no registry entry, should fall back to current_exe().parent()
    let result = application_dir();
    // We can't predict the exact path but it should be Some (tests run from a real exe)
    assert!(result.is_some());
}

#[test]
fn test_resolve_user_config_dir_returns_none_without_base_dir() {
    assert_eq!(resolve_user_config_dir(None), None);
}

#[test]
fn test_resolve_user_config_dir_appends_classic_directory_name() {
    let config_dir = PathBuf::from("C:/Users/Test/AppData/Roaming");

    assert_eq!(
        resolve_user_config_dir(Some(&config_dir)),
        Some(config_dir.join("CLASSIC"))
    );
}

#[test]
fn test_resolve_settings_search_paths_uses_only_app_dir_modern_filename() {
    let app_dir = PathBuf::from("C:/ClassicApp");
    let user_dir = PathBuf::from("C:/Users/Test/AppData/Roaming/CLASSIC");

    let paths = resolve_settings_search_paths(Some(&app_dir), Some(&user_dir));

    assert_eq!(paths, vec![app_dir.join(DEFAULT_CONFIG_FILENAME)]);
}

#[test]
fn test_resolve_settings_search_paths_uses_app_dir_only_when_user_dir_missing() {
    let app_dir = PathBuf::from("C:/ClassicApp");

    let paths = resolve_settings_search_paths(Some(&app_dir), None);

    assert_eq!(paths, vec![app_dir.join(DEFAULT_CONFIG_FILENAME)]);
}

#[test]
fn test_resolve_settings_search_paths_ignores_user_dir_when_app_dir_missing() {
    let user_dir = PathBuf::from("C:/Users/Test/AppData/Roaming/CLASSIC");

    let paths = resolve_settings_search_paths(None, Some(&user_dir));

    assert!(paths.is_empty());
}

#[test]
fn test_resolve_settings_search_paths_returns_empty_when_no_dirs_are_available() {
    let paths = resolve_settings_search_paths(None, None);

    assert!(paths.is_empty());
}

#[test]
fn test_choose_settings_write_path_prefers_existing_app_dir_file() {
    let temp_dir = tempdir().unwrap();
    let app_dir = temp_dir.path().join("app");
    let user_dir = temp_dir.path().join("user");
    std::fs::create_dir_all(&app_dir).unwrap();
    std::fs::create_dir_all(&user_dir).unwrap();

    let existing_path = app_dir.join(DEFAULT_CONFIG_FILENAME);
    std::fs::write(&existing_path, "fcx_mode: true\n").unwrap();
    let existing = vec![existing_path.clone()];
    let chosen =
        choose_settings_write_path(&existing, Some(&app_dir), Some(&user_dir)).unwrap();

    assert_eq!(chosen, Some(existing_path));
}

#[test]
fn test_choose_settings_write_path_ignores_existing_user_dir_file_when_app_has_none() {
    let temp_dir = tempdir().unwrap();
    let app_dir = temp_dir.path().join("app");
    let user_dir = temp_dir.path().join("user");
    std::fs::create_dir_all(&app_dir).unwrap();
    std::fs::create_dir_all(&user_dir).unwrap();

    let existing_path = user_dir.join("CLASSIC Settings.yaml");
    std::fs::write(&existing_path, "fcx_mode: true\n").unwrap();
    let existing = vec![existing_path.clone()];
    let chosen =
        choose_settings_write_path(&existing, Some(&app_dir), Some(&user_dir)).unwrap();

    assert_eq!(chosen, Some(app_dir.join(DEFAULT_CONFIG_FILENAME)));
}

#[test]
fn test_choose_settings_write_path_returns_none_when_app_dir_target_is_not_writable() {
    let temp_dir = tempdir().unwrap();
    let app_dir = temp_dir.path().join("app");
    let user_dir = temp_dir.path().join("user");
    std::fs::create_dir_all(&app_dir).unwrap();
    std::fs::create_dir_all(&user_dir).unwrap();

    let app_file = app_dir.join("CLASSIC Settings.yaml");
    let user_file = user_dir.join("CLASSIC Settings.yaml");
    let existing = vec![app_file.clone(), user_file.clone()];

    let chosen = choose_settings_write_path_with_access(
        &existing,
        Some(&app_dir),
        Some(&user_dir),
        |path| path != app_file.as_path(),
        |_| false,
    )
    .unwrap();

    assert_eq!(chosen, None);
}

#[test]
fn test_choose_settings_write_path_ignores_user_dir_when_app_dir_target_is_not_writable() {
    let temp_dir = tempdir().unwrap();
    let app_dir = temp_dir.path().join("app");
    let user_dir = temp_dir.path().join("user");
    std::fs::create_dir_all(&app_dir).unwrap();
    std::fs::create_dir_all(&user_dir).unwrap();

    let chosen = choose_settings_write_path_with_access(
        &[],
        Some(&app_dir),
        Some(&user_dir),
        |_| true,
        |path| path.parent() != Some(app_dir.as_path()),
    )
    .unwrap();

    assert_eq!(chosen, None);
}

#[test]
fn test_choose_settings_write_path_prefers_new_modern_file_in_app_dir() {
    let temp_dir = tempdir().unwrap();
    let app_dir = temp_dir.path().join("app");
    let user_dir = temp_dir.path().join("user");
    std::fs::create_dir_all(&app_dir).unwrap();
    std::fs::create_dir_all(&user_dir).unwrap();

    let chosen = choose_settings_write_path(&[], Some(&app_dir), Some(&user_dir)).unwrap();

    assert_eq!(chosen, Some(app_dir.join("CLASSIC Settings.yaml")));
}

#[test]
fn test_choose_settings_write_path_returns_none_when_only_user_dir_is_available() {
    let temp_dir = tempdir().unwrap();
    let user_dir = temp_dir.path().join("user");
    std::fs::create_dir_all(&user_dir).unwrap();

    let chosen = choose_settings_write_path(&[], None, Some(&user_dir)).unwrap();

    assert_eq!(chosen, None);
}

#[test]
fn test_choose_settings_write_path_returns_none_when_no_dirs_are_available() {
    let chosen = choose_settings_write_path(&[], None, None).unwrap();

    assert_eq!(chosen, None);
}

#[test]
fn test_resolve_settings_path_uses_compatibility_fallback_when_no_dirs_are_available() {
    assert_eq!(
        resolve_settings_write_path(None, None),
        PathBuf::from(DEFAULT_CONFIG_FILENAME)
    );
}

#[test]
fn test_resolve_settings_write_path_does_not_use_compatibility_fallback_when_dirs_are_available()
 {
    let app_dir = PathBuf::from("C:/ClassicApp");

    let path = resolve_settings_write_path(Some(&app_dir), None);

    assert_ne!(path, PathBuf::from(DEFAULT_CONFIG_FILENAME));
    assert_eq!(path, app_dir.join(DEFAULT_CONFIG_FILENAME));
}

#[test]
fn test_resolve_existing_settings_path_ignores_user_dir_file() {
    let temp_dir = tempdir().unwrap();
    let app_dir = temp_dir.path().join("app");
    let user_dir = temp_dir.path().join("user");
    std::fs::create_dir_all(&app_dir).unwrap();
    std::fs::create_dir_all(&user_dir).unwrap();

    let existing_path = user_dir.join(DEFAULT_CONFIG_FILENAME);
    std::fs::write(&existing_path, "fcx_mode: true\n").unwrap();

    let resolved = resolve_existing_settings_path(Some(&app_dir), Some(&user_dir));

    assert_eq!(resolved, None);
}

#[test]
fn test_resolve_settings_read_path_ignores_existing_user_dir_file() {
    let temp_dir = tempdir().unwrap();
    let app_dir = temp_dir.path().join("app");
    let user_dir = temp_dir.path().join("user");
    std::fs::create_dir_all(&app_dir).unwrap();
    std::fs::create_dir_all(&user_dir).unwrap();

    let existing_path = user_dir.join(DEFAULT_CONFIG_FILENAME);
    std::fs::write(&existing_path, "fcx_mode: true\n").unwrap();

    let resolved = resolve_settings_read_path(Some(&app_dir), Some(&user_dir));

    assert_eq!(resolved, app_dir.join(DEFAULT_CONFIG_FILENAME));
}

#[test]
fn test_resolve_settings_read_path_has_no_directory_creation_side_effects() {
    let temp_dir = tempdir().unwrap();
    let app_dir = temp_dir.path().join("app");
    let user_dir = temp_dir.path().join("user");

    let resolved = resolve_settings_read_path(Some(&app_dir), Some(&user_dir));

    assert_eq!(resolved, app_dir.join(DEFAULT_CONFIG_FILENAME));
    assert!(!app_dir.exists());
    assert!(!user_dir.exists());
}

#[test]
fn test_resolve_cache_path_prefers_user_config_dir() {
    let user_dir = PathBuf::from("C:/Users/Test/AppData/Roaming/CLASSIC");

    assert_eq!(
        resolve_cache_path(Some(&user_dir), None),
        user_dir.join("cache.yaml")
    );
}

#[test]
fn test_resolve_cache_path_prefers_application_dir_compatibility_fallback_without_user_config_dir()
 {
    let app_dir = PathBuf::from("C:/ClassicApp");

    assert_eq!(
        resolve_cache_path(None, Some(&app_dir)),
        app_dir.join("CLASSIC").join("cache.yaml")
    );
}

#[test]
fn test_resolve_cache_path_uses_relative_compatibility_fallback_without_user_or_app_dir() {
    assert_eq!(
        resolve_cache_path(None, None),
        PathBuf::from("CLASSIC").join("cache.yaml")
    );
}

#[tokio::test]
async fn test_load_or_default_no_file() {
    let temp_dir = tempdir().unwrap();
    let app_dir = temp_dir.path().join("app");
    let user_dir = temp_dir.path().join("user");
    std::fs::create_dir_all(&app_dir).unwrap();
    std::fs::create_dir_all(&user_dir).unwrap();

    let config = load_or_default_from_dirs(Some(&app_dir), Some(&user_dir))
        .await
        .unwrap();
    assert!(!config.fcx_mode);
    assert!(config.update_check);
}

#[tokio::test]
async fn test_load_or_default_prefers_existing_app_dir_file_when_both_locations_exist() {
    let temp_dir = tempdir().unwrap();
    let app_dir = temp_dir.path().join("app");
    let user_dir = temp_dir.path().join("user");
    std::fs::create_dir_all(&app_dir).unwrap();
    std::fs::create_dir_all(&user_dir).unwrap();
    let app_settings_path = app_dir.join("CLASSIC Settings.yaml");
    let user_settings_path = user_dir.join("CLASSIC Settings.yaml");

    std::fs::write(&app_settings_path, "fcx_mode: true\n").unwrap();
    std::fs::write(&user_settings_path, "fcx_mode: false\n").unwrap();

    let config = load_or_default_from_dirs(Some(&app_dir), Some(&user_dir))
        .await
        .unwrap();
    assert!(config.fcx_mode);
}

#[tokio::test]
async fn test_load_or_default_ignores_user_dir_when_app_has_no_settings_file() {
    let temp_dir = tempdir().unwrap();
    let app_dir = temp_dir.path().join("app");
    let user_dir = temp_dir.path().join("user");
    std::fs::create_dir_all(&app_dir).unwrap();
    std::fs::create_dir_all(&user_dir).unwrap();
    let settings_path = user_dir.join("CLASSIC Settings.yaml");

    std::fs::write(settings_path, "fcx_mode: true\n").unwrap();

    let config = load_or_default_from_dirs(Some(&app_dir), Some(&user_dir))
        .await
        .unwrap();
    assert!(!config.fcx_mode);
}

#[tokio::test]
async fn test_load_or_default_ignores_legacy_underscore_filename_from_app_dir() {
    let temp_dir = tempdir().unwrap();
    let app_dir = temp_dir.path().join("app");
    let user_dir = temp_dir.path().join("user");
    std::fs::create_dir_all(&app_dir).unwrap();
    std::fs::create_dir_all(&user_dir).unwrap();
    let settings_path = app_dir.join("CLASSIC_Settings.yaml");

    std::fs::write(settings_path, "fcx_mode: true\n").unwrap();

    let config = load_or_default_from_dirs(Some(&app_dir), Some(&user_dir))
        .await
        .unwrap();
    assert!(!config.fcx_mode);
}

#[test]
fn test_yaml_source_settings_path_mirrors_resolved_settings_path() {
    assert_eq!(
        YamlSource::Settings.path(""),
        resolve_settings_read_path(application_dir().as_deref(), user_config_dir().as_deref())
    );
}

#[test]
fn test_yaml_source_cache_path_matches_resolved_cache_path() {
    assert_eq!(
        YamlSource::Cache.path(""),
        resolve_cache_path(user_config_dir().as_deref(), application_dir().as_deref())
    );
}

#[test]
fn test_formid_databases_default() {
    let config = ClassicConfig::default();
    assert!(config.formid_databases.is_empty());
}

#[test]
fn test_formid_databases_yaml_round_trip() {
    let mut config = ClassicConfig::default();
    config.formid_databases.insert(
        "Fallout4".to_string(),
        vec![PathBuf::from("databases/FOLON FormIDs.db")],
    );
    config.formid_databases.insert("Skyrim".to_string(), vec![]);

    let yaml = config.to_yaml();
    let restored = ClassicConfig::from_yaml(&yaml).unwrap();

    assert_eq!(restored.formid_databases.len(), 2);
    assert_eq!(
        restored.formid_databases["Fallout4"],
        vec![PathBuf::from("databases/FOLON FormIDs.db")]
    );
    assert!(restored.formid_databases["Skyrim"].is_empty());
}

#[test]
fn test_formid_databases_missing_key_defaults_empty() {
    let yaml_str = "fcx_mode: false\n";
    let yaml = parse_yaml_document(yaml_str);

    let config = ClassicConfig::from_yaml(&yaml).unwrap();
    assert!(config.formid_databases.is_empty());
}

#[test]
fn test_formid_databases_multiple_paths_per_game() {
    let mut config = ClassicConfig::default();
    config.formid_databases.insert(
        "Fallout4".to_string(),
        vec![
            PathBuf::from("databases/FOLON FormIDs.db"),
            PathBuf::from("D:/Custom/My FormIDs.db"),
        ],
    );

    let yaml = config.to_yaml();
    let restored = ClassicConfig::from_yaml(&yaml).unwrap();

    assert_eq!(restored.formid_databases["Fallout4"].len(), 2);
    assert_eq!(
        restored.formid_databases["Fallout4"][0],
        PathBuf::from("databases/FOLON FormIDs.db")
    );
    assert_eq!(
        restored.formid_databases["Fallout4"][1],
        PathBuf::from("D:/Custom/My FormIDs.db")
    );
}
