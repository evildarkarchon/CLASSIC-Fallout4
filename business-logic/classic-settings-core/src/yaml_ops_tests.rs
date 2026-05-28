use super::*;
use std::fs;
use std::io::Write;
use std::sync::Arc;
use std::thread;
use std::time::Duration;
use tempfile::{tempdir, NamedTempFile};

// ============================================================================
// Basic Parse/Dump Tests (existing)
// ============================================================================

#[test]
#[serial_test::serial]
fn test_parse_yaml() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
            name: test
            value: 123
        "#;

    let result = ops.parse_yaml(yaml_str);
    assert!(result.is_ok());
}

#[test]
#[serial_test::serial]
fn test_dump_yaml() {
    let ops = YamlOperations::new();
    let mut hash = yaml_rust2::yaml::Hash::new();
    hash.insert(
        Yaml::String("name".to_string()),
        Yaml::String("test".to_string()),
    );
    hash.insert(Yaml::String("value".to_string()), Yaml::Integer(123));

    let yaml = Yaml::Hash(hash);
    let result = ops.dump_yaml(&yaml);
    assert!(result.is_ok());
    let yaml_str = result.unwrap();
    assert!(yaml_str.contains("name"));
    assert!(yaml_str.contains("test"));
}

#[test]
#[serial_test::serial]
fn test_get_setting() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
            settings:
              debug: true
              level: 5
        "#;

    let yaml = ops.parse_yaml(yaml_str).unwrap();
    let value = ops.get_setting(&yaml, "settings.debug");
    assert!(value.is_some());
    assert_eq!(value.unwrap(), Yaml::Boolean(true));
}

#[test]
#[serial_test::serial]
fn test_set_setting() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
            settings:
              debug: false
        "#;

    let yaml = ops.parse_yaml(yaml_str).unwrap();
    let new_yaml = ops
        .set_setting(&yaml, "settings.debug", Yaml::Boolean(true))
        .unwrap();
    let value = ops.get_setting(&new_yaml, "settings.debug");
    assert_eq!(value.unwrap(), Yaml::Boolean(true));
}

#[test]
#[serial_test::serial]
fn test_get_settings_batch() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
            settings:
              debug: true
              level: 5
              name: "test"
        "#;

    let yaml = ops.parse_yaml(yaml_str).unwrap();
    let keys = vec!["settings.debug", "settings.level", "settings.name"];
    let results = ops.get_settings_batch(&yaml, &keys);

    assert_eq!(results.len(), 3);
    assert_eq!(results.get("settings.debug"), Some(&Yaml::Boolean(true)));
    assert_eq!(results.get("settings.level"), Some(&Yaml::Integer(5)));
    assert_eq!(
        results.get("settings.name"),
        Some(&Yaml::String("test".to_string()))
    );
}

#[test]
#[serial_test::serial]
fn test_set_settings_batch() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
            settings:
              debug: false
        "#;

    let yaml = ops.parse_yaml(yaml_str).unwrap();
    let updates = vec![
        ("settings.debug", Yaml::Boolean(true)),
        ("settings.level", Yaml::Integer(10)),
        ("settings.name", Yaml::String("updated".to_string())),
    ];

    let updated = ops.set_settings_batch(&yaml, &updates).unwrap();

    assert_eq!(
        ops.get_setting(&updated, "settings.debug"),
        Some(Yaml::Boolean(true))
    );
    assert_eq!(
        ops.get_setting(&updated, "settings.level"),
        Some(Yaml::Integer(10))
    );
    assert_eq!(
        ops.get_setting(&updated, "settings.name"),
        Some(Yaml::String("updated".to_string()))
    );
}

// ============================================================================
// File I/O Tests
// ============================================================================

