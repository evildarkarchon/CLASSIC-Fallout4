use super::*;
use serial_test::serial;
use std::io::Write;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::thread;
use tempfile::NamedTempFile;

fn create_test_yaml(content: &str) -> NamedTempFile {
    let mut file = NamedTempFile::new().unwrap();
    file.write_all(content.as_bytes()).unwrap();
    file.flush().unwrap();
    file
}

fn reset_cache_state() {
    clear_cache();
    reset_cache_stats();
}

#[test]
#[serial]
fn test_load_settings_sync() {
    reset_cache_state();

    let yaml_content = "key: value\nnumber: 42\n";
    let file = create_test_yaml(yaml_content);

    let result = load_settings_sync("test", file.path());
    assert!(result.is_ok());

    let cached = get_cached("test");
    assert!(cached.is_some());
}

#[tokio::test]
#[serial]
async fn test_load_settings_async() {
    reset_cache_state();

    let yaml_content = "key: value\nnumber: 42\n";
    let file = create_test_yaml(yaml_content);

    let result = load_settings_async("test_async", file.path()).await;
    assert!(result.is_ok());

    let cached = get_cached("test_async");
    assert!(cached.is_some());
}

#[test]
#[serial]
fn test_load_batch_sync() {
    reset_cache_state();

    let yaml1 = create_test_yaml("key1: value1\n");
    let yaml2 = create_test_yaml("key2: value2\n");

    let paths = vec![yaml1.path(), yaml2.path()];
    let result = load_batch_sync(&paths);

    assert!(result.is_ok());
    assert_eq!(result.unwrap(), 2);
    assert_eq!(cache_size(), 2);
}

#[tokio::test]
#[serial]
async fn test_load_batch_async() {
    reset_cache_state();

    let yaml1 = create_test_yaml("key1: value1\n");
    let yaml2 = create_test_yaml("key2: value2\n");

    let paths = vec![yaml1.path(), yaml2.path()];
    let result = load_batch_async(&paths).await;

    assert!(result.is_ok());
    assert_eq!(result.unwrap(), 2);
    assert_eq!(cache_size(), 2);
}

#[test]
#[serial]
fn test_cache_operations() {
    reset_cache_state();

    let yaml_content = "key: value\n";
    let file = create_test_yaml(yaml_content);

    // Load and check
    load_settings_sync("test_key", file.path()).unwrap();
    assert!(is_cached("test_key"));
    assert_eq!(cache_size(), 1);

    // Get keys
    let keys = cache_keys();
    assert_eq!(keys.len(), 1);
    assert!(keys.contains(&"test_key".to_string()));

    let stats = cache_stats();
    assert_eq!(stats.size, 1);
    assert_eq!(stats.capacity, 64);

    // Invalidate
    let removed = invalidate("test_key");
    assert!(removed);
    assert!(!is_cached("test_key"));
    assert_eq!(cache_size(), 0);
}

#[test]
#[serial]
fn test_clear_cache() {
    reset_cache_state();

    let yaml1 = create_test_yaml("key1: value1\n");
    let yaml2 = create_test_yaml("key2: value2\n");

    load_settings_sync("key1", yaml1.path()).unwrap();
    load_settings_sync("key2", yaml2.path()).unwrap();

    assert_eq!(cache_size(), 2);

    clear_cache();
    assert_eq!(cache_size(), 0);
}

// ========================================================================
// Additional Tests for Improved Coverage
// ========================================================================

#[test]
#[serial]
fn test_concurrent_read_access() {
    reset_cache_state();

    // Pre-populate cache
    let yaml_content = "concurrent: test\n";
    let file = create_test_yaml(yaml_content);
    load_settings_sync("concurrent_read", file.path()).unwrap();

    let success_count = AtomicUsize::new(0);

    // Spawn multiple threads to read concurrently
    thread::scope(|s| {
        for _ in 0..20 {
            s.spawn(|| {
                for _ in 0..100 {
                    let cached = get_cached("concurrent_read");
                    if cached.is_some() {
                        success_count.fetch_add(1, Ordering::Relaxed);
                    }
                }
            });
        }
    });

    // All reads should succeed
    assert_eq!(success_count.load(Ordering::Relaxed), 2000);
}

#[test]
#[serial]
fn test_concurrent_write_access() {
    reset_cache_state();

    let yaml_content = "write: test\n";
    let file = create_test_yaml(yaml_content);
    let path = file.path().to_path_buf();

    // Spawn multiple threads to write concurrently
    thread::scope(|s| {
        for i in 0..10 {
            let path = path.clone();
            s.spawn(move || {
                let key = format!("concurrent_write_{}", i);
                let _ = load_settings_sync(&key, &path);
            });
        }
    });

    // All writes should succeed
    assert_eq!(cache_size(), 10);
}

