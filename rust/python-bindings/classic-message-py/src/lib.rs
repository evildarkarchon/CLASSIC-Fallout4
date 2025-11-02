///! Python bindings for CLASSIC message core.
///!
///! This module provides Python access to the Rust message routing and formatting system.
///! It exposes message types, targets, formatting utilities, and logging functionality.

use classic_message_core as core;
use pyo3::prelude::*;

mod logging;

/// Message type enumeration for categorizing messages.
///
/// This Python class wraps the Rust `MessageType` enum, providing
/// various message categories for logging and display purposes.
///
/// Attributes:
///     INFO: Informational message.
///     WARNING: Warning message indicating a potential issue.
///     ERROR: Error message indicating a failure or problem.
///     SUCCESS: Message indicating successful completion of an operation.
///     PROGRESS: Message signaling the progress of an ongoing operation.
///     DEBUG: Message intended for debugging purposes.
///     CRITICAL: Message indicating a critical issue requiring immediate attention.
///
/// Example:
///     >>> import classic_message
///     >>> msg_type = classic_message.MessageType.INFO
///     >>> print(msg_type.name())
///     Info
#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MessageType {
    /// Informational message.
    Info = 0,
    /// Warning message.
    Warning = 1,
    /// Error message.
    Error = 2,
    /// Success message.
    Success = 3,
    /// Progress message.
    Progress = 4,
    /// Debug message.
    Debug = 5,
    /// Critical message.
    Critical = 6,
}

impl From<MessageType> for core::MessageType {
    fn from(py_type: MessageType) -> Self {
        match py_type {
            MessageType::Info => Self::Info,
            MessageType::Warning => Self::Warning,
            MessageType::Error => Self::Error,
            MessageType::Success => Self::Success,
            MessageType::Progress => Self::Progress,
            MessageType::Debug => Self::Debug,
            MessageType::Critical => Self::Critical,
        }
    }
}

impl From<core::MessageType> for MessageType {
    fn from(core_type: core::MessageType) -> Self {
        match core_type {
            core::MessageType::Info => Self::Info,
            core::MessageType::Warning => Self::Warning,
            core::MessageType::Error => Self::Error,
            core::MessageType::Success => Self::Success,
            core::MessageType::Progress => Self::Progress,
            core::MessageType::Debug => Self::Debug,
            core::MessageType::Critical => Self::Critical,
        }
    }
}

#[pymethods]
impl MessageType {
    /// Gets the human-readable name of the message type.
    ///
    /// Returns:
    ///     str: The name of the message type.
    ///
    /// Example:
    ///     >>> msg_type = classic_message.MessageType.WARNING
    ///     >>> msg_type.name()
    ///     'Warning'
    fn name(&self) -> &'static str {
        core::MessageType::from(*self).name()
    }

    /// Gets a string representation of the message type.
    ///
    /// Returns:
    ///     str: String representation of the message type.
    fn __repr__(&self) -> String {
        format!("MessageType.{}", self.name())
    }

    /// Gets a string representation of the message type.
    ///
    /// Returns:
    ///     str: String representation of the message type.
    fn __str__(&self) -> &'static str {
        self.name()
    }
}

/// Message target enumeration for routing messages.
///
/// This Python class wraps the Rust `MessageTarget` enum, providing
/// various message routing targets.
///
/// Attributes:
///     ALL: Show in both GUI and CLI.
///     GUI_ONLY: Show only in GUI mode (legacy).
///     CLI_ONLY: Show only in CLI mode (legacy).
///     LOG_ONLY: Only write to log file, no display.
///     GUI: Show only in GUI mode.
///     CONSOLE: Show only in CLI mode.
///
/// Example:
///     >>> import classic_message
///     >>> target = classic_message.MessageTarget.GUI
///     >>> print(target.should_display_in_gui())
///     True
#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MessageTarget {
    /// Show in both GUI and CLI.
    All = 0,
    /// Show only in GUI mode (legacy).
    GuiOnly = 1,
    /// Show only in CLI mode (legacy).
    CliOnly = 2,
    /// Only write to log file, no display.
    LogOnly = 3,
    /// Show only in GUI mode.
    Gui = 4,
    /// Show only in CLI mode.
    Console = 5,
}

impl From<MessageTarget> for core::MessageTarget {
    fn from(py_target: MessageTarget) -> Self {
        match py_target {
            MessageTarget::All => Self::All,
            MessageTarget::GuiOnly => Self::GuiOnly,
            MessageTarget::CliOnly => Self::CliOnly,
            MessageTarget::LogOnly => Self::LogOnly,
            MessageTarget::Gui => Self::Gui,
            MessageTarget::Console => Self::Console,
        }
    }
}

impl From<core::MessageTarget> for MessageTarget {
    fn from(core_target: core::MessageTarget) -> Self {
        match core_target {
            core::MessageTarget::All => Self::All,
            core::MessageTarget::GuiOnly => Self::GuiOnly,
            core::MessageTarget::CliOnly => Self::CliOnly,
            core::MessageTarget::LogOnly => Self::LogOnly,
            core::MessageTarget::Gui => Self::Gui,
            core::MessageTarget::Console => Self::Console,
        }
    }
}

