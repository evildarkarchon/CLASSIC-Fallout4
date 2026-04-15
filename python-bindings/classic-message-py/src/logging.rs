//! Python bindings for the CLASSIC Logger.
//!
//! This module provides Python access to the Rust logging bridge.

use classic_message_core as core;
use pyo3::prelude::*;

/// Python wrapper for the CLASSIC Logger.
///
/// This class provides a centralized logging facility that integrates with Rust's log crate.
/// It uses the logger name "CLASSIC" to match the Python logging configuration.
///
/// Example:
///     >>> import classic_message
///     >>> logger = classic_message.Logger()
///     >>> logger.info("Application started")
///     >>> logger.warning("Configuration file missing")
///     >>> logger.error("Failed to connect to database")
///
/// Thread Safety:
///     The Logger is thread-safe and can be shared across multiple Python threads.
#[pyclass(name = "Logger", from_py_object)]
#[derive(Clone)]
pub struct PyLogger {
    inner: core::Logger,
}

#[pymethods]
impl PyLogger {
    /// Creates a new Logger instance with the name "CLASSIC".
    ///
    /// Returns:
    ///     Logger: A new Logger instance.
    ///
    /// Example:
    ///     >>> import classic_message
    ///     >>> logger = classic_message.Logger()
    ///     >>> print(logger.name())
    ///     CLASSIC
    #[new]
    fn new() -> Self {
        Self {
            inner: core::Logger::new(),
        }
    }

    /// Gets the logger name.
    ///
    /// Returns:
    ///     str: The logger name (always "CLASSIC").
    ///
    /// Example:
    ///     >>> logger = classic_message.Logger()
    ///     >>> logger.name()
    ///     'CLASSIC'
    fn name(&self) -> &str {
        self.inner.name()
    }

    /// Logs an info-level message.
    ///
    /// Args:
    ///     msg: The message to log.
    ///
    /// Example:
    ///     >>> logger = classic_message.Logger()
    ///     >>> logger.info("Application initialized")
    fn info(&self, msg: &str) {
        self.inner.info(msg);
    }

    /// Logs a warning-level message.
    ///
    /// Args:
    ///     msg: The message to log.
    ///
    /// Example:
    ///     >>> logger = classic_message.Logger()
    ///     >>> logger.warning("Configuration file not found, using defaults")
    fn warning(&self, msg: &str) {
        self.inner.warning(msg);
    }

    /// Logs an error-level message.
    ///
    /// Args:
    ///     msg: The message to log.
    ///
    /// Example:
    ///     >>> logger = classic_message.Logger()
    ///     >>> logger.error("Failed to load database")
    fn error(&self, msg: &str) {
        self.inner.error(msg);
    }

    /// Logs a debug-level message.
    ///
    /// Args:
    ///     msg: The message to log.
    ///
    /// Example:
    ///     >>> logger = classic_message.Logger()
    ///     >>> logger.debug("Request ID: 12345")
    fn debug(&self, msg: &str) {
        self.inner.debug(msg);
    }

    /// Logs a trace-level message.
    ///
    /// Args:
    ///     msg: The message to log.
    ///
    /// Example:
    ///     >>> logger = classic_message.Logger()
    ///     >>> logger.trace("Function entry: process_data")
    fn trace(&self, msg: &str) {
        self.inner.trace(msg);
    }

    /// Logs a message at the specified log level.
    ///
    /// Args:
    ///     level: The log level as a string ("info", "warning", "error", "debug", "trace").
    ///     msg: The message to log.
    ///
    /// Raises:
    ///     ValueError: If the level string is not recognized.
    ///
    /// Example:
    ///     >>> logger = classic_message.Logger()
    ///     >>> logger.log("info", "Dynamic log level")
    fn log(&self, level: &str, msg: &str) -> PyResult<()> {
        let log_level = match level.to_lowercase().as_str() {
            "info" => log::Level::Info,
            "warning" | "warn" => log::Level::Warn,
            "error" => log::Level::Error,
            "debug" => log::Level::Debug,
            "trace" => log::Level::Trace,
            _ => {
                return Err(pyo3::exceptions::PyValueError::new_err(format!(
                    "Invalid log level: '{}'. Expected one of: info, warning, error, debug, trace",
                    level
                )));
            }
        };

        self.inner.log(log_level, msg);
        Ok(())
    }

