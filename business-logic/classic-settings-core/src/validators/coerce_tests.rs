use super::super::types::{CoercedValue, SettingType};
use super::*;

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