#[pymethods]
impl MessageTarget {
    /// Determines if the message should be displayed in GUI mode.
    ///
    /// Returns:
    ///     bool: True if the message should be displayed in GUI.
    ///
    /// Example:
    ///     >>> target = classic_message.MessageTarget.GUI
    ///     >>> target.should_display_in_gui()
    ///     True
    fn should_display_in_gui(&self) -> bool {
        core::MessageTarget::from(*self).should_display_in_gui()
    }

    /// Determines if the message should be displayed in CLI mode.
    ///
    /// Returns:
    ///     bool: True if the message should be displayed in CLI.
    ///
    /// Example:
    ///     >>> target = classic_message.MessageTarget.CONSOLE
    ///     >>> target.should_display_in_cli()
    ///     True
    fn should_display_in_cli(&self) -> bool {
        core::MessageTarget::from(*self).should_display_in_cli()
    }

    /// Determines if the message should be displayed at all (not log-only).
    ///
    /// Returns:
    ///     bool: True if the message should be displayed.
    ///
    /// Example:
    ///     >>> target = classic_message.MessageTarget.ALL
    ///     >>> target.should_display()
    ///     True
    fn should_display(&self) -> bool {
        core::MessageTarget::from(*self).should_display()
    }

    /// Gets a string representation of the message target.
    ///
    /// Returns:
    ///     str: String representation of the message target.
    fn __repr__(&self) -> String {
        format!("MessageTarget.{self:?}")
    }

    /// Gets a string representation of the message target.
    ///
    /// Returns:
    ///     str: String representation of the message target.
    fn __str__(&self) -> String {
        format!("{self:?}")
    }
}

/// Message data structure with content, type, target, and optional metadata.
///
/// This Python class wraps the Rust `Message` struct, providing
/// a standardized way to handle messages.
///
/// Example:
///     >>> import classic_message
///     >>> msg = classic_message.Message("Hello", classic_message.MessageType.INFO)
///     >>> print(msg.content())
///     Hello
///     >>> msg = msg.with_title("Greeting")
///     >>> print(msg.title())
///     Greeting
#[pyclass]
#[derive(Clone)]
pub struct Message {
    inner: core::Message,
}

#[pymethods]
impl Message {
    /// Creates a new message with the specified content and type.
    ///
    /// Args:
    ///     content: The main content of the message.
    ///     msg_type: The type/severity of the message.
    ///
    /// Returns:
    ///     Message: A new Message instance.
    ///
    /// Example:
    ///     >>> msg = classic_message.Message("Operation completed", classic_message.MessageType.SUCCESS)
    ///     >>> print(msg.content())
    ///     Operation completed
    #[new]
    fn new(content: String, msg_type: MessageType) -> Self {
        Self {
            inner: core::Message::new(content, msg_type.into()),
        }
    }

    /// Creates a new message with the specified content, type, and target.
    ///
    /// Args:
    ///     content: The main content of the message.
    ///     msg_type: The type/severity of the message.
    ///     target: The target audience for the message.
    ///
    /// Returns:
    ///     Message: A new Message instance.
    ///
    /// Example:
    ///     >>> msg = classic_message.Message.with_target(
    ///     ...     "Debug info",
    ///     ...     classic_message.MessageType.DEBUG,
    ///     ...     classic_message.MessageTarget.LOG_ONLY
    ///     ... )
    ///     >>> print(msg.target())
    ///     MessageTarget.LogOnly
    #[staticmethod]
    fn with_target(content: String, msg_type: MessageType, target: MessageTarget) -> Self {
        Self {
            inner: core::Message::with_target(content, msg_type.into(), target.into()),
        }
    }

