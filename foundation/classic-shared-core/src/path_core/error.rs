//! Error type for the generic path primitives.
//!
//! [`PathError`] moved here unchanged from `classic-path-core` so the neutral
//! existence, kind, permission, drive, and read-only primitives have one
//! domain-neutral owner. Its variants and `Display` messages are observed by the
//! CXX, Node, and Python path adapters, so they must stay stable.

use std::path::PathBuf;
use thiserror::Error;

/// General path operation errors.
#[derive(Error, Debug)]
pub enum PathError {
    /// Path does not exist in filesystem.
    #[error("Path does not exist: {0}")]
    NotFound(PathBuf),

    /// Path is not a directory when one was expected.
    #[error("Path is not a directory: {0}")]
    NotADirectory(PathBuf),

    /// Path is not a file when one was expected.
    #[error("Path is not a file: {0}")]
    NotAFile(PathBuf),

    /// I/O error occurred.
    #[error("I/O error for path {path}: {source}")]
    IoError {
        /// The path where the I/O error occurred.
        path: PathBuf,
        /// The underlying I/O error.
        source: std::io::Error,
    },

    /// Permission denied accessing path.
    #[error("Permission denied: {0}")]
    PermissionDenied(String),

    /// Invalid path format or characters.
    #[error("Invalid path: {0}")]
    InvalidPath(String),
}

/// Convenience type alias for Results with PathError.
pub type PathResult<T> = Result<T, PathError>;