#[test]
#[serial_test::serial]
fn test_load_yaml_file_success() {
    // Clear cache before test
    clear_global_yaml_cache();

    let mut temp_file = NamedTempFile::new().expect("Failed to create temp file");
    writeln!(
        temp_file,
        r#"
name: test_config
version: 1.0
settings:
  debug: true
"#
    )
    .expect("Failed to write to temp file");

    let ops = YamlOperations::new();
    let result = ops.load_yaml_file(temp_file.path());

    assert!(result.is_ok());
    let yaml = result.unwrap();
    assert_eq!(
        ops.get_setting(&yaml, "name"),
        Some(Yaml::String("test_config".to_string()))
    );
    assert_eq!(
        ops.get_setting(&yaml, "settings.debug"),
        Some(Yaml::Boolean(true))
    );
}

#[test]
#[serial_test::serial]
fn test_load_yaml_file_not_found() {
    let ops = YamlOperations::new();
    let result = ops.load_yaml_file(Path::new("/nonexistent/path/file.yaml"));

    assert!(result.is_err());
    match result {
        Err(YamlError::IoError(_)) => (),
        _ => panic!("Expected IoError for nonexistent file"),
    }
}

#[test]
#[serial_test::serial]
fn test_save_yaml_file_success() {
    // Clear cache before test
    clear_global_yaml_cache();

    let temp_file = NamedTempFile::new().expect("Failed to create temp file");
    let ops = YamlOperations::new();

    let mut hash = yaml_rust2::yaml::Hash::new();
    hash.insert(
        Yaml::String("key".to_string()),
        Yaml::String("value".to_string()),
    );
    let yaml = Yaml::Hash(hash);

    let result = ops.save_yaml_file(temp_file.path(), &yaml);
    assert!(result.is_ok());

    // Verify file content
    let content = fs::read_to_string(temp_file.path()).expect("Failed to read file");
    assert!(content.contains("key"));
    assert!(content.contains("value"));
}

#[test]
#[serial_test::serial]
fn test_save_yaml_file_atomic_write() {
    // Clear cache before test
    clear_global_yaml_cache();

    let temp_file = NamedTempFile::new().expect("Failed to create temp file");
    let ops = YamlOperations::new();

    let mut hash = yaml_rust2::yaml::Hash::new();
    hash.insert(Yaml::String("atomic".to_string()), Yaml::Boolean(true));
    let yaml = Yaml::Hash(hash);

    ops.save_yaml_file(temp_file.path(), &yaml)
        .expect("Save should succeed");

    // Verify the temp file doesn't exist (atomic rename should have removed it)
    let temp_path = temp_file.path().with_extension("yaml.tmp");
    assert!(
        !temp_path.exists(),
        "Temporary file should be cleaned up after atomic write"
    );
}

#[test]
#[serial_test::serial]
fn test_load_save_roundtrip() {
    // Clear cache before test
    clear_global_yaml_cache();

    let temp_file = NamedTempFile::new().expect("Failed to create temp file");
    let ops = YamlOperations::new();

    // Create original YAML
    let yaml_str = r#"
name: roundtrip_test
count: 42
nested:
  value: hello
"#;
    let original = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    // Save to file
    ops.save_yaml_file(temp_file.path(), &original)
        .expect("Save should succeed");

    // Clear cache to force re-read
    clear_global_yaml_cache();

    // Load from file
    let loaded = ops
        .load_yaml_file(temp_file.path())
        .expect("Load should succeed");

    // Verify contents
    assert_eq!(
        ops.get_setting(&loaded, "name"),
        Some(Yaml::String("roundtrip_test".to_string()))
    );
    assert_eq!(ops.get_setting(&loaded, "count"), Some(Yaml::Integer(42)));
    assert_eq!(
        ops.get_setting(&loaded, "nested.value"),
        Some(Yaml::String("hello".to_string()))
    );
}

