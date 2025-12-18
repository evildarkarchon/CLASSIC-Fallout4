//! Error handling framework for CLASSIC Rust extensions (Pure Rust - No PyO3)
//!
//! This module provides a comprehensive error handling system for Rust code.
//! Python exception conversion is handled in `classic-shared-py`.
//!
//! # Overview
//!
//! The `ClassicError` enum provides 13 different error types, each designed for
//! specific error scenarios. Errors can be created using convenient constructor
//! methods and enhanced with context.
//!
//! # Features
//!
//! - **Rich Error Types**: 13 specialized error variants for different scenarios
//! - **Context Enhancement**: Add contextual information with `with_context()`
//! - **Helper Trait**: `IntoClassicError` for ergonomic error conversion
//! - **Macro Support**: `classic_error!` macro for concise error creation
//!
//! # Complete Example
//!
//! ```rust,no_run
//! use classic_shared_core::{ClassicError, ClassicResult, IntoClassicError};
//! use std::path::Path;
//!
//! /// Reads and validates a configuration file
//! async fn load_config(path: &Path) -> ClassicResult<String> {
//!     // Use IntoClassicError to add context to std errors
//!     let content = tokio::fs::read_to_string(path)
//!         .await
//!         .into_classic(format!("Failed to read config: {}", path.display()))?;
//!
//!     // Validate the content
//!     if content.is_empty() {
//!         return Err(ClassicError::validation(
//!             "Configuration file is empty",
//!             Some("config_file")
//!         ));
//!     }
//!
//!     // Add context for debugging - use map_err to apply with_context
//!     parse_config(&content)
//!         .map_err(|e| e.with_context(format!("While parsing {}", path.display())))
//! }
//!
//! fn parse_config(content: &str) -> ClassicResult<String> {
//!     if !content.contains("version") {
//!         return Err(ClassicError::parse(
//!             "Missing required 'version' field",
//!             Some(0),
//!             Some("config parsing")
//!         ));
//!     }
//!     Ok(content.to_string())
//! }
//! ```

use thiserror::Error;

/// The `ClassicError` enum represents a comprehensive set of categorized errors
/// that can occur in a system. Each variant is tailored to a specific type of error
/// and includes relevant contextual information for easier debugging and error handling.
#[derive(Error, Debug)]
pub enum ClassicError {
    /// I/O related errors
    #[error("I/O error: {message}")]
    Io {
        /// Description of the I/O error
        message: String,
        /// Optional underlying source error
        source: Option<Box<dyn std::error::Error + Send + Sync>>,
    },

    /// Path-related errors
    #[error("Path error: {message}")]
    Path {
        /// Description of the path error
        message: String,
        /// Optional path that caused the error
        path: Option<String>,
    },

    /// Validation errors
    #[error("Validation error: {message}")]
    Validation {
        /// Description of the validation failure
        message: String,
        /// Optional name of the field that failed validation
        field: Option<String>,
    },

    /// Parsing errors
    #[error("Parse error: {message} at position {position:?}")]
    Parse {
        /// Description of the parse error
        message: String,
        /// Optional position in the input where the error occurred
        position: Option<usize>,
        /// Optional additional context about the error
        context: Option<String>,
    },

    /// Database errors
    #[error("Database error: {message}")]
    Database {
        /// Description of the database error
        message: String,
        /// Optional SQL or database query that caused the error
        query: Option<String>,
    },

    /// Cache errors
    #[error("Cache error: {message}")]
    Cache {
        /// Description of the cache error
        message: String,
    },

    /// Encoding errors
    #[error("Encoding error: {message}")]
    Encoding {
        /// Description of the encoding error
        message: String,
        /// Optional encoding type that caused the issue
        encoding: Option<String>,
    },

    /// Timeout errors
    #[error("Operation timed out after {duration_ms}ms: {operation}")]
    Timeout {
        /// Description of the operation that timed out
        operation: String,
        /// Timeout duration in milliseconds
        duration_ms: u64,
    },

    /// Permission errors
    #[error("Permission denied: {message}")]
    Permission {
        /// Description of the permission error
        message: String,
        /// Optional identifier of the resource for which access was denied
        resource: Option<String>,
    },

    /// Configuration errors
    #[error("Configuration error: {message}")]
    Configuration {
        /// Description of the configuration error
        message: String,
        /// Optional configuration key that caused the error
        key: Option<String>,
    },

    /// Processing errors
    #[error("Processing error: {message}")]
    Processing {
        /// Description of the processing error
        message: String,
        /// Optional stage of the process where the error occurred
        stage: Option<String>,
    },

    /// Resource not found
    #[error("Resource not found: {resource}")]
    NotFound {
        /// Description of the missing resource
        resource: String,
    },

    /// Invalid state
    #[error("Invalid state: {message}")]
    InvalidState {
        /// Description of the invalid state
        message: String,
        /// Optional description of the expected state
        expected: Option<String>,
        /// Optional description of the actual state encountered
        actual: Option<String>,
    },

    /// Generic error with context
    #[error("{message}")]
    Generic {
        /// Description of the error
        message: String,
        /// Optional additional details or context about the error
        details: Option<String>,
    },
}

