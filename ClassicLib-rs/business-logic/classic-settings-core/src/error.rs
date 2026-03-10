//! Error types for settings cache operations.

use std::fmt;
use std::io;
use std::path::PathBuf;

/// Identifies either a filesystem path or a logical in-memory source label.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SettingsSource {
    /// A filesystem-backed source.
    Path(PathBuf),
    /// A logical label for non-filesystem-backed content.
    Label(String),
}

impl SettingsSource {
    /// Returns the underlying path when this source is path-backed.
    pub fn path(&self) -> Option<&PathBuf> {
        match self {
            Self::Path(path) => Some(path),
            Self::Label(_) => None,
        }
    }

    /// Returns the underlying label when this source is label-backed.
    pub fn label(&self) -> Option<&str> {
        match self {
            Self::Path(_) => None,
            Self::Label(label) => Some(label),
        }
    }
}

impl From<PathBuf> for SettingsSource {
    fn from(value: PathBuf) -> Self {
        Self::Path(value)
    }
}

impl From<&std::path::Path> for SettingsSource {
    fn from(value: &std::path::Path) -> Self {
        Self::Path(value.to_path_buf())
    }
}

impl From<String> for SettingsSource {
    fn from(value: String) -> Self {
        Self::Label(value)
    }
}

impl From<&str> for SettingsSource {
    fn from(value: &str) -> Self {
        Self::Label(value.to_string())
    }
}

impl fmt::Display for SettingsSource {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Path(path) => write!(f, "{}", path.display()),
            Self::Label(label) => f.write_str(label),
        }
    }
}

/// Error type for settings cache operations.
#[derive(Debug)]
pub enum SettingsError {
    /// File I/O error
    IoError {
        /// The path that failed
        path: PathBuf,
        /// The underlying I/O error
        source: io::Error,
    },

    /// YAML parsing error
    YamlParseError {
        /// The path or logical source that failed to parse
        source: SettingsSource,
        /// Error message
        message: String,
    },

    /// YAML document stream was empty
    EmptyDocument {
        /// The path or logical source with no documents
        source: SettingsSource,
    },

    /// Cache key not found
    KeyNotFound(String),

    /// Invalid YAML structure
    InvalidYamlStructure {
        /// The path or logical source with invalid structure
        source: SettingsSource,
        /// Zero-based document index within the stream
        index: usize,
        /// What was found
        found: String,
    },

    /// Async task join failure while loading a specific path
    TaskJoinError {
        /// The path whose task failed to join
        path: PathBuf,
        /// The underlying task join error
        source: tokio::task::JoinError,
    },
}

impl fmt::Display for SettingsError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::IoError { path, source } => {
                write!(f, "Failed to read file {}: {}", path.display(), source)
            }
            Self::YamlParseError { source, message } => {
                write!(f, "Failed to parse YAML from {}: {}", source, message)
            }
            Self::EmptyDocument { source } => {
                write!(f, "Empty YAML document stream: {}", source)
            }
            Self::KeyNotFound(key) => write!(f, "Cache key not found: {}", key),
            Self::InvalidYamlStructure {
                source,
                index,
                found,
            } => write!(
                f,
                "Invalid YAML structure in {}: document {} must be a mapping, found {}",
                source, index, found
            ),
            Self::TaskJoinError { path, source } => {
                write!(
                    f,
                    "Task join error while loading {}: {}",
                    path.display(),
                    source
                )
            }
        }
    }
}

impl std::error::Error for SettingsError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::IoError { source, .. } => Some(source),
            Self::TaskJoinError { source, .. } => Some(source),
            _ => None,
        }
    }
}

/// Result type for settings cache operations.
pub type Result<T> = std::result::Result<T, SettingsError>;
