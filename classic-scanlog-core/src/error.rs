//! Error types for scan log operations

use thiserror::Error;

/// Errors that can occur during scan log operations
#[derive(Error, Debug)]
pub enum ScanLogError {
    #[error("Parse error: {0}")]
    ParseError(String),

    #[error("Invalid FormID: {0}")]
    InvalidFormID(String),

    #[error("Database error: {0}")]
    DatabaseError(String),

    #[error("File I/O error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("File I/O error: {0}")]
    FileIOError(#[from] classic_file_io_core::error::FileIOError),

    #[error("Regex error: {0}")]
    RegexError(#[from] regex::Error),

    #[error("Configuration error: {0}")]
    ConfigError(String),

    #[error("Analysis error: {0}")]
    AnalysisError(String),

    #[error("Invalid input: {0}")]
    InvalidInput(String),

    #[error("Pattern matching error: {0}")]
    PatternError(String),

    #[error("Report generation error: {0}")]
    ReportError(String),

    #[error("GPU detection error: {0}")]
    GpuError(String),

    #[error("Settings validation error: {0}")]
    ValidationError(String),

    #[error("Internal error: {0}")]
    Internal(String),
}

/// Result type for scan log operations
pub type Result<T> = std::result::Result<T, ScanLogError>;
