//! Error types for settings cache operations.

use std::io;
use std::path::PathBuf;
use thiserror::Error;

/// Error type for settings cache operations.
#[derive(Debug, Error)]
pub enum SettingsError {
    /// File I/O error
    #[error("Failed to read file {path}: {source}")]
    IoError {
        /// The path that failed
        path: PathBuf,
        /// The underlying I/O error
        source: io::Error,
    },

    /// YAML parsing error
    #[error("Failed to parse YAML from {path}: {message}")]
    YamlParseError {
        /// The path that failed to parse
        path: PathBuf,
        /// Error message
        message: String,
    },

    /// Cache key not found
    #[error("Cache key not found: {0}")]
    KeyNotFound(String),

    /// Invalid YAML structure
    #[error("Invalid YAML structure in {path}: expected {expected}, found {found}")]
    InvalidYamlStructure {
        /// The path with invalid structure
        path: PathBuf,
        /// What was expected
        expected: String,
        /// What was found
        found: String,
    },
}

/// Result type for settings cache operations.
pub type Result<T> = std::result::Result<T, SettingsError>;