    /// Builder method to set the message title.
    ///
    /// Args:
    ///     title: The title for the message.
    ///
    /// Returns:
    ///     Message: Self for method chaining.
    ///
    /// Example:
    ///     >>> msg = classic_message.Message("Content", classic_message.MessageType.INFO)
    ///     >>> msg = msg.with_title("Important")
    ///     >>> print(msg.title())
    ///     Important
    fn with_title(mut slf: PyRefMut<'_, Self>, title: String) -> PyRefMut<'_, Self> {
        slf.inner = slf.inner.clone().with_title(title);
        slf
    }

    /// Builder method to set the message details.
    ///
    /// Args:
    ///     details: Additional details or context for the message.
    ///
    /// Returns:
    ///     Message: Self for method chaining.
    ///
    /// Example:
    ///     >>> msg = classic_message.Message("Error", classic_message.MessageType.ERROR)
    ///     >>> msg = msg.with_details("Stack trace: ...")
    ///     >>> print(msg.details())
    ///     Stack trace: ...
    fn with_details(mut slf: PyRefMut<'_, Self>, details: String) -> PyRefMut<'_, Self> {
        slf.inner = slf.inner.clone().with_details(details);
        slf
    }

    /// Gets the message content.
    ///
    /// Returns:
    ///     str: The message content.
    fn content(&self) -> &str {
        self.inner.content()
    }

    /// Gets the message type.
    ///
    /// Returns:
    ///     MessageType: The message type.
    fn msg_type(&self) -> MessageType {
        self.inner.msg_type().into()
    }

    /// Gets the message target.
    ///
    /// Returns:
    ///     MessageTarget: The message target.
    fn target(&self) -> MessageTarget {
        self.inner.target().into()
    }

    /// Gets the optional message title.
    ///
    /// Returns:
    ///     str | None: The title if set, None otherwise.
    fn title(&self) -> Option<&str> {
        self.inner.title()
    }

    /// Gets the optional message details.
    ///
    /// Returns:
    ///     str | None: The details if set, None otherwise.
    fn details(&self) -> Option<&str> {
        self.inner.details()
    }

    /// Sets the message content.
    ///
    /// Args:
    ///     content: The new content for the message.
    fn set_content(&mut self, content: String) {
        self.inner.set_content(content);
    }

    /// Sets the message type.
    ///
    /// Args:
    ///     msg_type: The new type for the message.
    fn set_msg_type(&mut self, msg_type: MessageType) {
        self.inner.set_msg_type(msg_type.into());
    }

    /// Sets the message target.
    ///
    /// Args:
    ///     target: The new target for the message.
    fn set_target(&mut self, target: MessageTarget) {
        self.inner.set_target(target.into());
    }

    /// Sets the message title.
    ///
    /// Args:
    ///     title: The new title for the message, or None to clear it.
    fn set_title(&mut self, title: Option<String>) {
        self.inner.set_title(title);
    }

    /// Sets the message details.
    ///
    /// Args:
    ///     details: The new details for the message, or None to clear them.
    fn set_details(&mut self, details: Option<String>) {
        self.inner.set_details(details);
    }

    /// Gets a string representation of the message.
    ///
    /// Returns:
    ///     str: String representation.
    fn __repr__(&self) -> String {
        format!(
            "Message(content='{}', msg_type={:?}, target={:?})",
            self.inner.content(),
            self.inner.msg_type(),
            self.inner.target()
        )
    }

    /// Gets a string representation of the message.
    ///
    /// Returns:
    ///     str: The message content.
    fn __str__(&self) -> &str {
        self.inner.content()
    }
}

/// Strips emojis from the given text.
///
/// This function removes all emojis and symbols within specified Unicode ranges from
/// the input text. This is particularly useful for logging to avoid encoding issues
/// on Windows console.
///
/// Args:
///     text: The input text string possibly containing emojis.
///
/// Returns:
///     str: A string with all emojis removed and whitespace trimmed.
///
/// Example:
///     >>> import classic_message
///     >>> text = "Hello 👋 World 🌍!"
///     >>> clean = classic_message.strip_emoji(text)
///     >>> print(clean)
///     Hello  World !
#[pyfunction]
fn strip_emoji(text: &str) -> String {
    core::strip_emoji(text)
}

/// Formats a message for logging by stripping emojis from content and details.
///
/// Args:
///     content: The main message content.
///     details: Optional additional details.
///
/// Returns:
///     str: A formatted string suitable for logging.
///
/// Example:
///     >>> import classic_message
///     >>> formatted = classic_message.format_log_message("Success! ✅", "All tests passed 🎉")
///     >>> print(formatted)
///     Success!
///     Details: All tests passed
#[pyfunction]
fn format_log_message(content: &str, details: Option<&str>) -> String {
    core::format_log_message(content, details)
}

/// Python module for CLASSIC message routing and formatting.
///
/// This module provides Rust-accelerated message handling with type-safe
/// message types, targets, and formatting utilities.
///
/// Core Classes:
///     MessageType: Enum for message categories (INFO, WARNING, ERROR, etc.)
///     MessageTarget: Enum for message routing (ALL, GUI, CONSOLE, LOG_ONLY)
///     Message: Data structure for messages with content, type, target, and metadata
///     Logger: Centralized logging facility for the CLASSIC application
///
/// Core Functions:
///     strip_emoji(text): Remove emojis from text for log safety
///     format_log_message(content, details): Format message for logging
///
/// Example:
///     >>> import classic_message
///     >>> # Create a message
///     >>> msg = classic_message.Message("Operation started", classic_message.MessageType.INFO)
///     >>> msg = msg.with_title("Process").with_details("Processing 100 items")
///     >>>
///     >>> # Check routing
///     >>> if msg.target().should_display():
///     ...     print(msg.content())
///     >>>
///     >>> # Format for logging
///     >>> log_text = classic_message.format_log_message(msg.content(), msg.details())
///     >>>
///     >>> # Use the logger
///     >>> logger = classic_message.Logger()
///     >>> logger.info("Application started")
///     >>> logger.log_message(msg)
#[pymodule]
fn classic_message(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Add enums
    m.add_class::<MessageType>()?;
    m.add_class::<MessageTarget>()?;

    // Add message class
    m.add_class::<Message>()?;

    // Add logging
    logging::register(m)?;

    // Add functions
    m.add_function(wrap_pyfunction!(strip_emoji, m)?)?;
    m.add_function(wrap_pyfunction!(format_log_message, m)?)?;

    Ok(())
}
