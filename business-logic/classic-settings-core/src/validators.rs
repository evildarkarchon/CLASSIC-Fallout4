//! YAML setting validators and type coercion.
//!
//! This module provides validation and coercion utilities for YAML settings values.
//! It mirrors the behavior of Python's `ClassicLib.io.yaml.validators` module.
//!
//! # Overview
//!
//! - **Structure validation**: Check that a YAML document has the expected top-level shape
//! - **Value validation**: Check if a value matches an expected setting type
//! - **Value coercion**: Convert string values to their target types (int, bool, float, path)
//!
//! # Examples
//!
//! ```rust
//! use classic_settings_core::validators::{SettingType, validate_setting_value, coerce_setting_value};
//!
//! // Validate that "42" can be interpreted as an Int
//! assert!(validate_setting_value("42", SettingType::Int));
//!
//! // Coerce "42" to an Int
//! let coerced = coerce_setting_value("42", SettingType::Int).unwrap();
//! assert_eq!(coerced.as_i64(), Some(42));
//! ```

use yaml_rust2::Yaml;

/// The expected type of a YAML setting value.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SettingType {
    /// Integer value (e.g., `42`, `"42"`)
    Int,
    /// Boolean value (e.g., `true`, `"true"`, `"yes"`, `"1"`)
    Bool,
    /// Floating-point value (e.g., `3.125`, `"3.125"`)
    Float,
    /// Filesystem path (any non-empty string)
    Path,
    /// Arbitrary string
    String,
}

/// A coerced value from a YAML setting.
///
/// Represents the result of successfully coercing a string value to a target type.
#[derive(Debug, Clone, PartialEq)]
pub enum CoercedValue {
    /// Integer value.
    Int(i64),
    /// Boolean value.
    Bool(bool),
    /// Floating-point value.
    Float(f64),
    /// Filesystem path as a string.
    Path(String),
    /// Arbitrary string.
    String(String),
}

impl CoercedValue {
    /// Get the value as an `i64`, if it is an Int.
    #[must_use]
    pub fn as_i64(&self) -> Option<i64> {
        match self {
            CoercedValue::Int(v) => Some(*v),
            _ => None,
        }
    }

    /// Get the value as a `bool`, if it is a Bool.
    #[must_use]
    pub fn as_bool(&self) -> Option<bool> {
        match self {
            CoercedValue::Bool(v) => Some(*v),
            _ => None,
        }
    }

    /// Get the value as an `f64`, if it is a Float.
    #[must_use]
    pub fn as_f64(&self) -> Option<f64> {
        match self {
            CoercedValue::Float(v) => Some(*v),
            _ => None,
        }
    }

    /// Get the value as a `&str`, if it is a String or Path.
    #[must_use]
    pub fn as_str(&self) -> Option<&str> {
        match self {
            CoercedValue::String(v) | CoercedValue::Path(v) => Some(v),
            _ => None,
        }
    }
}

/// An issue found during settings structure validation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ValidationIssue {
    /// The severity of the issue.
    pub severity: IssueSeverity,
    /// A human-readable description of the issue.
    pub message: String,
}

/// Severity level for validation issues.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IssueSeverity {
    /// The issue is informational (e.g., empty data).
    Warning,
    /// The issue is a structural error.
    Error,
}

/// Validate the structure of a YAML settings document.
///
/// Checks for common structural issues:
/// - Document is not a Hash/mapping (expected top-level structure)
/// - Settings file is missing the `CLASSIC_Settings` root key
/// - Document is empty
///
/// # Arguments
///
/// * `yaml` - The parsed YAML document to validate
///
/// # Returns
///
/// A vector of `ValidationIssue`s found. An empty vector means the document is valid.
///
/// # Examples
///
/// ```rust
/// use yaml_rust2::YamlLoader;
/// use classic_settings_core::validators::{validate_settings_structure, IssueSeverity};
///
/// let docs = YamlLoader::load_from_str("CLASSIC_Settings:\n  VR Mode: false\n").unwrap();
/// let issues = validate_settings_structure(&docs[0]);
/// assert!(issues.is_empty());
///
/// let bad_docs = YamlLoader::load_from_str("42").unwrap();
/// let issues = validate_settings_structure(&bad_docs[0]);
/// assert!(issues.iter().any(|i| i.severity == IssueSeverity::Error));
/// ```
#[must_use]
pub fn validate_settings_structure(yaml: &Yaml) -> Vec<ValidationIssue> {
    let mut issues = Vec::new();

    match yaml {
        Yaml::Hash(map) => {
            if map.is_empty() {
                issues.push(ValidationIssue {
                    severity: IssueSeverity::Warning,
                    message: "Settings document is empty".to_string(),
                });
            }

            // Check for CLASSIC_Settings root key (expected in Settings files)
            let settings_key = Yaml::String("CLASSIC_Settings".to_string());
            if !map.contains_key(&settings_key) {
                issues.push(ValidationIssue {
                    severity: IssueSeverity::Warning,
                    message: "Settings document missing 'CLASSIC_Settings' root key".to_string(),
                });
            }
        }
        Yaml::BadValue | Yaml::Null => {
            issues.push(ValidationIssue {
                severity: IssueSeverity::Error,
                message: "Settings document is null or invalid".to_string(),
            });
        }
        _ => {
            issues.push(ValidationIssue {
                severity: IssueSeverity::Error,
                message: format!(
                    "Expected a YAML mapping at root, found: {}",
                    yaml_type_name(yaml)
                ),
            });
        }
    }

    issues
}

