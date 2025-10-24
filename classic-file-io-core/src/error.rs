//! File I/O error types

use thiserror::Error;

/// File I/O errors
#[derive(Debug, Error)]
pub enum FileIOError {
    /// Standard I/O error occurred
    #[error("I/O error: {0}")]
    IoError(#[from] std::io::Error),

    /// Text encoding detection or conversion error
    #[error("Encoding error: {0}")]
    EncodingError(String),

    /// Requested file does not exist
    #[error("File not found: {0}")]
    NotFound(String),

    /// File path is malformed or invalid
    #[error("Invalid path: {0}")]
    InvalidPath(String),

    /// Error parsing DDS (DirectDraw Surface) texture file
    #[error("DDS parsing error: {0}")]
    DDSError(String),

    /// Async task join operation failed
    #[error("Task join error: {0}")]
    JoinError(String),

    /// File cache operation error
    #[error("Cache error: {0}")]
    CacheError(String),

    /// Generic I/O operation failure
    #[error("I/O operation failed: {0}")]
    Io(String),
}

/// Result type alias for file I/O operations
pub type Result<T> = std::result::Result<T, FileIOError>;