#[test]
#[serial_test::serial]
fn test_load_yaml_files_batch() {
    // Clear cache before test
    clear_global_yaml_cache();

    let mut temp1 = NamedTempFile::new().expect("Failed to create temp file");
    let mut temp2 = NamedTempFile::new().expect("Failed to create temp file");

    writeln!(temp1, "file1: true").expect("Write failed");
    writeln!(temp2, "file2: true").expect("Write failed");

    let ops = YamlOperations::new();
    let paths = vec![temp1.path(), temp2.path()];
    let results = ops.load_yaml_files_batch(&paths);

    assert_eq!(results.len(), 2);
}

#[test]
#[serial_test::serial]
fn test_load_yaml_files_batch_with_missing() {
    // Clear cache before test
    clear_global_yaml_cache();

    let mut temp = NamedTempFile::new().expect("Failed to create temp file");
    writeln!(temp, "exists: true").expect("Write failed");

    let ops = YamlOperations::new();
    let missing_path = Path::new("/nonexistent/file.yaml");
    let paths = vec![temp.path(), missing_path];
    let results = ops.load_yaml_files_batch(&paths);

    // Only the existing file should be in results
    assert_eq!(results.len(), 1);
    assert!(results.contains_key(&temp.path().to_string_lossy().to_string()));
}

// ============================================================================
// Cache Tests
// ============================================================================

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
fn test_get_string_value_nested() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
game:
  info:
    name: Fallout4
    version: "1.10.163"
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let name = ops.get_string_value(&yaml, "game.info.name", "Unknown");
    assert_eq!(name, "Fallout4");

    let version = ops.get_string_value(&yaml, "game.info.version", "0.0.0");
    assert_eq!(version, "1.10.163");
}

#[test]
#[serial_test::serial]
fn test_get_string_value_default() {
    let ops = YamlOperations::new();
    let yaml_str = "exists: true";
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let missing = ops.get_string_value(&yaml, "nonexistent.path", "default_value");
    assert_eq!(missing, "default_value");
}

#[test]
#[serial_test::serial]
fn test_get_string_value_non_string() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
values:
  number: 42
  boolean: true
  null_value: ~
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    // Non-string values should return default
    let number = ops.get_string_value(&yaml, "values.number", "default");
    assert_eq!(number, "default");

    let boolean = ops.get_string_value(&yaml, "values.boolean", "default");
    assert_eq!(boolean, "default");

    let null_val = ops.get_string_value(&yaml, "values.null_value", "default");
    assert_eq!(null_val, "default");
}

#[test]
#[serial_test::serial]
fn test_get_string_value_top_level() {
    let ops = YamlOperations::new();
    let yaml_str = "simple: value";
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let value = ops.get_string_value(&yaml, "simple", "default");
    assert_eq!(value, "value");
}

#[test]
#[serial_test::serial]
fn test_get_vec_value_returns_strings() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
game:
  plugins:
    - plugin1.esp
    - plugin2.esp
    - plugin3.esp
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let plugins = ops.get_vec_value(&yaml, "game.plugins");
    assert_eq!(plugins.len(), 3);
    assert_eq!(plugins[0], "plugin1.esp");
    assert_eq!(plugins[1], "plugin2.esp");
    assert_eq!(plugins[2], "plugin3.esp");
}

#[test]
#[serial_test::serial]
fn test_get_vec_value_empty() {
    let ops = YamlOperations::new();
    let yaml_str = "empty_array: []";
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_vec_value(&yaml, "empty_array");
    assert!(result.is_empty());
}

#[test]
#[serial_test::serial]
fn test_get_vec_value_missing_key() {
    let ops = YamlOperations::new();
    let yaml_str = "exists: true";
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_vec_value(&yaml, "nonexistent");
    assert!(result.is_empty());
}

#[test]
#[serial_test::serial]
fn test_get_vec_value_filters_non_strings() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
mixed:
  - string_value
  - 42
  - true
  - another_string
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_vec_value(&yaml, "mixed");
    // Only string values should be returned
    assert_eq!(result.len(), 2);
    assert!(result.contains(&"string_value".to_string()));
    assert!(result.contains(&"another_string".to_string()));
}

