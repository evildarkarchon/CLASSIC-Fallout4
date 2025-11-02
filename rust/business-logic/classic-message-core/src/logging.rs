//! Logging bridge for CLASSIC application.
//!
//! This module provides a centralized logging facility that integrates with Rust's `log` crate
//! and the CLASSIC message system. It bridges Python's logging module with Rust's logging
//! infrastructure.
//!
//! # Features
//!
//! - **Named Logger**: Creates a logger named "CLASSIC" for consistent logging across the application
//! - **Level Mapping**: Maps MessageType to log::Level for seamless integration
//! - **Convenience Methods**: Provides easy-to-use methods for logging at different levels
//! - **Message Integration**: Works with the existing Message type for rich logging
//!
//! # Examples
//!
//! ## Basic Logging
//!
//! ```rust
//! use classic_message_core::logging::Logger;
//!
//! let logger = Logger::new();
//!
//! // Simple logging at different levels
//! logger.info("Application started");
//! logger.warning("Configuration file missing, using defaults");
//! logger.error("Failed to connect to database");
//! logger.debug("Processing request #42");
//! ```
//!
//! ## Logging with Messages
//!
//! ```rust
//! use classic_message_core::{Message, MessageType, logging::Logger};
//!
//! let logger = Logger::new();
//! let msg = Message::new("Operation completed successfully", MessageType::Success)
//!     .with_details("Processed 1000 records in 2.5 seconds");
//!
//! logger.log_message(&msg);
//! ```
//!
//! ## Conditional Logging
//!
//! ```rust
//! use classic_message_core::logging::Logger;
//!
//! let logger = Logger::new();
//!
//! if logger.is_enabled_for(log::Level::Debug) {
//!     // Only compute expensive debug info if debug logging is enabled
//!     let debug_info = compute_expensive_debug_info();
//!     logger.debug(&debug_info);
//! }
//! ```

#[allow(unused_imports)]
use crate::{Message, MessageType};

/// Logger instance for the CLASSIC application.
///
/// This struct provides a centralized logging facility that integrates with Rust's `log` crate.
/// It uses the logger name "CLASSIC" to match the Python logging configuration.
///
/// # Thread Safety
///
/// The Logger is thread-safe and can be shared across threads using Arc<Logger> or cloned
/// since it contains no mutable state.
///
/// # Examples
///
/// ```rust
/// use classic_message_core::logging::Logger;
///
/// let logger = Logger::new();
/// logger.info("Application initialized");
/// logger.warning("Using default configuration");
/// ```
#[derive(Debug, Clone)]
pub struct Logger {
    name: &'static str,
}

impl Logger {
    /// The logger name used throughout CLASSIC.
    pub const LOGGER_NAME: &'static str = "CLASSIC";

    /// Creates a new Logger instance with the name "CLASSIC".
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::logging::Logger;
    ///
    /// let logger = Logger::new();
    /// ```
    pub fn new() -> Self {
        Self {
            name: Self::LOGGER_NAME,
        }
    }

    /// Gets the logger name.
    ///
    /// # Returns
    ///
    /// Returns "CLASSIC" as the logger name.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::logging::Logger;
    ///
    /// let logger = Logger::new();
    /// assert_eq!(logger.name(), "CLASSIC");
    /// ```
    pub fn name(&self) -> &str {
        self.name
    }

    /// Logs an info-level message.
    ///
    /// # Arguments
    ///
    /// * `msg` - The message to log
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::logging::Logger;
    ///
    /// let logger = Logger::new();
    /// logger.info("Processing started");
    /// ```
    pub fn info(&self, msg: &str) {
        log::info!(target: self.name, "{}", msg);
    }

    /// Logs a warning-level message.
    ///
    /// # Arguments
    ///
    /// * `msg` - The message to log
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::logging::Logger;
    ///
    /// let logger = Logger::new();
    /// logger.warning("Configuration file not found, using defaults");
    /// ```
    pub fn warning(&self, msg: &str) {
        log::warn!(target: self.name, "{}", msg);
    }

    /// Logs an error-level message.
    ///
    /// # Arguments
    ///
    /// * `msg` - The message to log
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::logging::Logger;
    ///
    /// let logger = Logger::new();
    /// logger.error("Failed to load database");
    /// ```
    pub fn error(&self, msg: &str) {
        log::error!(target: self.name, "{}", msg);
    }

    /// Logs a debug-level message.
    ///
    /// # Arguments
    ///
    /// * `msg` - The message to log
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::logging::Logger;
    ///
    /// let logger = Logger::new();
    /// logger.debug("Request ID: 12345");
    /// ```
    pub fn debug(&self, msg: &str) {
        log::debug!(target: self.name, "{}", msg);
    }

    /// Logs a trace-level message.
    ///
    /// # Arguments
    ///
    /// * `msg` - The message to log
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::logging::Logger;
    ///
    /// let logger = Logger::new();
    /// logger.trace("Function entry: process_data");
    /// ```
    pub fn trace(&self, msg: &str) {
        log::trace!(target: self.name, "{}", msg);
    }

