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
//! ```rust,ignore
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

use crate::{Message, MessageType};
use std::collections::BTreeMap;

use crate::redaction::redact_contract_fields;

const DEFAULT_LOG_FILTER: &str = "info";

/// Initialize the process-wide Rust logger for CLASSIC.
///
/// Uses `env_logger` with `RUST_LOG` support and defaults to `info` when no
/// filter is provided by the environment. Repeated calls are safe and leave any
/// existing global logger in place.
pub fn init() {
    let mut builder = env_logger::Builder::from_env(
        env_logger::Env::default().default_filter_or(DEFAULT_LOG_FILTER),
    );
    let _ = builder.try_init();
}

/// Initialize the process-wide Rust logger with an explicit filter directive.
///
/// Repeated calls are safe and leave any existing global logger in place.
pub fn init_with_filter(filter: &str) {
    let mut builder = env_logger::Builder::new();
    builder.parse_filters(filter);
    let _ = builder.try_init();
}

/// Canonical event id for successful startup binding contract validation.
pub const EVENT_STARTUP_BINDING_CONTRACT_VALIDATED: &str =
    "classic.startup.binding_contract.validated";
/// Canonical event id for startup binding contract failure.
pub const EVENT_STARTUP_BINDING_CONTRACT_FAILED: &str = "classic.startup.binding_contract.failed";
/// Canonical event id for startup acceleration status summary.
pub const EVENT_STARTUP_ACCELERATION_STATUS: &str = "classic.startup.acceleration.status";

/// Structured contract event for parity-scoped logging.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContractEvent {
    event: String,
    severity: MessageType,
    component: String,
    outcome: String,
    context: BTreeMap<String, String>,
}

impl ContractEvent {
    /// Create a new structured contract event.
    #[must_use]
    pub fn new(
        component: impl Into<String>,
        event: impl Into<String>,
        severity: MessageType,
        outcome: impl Into<String>,
    ) -> Self {
        Self {
            event: event.into(),
            severity,
            component: component.into(),
            outcome: outcome.into(),
            context: BTreeMap::new(),
        }
    }

    /// Add a context field to the event.
    #[must_use]
    pub fn with_context(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.context.insert(key.into(), value.into());
        self
    }

    /// Get event identifier.
    #[must_use]
    pub fn event(&self) -> &str {
        &self.event
    }

    /// Get message severity.
    #[must_use]
    pub const fn severity(&self) -> MessageType {
        self.severity
    }

    /// Get component name.
    #[must_use]
    pub fn component(&self) -> &str {
        &self.component
    }

    /// Get event outcome.
    #[must_use]
    pub fn outcome(&self) -> &str {
        &self.outcome
    }

    /// Get event context fields.
    #[must_use]
    pub const fn context(&self) -> &BTreeMap<String, String> {
        &self.context
    }
}

#[must_use]
fn contract_severity_name(severity: MessageType) -> &'static str {
    match severity {
        MessageType::Info | MessageType::Success => "info",
        MessageType::Warning => "warning",
        MessageType::Error | MessageType::Critical => "error",
        MessageType::Debug | MessageType::Progress => "debug",
    }
}

#[must_use]
fn escape_contract_value(value: &str) -> String {
    if value.is_empty()
        || value.contains(' ')
        || value.contains('=')
        || value.contains('"')
        || value.contains('\n')
    {
        let escaped = value.replace('"', "\\\"");
        format!("\"{escaped}\"")
    } else {
        value.to_string()
    }
}

/// Format a structured contract event into a stable key=value log line.
#[must_use]
pub fn format_contract_event(event: &ContractEvent) -> String {
    let mut segments = vec![
        format!("event={}", escape_contract_value(event.event())),
        format!(
            "severity={}",
            escape_contract_value(contract_severity_name(event.severity()))
        ),
        format!("component={}", escape_contract_value(event.component())),
        format!("outcome={}", escape_contract_value(event.outcome())),
    ];

    let redacted = redact_contract_fields(event.context());
    for (key, value) in redacted {
        segments.push(format!("{}={}", key, escape_contract_value(value.as_str())));
    }

    segments.join(" ")
}

/// Logger instance for the CLASSIC application.
///
/// This struct provides a centralized logging facility that integrates with Rust's `log` crate.
/// It uses the logger name "CLASSIC" to match the Python logging configuration.
///
/// # Thread Safety
///
/// The Logger is thread-safe and can be shared across threads using `Arc<Logger>` or cloned
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

    /// Logs a structured contract event.
    pub fn log_contract_event(&self, event: &ContractEvent) {
        self.log(
            event.severity().to_log_level(),
            &format_contract_event(event),
        );
    }

    /// Logs startup contract validation success with canonical event fields.
    pub fn log_startup_binding_contract_validated(
        &self,
        contract: &str,
        checked_bindings: usize,
        correlation_id: Option<&str>,
    ) {
        let mut event = ContractEvent::new(
            "integration.startup",
            EVENT_STARTUP_BINDING_CONTRACT_VALIDATED,
            MessageType::Info,
            "success",
        )
        .with_context("contract", contract)
        .with_context("checked_bindings", checked_bindings.to_string());

        if let Some(correlation_id) = correlation_id {
            event = event.with_context("correlation_id", correlation_id);
        }

        self.log_contract_event(&event);
    }

    /// Logs startup contract validation failure with canonical event fields.
    pub fn log_startup_binding_contract_failed(
        &self,
        contract: &str,
        missing_binding: &str,
        failure_type: &str,
        failure_hint: &str,
        error: &str,
        correlation_id: Option<&str>,
    ) {
        let mut event = ContractEvent::new(
            "integration.startup",
            EVENT_STARTUP_BINDING_CONTRACT_FAILED,
            MessageType::Error,
            "failure",
        )
        .with_context("contract", contract)
        .with_context("missing_binding", missing_binding)
        .with_context("failure_type", failure_type)
        .with_context("failure_hint", failure_hint)
        .with_context("error", error);

        if let Some(correlation_id) = correlation_id {
            event = event.with_context("correlation_id", correlation_id);
        }

        self.log_contract_event(&event);
    }

    /// Logs startup acceleration summary with canonical event fields.
    pub fn log_startup_acceleration_status(
        &self,
        active_components: usize,
        total_components: usize,
        acceleration_level: &str,
        correlation_id: Option<&str>,
    ) {
        let mut event = ContractEvent::new(
            "integration.startup",
            EVENT_STARTUP_ACCELERATION_STATUS,
            MessageType::Info,
            "success",
        )
        .with_context("active_components", active_components.to_string())
        .with_context("total_components", total_components.to_string())
        .with_context("acceleration_level", acceleration_level);

        if let Some(correlation_id) = correlation_id {
            event = event.with_context("correlation_id", correlation_id);
        }

        self.log_contract_event(&event);
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
    /// ```rust,ignore
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
#[path = "logging_tests.rs"]
mod tests;