#[test]
#[serial]
fn test_concurrent_read_write() {
    reset_cache_state();

    let yaml_content = "mixed: access\n";
    let file = create_test_yaml(yaml_content);
    let path = file.path().to_path_buf();

    // Pre-populate
    load_settings_sync("mixed_key", &path).unwrap();

    thread::scope(|s| {
        // Readers
        for _ in 0..5 {
            s.spawn(|| {
                for _ in 0..50 {
                    let _ = get_cached("mixed_key");
                    let _ = is_cached("mixed_key");
                    let _ = cache_keys();
                }
            });
        }

        // Writers
        for i in 0..5 {
            let path = path.clone();
            s.spawn(move || {
                for j in 0..10 {
                    let key = format!("writer_{}_{}", i, j);
                    let _ = load_settings_sync(&key, &path);
                }
            });
        }
    });

    // All writer keys plus original key
    assert!(cache_size() >= 1);
}

#[test]
#[serial]
fn test_is_cached_on_empty_cache() {
    reset_cache_state();

    assert!(!is_cached("nonexistent"));
    assert!(!is_cached(""));
    assert!(!is_cached("   "));
}

#[test]
#[serial]
fn test_get_cached_on_empty_cache() {
    reset_cache_state();

    assert!(get_cached("nonexistent").is_none());
    assert!(get_cached("").is_none());
}

#[test]
#[serial]
fn test_invalidate_nonexistent_key() {
    reset_cache_state();

    assert!(!invalidate("never_added"));
    assert!(!invalidate(""));
}

#[test]
#[serial]
fn test_cache_keys_empty() {
    reset_cache_state();

    let keys = cache_keys();
    assert!(keys.is_empty());
}

#[test]
#[serial]
fn test_cache_size_empty() {
    reset_cache_state();

    assert_eq!(cache_size(), 0);
}

#[test]
#[serial]
fn test_clear_empty_cache() {
    reset_cache_state();

    // Should not panic on empty cache
    clear_cache();
    assert_eq!(cache_size(), 0);
}

#[test]
#[serial]
fn test_reload_same_key_updates_value() {
    reset_cache_state();

    let yaml1 = create_test_yaml("version: 1\n");
    let yaml2 = create_test_yaml("version: 2\n");

    load_settings_sync("version_key", yaml1.path()).unwrap();
    let cached1 = get_cached("version_key").unwrap();
    assert_eq!(cached1[0]["version"].as_i64(), Some(1));

    load_settings_sync("version_key", yaml2.path()).unwrap();
    let cached2 = get_cached("version_key").unwrap();
    assert_eq!(cached2[0]["version"].as_i64(), Some(2));

    // Cache size should still be 1
    assert_eq!(cache_size(), 1);
}

#[tokio::test]
#[serial]
async fn test_async_reload_same_key_updates_value() {
    reset_cache_state();

    let yaml1 = create_test_yaml("async_version: 1\n");
    let yaml2 = create_test_yaml("async_version: 2\n");

    load_settings_async("async_version_key", yaml1.path())
        .await
        .unwrap();
    let cached1 = get_cached("async_version_key").unwrap();
    assert_eq!(cached1[0]["async_version"].as_i64(), Some(1));

    load_settings_async("async_version_key", yaml2.path())
        .await
        .unwrap();
    let cached2 = get_cached("async_version_key").unwrap();
    assert_eq!(cached2[0]["async_version"].as_i64(), Some(2));
}

#[test]
#[serial]
fn test_arc_cloning_preserves_reference() {
    reset_cache_state();

    let yaml_content = "arc: test\n";
    let file = create_test_yaml(yaml_content);

    let result = load_settings_sync("arc_key", file.path()).unwrap();

    // Get from cache
    let cached = get_cached("arc_key").unwrap();

    // Both should be same Arc
    assert!(Arc::ptr_eq(&result, &cached));
}

#[test]
#[serial]
fn test_load_batch_sync_empty_paths() {
    reset_cache_state();

    let paths: Vec<&Path> = vec![];
    let result = load_batch_sync(&paths);

    assert!(result.is_ok());
    assert_eq!(result.unwrap(), 0);
    assert_eq!(cache_size(), 0);
}