impl ClassicError {
    /// Constructs a new `ClassicError::Io` variant.
    pub fn io<E: std::error::Error + Send + Sync + 'static>(
        message: impl Into<String>,
        source: Option<E>,
    ) -> Self {
        ClassicError::Io {
            message: message.into(),
            source: source.map(|e| Box::new(e) as Box<dyn std::error::Error + Send + Sync>),
        }
    }

    /// Creates a new `ClassicError::Path` instance
    pub fn path(message: impl Into<String>, path: Option<impl Into<String>>) -> Self {
        ClassicError::Path {
            message: message.into(),
            path: path.map(|p| p.into()),
        }
    }

    /// Creates a new `ClassicError::Validation` instance
    pub fn validation(message: impl Into<String>, field: Option<impl Into<String>>) -> Self {
        ClassicError::Validation {
            message: message.into(),
            field: field.map(|f| f.into()),
        }
    }

    /// Creates a new `ClassicError::Parse` instance
    pub fn parse(
        message: impl Into<String>,
        position: Option<usize>,
        context: Option<impl Into<String>>,
    ) -> Self {
        ClassicError::Parse {
            message: message.into(),
            position,
            context: context.map(|c| c.into()),
        }
    }

    /// Creates a new `ClassicError::Database` variant
    pub fn database(message: impl Into<String>, query: Option<impl Into<String>>) -> Self {
        ClassicError::Database {
            message: message.into(),
            query: query.map(|q| q.into()),
        }
    }

    /// Constructs a new `ClassicError::Encoding` variant
    pub fn encoding(message: impl Into<String>, encoding: Option<impl Into<String>>) -> Self {
        ClassicError::Encoding {
            message: message.into(),
            encoding: encoding.map(|e| e.into()),
        }
    }

    /// Constructs a `ClassicError::Timeout` variant
    pub fn timeout(operation: impl Into<String>, duration_ms: u64) -> Self {
        ClassicError::Timeout {
            operation: operation.into(),
            duration_ms,
        }
    }

    /// Creates a new `ClassicError::Permission` error
    pub fn permission(message: impl Into<String>, resource: Option<impl Into<String>>) -> Self {
        ClassicError::Permission {
            message: message.into(),
            resource: resource.map(|r| r.into()),
        }
    }

    /// Creates a new `ClassicError::NotFound` error instance
    pub fn not_found(resource: impl Into<String>) -> Self {
        ClassicError::NotFound {
            resource: resource.into(),
        }
    }

    /// Enhances a `ClassicError` instance with additional context information.
    ///
    /// This method takes the current `ClassicError` instance and adds a contextual
    /// message to it.
    pub fn with_context(self, context: impl Into<String>) -> Self {
        let context_msg = context.into();
        match self {
            ClassicError::Generic { message, details } => ClassicError::Generic {
                message,
                details: Some(match details {
                    Some(d) => format!("{} | Context: {}", d, context_msg),
                    None => context_msg,
                }),
            },
            other => ClassicError::Generic {
                message: other.to_string(),
                details: Some(context_msg),
            },
        }
    }
}

/// Result type alias for CLASSIC operations
pub type ClassicResult<T> = Result<T, ClassicError>;

/// Helper trait to convert standard errors to ClassicError
pub trait IntoClassicError<T> {
    /// Converts a `Result<T, E>` into a `ClassicResult<T>` by wrapping errors with context.
    fn into_classic(self, context: impl Into<String>) -> ClassicResult<T>;
}

impl<T, E: std::error::Error + Send + Sync + 'static> IntoClassicError<T> for Result<T, E> {
    fn into_classic(self, context: impl Into<String>) -> ClassicResult<T> {
        self.map_err(|e| ClassicError::Generic {
            message: context.into(),
            details: Some(e.to_string()),
        })
    }
}

/// A macro to create instances of `ClassicError` with a concise syntax
#[macro_export]
macro_rules! classic_error {
    ($err_type:ident, $msg:expr) => {
        $crate::errors::ClassicError::$err_type($msg.into())
    };
    ($err_type:ident, $msg:expr, $($field:ident = $value:expr),+) => {{
        let mut err = $crate::errors::ClassicError::$err_type($msg.into());
        $(
            err.$field = Some($value.into());
        )+
        err
    }};
}

/// Convert std::io::Error to ClassicError
impl From<std::io::Error> for ClassicError {
    fn from(err: std::io::Error) -> Self {
        use std::io::ErrorKind;
        match err.kind() {
            ErrorKind::NotFound => ClassicError::not_found(err.to_string()),
            ErrorKind::PermissionDenied => {
                ClassicError::permission(err.to_string(), None::<String>)
            }
            ErrorKind::TimedOut => ClassicError::timeout("I/O operation", 0),
            _ => ClassicError::io(err.to_string(), Some(err)),
        }
    }
}

/// Convert encoding_rs errors
impl From<std::str::Utf8Error> for ClassicError {
    fn from(err: std::str::Utf8Error) -> Self {
        ClassicError::encoding(err.to_string(), Some("UTF-8"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_creation() {
        let err = ClassicError::io("Test I/O error", None::<std::io::Error>);
        assert!(err.to_string().contains("I/O error"));

        let err = ClassicError::path("Invalid path", Some("/test/path"));
        assert!(err.to_string().contains("Invalid path"));
    }

    #[test]
    fn test_error_with_context() {
        let err = ClassicError::validation("Invalid value", Some("test_field"))
            .with_context("During configuration loading");
        assert!(err.to_string().contains("Invalid value"));
    }
}
