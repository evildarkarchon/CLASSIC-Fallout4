//! Error types for path management operations.
//!
//! This module defines comprehensive error types for all path management operations,
//! providing rich context for debugging and user-facing error messages.

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
        path: PathBuf,
        source: std::io::Error,
    },

    /// Permission denied accessing path.
    #[error("Permission denied: {0}")]
    PermissionDenied(String),

    /// Invalid path format or characters.
    #[error("Invalid path: {0}")]
    InvalidPath(String),
}

/// Path validation errors.
#[derive(Error, Debug)]
pub enum ValidationError {
    /// Path is restricted for custom scans.
    #[error("Path is restricted for custom scans: {0}")]
    RestrictedPath(PathBuf),

    /// Required file not found in path.
    #[error("Required file '{file}' not found in path: {path}")]
    RequiredFileNotFound { path: PathBuf, file: String },

    /// Path validation failed.
    #[error("Path validation failed for {setting}: {reason}")]
    ValidationFailed { setting: String, reason: String },

    /// General path error.
    #[error(transparent)]
    PathError(#[from] PathError),
}

/// Game path detection errors.
#[derive(Error, Debug)]
pub enum GamePathError {
    /// Game not found by any detection method.
    #[error("Game installation not found via any detection method")]
    NotFound,

    /// Game not found in Windows registry.
    #[error("Game installation not found in Windows registry")]
    RegistryNotFound,

    /// Registry query failed.
    #[error("Failed to query Windows registry: {0}")]
    RegistryError(String),

    /// XSE log file not found.
    #[error("XSE log file not found: {0}")]
    XseLogNotFound(PathBuf),

    /// Failed to read XSE log file.
    #[error("Failed to read XSE log file '{path}': {source}")]
    XseLogReadError {
        path: PathBuf,
        source: std::io::Error,
    },

    /// Failed to parse XSE log file.
    #[error("Failed to parse XSE log: {0}")]
    XseLogParseError(String),

    /// XSE log file not found or unreadable (deprecated - use XseLogNotFound or XseLogReadError).
    #[error("XSE log file not found or unreadable: {0}")]
    XseLogMissing(PathBuf),

    /// XSE log does not contain plugin directory path (deprecated - use XseLogParseError).
    #[error("XSE log does not contain plugin directory path")]
    XsePathNotFound,

    /// Game executable not found in detected path.
    #[error("Game executable '{exe}' not found in path: {path}")]
    ExecutableNotFound { path: PathBuf, exe: String },

    /// XSE file not found in detected path.
    #[error("XSE file '{xse}' not found in path: {path}")]
    XseFileNotFound { path: PathBuf, xse: String },

    /// Game path validation failed.
    #[error("Game path validation failed: {0}")]
    ValidationFailed(String),

    /// User cancelled the path selection dialog.
    #[error("User cancelled path selection")]
    UserCancelled,

    /// Invalid game path provided.
    #[error("Invalid game path: {0}")]
    InvalidPath(String),

    /// General path error.
    #[error(transparent)]
    PathError(#[from] PathError),

    /// I/O error.
    #[error(transparent)]
    IoError(#[from] std::io::Error),
}

/// Documents path detection errors.
#[derive(Error, Debug)]
pub enum DocsPathError {
    /// Documents folder not found via any detection method.
    #[error("Documents folder not found")]
    NotFound,

    /// Windows registry query failed.
    #[error("Failed to query Windows registry for documents path: {0}")]
    RegistryError(String),

    /// Steam library VDF file not found.
    #[error("Steam library VDF file not found: {0}")]
    SteamLibraryNotFound(PathBuf),

    /// Failed to parse Steam library VDF file.
    #[error("Failed to parse Steam library VDF: {0}")]
    SteamLibraryParseError(String),

    /// Game not found in Steam library.
    #[error("Game (Steam ID: {0}) not found in Steam library")]
    GameNotInSteamLibrary(u32),

    /// INI file validation failed.
    #[error("INI file validation failed for '{ini}': {reason}")]
    IniValidationFailed { ini: String, reason: String },

    /// INI parsing error.
    #[error("Failed to parse INI file '{path}': {reason}")]
    IniParseError { path: PathBuf, reason: String },

    /// User cancelled the path selection.
    #[error("User cancelled documents path selection")]
    UserCancelled,

    /// General path error.
    #[error(transparent)]
    PathError(#[from] PathError),

    /// I/O error.
    #[error(transparent)]
    IoError(#[from] std::io::Error),
}

/// Backup operation errors.
#[derive(Error, Debug)]
pub enum BackupError {
    /// XSE log file not found for version extraction.
    #[error("XSE log file not found: {0}")]
    XseLogNotFound(PathBuf),

    /// Version string not found in XSE log.
    #[error("Version string not found in XSE log")]
    VersionNotFound,

    /// Invalid version format in XSE log.
    #[error("Invalid version format: {0}")]
    InvalidVersionFormat(String),

    /// Failed to create backup directory.
    #[error("Failed to create backup directory '{path}': {source}")]
    CreateDirectoryFailed {
        path: PathBuf,
        source: std::io::Error,
    },

    /// Failed to copy file to backup.
    #[error("Failed to copy file '{src}' to '{dst}': {source}")]
    CopyFileFailed {
        src: PathBuf,
        dst: PathBuf,
        source: std::io::Error,
    },

    /// Source file not found for backup.
    #[error("Source file not found: {0}")]
    SourceNotFound(PathBuf),

    /// General path error.
    #[error(transparent)]
    PathError(#[from] PathError),

    /// I/O error.
    #[error(transparent)]
    IoError(#[from] std::io::Error),
}

/// Convenience type alias for Results with PathError.
pub type PathResult<T> = Result<T, PathError>;

/// Convenience type alias for Results with ValidationError.
pub type ValidationResult<T> = Result<T, ValidationError>;

/// Convenience type alias for Results with GamePathError.
pub type GamePathResult<T> = Result<T, GamePathError>;

/// Convenience type alias for Results with DocsPathError.
pub type DocsPathResult<T> = Result<T, DocsPathError>;

/// Convenience type alias for Results with BackupError.
pub type BackupResult<T> = Result<T, BackupError>;
