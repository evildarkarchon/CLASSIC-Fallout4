//! Error handling framework for CLASSIC Rust extensions
//!
//! This module provides a comprehensive error handling system that maps
//! Rust errors to appropriate Python exceptions for seamless integration.
//!
//! # Overview
//!
//! The `ClassicError` enum provides 13 different error types, each designed for
//! specific error scenarios. Errors can be created using convenient constructor
//! methods, enhanced with context, and automatically convert to Python exceptions
//! when crossing the Rust-Python boundary.
//!
//! # Features
//!
//! - **Rich Error Types**: 13 specialized error variants for different scenarios
//! - **Context Enhancement**: Add contextual information with `with_context()`
//! - **Python Integration**: Automatic conversion to appropriate Python exceptions
//! - **Helper Trait**: `IntoClassicError` for ergonomic error conversion
//! - **Macro Support**: `classic_error!` macro for concise error creation
//!
//! # Complete Example
//!
//! ```rust
//! use classic_shared::{ClassicError, ClassicResult, IntoClassicError};
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
//!     // Add context for debugging
//!     parse_config(&content)
//!         .with_context(format!("While parsing {}", path.display()))
//! }
//!
//! fn parse_config(content: &str) -> ClassicResult<String> {
//!     // Simulate parsing
//!     if !content.contains("version") {
//!         return Err(ClassicError::parse(
//!             "Missing required 'version' field",
//!             Some(0),
//!             Some("config parsing")
//!         ));
//!     }
//!     Ok(content.to_string())
//! }
//!
//! /// Process data with timeout handling
//! async fn process_with_timeout(data: &str, timeout_ms: u64) -> ClassicResult<String> {
//!     use tokio::time::{timeout, Duration};
//!
//!     timeout(
//!         Duration::from_millis(timeout_ms),
//!         async_processing(data)
//!     )
//!     .await
//!     .map_err(|_| ClassicError::timeout("data processing", timeout_ms))?
//! }
//!
//! async fn async_processing(data: &str) -> ClassicResult<String> {
//!     // Simulate processing
//!     Ok(data.to_uppercase())
//! }
//!
//! /// Database query with error handling
//! async fn query_database(query: &str) -> ClassicResult<Vec<String>> {
//!     // Simulate database error
//!     if query.contains("DROP") {
//!         return Err(ClassicError::database(
//!             "Dangerous query rejected",
//!             Some(query)
//!         ));
//!     }
//!     Ok(vec!["result1".to_string(), "result2".to_string()])
//! }
//! ```
//!
//! # Error Chaining Example
//!
//! ```rust
//! use classic_shared::{ClassicError, ClassicResult};
//!
//! fn high_level_operation() -> ClassicResult<()> {
//!     mid_level_operation()
//!         .with_context("High-level operation failed")
//! }
//!
//! fn mid_level_operation() -> ClassicResult<()> {
//!     low_level_operation()
//!         .with_context("Mid-level processing error")
//! }
//!
//! fn low_level_operation() -> ClassicResult<()> {
//!     Err(ClassicError::Generic {
//!         message: "Connection lost".to_string(),
//!         details: Some("Network timeout after 30s".to_string()),
//!     })
//! }
//!
//! // When called, produces error with full context chain:
//! // "Connection lost | Context: Mid-level processing error | Context: High-level operation failed"
//! ```
//!
//! # Python Integration
//!
//! When errors cross the Rust-Python boundary (via PyO3), they automatically
//! convert to appropriate Python exceptions:
//!
//! ```python
//! # Python code calling Rust functions
//! try:
//!     result = rust_module.load_config("missing_file.yaml")
//! except FileNotFoundError as e:
//!     print(f"File error: {e}")  # ClassicError::NotFound -> FileNotFoundError
//! except PermissionError as e:
//!     print(f"Permission error: {e}")  # ClassicError::Permission -> PermissionError
//! except ValueError as e:
//!     print(f"Validation error: {e}")  # ClassicError::Validation -> ValueError
//! except IOError as e:
//!     print(f"I/O error: {e}")  # ClassicError::Io/Path -> IOError
//! ```

use pyo3::exceptions::{
    PyFileNotFoundError, PyIOError, PyPermissionError, PyRuntimeError, PyTimeoutError, PyValueError,
};
use pyo3::prelude::*;
use thiserror::Error;

