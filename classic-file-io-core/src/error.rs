//! File I/O error types

use thiserror::Error;

/// File I/O errors
#[derive(Debug, Error)]
pub enum FileIOError {
    #[error("I/O error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("Encoding error: {0}")]
    EncodingError(String),

    #[error("File not found: {0}")]
    NotFound(String),

    #[error("Invalid path: {0}")]
    InvalidPath(String),

    #[error("DDS parsing error: {0}")]
    DDSError(String),

    #[error("Task join error: {0}")]
    JoinError(String),

    #[error("Cache error: {0}")]
    CacheError(String),
}
