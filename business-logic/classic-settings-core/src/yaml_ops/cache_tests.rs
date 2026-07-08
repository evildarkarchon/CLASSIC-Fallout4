#![allow(unused_imports)]

use super::super::*;
use std::fs;
use std::io::Write;
use std::path::Path;
use std::sync::Arc;
use std::thread;
use std::time::Duration;
use tempfile::{NamedTempFile, tempdir};
use yaml_rust2::Yaml;
#[test]
#[serial_test::serial]
fn test_cache_hit_on_second_load() {
    clear_global_yaml_cache();
    reset_yaml_cache_stats();

    let mut temp_file = NamedTempFile::new().expect("Failed to create temp file");
    writeln!(temp_file, "cached: true").expect("Write failed");
    let file_path = temp_file.path().to_path_buf();

    let ops = YamlOperations::new();

    let _ = ops
        .load_yaml_file(&file_path)
        .expect("First load should succeed");
    let _ = ops
        .load_yaml_file(&file_path)
        .expect("Second load should succeed");

    let stats = yaml_cache_stats();
    assert_eq!(stats.misses, 1, "First unchanged load should miss once");
    assert_eq!(stats.hits, 1, "Second unchanged load should hit once");
    assert_eq!(stats.size, 1, "Exactly one file should be cached");
}

#[test]
#[serial_test::serial]
fn test_cache_invalidation_on_file_modify() {
    // Clear cache before test
    clear_global_yaml_cache();

    let mut temp_file = NamedTempFile::new().expect("Failed to create temp file");
    writeln!(temp_file, "version: 1").expect("Write failed");

    let ops = YamlOperations::new();

    // First load
    let yaml1 = ops
        .load_yaml_file(temp_file.path())
        .expect("Load should succeed");
    assert_eq!(ops.get_setting(&yaml1, "version"), Some(Yaml::Integer(1)));

    // Wait a bit to ensure different mtime
    thread::sleep(Duration::from_millis(50));

    // Modify file
    let file = fs::OpenOptions::new()
        .write(true)
        .truncate(true)
        .open(temp_file.path())
        .expect("Open failed");
    let mut writer = std::io::BufWriter::new(file);
    writeln!(writer, "version: 2").expect("Write failed");
    writer.flush().expect("Flush failed");
    drop(writer);

    // Second load should see new content
    let yaml2 = ops
        .load_yaml_file(temp_file.path())
        .expect("Load should succeed");
    assert_eq!(ops.get_setting(&yaml2, "version"), Some(Yaml::Integer(2)));
}

#[test]
#[serial_test::serial]
fn test_cache_disabled_always_reads() {
    clear_global_yaml_cache();
    reset_yaml_cache_stats();

    let mut temp_file = NamedTempFile::new().expect("Failed to create temp file");
    writeln!(temp_file, "cached: false").expect("Write failed");
    let file_path = temp_file.path().to_path_buf();

    let mut ops = YamlOperations::new();
    ops.set_cache_enabled(false);

    let _ = ops
        .load_yaml_file(&file_path)
        .expect("First load should succeed");
    let _ = ops
        .load_yaml_file(&file_path)
        .expect("Second load should succeed");

    let stats = yaml_cache_stats();
    assert_eq!(stats.hits, 0, "Disabled caching should not record hits");
    assert_eq!(
        stats.misses, 2,
        "Disabled caching should re-read on every load"
    );
    assert_eq!(stats.size, 0, "Disabled caching should not retain entries");
}

#[test]
#[serial_test::serial]
fn test_cache_stats_empty() {
    clear_global_yaml_cache();

    let ops = YamlOperations::new();
    let stats = ops.get_cache_stats();

    assert_eq!(stats.get("cached_files"), Some(&0));
    assert_eq!(stats.get("total_bytes"), Some(&0));
}

#[test]
#[serial_test::serial]
fn test_cache_stats_after_load() {
    clear_global_yaml_cache();
    reset_yaml_cache_stats();

    let ops = YamlOperations::new();

    let mut temp_file = NamedTempFile::new().expect("Failed to create temp file");
    let content = "stats_test: true\nvalue: 123";
    writeln!(temp_file, "{}", content).expect("Write failed");

    let _ = ops
        .load_yaml_file(temp_file.path())
        .expect("Load should succeed");

    let stats = ops.get_cache_stats();
    assert_eq!(stats.get("cached_files"), Some(&1));
    assert_eq!(stats.get("capacity"), Some(&128));
    assert!(
        stats.get("total_bytes").copied().unwrap_or_default() > 0,
        "Cache byte count should increase after load"
    );
}