/// The `ClassicError` enum represents a comprehensive set of categorized errors
/// that can occur in a system. Each variant is tailored to a specific type of error
/// and includes relevant contextual information for easier debugging and error handling.
/// # Variants
///
/// * `Io`
///     - Represents input/output related errors.
///     - Fields:
///         - `message`: A description of the error.
///         - `source`: An optional underlying source error.
///
/// * `Path`
///     - Represents errors related to file or directory paths.
///     - Fields:
///         - `message`: A description of the error.
///         - `path`: The optional path that caused the error.
///
/// * `Validation`
///     - Indicates a validation error occurred.
///     - Fields:
///         - `message`: A description of the validation failure.
///         - `field`: An optional name of the field being validated.
///
/// * `Parse`
///     - Represents parsing-related errors (e.g., parsing files, data, etc.).
///     - Fields:
///         - `message`: A description of the parse error.
///         - `position`: The optional position in the input where the error occurred.
///         - `context`: Optional additional context about the error.
///
/// * `Database`
///     - Represents errors related to database operations.
///     - Fields:
///         - `message`: A description of the database error.
///         - `query`: The optional SQL or database query being executed.
///
/// * `Cache`
///     - Represents errors involving cache systems.
///     - Fields:
///         - `message`: A description of the cache error.
///
/// * `Encoding`
///     - Denotes errors during the encoding or decoding of data.
///     - Fields:
///         - `message`: A description of the error.
///         - `encoding`: The optional encoding type causing the issue.
///
/// * `Timeout`
///     - Occurs when an operation exceeds the allowed time limit.
///     - Fields:
///         - `operation`: A description of the operation being performed.
///         - `duration_ms`: The timeout duration in milliseconds.
///
/// * `Permission`
///     - Represents a permission or access-related error.
///     - Fields:
///         - `message`: A description of the error.
///         - `resource`: An optional identifier of the resource for which access was denied.
///
/// * `Configuration`
///     - Represents errors in the system configuration.
///     - Fields:
///         - `message`: A description of the configuration issue.
///         - `key`: The optional configuration key involved.
///
/// * `Processing`
///     - Indicates issues encountered during processing stages of the application.
///     - Fields:
///         - `message`: A description of the processing error.
///         - `stage`: The optional stage of the process where the error occurred.
///
/// * `NotFound`
///     - Denotes a missing resource error.
///     - Fields:
///         - `resource`: A description of the missing resource.
///
/// * `InvalidState`
///     - Represents an issue where a resource or system is in an invalid state.
///     - Fields:
///         - `message`: A description of the invalid state.
///         - `expected`: An optional description of the expected state.
///         - `actual`: An optional description of the actual state encountered.
///
/// * `Generic`
///     - A general-purpose error variant to represent custom errors with additional details.
///     - Fields:
///         - `message`: A description of the error.
///         - `details`: Optional additional details or context about the error.
///
/// # Examples
///
/// ```rust
/// use thiserror::Error;
/// use crate::ClassicError;
///
/// fn example_function() -> Result<(), ClassicError> {
///     // Example of creating an Io error.
///     Err(ClassicError::Io {
///         message: "Failed to read file".to_string(),
///         source: None,
///     })
/// }
///
/// match example_function() {
///     Err(ClassicError::Io { message, .. }) => println!("I/O Error: {}", message),
///     _ => (),
/// }
/// ```
#[derive(Error, Debug)]
pub enum ClassicError {
    /// I/O related errors
    #[error("I/O error: {message}")]
    Io {
        message: String,
        source: Option<Box<dyn std::error::Error + Send + Sync>>,
    },

    /// Path-related errors
    #[error("Path error: {message}")]
    Path {
        message: String,
        path: Option<String>,
    },

    /// Validation errors
    #[error("Validation error: {message}")]
    Validation {
        message: String,
        field: Option<String>,
    },

    /// Parsing errors
    #[error("Parse error: {message} at position {position:?}")]
    Parse {
        message: String,
        position: Option<usize>,
        context: Option<String>,
    },

    /// Database errors
    #[error("Database error: {message}")]
    Database {
        message: String,
        query: Option<String>,
    },

    /// Cache errors
    #[error("Cache error: {message}")]
    Cache { message: String },

    /// Encoding errors
    #[error("Encoding error: {message}")]
    Encoding {
        message: String,
        encoding: Option<String>,
    },

    /// Timeout errors
    #[error("Operation timed out after {duration_ms}ms: {operation}")]
    Timeout { operation: String, duration_ms: u64 },

