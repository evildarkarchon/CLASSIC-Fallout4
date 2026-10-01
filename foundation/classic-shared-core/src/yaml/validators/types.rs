//! Validator value and type definitions.

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

#[cfg(test)]
#[path = "types_tests.rs"]
mod tests;
