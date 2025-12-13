//! Error types for scan log operations

use thiserror::Error;

/// Errors that can occur during scan log operations
#[derive(Error, Debug)]
pub enum ScanLogError {
    /// Error parsing crash log content or structure
    #[error("Parse error: {0}")]
    ParseError(String),

    /// FormID string has invalid format or value
    #[error("Invalid FormID: {0}")]
    InvalidFormID(String),

    /// Error querying or accessing the database
    #[error("Database error: {0}")]
    DatabaseError(String),

    /// Standard I/O error occurred
    #[error("File I/O error: {0}")]
    IoError(#[from] std::io::Error),

    /// File I/O error from classic-file-io-core
    #[error("File I/O error: {0}")]
    FileIOError(#[from] classic_file_io_core::error::FileIOError),

    /// Regular expression compilation or matching error
    #[error("Regex error: {0}")]
    RegexError(#[from] regex::Error),

    /// Configuration parameter is invalid or missing
    #[error("Configuration error: {0}")]
    ConfigError(String),

    /// Error during crash log analysis
    #[error("Analysis error: {0}")]
    AnalysisError(String),

    /// Invalid input provided to a function
    #[error("Invalid input: {0}")]
    InvalidInput(String),

    /// Error matching patterns in crash log
    #[error("Pattern matching error: {0}")]
    PatternError(#[from] aho_corasick::BuildError),

    /// Error generating analysis report
    #[error("Report generation error: {0}")]
    ReportError(String),

    /// Error detecting or identifying GPU information
    #[error("GPU detection error: {0}")]
    GpuError(String),

    /// Settings failed validation checks
    #[error("Settings validation error: {0}")]
    ValidationError(String),

    /// Internal error that should not occur during normal operation
    #[error("Internal error: {0}")]
    Internal(String),
}

/// Result type for scan log operations
pub type Result<T> = std::result::Result<T, ScanLogError>;
