//! Message routing and formatting bindings (classic-message-core)
//!
//! Exposes message types, targets, creation, formatting, and Logger class
//! to JavaScript/TypeScript.

use classic_message_core::{Message, MessageTarget, MessageType, format_log_message};
// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

/// Message severity/category.
#[napi(string_enum)]
pub enum JsMessageType {
    /// Informational message.
    Info,
    /// Warning message indicating a potential issue.
    Warning,
    /// Error message indicating a failure.
    Error,
    /// Message indicating successful completion.
    Success,
    /// Message signaling progress of an ongoing operation.
    Progress,
    /// Message intended for debugging purposes.
    Debug,
    /// Message indicating a critical issue requiring immediate attention.
    Critical,
}

/// Where a message should be directed.
#[napi(string_enum)]
pub enum JsMessageTarget {
    /// Show in both GUI and CLI.
    All,
    /// Show only in GUI mode.
    Gui,
    /// Show only in CLI mode.
    Console,
    /// Only write to log file, no display.
    LogOnly,
}

// ---------------------------------------------------------------------------
// Enum conversions
// ---------------------------------------------------------------------------

impl From<JsMessageType> for MessageType {
    fn from(js: JsMessageType) -> Self {
        match js {
            JsMessageType::Info => Self::Info,
            JsMessageType::Warning => Self::Warning,
            JsMessageType::Error => Self::Error,
            JsMessageType::Success => Self::Success,
            JsMessageType::Progress => Self::Progress,
            JsMessageType::Debug => Self::Debug,
            JsMessageType::Critical => Self::Critical,
        }
    }
}

impl From<MessageType> for JsMessageType {
    fn from(core: MessageType) -> Self {
        match core {
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

impl From<JsMessageTarget> for MessageTarget {
    fn from(js: JsMessageTarget) -> Self {
        match js {
            JsMessageTarget::All => Self::All,
            JsMessageTarget::Gui => Self::Gui,
            JsMessageTarget::Console => Self::Console,
            JsMessageTarget::LogOnly => Self::LogOnly,
        }
    }
}

impl From<MessageTarget> for JsMessageTarget {
    fn from(core: MessageTarget) -> Self {
        match core {
            MessageTarget::All => Self::All,
            MessageTarget::Gui | MessageTarget::GuiOnly => Self::Gui,
            MessageTarget::Console | MessageTarget::CliOnly => Self::Console,
            MessageTarget::LogOnly => Self::LogOnly,
        }
    }
}

// ---------------------------------------------------------------------------
// JsMessage — plain-object representation returned to JavaScript
// ---------------------------------------------------------------------------

/// A message object with type, target, content, and optional metadata.
#[napi(object)]
pub struct JsMessage {
    /// Message severity as a string (e.g. "Info", "Error").
    pub message_type: String,
    /// Message routing target as a string (e.g. "All", "Gui").
    pub target: String,
    /// The main message content.
    pub content: String,
    /// Optional title for the message.
    pub title: Option<String>,
    /// Optional additional details.
    pub details: Option<String>,
    /// Milliseconds since Unix epoch when the message was created.
    pub timestamp: f64,
}

/// Returns the current time as milliseconds since Unix epoch.
fn now_millis() -> f64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs_f64() * 1000.0)
        .unwrap_or(0.0)
}

/// Get the string name of a JsMessageTarget variant.
fn js_message_target_name(target: JsMessageTarget) -> String {
    match target {
        JsMessageTarget::All => "All",
        JsMessageTarget::Gui => "Gui",
        JsMessageTarget::Console => "Console",
        JsMessageTarget::LogOnly => "LogOnly",
    }
    .to_string()
}

/// Converts a core `Message` into a `JsMessage`.
fn core_to_js(msg: &Message) -> JsMessage {
    JsMessage {
        message_type: msg.msg_type().name().to_string(),
        target: js_message_target_name(JsMessageTarget::from(msg.target())),
        content: msg.content().to_string(),
        title: msg.title().map(String::from),
        details: msg.details().map(String::from),
        timestamp: now_millis(),
    }
}

// ---------------------------------------------------------------------------
// Free functions
// ---------------------------------------------------------------------------

/// Create a new message.
///
/// @param msgType - The severity/category of the message.
/// @param content - The main message text.
/// @param target  - Where the message should be routed (defaults to All).
#[napi]
pub fn create_message(
    msg_type: JsMessageType,
    content: String,
    target: Option<JsMessageTarget>,
) -> JsMessage {
    let core_type: MessageType = msg_type.into();
    let core_target: MessageTarget = target
        .map(MessageTarget::from)
        .unwrap_or(MessageTarget::All);

    let msg = Message::with_target(&content, core_type, core_target);
    core_to_js(&msg)
}

/// Format a message for display/logging while preserving valid UTF-8.
///
/// @param message - A JsMessage object.
/// @returns A formatted string suitable for logging.
#[napi]
pub fn format_message(message: JsMessage) -> String {
    format_log_message(&message.content, message.details.as_deref())
}

// ---------------------------------------------------------------------------
// JsLogger — wraps classic_message_core::Logger
// ---------------------------------------------------------------------------

/// A named logger that delegates to Rust's `log` crate.
///
/// The underlying log target is always "CLASSIC" (matching the Python logger).
/// The `name` passed at construction is exposed for identification purposes.
#[napi]
pub struct JsLogger {
    inner: classic_message_core::Logger,
    /// The name provided by the JavaScript consumer.
    name: String,
}

#[napi]
impl JsLogger {
    /// Create a new logger.
    ///
    /// @param name - A name for this logger instance (used for identification).
    #[napi(constructor)]
    pub fn new(name: String) -> Self {
        Self {
            inner: classic_message_core::Logger::new(),
            name,
        }
    }

    /// Get the logger name.
    #[napi(getter)]
    pub fn name(&self) -> String {
        self.name.clone()
    }

    /// Log an info-level message.
    #[napi]
    pub fn info(&self, content: String) {
        self.inner.info(&content);
    }

    /// Log a warning-level message.
    #[napi]
    pub fn warning(&self, content: String) {
        self.inner.warning(&content);
    }

    /// Log an error-level message.
    #[napi]
    pub fn error(&self, content: String) {
        self.inner.error(&content);
    }

    /// Log a debug-level message.
    #[napi]
    pub fn debug(&self, content: String) {
        self.inner.debug(&content);
    }
}

/// Create a new logger instance.
///
/// @param name - A name for this logger (used for identification).
/// @returns A new JsLogger.
#[napi]
pub fn create_logger(name: String) -> JsLogger {
    JsLogger::new(name)
}
