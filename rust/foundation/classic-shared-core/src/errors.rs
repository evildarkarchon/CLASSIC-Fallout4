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

    // ---- Comprehensive error constructor tests ----

    #[test]
    fn test_io_error_with_source() {
        let source = std::io::Error::new(std::io::ErrorKind::NotFound, "file missing");
        let err = ClassicError::io("Read failed", Some(source));
        assert!(err.to_string().contains("I/O error"));
        assert!(err.to_string().contains("Read failed"));
    }

    #[test]
    fn test_path_error_no_path() {
        let err = ClassicError::path("Bad path", None::<String>);
        assert!(err.to_string().contains("Path error"));
    }

    #[test]
    fn test_validation_error_no_field() {
        let err = ClassicError::validation("Invalid", None::<String>);
        assert!(err.to_string().contains("Validation error"));
    }

    #[test]
    fn test_parse_error_full() {
        let err = ClassicError::parse("Syntax error", Some(42), Some("yaml"));
        let msg = err.to_string();
        assert!(msg.contains("Parse error"));
        assert!(msg.contains("42"));
    }

    #[test]
    fn test_parse_error_minimal() {
        let err = ClassicError::parse("Bad format", None, None::<String>);
        assert!(err.to_string().contains("Parse error"));
    }

    #[test]
    fn test_database_error() {
        let err = ClassicError::database("Query failed", Some("SELECT * FROM logs"));
        let msg = err.to_string();
        assert!(msg.contains("Database error"));
    }

    #[test]
    fn test_database_error_no_query() {
        let err = ClassicError::database("Connection lost", None::<String>);
        assert!(err.to_string().contains("Database error"));
    }

    #[test]
    fn test_encoding_error() {
        let err = ClassicError::encoding("Invalid bytes", Some("UTF-8"));
        assert!(err.to_string().contains("Encoding error"));
    }

    #[test]
    fn test_encoding_error_no_encoding() {
        let err = ClassicError::encoding("Bad data", None::<String>);
        assert!(err.to_string().contains("Encoding error"));
    }

    #[test]
    fn test_timeout_error() {
        let err = ClassicError::timeout("file read", 5000);
        let msg = err.to_string();
        assert!(msg.contains("timed out"));
        assert!(msg.contains("5000"));
    }

    #[test]
    fn test_permission_error() {
        let err = ClassicError::permission("Access denied", Some("/secure/file"));
        assert!(err.to_string().contains("Permission denied"));
    }

    #[test]
    fn test_permission_error_no_resource() {
        let err = ClassicError::permission("Not allowed", None::<String>);
        assert!(err.to_string().contains("Permission denied"));
    }

    #[test]
    fn test_not_found_error() {
        let err = ClassicError::not_found("settings.yaml");
        assert!(err.to_string().contains("not found"));
    }

    #[test]
    fn test_with_context_generic() {
        let err = ClassicError::Generic {
            message: "Something failed".to_string(),
            details: None,
        };
        let contexted = err.with_context("During init");
        match contexted {
            ClassicError::Generic { message, details } => {
                assert_eq!(message, "Something failed");
                assert_eq!(details, Some("During init".to_string()));
            }
            _ => panic!("Expected Generic variant"),
        }
    }

    #[test]
    fn test_with_context_generic_existing_details() {
        let err = ClassicError::Generic {
            message: "Error".to_string(),
            details: Some("Original details".to_string()),
        };
        let contexted = err.with_context("Extra context");
        match contexted {
            ClassicError::Generic { details, .. } => {
                let d = details.unwrap();
                assert!(d.contains("Original details"));
                assert!(d.contains("Extra context"));
            }
            _ => panic!("Expected Generic variant"),
        }
    }

    #[test]
    fn test_with_context_non_generic_wraps() {
        let err = ClassicError::not_found("config.yaml");
        let contexted = err.with_context("While loading settings");
        match contexted {
            ClassicError::Generic { message, details } => {
                assert!(message.contains("not found"));
                assert_eq!(details, Some("While loading settings".to_string()));
            }
            _ => panic!("Expected Generic variant after wrapping non-Generic"),
        }
    }

    // ---- From implementations ----

    #[test]
    fn test_from_io_error_not_found() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "file missing");
        let err: ClassicError = io_err.into();
        match err {
            ClassicError::NotFound { .. } => {}
            _ => panic!("Expected NotFound variant, got {:?}", err),
        }
    }

    #[test]
    fn test_from_io_error_permission() {
        let io_err = std::io::Error::new(std::io::ErrorKind::PermissionDenied, "denied");
        let err: ClassicError = io_err.into();
        match err {
            ClassicError::Permission { .. } => {}
            _ => panic!("Expected Permission variant, got {:?}", err),
        }
    }

    #[test]
    fn test_from_io_error_timeout() {
        let io_err = std::io::Error::new(std::io::ErrorKind::TimedOut, "timed out");
        let err: ClassicError = io_err.into();
        match err {
            ClassicError::Timeout { .. } => {}
            _ => panic!("Expected Timeout variant, got {:?}", err),
        }
    }

    #[test]
    fn test_from_io_error_other() {
        let io_err = std::io::Error::new(std::io::ErrorKind::Other, "unexpected");
        let err: ClassicError = io_err.into();
        match err {
            ClassicError::Io { .. } => {}
            _ => panic!("Expected Io variant, got {:?}", err),
        }
    }

    #[test]
    fn test_from_utf8_error() {
        // Create an invalid UTF-8 sequence
        let bytes = &[0xff, 0xfe];
        let utf8_err = std::str::from_utf8(bytes).unwrap_err();
        let err: ClassicError = utf8_err.into();
        match err {
            ClassicError::Encoding { encoding, .. } => {
                assert_eq!(encoding, Some("UTF-8".to_string()));
            }
            _ => panic!("Expected Encoding variant, got {:?}", err),
        }
    }

    // ---- IntoClassicError trait ----

    #[test]
    fn test_into_classic_error_ok() {
        let result: Result<i32, std::io::Error> = Ok(42);
        let classic_result = result.into_classic("test context");
        assert_eq!(classic_result.unwrap(), 42);
    }

    #[test]
    fn test_into_classic_error_err() {
        let result: Result<i32, std::io::Error> = Err(std::io::Error::new(
            std::io::ErrorKind::Other,
            "bad things",
        ));
        let classic_result = result.into_classic("test context");
        let err = classic_result.unwrap_err();
        match err {
            ClassicError::Generic { message, details } => {
                assert_eq!(message, "test context");
                assert!(details.unwrap().contains("bad things"));
            }
            _ => panic!("Expected Generic variant"),
        }
    }

    // ---- Error variant Display ----

    #[test]
    fn test_all_error_variants_display() {
        let errors: Vec<ClassicError> = vec![
            ClassicError::Io { message: "io".to_string(), source: None },
            ClassicError::Path { message: "path".to_string(), path: Some("/p".to_string()) },
            ClassicError::Validation { message: "val".to_string(), field: Some("f".to_string()) },
            ClassicError::Parse { message: "parse".to_string(), position: Some(1), context: Some("ctx".to_string()) },
            ClassicError::Database { message: "db".to_string(), query: Some("q".to_string()) },
            ClassicError::Cache { message: "cache".to_string() },
            ClassicError::Encoding { message: "enc".to_string(), encoding: Some("UTF-8".to_string()) },
            ClassicError::Timeout { operation: "op".to_string(), duration_ms: 100 },
            ClassicError::Permission { message: "perm".to_string(), resource: Some("res".to_string()) },
            ClassicError::Configuration { message: "config".to_string(), key: Some("k".to_string()) },
            ClassicError::Processing { message: "proc".to_string(), stage: Some("s".to_string()) },
            ClassicError::NotFound { resource: "res".to_string() },
            ClassicError::InvalidState { message: "state".to_string(), expected: Some("A".to_string()), actual: Some("B".to_string()) },
            ClassicError::Generic { message: "gen".to_string(), details: Some("det".to_string()) },
        ];

        for err in errors {
            let display = err.to_string();
            assert!(!display.is_empty(), "Error Display should not be empty");
        }
    }
}
