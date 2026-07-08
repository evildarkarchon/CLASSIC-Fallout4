//! YAML setting value validation and coercion.

use super::types::{CoercedValue, SettingType};

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

#[cfg(test)]
#[path = "coerce_tests.rs"]
mod tests;
