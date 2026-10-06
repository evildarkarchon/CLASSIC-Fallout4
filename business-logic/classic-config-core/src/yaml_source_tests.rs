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

    classic_shared_core::yaml::clear_global_yaml_cache();
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

// The stable tokens, descriptions, order, display, and serde form below are
// the projections the retired `classic_settings_core::YamlFile` exposed. The
// literals come from that former contract (and the `yaml-file-values`
// conformance pack), not from this implementation.
#[test]
fn as_str_keeps_the_former_yaml_file_tokens() {
    assert_eq!(YamlSource::Main.as_str(), "Main");
    assert_eq!(YamlSource::Ignore.as_str(), "Ignore");
    assert_eq!(YamlSource::Game.as_str(), "Game");
    assert_eq!(YamlSource::GameLocal.as_str(), "GameLocal");
    assert_eq!(YamlSource::Test.as_str(), "Test");
    assert_eq!(YamlSource::Cache.as_str(), "Cache");
}

#[test]
fn description_keeps_the_former_yaml_file_locations() {
    assert_eq!(
        YamlSource::Main.description(),
        "CLASSIC Data/databases/CLASSIC Main.yaml"
    );
    assert_eq!(YamlSource::Ignore.description(), "CLASSIC Ignore.yaml");
    assert_eq!(
        YamlSource::Game.description(),
        "CLASSIC Data/databases/CLASSIC {Game}.yaml"
    );
    assert_eq!(
        YamlSource::GameLocal.description(),
        "CLASSIC Data/CLASSIC {Game} Local.yaml"
    );
    assert_eq!(YamlSource::Test.description(), "tests/test_settings.yaml");
    assert_eq!(
        YamlSource::Cache.description(),
        "User config dir/CLASSIC/cache.yaml"
    );
}

#[test]
fn all_lists_the_six_kinds_in_stable_order() {
    assert_eq!(
        YamlSource::all(),
        [
            YamlSource::Main,
            YamlSource::Ignore,
            YamlSource::Game,
            YamlSource::GameLocal,
            YamlSource::Test,
            YamlSource::Cache,
        ]
    );
}

#[test]
fn display_uses_the_stable_token_not_the_display_name() {
    assert_eq!(YamlSource::Main.to_string(), "Main");
    assert_eq!(YamlSource::GameLocal.to_string(), "GameLocal");
    // `display_name` stays the human-facing label and is unaffected.
    assert_eq!(YamlSource::Main.display_name(), "Main Database");
}

#[test]
fn serde_uses_the_former_yaml_file_variant_names() {
    assert_eq!(
        serde_json::to_string(&YamlSource::GameLocal).unwrap(),
        "\"GameLocal\""
    );
    for source in YamlSource::all() {
        let json = serde_json::to_string(&source).unwrap();
        assert_eq!(json, format!("\"{}\"", source.as_str()));
        let round_trip: YamlSource = serde_json::from_str(&json).unwrap();
        assert_eq!(round_trip, source);
    }
    assert!(serde_json::from_str::<YamlSource>("\"Settings\"").is_err());
}

#[test]
fn schema_compat_names_the_range_for_each_update_eligible_file() {
    assert_eq!(
        YamlSource::Main.schema_compat(""),
        Some(SchemaCompat::new(2, 0))
    );
    assert_eq!(
        YamlSource::Game.schema_compat("Fallout4"),
        Some(SchemaCompat::new(1, 0))
    );
    // Fallout 4 VR shares the Fallout 4 game database and its range.
    assert_eq!(
        YamlSource::Game.schema_compat("Fallout4VR"),
        Some(SchemaCompat::new(1, 0))
    );
}

#[test]
fn schema_compat_is_absent_for_files_without_a_declared_range() {
    assert_eq!(YamlSource::Game.schema_compat("Skyrim"), None);
    for source in [
        YamlSource::Ignore,
        YamlSource::GameLocal,
        YamlSource::Test,
        YamlSource::Cache,
    ] {
        assert_eq!(source.schema_compat("Fallout4"), None, "{source}");
    }
}

#[test]
fn resolves_generic_paths() {
    assert_eq!(
        YamlSource::Game.path("Fallout4"),
        PathBuf::from("CLASSIC Data/databases/CLASSIC Fallout4.yaml")
    );
    assert_eq!(
        YamlSource::Game.path("Fallout4VR"),
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
    assert_eq!(
        application_dir_in(&classic_registry_core::RegistryScope::default_scope()),
        Some(override_dir)
    );
    classic_registry_core::unregister(classic_registry_core::Keys::APP_DIR);
}

#[test]
#[serial]
fn application_dir_in_reads_only_the_selected_registry_scope() {
    let scope = classic_registry_core::RegistryScope::new_isolated();
    let scoped_dir = PathBuf::from("C:/facade/config");
    let default_dir = PathBuf::from("C:/default/app");
    classic_registry_core::set_application_dir(default_dir.clone());
    scope.set_application_dir(scoped_dir.clone());

    assert_eq!(application_dir_in(&scope), Some(scoped_dir));
    assert_eq!(
        application_dir_in(&classic_registry_core::RegistryScope::default_scope()),
        Some(default_dir.clone())
    );
    assert_eq!(
        classic_registry_core::get_application_dir(),
        Some(default_dir)
    );

    // An empty scope falls back to the executable directory, never to the
    // default scope's override.
    let empty = classic_registry_core::RegistryScope::new_isolated();
    let exe_dir = std::env::current_exe()
        .ok()
        .and_then(|path| resolve_application_dir(Some(path.as_path())));
    assert_eq!(application_dir_in(&empty), exe_dir);
    classic_registry_core::unregister(classic_registry_core::Keys::APP_DIR);
}

#[test]
#[serial]
fn cache_path_in_registry_scope_uses_that_scope_application_dir() {
    let scope = classic_registry_core::RegistryScope::new_isolated();
    let scoped_dir = PathBuf::from("C:/facade/config");
    scope.set_application_dir(scoped_dir.clone());
    classic_registry_core::set_application_dir(PathBuf::from("C:/default/app"));

    let user_dir = user_config_dir();
    assert_eq!(
        YamlSource::Cache.path_in_registry_scope("", &scope),
        resolve_cache_path(user_dir.as_deref(), Some(scoped_dir.as_path()))
    );
    // Non-cache sources never consult the registry.
    assert_eq!(
        YamlSource::Main.path_in_registry_scope("", &scope),
        YamlSource::Main.path("")
    );
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
