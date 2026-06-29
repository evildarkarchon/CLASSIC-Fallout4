//! Core message routing and formatting for CLASSIC.
//!
//! This crate provides the core business logic for message handling in the CLASSIC application.
//! It includes:
//!
//! - **Message Types**: Enum for categorizing messages (Info, Warning, Error, etc.)
//! - **Message Targets**: Enum for routing messages to GUI, CLI, or log-only
//! - **Message Struct**: Data structure for encapsulating message content and metadata
//! - **Formatting**: Utilities for preparing UTF-8 messages for display/logging
//! - **Logger Initialization**: Opt-in, idempotent `env_logger` setup for CLASSIC logging
//!
//! # Architecture
//!
//! This is the `-core` crate containing pure Rust business logic. The Python bindings
//! are in the separate `classic-message-py` crate, following the **SEPARATION OF CONCERNS** rule.
//!
//! # Examples
//!
//! ## Creating Messages
//!
//! ```rust
//! use classic_message_core::{Message, MessageType, MessageTarget};
//!
//! // Simple info message
//! let msg = Message::new("Operation started", MessageType::Info);
//!
//! // Message with title and details
//! let msg = Message::new("Error occurred", MessageType::Error)
//!     .with_title("Critical Error")
//!     .with_details("Stack trace: ...");
//!
//! // GUI-only message
//! let msg = Message::with_target(
//!     "Select a file",
//!     MessageType::Info,
//!     MessageTarget::Gui
//! );
//! ```
//!
//! ## Message Routing
//!
//! ```rust
//! use classic_message_core::{Message, MessageType, MessageTarget};
//!
//! let msg = Message::new("Processing...", MessageType::Progress);
//!
//! // Check if message should be displayed
//! if msg.target().should_display() {
//!     println!("{}", msg.content());
//! }
//!
//! // Check if GUI should show this message
//! if msg.target().should_display_in_gui() {
//!     // Show in GUI
//! }
//!
//! // Check if CLI should show this message
//! if msg.target().should_display_in_cli() {
//!     // Show in CLI
//! }
//! ```
//!
//! ## Formatting for Logs
//!
//! ```rust
//! use classic_message_core::{Message, MessageType, format_log_message};
//!
//! let msg = Message::new("Success! ✅", MessageType::Success)
//!     .with_details("All tests passed 🎉");
//!
//! // Preserve valid UTF-8 while appending details for log output
//! let log_text = format_log_message(msg.content(), msg.details());
//! assert_eq!(log_text, "Success! ✅\nDetails: All tests passed 🎉");
//! ```
//!
//! ## Log Level Mapping
//!
//! ```rust
//! use classic_message_core::{Message, MessageType};
//!
//! let msg = Message::new("Warning!", MessageType::Warning);
//!
//! // Get corresponding log level
//! let level = msg.msg_type().to_log_level();
//! log::log!(level, "{}", msg.content());
//! ```

mod enums;
mod formatter;
pub mod logging;
mod message;
mod redaction;

// Re-export public API
pub use enums::{MessageTarget, MessageType};
pub use formatter::format_log_message;
pub use logging::{
    ContractEvent, EVENT_STARTUP_ACCELERATION_STATUS, EVENT_STARTUP_BINDING_CONTRACT_FAILED,
    EVENT_STARTUP_BINDING_CONTRACT_VALIDATED, Logger, format_contract_event, init,
    init_with_filter,
};
pub use message::Message;
pub use redaction::{redact_contract_fields, redact_field_value};

#[cfg(test)]
#[path = "lib_tests.rs"]
mod tests;