#[test]
#[serial_test::serial]
fn test_get_vec_value_not_array() {
    let ops = YamlOperations::new();
    let yaml_str = "not_array: just_a_string";
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_vec_value(&yaml, "not_array");
    assert!(result.is_empty());
}

#[test]
#[serial_test::serial]
fn test_get_hashmap_value_returns_map() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
game:
  mods:
    mod1: "Description 1"
    mod2: "Description 2"
    mod3: "Description 3"
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let mods = ops.get_hashmap_value(&yaml, "game.mods");
    assert_eq!(mods.len(), 3);
    assert_eq!(mods.get("mod1"), Some(&"Description 1".to_string()));
    assert_eq!(mods.get("mod2"), Some(&"Description 2".to_string()));
    assert_eq!(mods.get("mod3"), Some(&"Description 3".to_string()));
}

#[test]
#[serial_test::serial]
fn test_get_hashmap_value_empty() {
    let ops = YamlOperations::new();
    let yaml_str = "empty_map: {}";
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_hashmap_value(&yaml, "empty_map");
    assert!(result.is_empty());
}

#[test]
#[serial_test::serial]
fn test_get_hashmap_value_missing_key() {
    let ops = YamlOperations::new();
    let yaml_str = "exists: true";
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_hashmap_value(&yaml, "nonexistent");
    assert!(result.is_empty());
}

#[test]
#[serial_test::serial]
fn test_get_hashmap_value_filters_non_strings() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
mixed_map:
  string_key: "string_value"
  number_key: 42
  bool_key: true
  another_string: "another_value"
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_hashmap_value(&yaml, "mixed_map");
    // Only string-to-string entries should be returned
    assert_eq!(result.len(), 2);
    assert_eq!(result.get("string_key"), Some(&"string_value".to_string()));
    assert_eq!(
        result.get("another_string"),
        Some(&"another_value".to_string())
    );
}

#[test]
#[serial_test::serial]
fn test_get_hashmap_value_not_map() {
    let ops = YamlOperations::new();
    let yaml_str = "not_map: just_a_string";
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_hashmap_value(&yaml, "not_map");
    assert!(result.is_empty());
}

// ============================================================================
// Thread Safety Tests
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
fn test_concurrent_parse_operations() {
    let ops = Arc::new(YamlOperations::new());
    let yaml_content = Arc::new("key: value\nnumber: 123".to_string());

    let handles: Vec<_> = (0..4)
        .map(|_| {
            let ops_clone = ops.clone();
            let content_clone = yaml_content.clone();
            thread::spawn(move || {
                for _ in 0..100 {
                    let result = ops_clone.parse_yaml(&content_clone);
                    assert!(result.is_ok());
                }
            })
        })
        .collect();

    for handle in handles {
        handle.join().expect("Thread panicked");
    }
}

// ============================================================================
// Error Handling Tests
// ============================================================================

#[test]
#[serial_test::serial]
fn test_parse_empty_content() {
    let ops = YamlOperations::new();
    let result = ops.parse_yaml("");

    assert!(result.is_err());
    match result {
        Err(YamlError::EmptyDocument) => (),
        _ => panic!("Expected EmptyDocument error"),
    }
}

#[test]
#[serial_test::serial]
fn test_parse_invalid_yaml() {
    let ops = YamlOperations::new();
    // Invalid YAML with tab character in wrong place
    let invalid = "key:\n\t- bad indent";
    let result = ops.parse_yaml(invalid);

    assert!(result.is_err());
    match result {
        Err(YamlError::ParseError(_)) => (),
        _ => panic!("Expected ParseError for invalid YAML"),
    }
}

