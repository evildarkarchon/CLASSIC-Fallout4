use super::*;
use crate::YamlOperations;

#[test]
fn test_merge_keys_single_mapping() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
defaults: &defaults
  adapter: postgres
  host: localhost

development:
  <<: *defaults
  database: dev_db
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");
    let merged = merge_keys(yaml).expect("Merge should succeed");

    // Merged values should be accessible
    assert_eq!(
        ops.get_string_value(&merged, "development.adapter", ""),
        "postgres"
    );
    assert_eq!(
        ops.get_string_value(&merged, "development.host", ""),
        "localhost"
    );
    assert_eq!(
        ops.get_string_value(&merged, "development.database", ""),
        "dev_db"
    );
}

#[test]
fn test_merge_keys_override() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
defaults: &defaults
  adapter: postgres
  host: localhost

production:
  <<: *defaults
  host: prod.example.com
  database: prod_db
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");
    let merged = merge_keys(yaml).expect("Merge should succeed");

    // Local values should override merged values
    assert_eq!(
        ops.get_string_value(&merged, "production.adapter", ""),
        "postgres"
    );
    assert_eq!(
        ops.get_string_value(&merged, "production.host", ""),
        "prod.example.com"
    );
    assert_eq!(
        ops.get_string_value(&merged, "production.database", ""),
        "prod_db"
    );
}

#[test]
fn test_merge_keys_multiple_mappings() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
center: &center
  x: 1
  y: 2

big: &big
  r: 10

combined:
  <<: [*center, *big]
  label: center/big
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");
    let merged = merge_keys(yaml).expect("Merge should succeed");

    // All merged values should be accessible
    assert_eq!(
        ops.get_setting(&merged, "combined.x"),
        Some(Yaml::Integer(1))
    );
    assert_eq!(
        ops.get_setting(&merged, "combined.y"),
        Some(Yaml::Integer(2))
    );
    assert_eq!(
        ops.get_setting(&merged, "combined.r"),
        Some(Yaml::Integer(10))
    );
    assert_eq!(
        ops.get_string_value(&merged, "combined.label", ""),
        "center/big"
    );
}

#[test]
fn test_merge_keys_nested() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
base: &base
  nested:
    value: from_base

derived:
  <<: *base
  extra: added
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");
    let merged = merge_keys(yaml).expect("Merge should succeed");

    // Nested values should be merged
    assert_eq!(
        ops.get_string_value(&merged, "derived.nested.value", ""),
        "from_base"
    );
    assert_eq!(ops.get_string_value(&merged, "derived.extra", ""), "added");
}

#[test]
fn test_merge_keys_recursive() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
level1: &l1
  a: 1

level2: &l2
  <<: *l1
  b: 2

level3:
  <<: *l2
  c: 3
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");
    let merged = merge_keys(yaml).expect("Merge should succeed");

    // All levels should be merged
    assert_eq!(ops.get_setting(&merged, "level3.a"), Some(Yaml::Integer(1)));
    assert_eq!(ops.get_setting(&merged, "level3.b"), Some(Yaml::Integer(2)));
    assert_eq!(ops.get_setting(&merged, "level3.c"), Some(Yaml::Integer(3)));
}

#[test]
fn test_merge_keys_invalid_value() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
invalid:
  <<: "not_a_mapping"
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");
    let result = merge_keys(yaml);

    assert!(result.is_err());
    match result {
        Err(YamlError::InvalidValue(msg)) => {
            assert!(msg.contains("mapping"));
        }
        _ => panic!("Expected InvalidValue error"),
    }
}

#[test]
fn test_merge_keys_no_merge() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
simple:
  key: value
  number: 42
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");
    let original_clone = yaml.clone();
    let merged = merge_keys(yaml).expect("Merge should succeed");

    // Without merge keys, the result should be equivalent
    assert_eq!(merged, original_clone);
}

#[test]
fn test_merge_keys_in_array() {
    let ops = YamlOperations::new();
    let yaml_str = r#"
base: &base
  type: base

items:
  - <<: *base
    name: item1
  - <<: *base
    name: item2
"#;
    let yaml = ops.parse_yaml(yaml_str).expect("Parse should succeed");
    let merged = merge_keys(yaml).expect("Merge should succeed");

    // Check that array items have merged values
    if let Some(Yaml::Array(items)) = ops.get_setting(&merged, "items") {
        assert_eq!(items.len(), 2);

        // First item
        if let Yaml::Hash(item) = &items[0] {
            let type_key = Yaml::String("type".to_string());
            let name_key = Yaml::String("name".to_string());
            assert_eq!(item.get(&type_key), Some(&Yaml::String("base".to_string())));
            assert_eq!(
                item.get(&name_key),
                Some(&Yaml::String("item1".to_string()))
            );
        } else {
            panic!("Expected first item to be a hash");
        }

        // Second item
        if let Yaml::Hash(item) = &items[1] {
            let type_key = Yaml::String("type".to_string());
            let name_key = Yaml::String("name".to_string());
            assert_eq!(item.get(&type_key), Some(&Yaml::String("base".to_string())));
            assert_eq!(
                item.get(&name_key),
                Some(&Yaml::String("item2".to_string()))
            );
        } else {
            panic!("Expected second item to be a hash");
        }
    } else {
        panic!("Expected items to be an array");
    }
}
