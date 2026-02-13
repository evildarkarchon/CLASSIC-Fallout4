//! Error conversion utilities for CLASSIC Python bindings
//!
//! This module provides traits and helpers for converting Rust errors
//! to Python exceptions in a consistent manner across all CLASSIC crates.
//!
//! # Architecture
//!
//! The `ToPyErr` trait provides a standard interface for error conversion.
//! Each Python binding crate implements this trait for their specific error types,
//! mapping error variants to the appropriate exception types.
//!
//! # Example
//!
//! ```rust,ignore
//! use classic_shared::ToPyErr;
//!
//! impl ToPyErr for YamlError {
//!     type BaseException = RustYamlError;
//!     type IOException = RustYamlIOError;
//!     type ParseException = RustYamlParseError;
//!
//!     fn to_pyerr(self) -> PyErr {
//!         match self {
//!             YamlError::IoError(e) => Self::io_err(format!("I/O error: {}", e)),
//!             YamlError::ParseError(e) => Self::parse_err(format!("Parse error: {}", e)),
//!             _ => Self::base_err(self.to_string()),
//!         }
//!     }
//! }
//! ```

use pyo3::PyErr;

/// Trait for converting Rust errors to Python exceptions
///
/// This trait provides a standardized way to convert crate-specific errors
/// to PyErr with appropriate exception types. Implementors should map their
/// error variants to the correct exception category (base, IO, or parse).
///
/// # Associated Types
///
/// - `BaseException`: The base exception type (e.g., `RustYamlError`)
/// - `IOException`: The I/O exception type (e.g., `RustYamlIOError`)
/// - `ParseException`: The parse exception type (e.g., `RustYamlParseError`)
///
/// # Example Implementation
///
/// ```rust,ignore
/// impl ToPyErr for MyError {
///     type BaseException = RustMyError;
///     type IOException = RustMyIOError;
///     type ParseException = RustMyParseError;
///
///     fn to_pyerr(self) -> PyErr {
///         match self {
///             MyError::FileNotFound(path) => Self::io_err(format!("File not found: {}", path)),
///             MyError::InvalidFormat(msg) => Self::parse_err(msg),
///             MyError::Other(msg) => Self::base_err(msg),
///         }
///     }
/// }
/// ```
pub trait ToPyErr: Sized {
    /// The base exception type for this error category
    type BaseException: pyo3::type_object::PyTypeInfo;
    /// The I/O exception type (should inherit from BaseException)
    type IOException: pyo3::type_object::PyTypeInfo;
    /// The parse/validation exception type (should inherit from BaseException)
    type ParseException: pyo3::type_object::PyTypeInfo;

    /// Convert this error to a PyErr
    ///
    /// Implementors should match on error variants and call the appropriate
    /// helper method (`base_err`, `io_err`, or `parse_err`).
    fn to_pyerr(self) -> PyErr;

    /// Create a base exception with the given message
    fn base_err(msg: impl Into<String>) -> PyErr {
        PyErr::new::<Self::BaseException, _>(msg.into())
    }

    /// Create an I/O exception with the given message
    fn io_err(msg: impl Into<String>) -> PyErr {
        PyErr::new::<Self::IOException, _>(msg.into())
    }

    /// Create a parse/validation exception with the given message
    fn parse_err(msg: impl Into<String>) -> PyErr {
        PyErr::new::<Self::ParseException, _>(msg.into())
    }
}

/// Extension trait for Result types with ToPyErr errors
///
/// This trait provides convenient methods for converting `Result<T, E>`
/// to `PyResult<T>` when `E` implements `ToPyErr`.
///
/// # Example
///
/// ```rust,ignore
/// use classic_shared::ResultExt;
///
/// fn my_function() -> PyResult<String> {
///     some_rust_function().map_pyerr()
/// }
/// ```
pub trait ResultExt<T, E: ToPyErr> {
    /// Convert the error to PyErr using the ToPyErr implementation
    fn map_pyerr(self) -> pyo3::PyResult<T>;
}

impl<T, E: ToPyErr> ResultExt<T, E> for Result<T, E> {
    fn map_pyerr(self) -> pyo3::PyResult<T> {
        self.map_err(|e| e.to_pyerr())
    }
}

/// Helper macro for implementing ToPyErr with common patterns
///
/// This macro reduces boilerplate when implementing ToPyErr for error types
/// that follow the common IO/Parse/Other pattern.
///
/// # Example
///
/// ```rust,ignore
/// impl_to_pyerr! {
///     error: YamlError,
///     base: RustYamlError,
///     io: RustYamlIOError,
///     parse: RustYamlParseError,
///     io_variants: [IoError],
///     parse_variants: [ParseError, SerializeError, EmptyDocument, InvalidValue, InvalidKeyPath, TypeConversionError, UnresolvedAlias]
/// }
/// ```
#[macro_export]
macro_rules! impl_to_pyerr {
    (
        error: $error:ty,
        base: $base:ty,
        io: $io:ty,
        parse: $parse:ty,
        io_variants: [$($io_variant:ident),* $(,)?],
        parse_variants: [$($parse_variant:ident),* $(,)?]
    ) => {
        impl $crate::ToPyErr for $error {
            type BaseException = $base;
            type IOException = $io;
            type ParseException = $parse;

            fn to_pyerr(self) -> pyo3::PyErr {
                match &self {
                    $(
                        Self::$io_variant(_) => Self::io_err(self.to_string()),
                    )*
                    $(
                        Self::$parse_variant(_) => Self::parse_err(self.to_string()),
                    )*
                    #[allow(unreachable_patterns)]
                    _ => Self::base_err(self.to_string()),
                }
            }
        }
    };
}

#[cfg(test)]
mod tests {
    // The traits are tested implicitly by the consuming crates
    // since they require actual PyO3 exception types to work
}