#[test]
#[serial_test::serial]
fn test_set_setting_empty_key_path() {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml("key: value").expect("Parse should succeed");

    let result = ops.set_setting(&yaml, "", Yaml::Boolean(true));
    assert!(result.is_err());
    match result {
        Err(YamlError::InvalidKeyPath(_)) => (),
        _ => panic!("Expected InvalidKeyPath error for empty path"),
    }
}

#[test]
#[serial_test::serial]
fn test_set_setting_whitespace_key_path() {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml("key: value").expect("Parse should succeed");

    let result = ops.set_setting(&yaml, "   ", Yaml::Boolean(true));
    assert!(result.is_err());
    match result {
        Err(YamlError::InvalidKeyPath(_)) => (),
        _ => panic!("Expected InvalidKeyPath error for whitespace path"),
    }
}

#[test]
#[serial_test::serial]
fn test_get_setting_missing_key() {
    let ops = YamlOperations::new();
    let yaml_str = "exists: true";
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_setting(&yaml, "nonexistent");
    assert!(result.is_none());
}

#[test]
#[serial_test::serial]
fn test_get_setting_partial_path() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
outer:
  inner:
    value: test
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    // Path exists but goes through non-hash
    let result = ops.get_setting(&yaml, "outer.inner.value.deeper");
    assert!(result.is_none());
}

#[test]
#[serial_test::serial]
fn test_get_settings_batch_with_missing_keys() {
    let ops = YamlOperations::new();
    let yaml_str = "exists: true";
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let keys = vec!["exists", "missing1", "missing2"];
    let results = ops.get_settings_batch(&yaml, &keys);

    // Only existing key should be in results
    assert_eq!(results.len(), 1);
    assert!(results.contains_key("exists"));
}

// ============================================================================
// Edge Case Tests
// ============================================================================

#[test]
#[serial_test::serial]
fn test_yaml_operations_default_trait() {
    let ops1 = YamlOperations::new();
    let ops2 = YamlOperations::default();

    assert_eq!(ops1.is_cache_enabled(), ops2.is_cache_enabled());
}

#[test]
#[serial_test::serial]
fn test_nested_setting_creation() {
    let ops = YamlOperations::new();
    let yaml = Yaml::Hash(yaml_rust2::yaml::Hash::new());

    // Create deeply nested setting from empty hash
    let updated = ops
        .set_setting(&yaml, "a.b.c.d", Yaml::String("deep".to_string()))
        .expect("Should create nested path");

    let value = ops.get_setting(&updated, "a.b.c.d");
    assert_eq!(value, Some(Yaml::String("deep".to_string())));
}

#[test]
#[serial_test::serial]
fn test_deep_nesting() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
level1:
  level2:
    level3:
      level4:
        level5:
          value: "deep"
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let value = ops.get_setting(&yaml, "level1.level2.level3.level4.level5.value");
    assert_eq!(value, Some(Yaml::String("deep".to_string())));
}

#[test]
#[serial_test::serial]
fn test_parse_multi_document_returns_first() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
first: doc1
---
second: doc2
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    // Should return first document
    let value = ops.get_setting(&yaml, "first");
    assert_eq!(value, Some(Yaml::String("doc1".to_string())));

    // Second document should not be accessible
    let value2 = ops.get_setting(&yaml, "second");
    assert!(value2.is_none());
}

#[test]
#[serial_test::serial]
fn test_yaml_with_special_characters() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
special:
  colon: "value:with:colons"
  quote: "value with 'quotes'"
  unicode: "日本語テスト"
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    assert_eq!(
        ops.get_string_value(&yaml, "special.colon", ""),
        "value:with:colons"
    );
    assert_eq!(
        ops.get_string_value(&yaml, "special.quote", ""),
        "value with 'quotes'"
    );
    assert_eq!(
        ops.get_string_value(&yaml, "special.unicode", ""),
        "日本語テスト"
    );
}

