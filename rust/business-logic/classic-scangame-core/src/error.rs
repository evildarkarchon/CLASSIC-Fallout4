//! Error types for ScanGame operations

use thiserror::Error;

/// Errors that can occur during game scanning and validation operations
#[derive(Debug, Error)]
pub enum ScanGameError {
    /// I/O error occurred during file operations
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    /// Configuration validation error
    #[error("Configuration error: {0}")]
    Config(String),

    /// Archive processing error
    #[error("Archive error: {0}")]
    Archive(String),

    /// DDS texture validation error
    #[error("DDS validation error: {0}")]
    Dds(String),

    /// INI file validation error
    #[error("INI validation error: {0}")]
    Ini(String),

    /// TOML validation error
    #[error("TOML validation error: {0}")]
    Toml(String),

    /// XSE plugin validation error
    #[error("XSE plugin error: {0}")]
    Xse(String),

    /// Log processing error
    #[error("Log processing error: {0}")]
    LogProcessing(String),

    /// Unsupported operation
    #[error("Unsupported operation: {0}")]
    Unsupported(String),

    /// Generic error
    #[error("{0}")]
    Other(String),
}

/// Result type for ScanGame operations
pub type Result<T> = std::result::Result<T, ScanGameError>;