#[test]
#[serial_test::serial]
fn test_clear_cache() {
    // Clear cache at start to prevent pollution from other serial tests
    clear_global_yaml_cache();

    let mut temp_file = NamedTempFile::new().expect("Failed to create temp file");
    writeln!(temp_file, "clear_test: true").expect("Write failed");

    let ops = YamlOperations::new();
    let _ = ops
        .load_yaml_file(temp_file.path())
        .expect("Load should succeed");

    // Verify cache has at least one entry
    let stats = ops.get_cache_stats();
    assert!(
        stats.get("cached_files").unwrap() >= &1,
        "Cache should have at least one entry after load"
    );

    // Clear cache
    ops.clear_cache();

    // Verify cache is empty
    let stats = ops.get_cache_stats();
    assert_eq!(stats.get("cached_files"), Some(&0));
}

#[test]
#[serial_test::serial]
fn test_clear_global_yaml_cache_function() {
    // Clear cache at start to prevent pollution from other serial tests
    clear_global_yaml_cache();

    // Load a file to populate cache
    let mut temp_file = NamedTempFile::new().expect("Failed to create temp file");
    writeln!(temp_file, "global_clear: true").expect("Write failed");

    let ops = YamlOperations::new();
    let _ = ops
        .load_yaml_file(temp_file.path())
        .expect("Load should succeed");

    // Clear using global function
    clear_global_yaml_cache();

    // Verify cache is empty
    let stats = ops.get_cache_stats();
    assert_eq!(stats.get("cached_files"), Some(&0));
}

#[test]
#[serial_test::serial]
fn test_cache_enabled_toggle() {
    let mut ops = YamlOperations::new();

    // Default should be enabled
    assert!(ops.is_cache_enabled());

    // Disable
    ops.set_cache_enabled(false);
    assert!(!ops.is_cache_enabled());

    // Re-enable
    ops.set_cache_enabled(true);
    assert!(ops.is_cache_enabled());
}

// ============================================================================
// Helper Method Tests
// ============================================================================

#[test]
#[serial_test::serial]
fn test_concurrent_cache_access() {
    // Clear cache before test
    clear_global_yaml_cache();

    let mut temp_file = NamedTempFile::new().expect("Failed to create temp file");
    writeln!(temp_file, "concurrent: true\nvalue: 42").expect("Write failed");
    let path = temp_file.path().to_path_buf();

    let ops = Arc::new(YamlOperations::new());

    // Spawn multiple threads reading the same file
    let handles: Vec<_> = (0..4)
        .map(|_| {
            let ops_clone = ops.clone();
            let path_clone = path.clone();
            thread::spawn(move || ops_clone.load_yaml_file(&path_clone))
        })
        .collect();

    // All threads should succeed
    for handle in handles {
        let result = handle.join().expect("Thread panicked");
        assert!(result.is_ok());
    }
}

#[test]
#[serial_test::serial]
fn test_concurrent_cache_reads() {
    let mut temp_file = NamedTempFile::new().expect("Failed to create temp file");
    writeln!(temp_file, "multi_read: true").expect("Write failed");
    let path = temp_file.path().to_path_buf();

    let ops = Arc::new(YamlOperations::new());

    // First, load to populate cache
    let initial_yaml = ops
        .load_yaml_file(&path)
        .expect("Initial load should succeed");

    // Now spawn multiple threads to read concurrently
    // Note: We don't assert cache state here due to parallel test execution
    // The key test is that concurrent reads work without panics or errors
    let handles: Vec<_> = (0..8)
        .map(|_| {
            let ops_clone = ops.clone();
            let path_clone = path.clone();
            thread::spawn(move || {
                for _ in 0..10 {
                    let result = ops_clone.load_yaml_file(&path_clone);
                    assert!(result.is_ok(), "Concurrent read should succeed");
                }
            })
        })
        .collect();

    // All threads should complete successfully
    for handle in handles {
        handle
            .join()
            .expect("Thread should not panic during concurrent reads");
    }

    // Final load should also succeed and return same content
    let final_yaml = ops
        .load_yaml_file(&path)
        .expect("Final load should succeed");
    assert_eq!(
        ops.get_setting(&initial_yaml, "multi_read"),
        ops.get_setting(&final_yaml, "multi_read"),
        "Content should be consistent across reads"
    );
}

#[test]
#[serial_test::serial]
fn test_cache_stats_function() {
    clear_global_yaml_cache();
    reset_yaml_cache_stats();

    let stats = yaml_cache_stats();
    assert_eq!(stats.hits, 0);
    assert_eq!(stats.misses, 0);
    assert_eq!(stats.hit_rate, 0.0);
    assert_eq!(stats.size, 0);

    let serialized = serde_json::to_value(&stats).expect("Cache stats should serialize");
    let object = serialized
        .as_object()
        .expect("Serialized cache stats should be an object");

    assert_eq!(object.len(), 5, "Cache stats should expose five fields");
    assert!(object.contains_key("hits"));
    assert!(object.contains_key("misses"));
    assert!(object.contains_key("hit_rate"));
    assert!(object.contains_key("size"));
    assert!(object.contains_key("capacity"));
    assert!(!object.contains_key("total_bytes"));
}

