//! YAML operation error types.

use thiserror::Error;

/// An enumeration of errors that can occur while working with YAML data.
///
/// This error type encompasses various error scenarios, including parsing,
/// serialization, I/O issues, and semantic considerations.
/// # Variants
///
/// - `ParseError(String)`
///   An error occurred when parsing a YAML document.
///   This includes the detailed error message as a string.
///
/// - `SerializeError(String)`
///   An error occurred while attempting to serialize data into YAML format.
///   The error message provides additional context as a string.
///
/// - `IoError(std::io::Error)`
///   Represents I/O-related errors encountered during YAML operations,
///   such as reading from or writing to a file. This variant wraps the
///   underlying `std::io::Error`.
///
/// - `EmptyDocument`
///   The YAML document is empty or does not contain any meaningful content.
///
/// - `InvalidValue(String)`
///   Indicates that a value in the YAML document is invalid or not as
///   expected. The string contains details about the invalid value.
///
/// - `UnresolvedAlias`
///   An unresolved YAML alias was encountered. This occurs when a YAML
///   alias references an anchor that was not defined in the document.
///
/// - `InvalidKeyPath(String)`
///   An invalid key path was specified, typically when trying to access
///   a nested value in a YAML document. The string provides the
///   problematic key path or a description of the error.
///
/// - `TypeConversionError(String)`
///   Indicates a type conversion error when trying to serialize or deserialize
///   YAML data into a specific type. The string provides additional details about
///   the conversion failure.
///
/// # Example
/// ```rust
/// use classic_settings_core::YamlError;
///
/// fn handle_yaml() -> Result<(), YamlError> {
///     // Example usage of the YamlError enum.
///     Err(YamlError::ParseError("Unexpected token".to_string()))
/// }
///
/// if let Err(e) = handle_yaml() {
///     println!("Error occurred: {}", e);
/// }
/// ```
///
/// This error type is particularly useful when working with YAML libraries or
/// tools to clearly handle and report different failure scenarios.
#[derive(Debug, Error)]
pub enum YamlError {
    /// Failed to parse YAML document
    #[error("Failed to parse YAML: {0}")]
    ParseError(String),

    /// Failed to serialize YAML to string
    #[error("Failed to serialize YAML: {0}")]
    SerializeError(String),

    /// I/O error during file operations
    #[error("I/O error: {0}")]
    IoError(#[from] std::io::Error),

    /// YAML document is empty
    #[error("Empty YAML document")]
    EmptyDocument,

    /// Invalid value encountered
    #[error("Invalid value: {0}")]
    InvalidValue(String),

    /// Unresolved YAML alias reference
    #[error("Unresolved YAML alias")]
    UnresolvedAlias,

    /// Invalid key path for nested access
    #[error("Invalid key path: {0}")]
    InvalidKeyPath(String),

    /// Type conversion failed
    #[error("Type conversion error: {0}")]
    TypeConversionError(String),
}

#[cfg(test)]
#[path = "error_tests.rs"]
mod tests;
