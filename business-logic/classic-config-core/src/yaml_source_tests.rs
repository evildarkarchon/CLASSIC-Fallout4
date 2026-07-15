use super::*;
use serial_test::serial;
use std::sync::{Mutex, OnceLock};
use tempfile::tempdir;

fn current_dir_lock() -> &'static Mutex<()> {
    static LOCK: OnceLock<Mutex<()>> = OnceLock::new();
    LOCK.get_or_init(|| Mutex::new(()))
}

#[test]
#[serial]
fn main_load_routes_through_shippable_loader() {
    // The process CWD is global, so keep the lock out of an async await point.
    let _guard = current_dir_lock().lock().unwrap();
    let original_dir = std::env::current_dir().unwrap();
    let work_dir = tempdir().unwrap();
    let bundled_dir = work_dir.path().join("CLASSIC Data").join("databases");
    std::fs::create_dir_all(&bundled_dir).unwrap();
    let bundled_payload = concat!(
        "schema_version: \"2.0\"\n",
        "CLASSIC_Info:\n",
        "  version: shippable-routing-regression\n",
    );
    std::fs::write(bundled_dir.join("CLASSIC Main.yaml"), bundled_payload).unwrap();

    classic_settings_core::clear_global_yaml_cache();
    std::env::set_current_dir(work_dir.path()).unwrap();
    let runtime = tokio::runtime::Runtime::new().unwrap();
    let result = runtime.block_on(async { YamlSource::Main.load("").await });
    std::env::set_current_dir(original_dir).unwrap();

    let yaml = result.expect("shippable load must accept a compatible bundled copy");
    assert_eq!(
        yaml["CLASSIC_Info"]["version"].as_str(),
        Some("shippable-routing-regression")
    );
}

#[test]
fn exposes_only_non_user_settings_sources() {
    let sources = [
        YamlSource::Main,
        YamlSource::Ignore,
        YamlSource::Game,
        YamlSource::GameLocal,
        YamlSource::Test,
        YamlSource::Cache,
    ];

    assert!(
        sources
            .iter()
            .all(|source| source.display_name() != "Settings")
    );
}

#[test]
fn resolves_generic_paths() {
    assert_eq!(
        YamlSource::Game.path("Fallout4"),
        PathBuf::from("CLASSIC Data/databases/CLASSIC Fallout4.yaml")
    );
    assert_eq!(
        YamlSource::GameLocal.path("Fallout4"),
        PathBuf::from("CLASSIC Data/CLASSIC Fallout4 Local.yaml")
    );
    assert_eq!(
        YamlSource::Ignore.path(""),
        PathBuf::from("CLASSIC Ignore.yaml")
    );
}

#[test]
fn resolve_application_dir_returns_none_without_exe_path() {
    assert_eq!(resolve_application_dir(None), None);
}

#[test]
#[serial]
fn application_dir_uses_registry_override_when_set() {
    let override_dir = PathBuf::from("C:/my/project");
    classic_registry_core::set_application_dir(override_dir.clone());
    assert_eq!(application_dir(), Some(override_dir));
    classic_registry_core::unregister(classic_registry_core::Keys::APP_DIR);
}

#[test]
fn resolve_user_config_dir_appends_classic_directory_name() {
    let config_dir = PathBuf::from("C:/Users/Test/AppData/Roaming");
    assert_eq!(
        resolve_user_config_dir(Some(&config_dir)),
        Some(config_dir.join("CLASSIC"))
    );
}

#[test]
fn resolve_cache_path_prefers_user_config_dir() {
    let user_dir = PathBuf::from("C:/Users/Test/AppData/Roaming/CLASSIC");
    assert_eq!(
        resolve_cache_path(Some(&user_dir), None),
        user_dir.join("cache.yaml")
    );
}

#[test]
fn resolve_cache_path_uses_application_fallback_without_user_config_dir() {
    let app_dir = PathBuf::from("C:/ClassicApp");
    assert_eq!(
        resolve_cache_path(None, Some(&app_dir)),
        app_dir.join("CLASSIC").join("cache.yaml")
    );
}

#[test]
fn resolve_cache_path_uses_relative_fallback_without_known_directories() {
    assert_eq!(
        resolve_cache_path(None, None),
        PathBuf::from("CLASSIC").join("cache.yaml")
    );
}
