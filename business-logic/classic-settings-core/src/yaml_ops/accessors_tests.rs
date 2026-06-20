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
fn test_set_setting_rejects_empty_key_path_segments() {
    let ops = YamlOperations::new();
    let yaml = ops.parse_yaml("key: value").expect("Parse should succeed");

    for key_path in [".a", "a..b", "a."] {
        let result = ops.set_setting(&yaml, key_path, Yaml::Boolean(true));
        assert!(
            matches!(result, Err(YamlError::InvalidKeyPath(_))),
            "expected InvalidKeyPath for {key_path:?}, got {result:?}"
        );
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