/// Validate that a string value can be interpreted as the expected setting type.
///
/// Checks if the value is directly compatible or can be coerced to the expected type.
///
/// # Arguments
///
/// * `value` - The string value to validate
/// * `expected_type` - The expected setting type
///
/// # Returns
///
/// `true` if the value matches or can be coerced to the expected type.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::validators::{SettingType, validate_setting_value};
///
/// assert!(validate_setting_value("42", SettingType::Int));
/// assert!(validate_setting_value("true", SettingType::Bool));
/// assert!(validate_setting_value("3.125", SettingType::Float));
/// assert!(validate_setting_value("any string", SettingType::String));
/// assert!(validate_setting_value("C:\\Games", SettingType::Path));
/// assert!(!validate_setting_value("hello", SettingType::Int));
/// assert!(!validate_setting_value("", SettingType::Path));
/// ```
#[must_use]
pub fn validate_setting_value(value: &str, expected_type: SettingType) -> bool {
    match expected_type {
        SettingType::Int => value.parse::<i64>().is_ok(),
        SettingType::Bool => parse_bool(value).is_some(),
        SettingType::Float => value.parse::<f64>().is_ok(),
        SettingType::Path => !value.is_empty(),
        SettingType::String => true,
    }
}

/// Coerce a string value to the target setting type.
///
/// Attempts to convert the value to the expected type. Supports:
/// - `Int`: Parses as `i64`
/// - `Bool`: Accepts `true/false`, `yes/no`, `1/0`, `on/off` (case-insensitive)
/// - `Float`: Parses as `f64`
/// - `Path`: Any non-empty string
/// - `String`: Always succeeds (identity conversion)
///
/// # Arguments
///
/// * `value` - The string value to coerce
/// * `target_type` - The target setting type
///
/// # Returns
///
/// `Ok(CoercedValue)` if coercion succeeded, or `Err` with a description if not.
///
/// # Examples
///
/// ```rust
/// use classic_settings_core::validators::{SettingType, CoercedValue, coerce_setting_value};
///
/// let result = coerce_setting_value("42", SettingType::Int).unwrap();
/// assert_eq!(result, CoercedValue::Int(42));
///
/// let result = coerce_setting_value("yes", SettingType::Bool).unwrap();
/// assert_eq!(result, CoercedValue::Bool(true));
///
/// let result = coerce_setting_value("3.125", SettingType::Float).unwrap();
/// assert_eq!(result.as_f64().unwrap(), 3.125);
/// ```
pub fn coerce_setting_value(value: &str, target_type: SettingType) -> Result<CoercedValue, String> {
    match target_type {
        SettingType::Int => value
            .parse::<i64>()
            .map(CoercedValue::Int)
            .map_err(|e| format!("Cannot coerce '{}' to Int: {}", value, e)),

        SettingType::Bool => parse_bool(value)
            .map(CoercedValue::Bool)
            .ok_or_else(|| format!("Cannot coerce '{}' to Bool", value)),

        SettingType::Float => value
            .parse::<f64>()
            .map(CoercedValue::Float)
            .map_err(|e| format!("Cannot coerce '{}' to Float: {}", value, e)),

        SettingType::Path => {
            if value.is_empty() {
                Err("Cannot coerce empty string to Path".to_string())
            } else {
                Ok(CoercedValue::Path(value.to_string()))
            }
        }

        SettingType::String => Ok(CoercedValue::String(value.to_string())),
    }
}

/// Parse a boolean from a string, supporting common representations.
///
/// Accepted true values: `true`, `yes`, `1`, `on` (case-insensitive)
/// Accepted false values: `false`, `no`, `0`, `off` (case-insensitive)
fn parse_bool(value: &str) -> Option<bool> {
    match value.to_lowercase().as_str() {
        "true" | "yes" | "1" | "on" => Some(true),
        "false" | "no" | "0" | "off" => Some(false),
        _ => None,
    }
}

/// Get a human-readable name for a YAML value type.
fn yaml_type_name(yaml: &Yaml) -> &'static str {
    match yaml {
        Yaml::Real(_) => "float",
        Yaml::Integer(_) => "integer",
        Yaml::String(_) => "string",
        Yaml::Boolean(_) => "boolean",
        Yaml::Array(_) => "array",
        Yaml::Hash(_) => "mapping",
        Yaml::Alias(_) => "alias",
        Yaml::Null => "null",
        Yaml::BadValue => "bad value",
    }
}

#[cfg(test)]
#[path = "validators_tests.rs"]
mod tests;