#[test]
#[serial_test::serial]
fn test_yaml_with_anchors_and_aliases() {
    let ops = YamlOperations::new();
    // Test basic anchor/alias functionality
    let yaml_str = r#"
anchor_value: &myanchor "shared_value"
reference: *myanchor
defaults: &defaults
  adapter: postgres
  host: localhost
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    // Basic alias resolution should work
    assert_eq!(
        ops.get_string_value(&yaml, "anchor_value", ""),
        "shared_value"
    );
    assert_eq!(ops.get_string_value(&yaml, "reference", ""), "shared_value");

    // Anchor on a hash should still be accessible
    assert_eq!(
        ops.get_string_value(&yaml, "defaults.adapter", ""),
        "postgres"
    );
    assert_eq!(
        ops.get_string_value(&yaml, "defaults.host", ""),
        "localhost"
    );
}

#[test]
#[serial_test::serial]
fn test_set_setting_overwrites_non_hash() {
    let ops = YamlOperations::new();
    let yaml_str = "simple: string_value";
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    // Setting a nested value should replace the string with a hash
    let updated = ops
        .set_setting(&yaml, "simple.nested", Yaml::Boolean(true))
        .expect("Should succeed");

    let value = ops.get_setting(&updated, "simple.nested");
    assert_eq!(value, Some(Yaml::Boolean(true)));
}

#[test]
#[serial_test::serial]
fn test_yaml_integer_types() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
numbers:
  positive: 42
  negative: -100
  zero: 0
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    assert_eq!(
        ops.get_setting(&yaml, "numbers.positive"),
        Some(Yaml::Integer(42))
    );
    assert_eq!(
        ops.get_setting(&yaml, "numbers.negative"),
        Some(Yaml::Integer(-100))
    );
    assert_eq!(
        ops.get_setting(&yaml, "numbers.zero"),
        Some(Yaml::Integer(0))
    );
}

#[test]
#[serial_test::serial]
fn test_yaml_float_types() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
floats:
  positive: 3.14
  negative: -2.5
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let pos = ops.get_setting(&yaml, "floats.positive");
    assert!(matches!(pos, Some(Yaml::Real(_))));

    let neg = ops.get_setting(&yaml, "floats.negative");
    assert!(matches!(neg, Some(Yaml::Real(_))));
}

#[test]
#[serial_test::serial]
fn test_yaml_null_values() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
nulls:
  explicit: null
  tilde: ~
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    assert_eq!(ops.get_setting(&yaml, "nulls.explicit"), Some(Yaml::Null));
    assert_eq!(ops.get_setting(&yaml, "nulls.tilde"), Some(Yaml::Null));
}

// ============================================================================
// IndexMap Value Tests
// ============================================================================

#[test]
#[serial_test::serial]
fn test_get_indexmap_value_returns_ordered_map() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
game:
  mods:
    alpha_mod: "First mod"
    beta_mod: "Second mod"
    gamma_mod: "Third mod"
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let mods = ops.get_indexmap_value(&yaml, "game.mods");
    assert_eq!(mods.len(), 3);

    // Verify values
    assert_eq!(mods.get("alpha_mod"), Some(&"First mod".to_string()));
    assert_eq!(mods.get("beta_mod"), Some(&"Second mod".to_string()));
    assert_eq!(mods.get("gamma_mod"), Some(&"Third mod".to_string()));

    // Verify order is preserved
    let keys: Vec<&String> = mods.keys().collect();
    assert_eq!(keys[0], "alpha_mod");
    assert_eq!(keys[1], "beta_mod");
    assert_eq!(keys[2], "gamma_mod");
}

#[test]
#[serial_test::serial]
fn test_get_indexmap_value_empty_map() {
    let ops = YamlOperations::new();
    let yaml_str = "empty_map: {}";
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_indexmap_value(&yaml, "empty_map");
    assert!(result.is_empty());
}

#[test]
#[serial_test::serial]
fn test_get_indexmap_value_missing_key() {
    let ops = YamlOperations::new();
    let yaml_str = "exists: true";
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_indexmap_value(&yaml, "nonexistent.path");
    assert!(result.is_empty());
}

