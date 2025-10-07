//! Error handling framework for CLASSIC Rust extensions
//!
//! This module provides a comprehensive error handling system that maps
//! Rust errors to appropriate Python exceptions for seamless integration.

use pyo3::prelude::*;
use pyo3::exceptions::{
    PyIOError, PyValueError, PyRuntimeError, PyPermissionError, PyFileNotFoundError, PyTimeoutError
};
use thiserror::Error;

/// Core error types for the CLASSIC Rust extensions
#[derive(Error, Debug)]
pub enum ClassicError {
    /// I/O related errors
    #[error("I/O error: {message}")]
    Io { message: String, source: Option<Box<dyn std::error::Error + Send + Sync>> },

    /// Path-related errors
    #[error("Path error: {message}")]
    Path { message: String, path: Option<String> },

    /// Validation errors
    #[error("Validation error: {message}")]
    Validation { message: String, field: Option<String> },

    /// Parsing errors
    #[error("Parse error: {message} at position {position:?}")]
    Parse { message: String, position: Option<usize>, context: Option<String> },

    /// Database errors
    #[error("Database error: {message}")]
    Database { message: String, query: Option<String> },

    /// Cache errors
    #[error("Cache error: {message}")]
    Cache { message: String },

    /// Encoding errors
    #[error("Encoding error: {message}")]
    Encoding { message: String, encoding: Option<String> },

    /// Timeout errors
    #[error("Operation timed out after {duration_ms}ms: {operation}")]
    Timeout { operation: String, duration_ms: u64 },

    /// Permission errors
    #[error("Permission denied: {message}")]
    Permission { message: String, resource: Option<String> },

    /// Configuration errors
    #[error("Configuration error: {message}")]
    Configuration { message: String, key: Option<String> },

    /// Processing errors
    #[error("Processing error: {message}")]
    Processing { message: String, stage: Option<String> },

    /// Resource not found
    #[error("Resource not found: {resource}")]
    NotFound { resource: String },

    /// Invalid state
    #[error("Invalid state: {message}")]
    InvalidState { message: String, expected: Option<String>, actual: Option<String> },

    /// Generic error with context
    #[error("{message}")]
    Generic { message: String, details: Option<String> },
}

impl ClassicError {
    /// Create an I/O error with optional source
    pub fn io<E: std::error::Error + Send + Sync + 'static>(message: impl Into<String>, source: Option<E>) -> Self {
        ClassicError::Io {
            message: message.into(),
            source: source.map(|e| Box::new(e) as Box<dyn std::error::Error + Send + Sync>),
        }
    }

    /// Create a path error
    pub fn path(message: impl Into<String>, path: Option<impl Into<String>>) -> Self {
        ClassicError::Path {
            message: message.into(),
            path: path.map(|p| p.into()),
        }
    }

    /// Create a validation error
    pub fn validation(message: impl Into<String>, field: Option<impl Into<String>>) -> Self {
        ClassicError::Validation {
            message: message.into(),
            field: field.map(|f| f.into()),
        }
    }

    /// Create a parse error
    pub fn parse(message: impl Into<String>, position: Option<usize>, context: Option<impl Into<String>>) -> Self {
        ClassicError::Parse {
            message: message.into(),
            position,
            context: context.map(|c| c.into()),
        }
    }

    /// Create a database error
    pub fn database(message: impl Into<String>, query: Option<impl Into<String>>) -> Self {
        ClassicError::Database {
            message: message.into(),
            query: query.map(|q| q.into()),
        }
    }

    /// Create an encoding error
    pub fn encoding(message: impl Into<String>, encoding: Option<impl Into<String>>) -> Self {
        ClassicError::Encoding {
            message: message.into(),
            encoding: encoding.map(|e| e.into()),
        }
    }

    /// Create a timeout error
    pub fn timeout(operation: impl Into<String>, duration_ms: u64) -> Self {
        ClassicError::Timeout {
            operation: operation.into(),
            duration_ms,
        }
    }

    /// Create a permission error
    pub fn permission(message: impl Into<String>, resource: Option<impl Into<String>>) -> Self {
        ClassicError::Permission {
            message: message.into(),
            resource: resource.map(|r| r.into()),
        }
    }

    /// Create a not found error
    pub fn not_found(resource: impl Into<String>) -> Self {
        ClassicError::NotFound {
            resource: resource.into(),
        }
    }

    /// Add context to an existing error
    pub fn with_context(self, context: impl Into<String>) -> Self {
        let context_msg = context.into();
        match self {
            ClassicError::Generic { message, details } => {
                ClassicError::Generic {
                    message,
                    details: Some(match details {
                        Some(d) => format!("{} | Context: {}", d, context_msg),
                        None => context_msg,
                    }),
                }
            }
            other => {
                ClassicError::Generic {
                    message: other.to_string(),
                    details: Some(context_msg),
                }
            }
        }
    }
}

