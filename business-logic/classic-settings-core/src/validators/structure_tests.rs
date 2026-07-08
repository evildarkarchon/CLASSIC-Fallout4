use super::*;
use yaml_rust2::{Yaml, YamlLoader};

// ========================================================================
// Structure Validation Tests
// ========================================================================

#[test]
fn test_validate_valid_settings() {
    let docs = YamlLoader::load_from_str("CLASSIC_Settings:\n  VR Mode: false\n").unwrap();
    let issues = validate_settings_structure(&docs[0]);
    assert!(
        issues.is_empty(),
        "Valid settings should have no issues: {:?}",
        issues
    );
}

#[test]
fn test_validate_missing_root_key() {
    let docs = YamlLoader::load_from_str("other_key: value\n").unwrap();
    let issues = validate_settings_structure(&docs[0]);
    assert_eq!(issues.len(), 1);
    assert_eq!(issues[0].severity, IssueSeverity::Warning);
    assert!(issues[0].message.contains("CLASSIC_Settings"));
}

#[test]
fn test_validate_empty_mapping() {
    let docs = YamlLoader::load_from_str("{}").unwrap();
    let issues = validate_settings_structure(&docs[0]);
    // Should have both empty warning and missing root key warning
    assert!(!issues.is_empty());
    assert!(issues.iter().any(|i| i.message.contains("empty")));
    assert!(issues.iter().any(|i| {
        i.severity == IssueSeverity::Warning && i.message.contains("CLASSIC_Settings")
    }));
}

#[test]
fn test_validate_non_mapping_root() {
    let docs = YamlLoader::load_from_str("42").unwrap();
    let issues = validate_settings_structure(&docs[0]);
    assert_eq!(issues.len(), 1);
    assert_eq!(issues[0].severity, IssueSeverity::Error);
    assert!(issues[0].message.contains("mapping"));
}

#[test]
fn test_validate_null_document() {
    let issues = validate_settings_structure(&Yaml::Null);
    assert_eq!(issues.len(), 1);
    assert_eq!(issues[0].severity, IssueSeverity::Error);
}

#[test]
fn test_validate_bad_value() {
    let issues = validate_settings_structure(&Yaml::BadValue);
    assert_eq!(issues.len(), 1);
    assert_eq!(issues[0].severity, IssueSeverity::Error);
}

#[test]
fn test_validate_array_root() {
    let docs = YamlLoader::load_from_str("- item1\n- item2\n").unwrap();
    let issues = validate_settings_structure(&docs[0]);
    assert_eq!(issues.len(), 1);
    assert_eq!(issues[0].severity, IssueSeverity::Error);
    assert!(issues[0].message.contains("array"));
}

#[test]
fn test_yaml_type_name() {
    assert_eq!(yaml_type_name(&Yaml::Integer(1)), "integer");
    assert_eq!(yaml_type_name(&Yaml::String("s".into())), "string");
    assert_eq!(yaml_type_name(&Yaml::Boolean(true)), "boolean");
    assert_eq!(yaml_type_name(&Yaml::Null), "null");
}
