use super::*;
use yaml_rust2::YamlLoader;

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

// ========================================================================
// Setting Value Validation Tests
// ========================================================================

#[test]
fn test_validate_int() {
    assert!(validate_setting_value("42", SettingType::Int));
    assert!(validate_setting_value("-10", SettingType::Int));
    assert!(validate_setting_value("0", SettingType::Int));
    assert!(!validate_setting_value("abc", SettingType::Int));
    assert!(!validate_setting_value("3.125", SettingType::Int));
    assert!(!validate_setting_value("", SettingType::Int));
}

#[test]
fn test_validate_bool() {
    assert!(validate_setting_value("true", SettingType::Bool));
    assert!(validate_setting_value("false", SettingType::Bool));
    assert!(validate_setting_value("True", SettingType::Bool));
    assert!(validate_setting_value("FALSE", SettingType::Bool));
    assert!(validate_setting_value("yes", SettingType::Bool));
    assert!(validate_setting_value("no", SettingType::Bool));
    assert!(validate_setting_value("1", SettingType::Bool));
    assert!(validate_setting_value("0", SettingType::Bool));
    assert!(validate_setting_value("on", SettingType::Bool));
    assert!(validate_setting_value("off", SettingType::Bool));
    assert!(!validate_setting_value("maybe", SettingType::Bool));
    assert!(!validate_setting_value("", SettingType::Bool));
}

#[test]
fn test_validate_float() {
    assert!(validate_setting_value("3.125", SettingType::Float));
    assert!(validate_setting_value("-1.5", SettingType::Float));
    assert!(validate_setting_value("42", SettingType::Float)); // int is valid float
    assert!(validate_setting_value("0.0", SettingType::Float));
    assert!(!validate_setting_value("abc", SettingType::Float));
    assert!(!validate_setting_value("", SettingType::Float));
}

#[test]
fn test_validate_path() {
    assert!(validate_setting_value(
        "C:\\Games\\Fallout4",
        SettingType::Path
    ));
    assert!(validate_setting_value("/home/user", SettingType::Path));
    assert!(validate_setting_value("relative/path", SettingType::Path));
    assert!(!validate_setting_value("", SettingType::Path));
}

#[test]
fn test_validate_string() {
    assert!(validate_setting_value("anything", SettingType::String));
    assert!(validate_setting_value("", SettingType::String));
    assert!(validate_setting_value("42", SettingType::String));
}

// ========================================================================
// Coercion Tests
// ========================================================================

#[test]
fn test_coerce_int() {
    assert_eq!(
        coerce_setting_value("42", SettingType::Int).unwrap(),
        CoercedValue::Int(42)
    );
    assert_eq!(
        coerce_setting_value("-10", SettingType::Int).unwrap(),
        CoercedValue::Int(-10)
    );
    assert!(coerce_setting_value("abc", SettingType::Int).is_err());
}

#[test]
fn test_coerce_bool() {
    assert_eq!(
        coerce_setting_value("true", SettingType::Bool).unwrap(),
        CoercedValue::Bool(true)
    );
    assert_eq!(
        coerce_setting_value("false", SettingType::Bool).unwrap(),
        CoercedValue::Bool(false)
    );
    assert_eq!(
        coerce_setting_value("YES", SettingType::Bool).unwrap(),
        CoercedValue::Bool(true)
    );
    assert_eq!(
        coerce_setting_value("no", SettingType::Bool).unwrap(),
        CoercedValue::Bool(false)
    );
    assert_eq!(
        coerce_setting_value("1", SettingType::Bool).unwrap(),
        CoercedValue::Bool(true)
    );
    assert_eq!(
        coerce_setting_value("0", SettingType::Bool).unwrap(),
        CoercedValue::Bool(false)
    );
    assert_eq!(
        coerce_setting_value("ON", SettingType::Bool).unwrap(),
        CoercedValue::Bool(true)
    );
    assert_eq!(
        coerce_setting_value("off", SettingType::Bool).unwrap(),
        CoercedValue::Bool(false)
    );
    assert!(coerce_setting_value("maybe", SettingType::Bool).is_err());
}

#[test]
fn test_coerce_float() {
    let result = coerce_setting_value("3.125", SettingType::Float).unwrap();
    assert_eq!(result.as_f64().unwrap(), 3.125);

    let result = coerce_setting_value("42", SettingType::Float).unwrap();
    assert_eq!(result.as_f64().unwrap(), 42.0);

    assert!(coerce_setting_value("abc", SettingType::Float).is_err());
}

#[test]
fn test_coerce_path() {
    assert_eq!(
        coerce_setting_value("C:\\Games", SettingType::Path).unwrap(),
        CoercedValue::Path("C:\\Games".to_string())
    );
    assert!(coerce_setting_value("", SettingType::Path).is_err());
}

#[test]
fn test_coerce_string() {
    assert_eq!(
        coerce_setting_value("hello", SettingType::String).unwrap(),
        CoercedValue::String("hello".to_string())
    );
    assert_eq!(
        coerce_setting_value("", SettingType::String).unwrap(),
        CoercedValue::String(String::new())
    );
}

// ========================================================================
// CoercedValue Accessor Tests
// ========================================================================

#[test]
fn test_coerced_value_accessors() {
    assert_eq!(CoercedValue::Int(42).as_i64(), Some(42));
    assert_eq!(CoercedValue::Int(42).as_bool(), None);
    assert_eq!(CoercedValue::Bool(true).as_bool(), Some(true));
    assert_eq!(CoercedValue::Bool(true).as_i64(), None);
    assert_eq!(CoercedValue::Float(3.125).as_f64(), Some(3.125));
    assert_eq!(CoercedValue::Float(3.125).as_str(), None);
    assert_eq!(CoercedValue::String("hi".into()).as_str(), Some("hi"));
    assert_eq!(CoercedValue::Path("/tmp".into()).as_str(), Some("/tmp"));
}

// ========================================================================
// Helper Function Tests
// ========================================================================

#[test]
fn test_parse_bool_values() {
    assert_eq!(parse_bool("true"), Some(true));
    assert_eq!(parse_bool("TRUE"), Some(true));
    assert_eq!(parse_bool("True"), Some(true));
    assert_eq!(parse_bool("false"), Some(false));
    assert_eq!(parse_bool("yes"), Some(true));
    assert_eq!(parse_bool("no"), Some(false));
    assert_eq!(parse_bool("1"), Some(true));
    assert_eq!(parse_bool("0"), Some(false));
    assert_eq!(parse_bool("on"), Some(true));
    assert_eq!(parse_bool("off"), Some(false));
    assert_eq!(parse_bool("invalid"), None);
    assert_eq!(parse_bool(""), None);
}

#[test]
fn test_yaml_type_name() {
    assert_eq!(yaml_type_name(&Yaml::Integer(1)), "integer");
    assert_eq!(yaml_type_name(&Yaml::String("s".into())), "string");
    assert_eq!(yaml_type_name(&Yaml::Boolean(true)), "boolean");
    assert_eq!(yaml_type_name(&Yaml::Null), "null");
}