/// Convert ClassicError to appropriate Python exceptions
impl From<ClassicError> for PyErr {
    fn from(err: ClassicError) -> PyErr {
        match err {
            ClassicError::Io { message, .. } => PyIOError::new_err(message),
            ClassicError::Path { message, path } => {
                let msg = match path {
                    Some(p) => format!("{}: {}", message, p),
                    None => message,
                };
                PyIOError::new_err(msg)
            }
            ClassicError::Validation { message, field } => {
                let msg = match field {
                    Some(f) => format!("{}: field '{}'", message, f),
                    None => message,
                };
                PyValueError::new_err(msg)
            }
            ClassicError::Parse { message, position, context } => {
                let msg = match (position, context) {
                    (Some(pos), Some(ctx)) => format!("{} at position {} in: {}", message, pos, ctx),
                    (Some(pos), None) => format!("{} at position {}", message, pos),
                    (None, Some(ctx)) => format!("{} in: {}", message, ctx),
                    (None, None) => message,
                };
                PyValueError::new_err(msg)
            }
            ClassicError::Database { message, query } => {
                let msg = match query {
                    Some(q) => format!("{} | Query: {}", message, q),
                    None => message,
                };
                PyRuntimeError::new_err(msg)
            }
            ClassicError::Cache { message } => PyRuntimeError::new_err(message),
            ClassicError::Encoding { message, encoding } => {
                let msg = match encoding {
                    Some(e) => format!("{}: {}", message, e),
                    None => message,
                };
                PyValueError::new_err(msg)
            }
            ClassicError::Timeout { operation, duration_ms } => {
                PyTimeoutError::new_err(format!("Operation '{}' timed out after {}ms", operation, duration_ms))
            }
            ClassicError::Permission { message, resource } => {
                let msg = match resource {
                    Some(r) => format!("{}: {}", message, r),
                    None => message,
                };
                PyPermissionError::new_err(msg)
            }
            ClassicError::Configuration { message, key } => {
                let msg = match key {
                    Some(k) => format!("{}: key '{}'", message, k),
                    None => message,
                };
                PyValueError::new_err(msg)
            }
            ClassicError::Processing { message, stage } => {
                let msg = match stage {
                    Some(s) => format!("{} in stage: {}", message, s),
                    None => message,
                };
                PyRuntimeError::new_err(msg)
            }
            ClassicError::NotFound { resource } => {
                PyFileNotFoundError::new_err(format!("Resource not found: {}", resource))
            }
            ClassicError::InvalidState { message, expected, actual } => {
                let msg = match (expected, actual) {
                    (Some(exp), Some(act)) => format!("{} | Expected: {}, Actual: {}", message, exp, act),
                    _ => message,
                };
                PyRuntimeError::new_err(msg)
            }
            ClassicError::Generic { message, details } => {
                let msg = match details {
                    Some(d) => format!("{} | Details: {}", message, d),
                    None => message,
                };
                PyRuntimeError::new_err(msg)
            }
        }
    }
}

/// Result type alias for CLASSIC operations
pub type ClassicResult<T> = Result<T, ClassicError>;

/// Helper trait to convert standard errors to ClassicError
pub trait IntoClassicError<T> {
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

/// Macro for easy error creation with context
#[macro_export]
macro_rules! classic_error {
    ($err_type:ident, $msg:expr) => {
        $crate::utils::errors::ClassicError::$err_type($msg.into())
    };
    ($err_type:ident, $msg:expr, $($field:ident = $value:expr),+) => {{
        let mut err = $crate::utils::errors::ClassicError::$err_type($msg.into());
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
            ErrorKind::PermissionDenied => ClassicError::permission(err.to_string(), None::<String>),
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