#[test]
#[serial_test::serial]
fn test_get_indexmap_value_not_a_map() {
    let ops = YamlOperations::new();
    let yaml_str = "scalar: just_a_string";
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_indexmap_value(&yaml, "scalar");
    assert!(result.is_empty());
}

#[test]
#[serial_test::serial]
fn test_get_indexmap_value_filters_non_string_pairs() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
mixed:
  string_key: "string_value"
  number_key: 42
  bool_key: true
  another_string: "another_value"
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_indexmap_value(&yaml, "mixed");
    // Only string-to-string entries should be returned
    assert_eq!(result.len(), 2);
    assert_eq!(result.get("string_key"), Some(&"string_value".to_string()));
    assert_eq!(
        result.get("another_string"),
        Some(&"another_value".to_string())
    );
}

#[test]
#[serial_test::serial]
fn test_get_indexmap_value_nested_path() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
outer:
  inner:
    key1: val1
    key2: val2
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_indexmap_value(&yaml, "outer.inner");
    assert_eq!(result.len(), 2);
    assert_eq!(result.get("key1"), Some(&"val1".to_string()));
}

#[test]
#[serial_test::serial]
fn test_get_indexmap_value_path_through_non_hash() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
items:
  - list_item
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    // Path goes through an array, not a hash
    let result = ops.get_indexmap_value(&yaml, "items.subkey");
    assert!(result.is_empty());
}

// ============================================================================
// HashMap Vec Value Tests
// ============================================================================

#[test]
#[serial_test::serial]
fn test_get_hashmap_vec_value_with_arrays() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
Crashlog_Stack_Check:
  "6 | BA2 Limit Crash":
    - LooseFileAsyncStream
  "3 | NPC Pathing Crash":
    - NavMesh
    - PathingCell
    - BSPathBuilder
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_hashmap_vec_value(&yaml, "Crashlog_Stack_Check");
    assert_eq!(result.len(), 2);

    let ba2 = result
        .get("6 | BA2 Limit Crash")
        .expect("BA2 entry should exist");
    assert_eq!(ba2, &vec!["LooseFileAsyncStream".to_string()]);

    let npc = result
        .get("3 | NPC Pathing Crash")
        .expect("NPC entry should exist");
    assert_eq!(npc.len(), 3);
    assert!(npc.contains(&"NavMesh".to_string()));
    assert!(npc.contains(&"PathingCell".to_string()));
    assert!(npc.contains(&"BSPathBuilder".to_string()));
}

#[test]
#[serial_test::serial]
fn test_get_hashmap_vec_value_with_single_strings() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
patterns:
  crash1: SinglePattern
  crash2: AnotherPattern
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_hashmap_vec_value(&yaml, "patterns");
    assert_eq!(result.len(), 2);

    // Single string values should be wrapped in vec
    assert_eq!(
        result.get("crash1"),
        Some(&vec!["SinglePattern".to_string()])
    );
    assert_eq!(
        result.get("crash2"),
        Some(&vec!["AnotherPattern".to_string()])
    );
}

#[test]
#[serial_test::serial]
fn test_get_hashmap_vec_value_mixed() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
checks:
  single: OnlyOne
  multi:
    - First
    - Second
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_hashmap_vec_value(&yaml, "checks");
    assert_eq!(result.len(), 2);

    assert_eq!(result.get("single"), Some(&vec!["OnlyOne".to_string()]));
    let multi = result.get("multi").expect("multi should exist");
    assert_eq!(multi, &vec!["First".to_string(), "Second".to_string()]);
}

#[test]
#[serial_test::serial]
fn test_get_hashmap_vec_value_missing_key() {
    let ops = YamlOperations::new();
    let yaml_str = "exists: true";
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_hashmap_vec_value(&yaml, "nonexistent");
    assert!(result.is_empty());
}