#[test]
#[serial_test::serial]
fn test_cache_stats_after_operations() {
    clear_global_yaml_cache();
    reset_yaml_cache_stats();

    let mut temp_file = NamedTempFile::new().expect("Failed to create temp file");
    writeln!(temp_file, "stats_test: true").expect("Write failed");

    let ops = YamlOperations::new();

    let _ = ops
        .load_yaml_file(temp_file.path())
        .expect("First load should succeed");
    let _ = ops
        .load_yaml_file(temp_file.path())
        .expect("Second load should succeed");

    let stats = yaml_cache_stats();
    assert_eq!(stats.misses, 1, "Initial read should miss once");
    assert_eq!(stats.hits, 1, "Second unchanged read should hit once");
    assert_eq!(stats.size, 1, "One file should remain cached");
    assert_eq!(
        stats.hit_rate, 0.5,
        "Hit rate should reflect one hit in two reads"
    );

    let serialized = serde_json::to_value(&stats).expect("Cache stats should serialize");
    assert_eq!(serialized["capacity"].as_u64(), Some(128));
}

#[test]
#[serial_test::serial]
fn test_reset_cache_stats_function() {
    clear_global_yaml_cache();
    reset_yaml_cache_stats();

    // Generate some hits/misses
    let mut temp_file = NamedTempFile::new().expect("Failed to create temp file");
    writeln!(temp_file, "reset_test: yes").expect("Write failed");

    let ops = YamlOperations::new();
    let _ = ops.load_yaml_file(temp_file.path()).unwrap();
    let _ = ops.load_yaml_file(temp_file.path()).unwrap();

    let stats = yaml_cache_stats();
    assert!(stats.hits > 0 || stats.misses > 0);

    // Reset
    reset_yaml_cache_stats();

    let stats = yaml_cache_stats();
    assert_eq!(stats.hits, 0);
    assert_eq!(stats.misses, 0);
    assert_eq!(stats.hit_rate, 0.0);
    assert_eq!(
        stats.size, 1,
        "Resetting counters should not clear cache entries"
    );
}

#[test]
#[serial_test::serial]
fn test_cache_size_is_bounded_without_assuming_evicted_key() {
    clear_global_yaml_cache();
    reset_yaml_cache_stats();

    let temp_dir = tempdir().expect("Failed to create temp dir");
    let ops = YamlOperations::new();

    for index in 0..129 {
        let path = temp_dir.path().join(format!("cache-{index}.yaml"));
        fs::write(&path, format!("index: {index}\n")).expect("Failed to write test YAML");
        let _ = ops.load_yaml_file(&path).expect("Load should succeed");
    }

    let stats = yaml_cache_stats();
    let serialized = serde_json::to_value(&stats).expect("Cache stats should serialize");

    assert_eq!(serialized["capacity"].as_u64(), Some(128));
    assert!(
        stats.size <= 128,
        "Bounded cache should never report more entries than capacity"
    );
}

// ============================================================================
// Additional Edge Cases for set_setting / set_settings_batch
// ============================================================================

#[test]
#[serial_test::serial]
fn test_save_yaml_file_with_cache_disabled() {
    clear_global_yaml_cache();

    let temp_dir = tempfile::tempdir().expect("Failed to create temp dir");
    let config_path = temp_dir.path().join("no_cache_save.yaml");

    let mut ops = YamlOperations::new();
    ops.set_cache_enabled(false);

    let mut hash = yaml_rust2::yaml::Hash::new();
    hash.insert(Yaml::String("saved".to_string()), Yaml::Boolean(true));
    let yaml = Yaml::Hash(hash);

    ops.save_yaml_file(&config_path, &yaml)
        .expect("Save should succeed");

    // File should exist and be valid
    let content = fs::read_to_string(&config_path).expect("Should read file");
    assert!(content.contains("saved"));
}

// ============================================================================
// load_yaml_file cache edge cases
// ============================================================================

#[test]
#[serial_test::serial]
fn test_load_yaml_file_with_cache_disabled_no_cache_entry() {
    clear_global_yaml_cache();
    reset_yaml_cache_stats();

    let mut temp_file = NamedTempFile::new().expect("Failed to create temp file");
    writeln!(temp_file, "no_cache: true").expect("Write failed");
    let file_path = temp_file.path().to_path_buf();

    let mut ops = YamlOperations::new();
    ops.set_cache_enabled(false);

    let yaml = ops.load_yaml_file(&file_path).expect("Load should succeed");
    assert_eq!(
        ops.get_setting(&yaml, "no_cache"),
        Some(Yaml::Boolean(true))
    );

    let stats = yaml_cache_stats();
    assert_eq!(
        stats.size, 0,
        "Disabled cache reads should not retain entries"
    );
    assert_eq!(stats.hits, 0, "Disabled cache reads should not count hits");
    assert_eq!(stats.misses, 1, "Disabled cache reads should count a miss");
}