    /// Permission errors
    #[error("Permission denied: {message}")]
    Permission {
        message: String,
        resource: Option<String>,
    },

    /// Configuration errors
    #[error("Configuration error: {message}")]
    Configuration {
        message: String,
        key: Option<String>,
    },

    /// Processing errors
    #[error("Processing error: {message}")]
    Processing {
        message: String,
        stage: Option<String>,
    },

    /// Resource not found
    #[error("Resource not found: {resource}")]
    NotFound { resource: String },

    /// Invalid state
    #[error("Invalid state: {message}")]
    InvalidState {
        message: String,
        expected: Option<String>,
        actual: Option<String>,
    },

    /// Generic error with context
    #[error("{message}")]
    Generic {
        message: String,
        details: Option<String>,
    },
}

impl ClassicError {
    /// Constructs a new `ClassicError::Io` variant.
    ///
    /// This function is used to create an instance of the `ClassicError::Io` variant, which represents
    /// an input/output-related error. It accepts a message providing additional context about the error
    /// and an optional source error that caused the IO-related issue.
    /// # Type Parameters
    /// - `E`: A type that implements the `std::error::Error`, `Send`, `Sync`, and `'static` traits.
    ///
    /// # Parameters
    /// - `message`: A value that can be converted into a `String`, providing context or a description
    ///   of the error.
    /// - `source`: An optional error of type `E`, representing the underlying cause of the IO-related error.
    ///
    /// # Returns
    /// A `ClassicError::Io` variant containing the provided message and optional source error.
    ///
    /// # Example
    /// ```rust
    /// use some_module::ClassicError;
    /// use std::io;
    ///
    /// let io_error = io::Error::new(io::ErrorKind::NotFound, "File not found");
    /// let error = ClassicError::io("Failed to open file", Some(io_error));
    /// ```
    ///
    /// In this example, `ClassicError::io` constructs an instance of `ClassicError::Io` with a
    /// description and the underlying IO error as its source.
    pub fn io<E: std::error::Error + Send + Sync + 'static>(
        message: impl Into<String>,
        source: Option<E>,
    ) -> Self {
        ClassicError::Io {
            message: message.into(),
            source: source.map(|e| Box::new(e) as Box<dyn std::error::Error + Send + Sync>),
        }
    }

    /// Creates a new `ClassicError::Path` instance with the provided message and optional path.
    /// # Arguments
    ///
    /// * `message` - A type that can be converted into a `String`, representing the error message.
    /// * `path` - An optional value that can also be converted into a `String`, representing the associated file path or location.
    ///
    /// # Returns
    ///
    /// Returns an instance of `Self`, specifically `ClassicError::Path` variant, containing the provided message and optional path.
    ///
    /// # Example
    ///
    /// ```rust
    /// let error_with_path = ClassicError::path("File not found", Some("/path/to/file"));
    /// let error_without_path = ClassicError::path("Path is missing", None);
    /// ```
    ///
    /// # Notes
    ///
    /// - The `path` parameter is optional; if `None` is provided, the `ClassicError::Path` instance will not include a path.
    /// - This method is typically used for creating structured errors that include a descriptive message and an optional path for context.
    pub fn path(message: impl Into<String>, path: Option<impl Into<String>>) -> Self {
        ClassicError::Path {
            message: message.into(),
            path: path.map(|p| p.into()),
        }
    }

    /// Creates a new `ClassicError` instance representing a validation error.
    /// # Parameters
    /// - `message`: An error message describing the validation issue. This can be any type 
    ///   that implements the `Into<String>` trait.
    /// - `field`: An optional field name related to the validation error. This can be any type 
    ///   that implements the `Into<String>` trait. If `None` is provided, the error will not 
    ///   be associated with a specific field.
    ///
    /// # Returns
    /// A new `ClassicError::Validation` variant containing the provided message and optional field name.
    ///
    /// # Example
    /// ```rust
    /// let error = ClassicError::validation("Invalid input", Some("username"));
    /// let error_without_field = ClassicError::validation("Missing required field", None);
    /// ```
    pub fn validation(message: impl Into<String>, field: Option<impl Into<String>>) -> Self {
        ClassicError::Validation {
            message: message.into(),
            field: field.map(|f| f.into()),
        }
    }

    /// Constructs a new `ClassicError::Parse` instance.
    ///
    /// This function creates a parse error with a given message, an optional position
    /// indicating where the parsing error occurred, and an optional context to provide
    /// additional details about the error.
    /// # Parameters
    ///
    /// - `message`: A message describing the parsing error. This can be any type that 
    ///   implements `Into<String>`.
    /// - `position`: An optional `usize` indicating the position in the input where the 
    ///   parsing error occurred. If `None`, the position is unspecified.
    /// - `context`: An optional additional context for the error. This can be any type 
    ///   that implements `Into<String>`. If `None`, no context is provided.
    ///
    /// # Returns
    ///
    /// Returns an instance of `ClassicError::Parse` containing the specified message, 
    /// position, and context.
    ///
    /// # Example
    ///
    /// ```rust
    /// let error = ClassicError::parse("Invalid syntax", Some(42), Some("while parsing a number"));
    /// ```
    ///
    /// This creates a `ClassicError::Parse` error with the message "Invalid syntax", 
    /// position `42`, and additional context "while parsing a number".
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

    /// Creates a new `ClassicError::Database` variant.
    ///
    /// This function is used to construct an error representing a database-related issue.
    /// It accepts a mandatory error message and an optional SQL query string that is
    /// associated with the error.
    /// # Parameters
    ///
    /// - `message`: The primary error message as a string or any type that can be converted into a string.
    /// - `query`: An optional parameter representing the SQL query causing the error, which could be `None` or any type convertible into a string.
    ///
    /// # Returns
    ///
    /// A new instance of the `ClassicError::Database` variant, with the provided message and optional query.
    ///
    /// # Examples
    ///
    /// ```rust
    /// let err = ClassicError::database("Connection failed", Some("SELECT * FROM table"));
    /// let err_without_query = ClassicError::database("Connection failed", None);
    /// ```
    ///
    /// In this example:
    /// - `err` represents a database error with a specific SQL query attached.
    /// - `err_without_query` represents a database error without any associated query.
    pub fn database(message: impl Into<String>, query: Option<impl Into<String>>) -> Self {
        ClassicError::Database {
            message: message.into(),
            query: query.map(|q| q.into()),
        }
    }

    /// Constructs a new `ClassicError::Encoding` variant.
    ///
    /// This function creates an instance of the `ClassicError` enum, specifically the `Encoding`
    /// variant. It requires a message describing the encoding error and optionally accepts the type
    /// of encoding to be associated with the error.
    /// # Parameters
    /// - `message`: A value that can be converted into a `String`. This represents the error message
    ///   describing the encoding issue.
    /// - `encoding`: An optional value that can be converted into a `String`. This represents the type
    ///   of encoding involved in the error, if applicable.
    ///
    /// # Returns
    /// - Returns an instance of `ClassicError` with the `Encoding` variant containing the provided
    ///   message and optional encoding type.
    ///
    /// # Example
    /// ```
    /// let error = ClassicError::encoding("Invalid encoding detected", Some("UTF-8"));
    /// let error_without_encoding = ClassicError::encoding("Unknown encoding", None);
    /// ```
    ///
    /// In the first example, the `message` is `"Invalid encoding detected"` and the `encoding` is
    /// `"UTF-8"`. In the second example, only the `message` is provided, while the `encoding` is `None`.
    pub fn encoding(message: impl Into<String>, encoding: Option<impl Into<String>>) -> Self {
        ClassicError::Encoding {
            message: message.into(),
            encoding: encoding.map(|e| e.into()),
        }
    }

    /// Constructs a `ClassicError::Timeout` variant representing a timeout error for a specified operation.
    /// # Parameters
    /// - `operation`: A value implementing `Into<String>` that describes the operation that timed out.
    /// - `duration_ms`: The timeout duration in milliseconds as a `u64`.
    ///
    /// # Returns
    /// A `ClassicError` instance with the `Timeout` variant populated with the provided operation and timeout duration.
    ///
    /// # Example
    /// ```rust
    /// let timeout_error = ClassicError::timeout("database_query", 5000);
    /// assert!(matches!(timeout_error, ClassicError::Timeout { .. }));
    /// ```
    ///
    /// This method is useful when you need to indicate that an operation has exceeded its permitted execution time.
    pub fn timeout(operation: impl Into<String>, duration_ms: u64) -> Self {
        ClassicError::Timeout {
            operation: operation.into(),
            duration_ms,
        }
    }

    /// Creates a new `ClassicError::Permission` error with a specified message and an optional resource.
    /// # Parameters
    /// - `message`: The error message, which can be converted into a `String`. This provides details 
    ///   about the permission error.
    /// - `resource`: An optional parameter representing the resource related to the permission error. 
    ///   This can also be converted into a `String`.
    ///
    /// # Returns
    /// - Returns an instance of the `ClassicError` enum with the `Permission` variant initialized 
    ///   with the given message and optional resource.
    ///
    /// # Example
    /// ```rust
    /// let error = ClassicError::permission("Access denied", Some("/protected/resource"));
    /// let error_without_resource = ClassicError::permission("Operation not permitted", None);
    /// ```
    pub fn permission(message: impl Into<String>, resource: Option<impl Into<String>>) -> Self {
        ClassicError::Permission {
            message: message.into(),
            resource: resource.map(|r| r.into()),
        }
    }

    /// Creates a new `ClassicError::NotFound` error instance for a specified resource.
    /// # Parameters
    /// - `resource`: A value that implements the `Into<String>` trait, representing 
    ///   the name or description of the resource that was not found.
    ///
    /// # Returns
    /// An instance of `ClassicError::NotFound` with the provided resource name.
    ///
    /// # Examples
    /// ```
    /// let error = ClassicError::not_found("user");
    /// // This creates a NotFound error for the resource "user".
    /// ```
    pub fn not_found(resource: impl Into<String>) -> Self {
        ClassicError::NotFound {
            resource: resource.into(),
        }
    }

    /// Enhances a `ClassicError` instance with additional context information.
    ///
    /// This method takes the current `ClassicError` instance and adds a contextual
    /// message to it. If the error is already a `Generic` variant, the additional
    /// context is appended to the existing details. If the `details` field is `None`,
    /// the context message becomes the new `details` value. For any other variant,
    /// the method converts it into a `Generic` variant, preserving its message and
    /// attaching the provided context as the `details`.
    /// # Parameters
    /// - `self`: The `ClassicError` instance to be augmented with context information.
    /// - `context`: An implementation of `Into<String>` that represents the additional
    ///   context to associate with the error.
    ///
    /// # Returns
    /// A new `ClassicError` instance with the added contextual information.
    ///
    /// # Examples
    /// ```rust
    /// let error = ClassicError::Generic {
    ///     message: "File not found".to_string(),
    ///     details: None,
    /// };
    /// let detailed_error = error.with_context("Attempted to open config file");
    /// // detailed_error now contains the details: "Attempted to open config file".
    ///
    /// let another_error = ClassicError::IoError(std::io::Error::from(std::io::ErrorKind::NotFound));
    /// let converted_error = another_error.with_context("Occurred during file read");
    /// // converted_error is converted to a Generic error with the provided details.
    /// ```
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