#[test]
#[serial_test::serial]
fn test_get_hashmap_vec_value_not_a_map() {
    let ops = YamlOperations::new();
    let yaml_str = "not_map: just_string";
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_hashmap_vec_value(&yaml, "not_map");
    assert!(result.is_empty());
}

#[test]
#[serial_test::serial]
fn test_get_hashmap_vec_value_filters_non_string_arrays() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
data:
  good:
    - string1
    - string2
  bad_value: 42
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_hashmap_vec_value(&yaml, "data");
    // Only string/array entries with string key, bad_value(42) is not a string or array
    assert_eq!(result.len(), 1);
    assert!(result.contains_key("good"));
}

#[test]
#[serial_test::serial]
fn test_get_hashmap_vec_value_nested_path() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
outer:
  inner:
    pattern1:
      - match_a
      - match_b
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let result = ops.get_hashmap_vec_value(&yaml, "outer.inner");
    assert_eq!(result.len(), 1);
    assert_eq!(
        result.get("pattern1"),
        Some(&vec!["match_a".to_string(), "match_b".to_string()])
    );
}

#[test]
#[serial_test::serial]
fn test_get_hashmap_vec_value_path_through_non_hash() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
list:
  - item1
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    // Path goes through array, not hash
    let result = ops.get_hashmap_vec_value(&yaml, "list.subkey");
    assert!(result.is_empty());
}

// ============================================================================
// Module-Level Cache Stats Function Tests
// ============================================================================

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
fn test_set_setting_creates_intermediate_path() {
    let ops = YamlOperations::new();
    let yaml_str = "existing: value";
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    // Create entirely new nested path
    let updated = ops
        .set_setting(
            &yaml,
            "new.deeply.nested.key",
            Yaml::String("created".to_string()),
        )
        .expect("Should succeed");

    assert_eq!(
        ops.get_setting(&updated, "new.deeply.nested.key"),
        Some(Yaml::String("created".to_string()))
    );
    // Existing key should still be present
    assert_eq!(
        ops.get_setting(&updated, "existing"),
        Some(Yaml::String("value".to_string()))
    );
}

#[test]
#[serial_test::serial]
fn test_set_settings_batch_with_empty_key_path_fails() {
    let ops = YamlOperations::new();
    let yaml_str = "key: value";
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    let updates = vec![("", Yaml::Boolean(true))];
    let result = ops.set_settings_batch(&yaml, &updates);
    assert!(result.is_err());
}

// ============================================================================
// get_string_value from non-hash root
// ============================================================================

#[test]
#[serial_test::serial]
fn test_get_string_value_from_array_root() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
- item1
- item2
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    // Root is array, not hash
    let result = ops.get_string_value(&yaml, "key", "default");
    assert_eq!(result, "default");
}

#[test]
#[serial_test::serial]
fn test_get_vec_value_from_non_hash_intermediate() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
outer: "string_not_hash"
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");

    // Path traverses through a string value, not a hash
    let result = ops.get_vec_value(&yaml, "outer.inner");
    assert!(result.is_empty());
}

// ============================================================================
// Dump YAML edge cases
// ============================================================================

#[test]
#[serial_test::serial]
fn test_dump_yaml_with_nested_structure() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
root:
  child:
    grandchild: value
  list:
    - item1
    - item2
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");
    let dumped = ops.dump_yaml(&yaml).expect("Dump should succeed");

    assert!(dumped.contains("root"));
    assert!(dumped.contains("grandchild"));
    assert!(dumped.contains("item1"));
}

#[test]
#[serial_test::serial]
fn test_dump_yaml_scalar() {
    let ops = YamlOperations::new();
    let yaml = Yaml::String("hello world".to_string());
    let dumped = ops.dump_yaml(&yaml).expect("Dump should succeed");
    assert!(dumped.contains("hello world"));
}

// ============================================================================
// save_yaml_file with cache disabled
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