    /// Logs a message at the specified log level.
    ///
    /// # Arguments
    ///
    /// * `level` - The log level to use
    /// * `msg` - The message to log
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::logging::Logger;
    ///
    /// let logger = Logger::new();
    /// logger.log(log::Level::Info, "Dynamic log level");
    /// ```
    pub fn log(&self, level: log::Level, msg: &str) {
        log::log!(target: self.name, level, "{}", msg);
    }

    /// Logs a Message instance at the appropriate log level.
    ///
    /// The log level is determined by the Message's MessageType using `to_log_level()`.
    ///
    /// # Arguments
    ///
    /// * `message` - The Message to log
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::{Message, MessageType, logging::Logger};
    ///
    /// let logger = Logger::new();
    /// let msg = Message::new("Operation completed", MessageType::Success);
    /// logger.log_message(&msg);
    /// ```
    pub fn log_message(&self, message: &Message) {
        let level = message.msg_type().to_log_level();
        let mut log_text = message.content().to_string();

        // Append title if present
        if let Some(title) = message.title() {
            log_text = format!("{}: {}", title, log_text);
        }

        // Append details if present
        if let Some(details) = message.details() {
            log_text = format!("{} - {}", log_text, details);
        }

        self.log(level, &log_text);
    }

    /// Checks if the logger is enabled for the specified log level.
    ///
    /// This is useful for avoiding expensive computations when the log level is not enabled.
    ///
    /// # Arguments
    ///
    /// * `level` - The log level to check
    ///
    /// # Returns
    ///
    /// Returns `true` if the logger is enabled for the specified level, `false` otherwise.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::logging::Logger;
    ///
    /// let logger = Logger::new();
    ///
    /// if logger.is_enabled_for(log::Level::Debug) {
    ///     // Only compute expensive debug info if debug logging is enabled
    ///     let debug_info = compute_expensive_debug_info();
    ///     logger.debug(&debug_info);
    /// }
    /// ```
    pub fn is_enabled_for(&self, level: log::Level) -> bool {
        log::log_enabled!(target: self.name, level)
    }

    /// Checks if info-level logging is enabled.
    ///
    /// # Returns
    ///
    /// Returns `true` if info-level logging is enabled.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::logging::Logger;
    ///
    /// let logger = Logger::new();
    /// if logger.is_info_enabled() {
    ///     logger.info("Info logging is enabled");
    /// }
    /// ```
    pub fn is_info_enabled(&self) -> bool {
        self.is_enabled_for(log::Level::Info)
    }

    /// Checks if debug-level logging is enabled.
    ///
    /// # Returns
    ///
    /// Returns `true` if debug-level logging is enabled.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::logging::Logger;
    ///
    /// let logger = Logger::new();
    /// if logger.is_debug_enabled() {
    ///     logger.debug("Debug logging is enabled");
    /// }
    /// ```
    pub fn is_debug_enabled(&self) -> bool {
        self.is_enabled_for(log::Level::Debug)
    }

    /// Checks if trace-level logging is enabled.
    ///
    /// # Returns
    ///
    /// Returns `true` if trace-level logging is enabled.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::logging::Logger;
    ///
    /// let logger = Logger::new();
    /// if logger.is_trace_enabled() {
    ///     logger.trace("Trace logging is enabled");
    /// }
    /// ```
    pub fn is_trace_enabled(&self) -> bool {
        self.is_enabled_for(log::Level::Trace)
    }
}

impl Default for Logger {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_logger_name() {
        let logger = Logger::new();
        assert_eq!(logger.name(), "CLASSIC");
        assert_eq!(Logger::LOGGER_NAME, "CLASSIC");
    }

    #[test]
    fn test_default_logger() {
        let logger = Logger::default();
        assert_eq!(logger.name(), "CLASSIC");
    }

    #[test]
    fn test_logger_methods_compile() {
        // These tests just verify that the methods compile and don't panic
        // Actual logging output depends on the log crate configuration
        let logger = Logger::new();

        logger.info("Info message");
        logger.warning("Warning message");
        logger.error("Error message");
        logger.debug("Debug message");
        logger.trace("Trace message");
        logger.log(log::Level::Info, "Log message");
    }

    #[test]
    fn test_log_message() {
        let logger = Logger::new();
        let msg = Message::new("Test content", MessageType::Info)
            .with_title("Test Title")
            .with_details("Test details");

        // This just verifies it compiles and doesn't panic
        logger.log_message(&msg);
    }

    #[test]
    fn test_is_enabled_checks() {
        let logger = Logger::new();

        // These return values depend on the log configuration,
        // but the methods should not panic
        let _ = logger.is_enabled_for(log::Level::Info);
        let _ = logger.is_info_enabled();
        let _ = logger.is_debug_enabled();
        let _ = logger.is_trace_enabled();
    }
}