#[tokio::test]
#[serial]
async fn test_load_batch_async_empty_paths() {
    reset_cache_state();

    let paths: Vec<&Path> = vec![];
    let result = load_batch_async(&paths).await;

    assert!(result.is_ok());
    assert_eq!(result.unwrap(), 0);
    assert_eq!(cache_size(), 0);
}

#[test]
#[serial]
fn test_special_key_characters() {
    reset_cache_state();

    let yaml_content = "key: value\n";
    let file = create_test_yaml(yaml_content);

    // Test keys with special characters
    let special_keys = [
        "key with spaces",
        "key/with/slashes",
        "key\\with\\backslashes",
        "key:with:colons",
        "key.with.dots",
        "key-with-dashes",
        "key_with_underscores",
        "中文键",
        "キー",
        "🔑",
    ];

    for key in special_keys {
        load_settings_sync(key, file.path()).unwrap();
        assert!(is_cached(key), "Key '{}' should be cached", key);
    }

    assert_eq!(cache_size(), special_keys.len());
}

#[test]
#[serial]
fn test_batch_uses_path_as_key() {
    reset_cache_state();

    let yaml1 = create_test_yaml("batch: one\n");
    let yaml2 = create_test_yaml("batch: two\n");

    let path1_str = yaml1.path().display().to_string();
    let path2_str = yaml2.path().display().to_string();

    let paths = vec![yaml1.path(), yaml2.path()];
    load_batch_sync(&paths).unwrap();

    // Keys should be the path strings
    let keys = cache_keys();
    assert!(keys.contains(&path1_str));
    assert!(keys.contains(&path2_str));
}

#[tokio::test]
#[serial]
async fn test_async_batch_uses_path_as_key() {
    reset_cache_state();

    let yaml1 = create_test_yaml("async_batch: one\n");
    let yaml2 = create_test_yaml("async_batch: two\n");

    let path1_str = yaml1.path().display().to_string();
    let path2_str = yaml2.path().display().to_string();

    let paths = vec![yaml1.path(), yaml2.path()];
    load_batch_async(&paths).await.unwrap();

    let keys = cache_keys();
    assert!(keys.contains(&path1_str));
    assert!(keys.contains(&path2_str));
}

#[test]
#[serial]
fn test_invalidate_during_reads() {
    reset_cache_state();

    let yaml_content = "invalidate: test\n";
    let file = create_test_yaml(yaml_content);

    load_settings_sync("inv_key", file.path()).unwrap();

    thread::scope(|s| {
        // Readers
        for _ in 0..5 {
            s.spawn(|| {
                for _ in 0..100 {
                    // These may or may not find the key depending on timing
                    let _ = get_cached("inv_key");
                }
            });
        }

        // Invalidator
        s.spawn(|| {
            std::thread::sleep(std::time::Duration::from_millis(1));
            let _ = invalidate("inv_key");
        });
    });

    // After all threads complete, key should be invalidated
    assert!(!is_cached("inv_key"));
}

#[test]
#[serial]
fn test_cache_hit_and_miss_stats_follow_get_cached_behavior() {
    reset_cache_state();

    let yaml_content = "many: entries\n";
    let file = create_test_yaml(yaml_content);

    load_settings_sync("tracked_key", file.path()).unwrap();

    assert!(get_cached("tracked_key").is_some());
    assert!(get_cached("missing_key").is_none());

    let stats = cache_stats();
    assert_eq!(stats.hits, 1);
    assert_eq!(stats.misses, 1);
    assert_eq!(stats.hit_rate, 0.5);
}

#[test]
#[serial]
fn test_cache_stats_reports_canonical_capacity_fields() {
    reset_cache_state();

    let CacheStats {
        hits,
        misses,
        hit_rate,
        size,
        capacity,
    } = cache_stats();

    assert_eq!(hits, 0);
    assert_eq!(misses, 0);
    assert_eq!(hit_rate, 0.0);
    assert_eq!(size, 0);
    assert_eq!(capacity, 64);
}

#[test]
#[serial]
fn test_bounded_cache_never_exceeds_capacity_without_asserting_victim_order() {
    reset_cache_state();

    let yaml_content = "many: entries\n";
    let file = create_test_yaml(yaml_content);

    for i in 0..128 {
        let key = format!("entry_{}", i);
        load_settings_sync(&key, file.path()).unwrap();
    }

    assert!(cache_size() <= 64);

    let stats = cache_stats();
    assert!(stats.size <= 64);
    assert_eq!(stats.capacity, 64);

    clear_cache();
    assert_eq!(cache_size(), 0);
}
