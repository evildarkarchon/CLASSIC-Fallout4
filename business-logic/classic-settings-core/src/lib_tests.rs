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
