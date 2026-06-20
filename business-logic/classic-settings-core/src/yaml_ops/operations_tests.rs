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
fn test_yaml_operations_default_trait() {
    let ops1 = YamlOperations::new();
    let ops2 = YamlOperations::default();

    assert_eq!(ops1.is_cache_enabled(), ops2.is_cache_enabled());
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