/// Convert ClassicError to appropriate Python exceptions
impl From<ClassicError> for PyErr {
    /// Converts a `ClassicError` instance into a `PyErr` instance for integration
    /// with Python error handling mechanisms. The generated `PyErr` will have
    /// a type and message corresponding to the kind of `ClassicError` it
    /// represents, ensuring meaningful and context-sensitive error reporting.
    /// # Arguments
    ///
    /// * `err` - An instance of `ClassicError` containing error details.
    ///
    /// # Returns
    ///
    /// A `PyErr` object aligned to the corresponding Python exception type
    /// with an appropriate error message derived from the `ClassicError`.
    ///
    /// # Mappings
    ///
    /// The function maps each variant of the `ClassicError` enum to a meaningful
    /// Python exception, including:
    ///
    /// * `ClassicError::Io` - Converts into a `PyIOError`.
    ///   - If the `Io` variant contains a message, it uses it for the error message.
    ///
    /// * `ClassicError::Path` - Converts into a `PyIOError`.
    ///   - If the `Path` variant includes a file path, it appends that path
    ///     to the error message.
    ///
    /// * `ClassicError::Validation` - Converts into a `PyValueError`.
    ///   - Incorporates optional offending field information into the message.
    ///
    /// * `ClassicError::Parse` - Converts into a `PyValueError`.
    ///   - Includes optional source position and parsing context in the error message.
    ///
    /// * `ClassicError::Database` - Converts into a `PyRuntimeError`.
    ///   - Adds optional query details to the error message.
    ///
    /// * `ClassicError::Cache` - Converts into a `PyRuntimeError`.
    ///   - Utilizes the provided error message.
    ///
    /// * `ClassicError::Encoding` - Converts into a `PyValueError`.
    ///   - Includes optional encoding information in the error message.
    ///
    /// * `ClassicError::Timeout` - Converts into a `PyTimeoutError`.
    ///   - Specifies the operation and duration of the timeout in milliseconds.
    ///
    /// * `ClassicError::Permission` - Converts into a `PyPermissionError`.
    ///   - Includes optional resource information in the error message.
    ///
    /// * `ClassicError::Configuration` - Converts into a `PyValueError`.
    ///   - Adds optional key information into the error message.
    ///
    /// * `ClassicError::Processing` - Converts into a `PyRuntimeError`.
    ///   - Includes details of the processing stage in the error message, if available.
    ///
    /// * `ClassicError::NotFound` - Converts into a `PyFileNotFoundError`.
    ///   - Specifies the resource that was not found.
    ///
    /// * `ClassicError::InvalidState` - Converts into a `PyRuntimeError`.
    ///   - When available, includes both expected and actual state details in
    ///     the error message.
    ///
    /// * `ClassicError::Generic` - Converts into a `PyRuntimeError`.
    ///   - Appends optional additional details to the base error message.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use some_module::ClassicError;
    /// use some_module_to_convert::from;
    ///
    /// let error = ClassicError::Io { 
    ///     message: "File not found".to_string(),
    ///     source: None 
    /// };
    ///
    /// let py_error = from(error);
    /// assert_eq!(py_error.to_string(), "PyIOError: File not found");
    /// ```
    ///
    /// This function ensures that Python receives meaningful, structured information
    /// from errors originating in Rust code. It is especially useful in applications
    /// integrating Rust backends with Python frontends.
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
            ClassicError::Parse {
                message,
                position,
                context,
            } => {
                let msg = match (position, context) {
                    (Some(pos), Some(ctx)) => {
                        format!("{} at position {} in: {}", message, pos, ctx)
                    }
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
            ClassicError::Timeout {
                operation,
                duration_ms,
            } => PyTimeoutError::new_err(format!(
                "Operation '{}' timed out after {}ms",
                operation, duration_ms
            )),
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
            ClassicError::InvalidState {
                message,
                expected,
                actual,
            } => {
                let msg = match (expected, actual) {
                    (Some(exp), Some(act)) => {
                        format!("{} | Expected: {}, Actual: {}", message, exp, act)
                    }
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
    /// Converts the current result into a `ClassicResult<T>` by mapping an existing error into a
    /// `ClassicError::Generic` variant with additional context information.
    /// # Parameters
    /// * `self` - The current `Result<T, E>` instance to transform. It must implement the `map_err` method.
    /// * `context` - A value that implements the `Into<String>` trait, providing additional context about the error.
    ///
    /// # Returns
    /// A `ClassicResult<T>` where:
    /// - `Ok(T)` remains unchanged.
    /// - `Err(E)` is transformed into a `ClassicError::Generic` containing:
    ///   - `message`: A string representation of the provided `context`.
    ///   - `details`: An optional string representation of the original error.
    ///
    /// # Example
    /// ```rust
    /// use crate::{ClassicError, ClassicResult}; // Adjust imports as needed
    ///
    /// let result: Result<u32, &str> = Err("Something went wrong");
    /// let classic_result = result.into_classic("Error context");
    ///
    /// match classic_result {
    ///     Ok(value) => println!("Success: {}", value),
    ///     Err(ClassicError::Generic { message, details }) => {
    ///         println!("Error occurred: {}", message);
    ///         if let Some(details) = details {
    ///             println!("Details: {}", details);
    ///         }
    ///     }
    /// }
    /// ```
    ///
    /// # Note
    /// The function assumes that the error type `E` implements the `ToString` trait in order to convert 
    /// the error details into a string format.
    fn into_classic(self, context: impl Into<String>) -> ClassicResult<T> {
        self.map_err(|e| ClassicError::Generic {
            message: context.into(),
            details: Some(e.to_string()),
        })
    }
}

/// A macro to create instances of `ClassicError` with a concise syntax while optionally
/// populating additional fields.
///
/// The macro can be called in two forms:
///
/// 1. With the error type and a message:
///    ```
///    classic_error!(ErrorType, "An error message");
///    ```
///
/// 2. With the error type, a message, and additional field assignments:
///    ```
///    classic_error!(ErrorType, "An error message", field1 = value1, field2 = value2);
///    ```
/// # Parameters
/// - `$err_type:ident`: The variant of `ClassicError` to create.
/// - `$msg:expr`: The error message to associate with the error.
/// - `$field:ident`: The name of a field to assign a value to in the error object (optional, used with additional fields).
/// - `$value:expr`: The value for the specified field (optional, used with additional fields).
///
/// # Returns
/// - An instance of `ClassicError` of the specified variant, optionally with additional fields populated.
///
/// # Example
///
/// Using the macro with just an error type and a message:
/// ```rust
/// let error = classic_error!(NotFound, "Resource not found");
/// ```
///
/// Using the macro to create an error and populate additional fields:
/// ```rust
/// let error = classic_error!(ValidationError, "Validation failed", field1 = "value1", field2 = "value2");
/// ```
///
/// In the second form, any additional fields specified are set on the error instance if they are
/// declared as `Option` fields in the `ClassicError` implementation. These fields are assigned
/// using the `Some` variant with the provided values converted to an appropriate type using `.into()`.
///
/// # Note
/// This macro depends on the following naming conventions and structures:
/// - The `$crate::errors::ClassicError` structure must exist.
/// - `ClassicError` must have variants matching `$err_type`.
/// - Variants of `ClassicError` used in the macro should support instantiation with a single `String` argument.
/// - Any additional fields being set dynamically must be `Option` types in the `ClassicError` structure.
///
/// # Caveats
/// Ensure the fields specified in the macro invocation exist in the `ClassicError` struct/enum and are mutable,
/// or the macro will result in a compile-time error.
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
    /// Converts a standard `std::io::Error` into a custom `ClassicError`.
    /// # Parameters
    /// - `err`: An instance of `std::io::Error` to be converted into a `ClassicError`.
    ///
    /// # Returns
    /// - A `ClassicError` variant corresponding to the provided `std::io::Error`. The specific variant
    ///   is chosen based on the `ErrorKind` of the input error:
    ///   - `ErrorKind::NotFound`: Returns a `ClassicError::not_found` initialized with the error's
    ///     description.
    ///   - `ErrorKind::PermissionDenied`: Returns a `ClassicError::permission` initialized with the
    ///     error's description and `None` as additional context.
    ///   - `ErrorKind::TimedOut`: Returns a `ClassicError::timeout` initialized with a static message
    ///     ("I/O operation") and a default timeout value of `0`.
    ///   - For all other error kinds, returns a `ClassicError::io` initialized with the error's
    ///     description and the original `std::io::Error` as additional context.
    ///
    /// # Examples
    /// ```rust
    /// use std::io::{self, ErrorKind};
    ///
    /// // Simulate a not found error
    /// let not_found_error = io::Error::new(ErrorKind::NotFound, "File not found");
    /// let classic_error = ClassicError::from(not_found_error);
    ///
    /// // Simulate a permission denied error
    /// let permission_error = io::Error::new(ErrorKind::PermissionDenied, "Access denied");
    /// let classic_error = ClassicError::from(permission_error);
    ///
    /// // Simulate an unknown I/O-related error
    /// let unknown_error = io::Error::new(ErrorKind::Other, "Unknown I/O error");
    /// let classic_error = ClassicError::from(unknown_error);
    /// ```
    ///
    /// # Notes
    /// This function uses pattern matching on `std::io::ErrorKind`. The implementation ensures that common
    /// standard error situations (e.g., IO operation timeout, missing files, or permission issues) are explicitly
    /// handled to provide more meaningful error messages. For any unhandled error kinds, it falls back to wrapping
    /// the original error within a generic `io`-specific `ClassicError`.
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
    /// Converts a `std::str::Utf8Error` into a `ClassicError`, with detailed information about the error.
    /// # Parameters
    /// - `err`: A `std::str::Utf8Error` instance representing the UTF-8 encoding error that occurred.
    ///
    /// # Returns
    /// Returns a `ClassicError` instance that encapsulates the provided error information,
    /// tagging it with additional context about the "UTF-8" encoding format.
    ///
    /// # Examples
    /// ```rust
    /// use std::str::Utf8Error;
    ///
    /// // Simulate a UTF-8 error
    /// let utf8_error = std::str::from_utf8(&[0xFF]).err().unwrap();
    /// let classic_error = ClassicError::from(utf8_error);
    ///
    /// // classic_error includes details about the UTF-8 error
    /// ```
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
