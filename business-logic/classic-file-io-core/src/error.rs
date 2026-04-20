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
    JoinError(#[from] tokio::task::JoinError),

    /// File cache operation error
    #[error("Cache error: {0}")]
    CacheError(String),

    /// Generic I/O operation failure
    #[error("I/O operation failed: {0}")]
    Io(String),

    /// File write operation failed
    #[error("Failed to write file {path}: {source}")]
    WriteError {
        /// Path to the file
        path: std::path::PathBuf,
        /// Underlying I/O error
        source: std::io::Error,
    },

    /// Directory creation failed
    #[error("Failed to create directory {path}: {source}")]
    CreateDirectoryError {
        /// Path to the directory
        path: std::path::PathBuf,
        /// Underlying I/O error
        source: std::io::Error,
    },

    /// SHA-256 integrity check failed during an atomic install.
    ///
    /// The `expected` value comes from the authoritative source (e.g., a
    /// release manifest) and `actual` is the digest computed from the
    /// downloaded bytes. `path` is the temporary file whose content failed
    /// verification; it is deleted before this error is returned so callers
    /// never see a tainted file on disk.
    #[error("SHA-256 mismatch for {path}: expected {expected}, got {actual}")]
    ChecksumMismatch {
        /// Path to the source file whose content failed verification.
        path: std::path::PathBuf,
        /// Manifest-declared (expected) digest.
        expected: String,
        /// Digest actually computed from file bytes.
        actual: String,
    },
}

/// Result type alias for file I/O operations
pub type Result<T> = std::result::Result<T, FileIOError>;
