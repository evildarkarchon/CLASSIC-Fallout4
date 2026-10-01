use super::*;
use serial_test::serial;
use std::io::Write;
use tempfile::NamedTempFile;

fn create_test_yaml(content: &str) -> NamedTempFile {
    let mut file = NamedTempFile::new().unwrap();
    file.write_all(content.as_bytes()).unwrap();
    file.flush().unwrap();
    file
}

#[test]
#[serial]
fn test_public_reexports_support_sync_workflow() {
    clear_cache();

    let yaml_content = "game: Fallout4\nversion: 1.0\n";
    let file = create_test_yaml(yaml_content);

    let merged = load_yaml_merged_sync(file.path()).unwrap();
    assert_eq!(merged["game"].as_str(), Some("Fallout4"));

    let result = load_settings_sync("game_settings", file.path());
    assert!(result.is_ok());
    assert!(is_cached("game_settings"));
    assert_eq!(cache_size(), 1);

    let cached = get_cached("game_settings");
    assert!(cached.is_some());

    let keys = cache_keys();
    assert_eq!(keys.len(), 1);
    assert!(keys.contains(&"game_settings".to_string()));

    assert!(invalidate("game_settings"));
    assert!(!is_cached("game_settings"));
}

#[tokio::test]
#[serial]
async fn test_public_reexports_support_async_workflow() {
    clear_cache();

    let yaml_content = "game: Skyrim\n---\nversion: 2\n";
    let file = create_test_yaml(yaml_content);

    let merged = load_yaml_merged_async(file.path()).await.unwrap();
    assert_eq!(merged["game"].as_str(), Some("Skyrim"));
    assert_eq!(merged["version"].as_i64(), Some(2));

    let result = load_settings_async("game_settings_async", file.path()).await;
    assert!(result.is_ok());

    assert!(is_cached("game_settings_async"));
    assert_eq!(cache_size(), 1);

    clear_cache();
    assert_eq!(cache_size(), 0);
}

/// The facade must forward to the shared-core owner rather than keep a second
/// cache: entries, counters, and clears are visible through both paths.
#[test]
#[serial]
fn test_facade_and_shared_core_share_one_logical_key_cache() {
    use classic_shared_core::yaml as shared_yaml;

    clear_cache();
    reset_cache_stats();

    let file = create_test_yaml("game: Fallout4\n");
    shared_yaml::load_settings_sync("shared_owner_key", file.path()).unwrap();

    assert!(is_cached("shared_owner_key"));
    assert!(get_cached("shared_owner_key").is_some());
    assert_eq!(shared_yaml::cache_stats().hits, 1);

    clear_cache();
    assert!(!shared_yaml::is_cached("shared_owner_key"));
    assert_eq!(shared_yaml::cache_size(), 0);

    // Clearing entries does not reset counters; resetting through the facade
    // resets the owner's counters.
    assert_eq!(shared_yaml::cache_stats().hits, 1);
    reset_cache_stats();
    assert_eq!(shared_yaml::cache_stats().hits, 0);
}

/// `YamlOperations` and the path/mtime-aware YAML-file cache are forwarded
/// from shared core too: a load through the facade lands in the owner's
/// default scope, and facade clears/resets act on that same scope.
#[test]
#[serial]
fn test_facade_and_shared_core_share_one_default_yaml_file_cache() {
    use classic_shared_core::yaml as shared_yaml;

    clear_global_yaml_cache();
    reset_yaml_cache_stats();

    let file = create_test_yaml("game: Fallout4\n");
    let ops = YamlOperations::new();
    assert_eq!(
        ops.cache_scope(),
        &shared_yaml::YamlFileCacheScope::default_scope()
    );
    ops.load_yaml_file(file.path()).unwrap();
    shared_yaml::YamlOperations::new()
        .load_yaml_file(file.path())
        .unwrap();

    let stats = shared_yaml::yaml_cache_stats();
    assert_eq!((stats.hits, stats.misses, stats.size), (1, 1, 1));

    clear_global_yaml_cache();
    assert_eq!(shared_yaml::yaml_cache_stats().size, 0);
    assert_eq!(shared_yaml::yaml_cache_stats().hits, 1);
    reset_yaml_cache_stats();
    assert_eq!(shared_yaml::yaml_cache_stats().hits, 0);

    // The YAML-file cache stays distinct from the logical-key cache.
    clear_cache();
    load_settings_sync("facade_logical", file.path()).unwrap();
    clear_global_yaml_cache();
    assert!(shared_yaml::is_cached("facade_logical"));
    clear_cache();
}