    /// Logs a Message instance at the appropriate log level.
    ///
    /// The log level is determined by the Message's MessageType.
    ///
    /// Args:
    ///     message: The Message to log.
    ///
    /// Example:
    ///     >>> logger = classic_message.Logger()
    ///     >>> msg = classic_message.Message("Operation completed", classic_message.MessageType.SUCCESS)
    ///     >>> logger.log_message(msg)
    fn log_message(&self, message: &crate::Message) {
        // Convert Python Message wrapper to Rust Message
        let rust_message =
            core::Message::new(message.content().to_string(), message.msg_type().into());

        // Add title if present
        let rust_message = if let Some(title) = message.title() {
            rust_message.with_title(title.to_string())
        } else {
            rust_message
        };

        // Add details if present
        let rust_message = if let Some(details) = message.details() {
            rust_message.with_details(details.to_string())
        } else {
            rust_message
        };

        self.inner.log_message(&rust_message);
    }

    /// Checks if the logger is enabled for the specified log level.
    ///
    /// This is useful for avoiding expensive computations when the log level is not enabled.
    ///
    /// Args:
    ///     level: The log level as a string ("info", "warning", "error", "debug", "trace").
    ///
    /// Returns:
    ///     bool: True if the logger is enabled for the specified level.
    ///
    /// Raises:
    ///     ValueError: If the level string is not recognized.
    ///
    /// Example:
    ///     >>> logger = classic_message.Logger()
    ///     >>> if logger.is_enabled_for("debug"):
    ///     ...     expensive_debug_info = compute_expensive_debug_info()
    ///     ...     logger.debug(expensive_debug_info)
    fn is_enabled_for(&self, level: &str) -> PyResult<bool> {
        let log_level = match level.to_lowercase().as_str() {
            "info" => log::Level::Info,
            "warning" | "warn" => log::Level::Warn,
            "error" => log::Level::Error,
            "debug" => log::Level::Debug,
            "trace" => log::Level::Trace,
            _ => {
                return Err(pyo3::exceptions::PyValueError::new_err(format!(
                    "Invalid log level: '{}'. Expected one of: info, warning, error, debug, trace",
                    level
                )));
            }
        };

        Ok(self.inner.is_enabled_for(log_level))
    }

    /// Checks if info-level logging is enabled.
    ///
    /// Returns:
    ///     bool: True if info-level logging is enabled.
    ///
    /// Example:
    ///     >>> logger = classic_message.Logger()
    ///     >>> if logger.is_info_enabled():
    ///     ...     logger.info("Info logging is enabled")
    fn is_info_enabled(&self) -> bool {
        self.inner.is_info_enabled()
    }

    /// Checks if debug-level logging is enabled.
    ///
    /// Returns:
    ///     bool: True if debug-level logging is enabled.
    ///
    /// Example:
    ///     >>> logger = classic_message.Logger()
    ///     >>> if logger.is_debug_enabled():
    ///     ...     logger.debug("Debug logging is enabled")
    fn is_debug_enabled(&self) -> bool {
        self.inner.is_debug_enabled()
    }

    /// Checks if trace-level logging is enabled.
    ///
    /// Returns:
    ///     bool: True if trace-level logging is enabled.
    ///
    /// Example:
    ///     >>> logger = classic_message.Logger()
    ///     >>> if logger.is_trace_enabled():
    ///     ...     logger.trace("Trace logging is enabled")
    fn is_trace_enabled(&self) -> bool {
        self.inner.is_trace_enabled()
    }

    /// Gets a string representation of the logger.
    ///
    /// Returns:
    ///     str: String representation showing the logger name.
    fn __repr__(&self) -> String {
        format!("Logger(name='{}')", self.inner.name())
    }

    /// Gets a string representation of the logger.
    ///
    /// Returns:
    ///     str: The logger name.
    fn __str__(&self) -> &str {
        self.inner.name()
    }
}

/// Register logging components with the Python module.
///
/// This function is called during module initialization to add the Logger class
/// to the Python module.
///
/// # Arguments
///
/// * `m` - The Python module to register components with
///
/// # Returns
///
/// Returns `PyResult<()>` indicating success or failure of registration.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyLogger>()?;
    Ok(())
}
