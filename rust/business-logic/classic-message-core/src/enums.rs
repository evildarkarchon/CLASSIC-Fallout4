//! Message type and target enumerations for the MessageHandler system.
use serde::{Deserialize, Serialize};

/// Represents various types of messages categorized by their context and severity.
///
/// This enumeration helps to define and manage message categories efficiently
/// for logging or displaying purposes. It provides a predefined set of message
/// types that can be used across an application to standardize how messages are
/// identified and processed.
///
/// # Examples
///
/// ```rust
/// use classic_message_core::MessageType;
///
/// let msg_type = MessageType::Info;
/// assert_eq!(msg_type.to_log_level(), log::Level::Info);
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum MessageType {
    /// Denotes an informational message.
    Info,
    /// Denotes a warning message indicating a potential issue.
    Warning,
    /// Denotes an error message indicating a failure or problem.
    Error,
    /// Denotes a message indicating the successful completion of an operation or process.
    Success,
    /// Denotes a message signaling the progress of an ongoing operation.
    Progress,
    /// Denotes a message intended for debugging purposes.
    Debug,
    /// Denotes a message indicating a critical issue requiring immediate attention.
    Critical,
}

impl MessageType {
    /// Converts the message type to its corresponding log level.
    ///
    /// Maps message types to standard logging levels for consistent logging behavior:
    /// - Info, Success → log::Level::Info
    /// - Warning → log::Level::Warn
    /// - Error, Critical → log::Level::Error
    /// - Debug, Progress → log::Level::Debug
    ///
    /// # Returns
    ///
    /// The corresponding `log::Level` for this message type.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::MessageType;
    ///
    /// assert_eq!(MessageType::Error.to_log_level(), log::Level::Error);
    /// assert_eq!(MessageType::Info.to_log_level(), log::Level::Info);
    /// ```
    #[must_use]
    pub const fn to_log_level(&self) -> log::Level {
        match self {
            Self::Debug | Self::Progress => log::Level::Debug,
            Self::Info | Self::Success => log::Level::Info,
            Self::Warning => log::Level::Warn,
            Self::Error | Self::Critical => log::Level::Error,
        }
    }

    /// Returns a human-readable name for the message type.
    ///
    /// # Returns
    ///
    /// A string slice representing the name of the message type.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::MessageType;
    ///
    /// assert_eq!(MessageType::Info.name(), "Info");
    /// assert_eq!(MessageType::Critical.name(), "Critical");
    /// ```
    #[must_use]
    pub const fn name(&self) -> &'static str {
        match self {
            Self::Info => "Info",
            Self::Warning => "Warning",
            Self::Error => "Error",
            Self::Success => "Success",
            Self::Progress => "Progress",
            Self::Debug => "Debug",
            Self::Critical => "Critical",
        }
    }
}

/// Enumeration to specify where a message should be directed.
///
/// This enum defines various message targets such as both GUI and CLI,
/// only GUI, only CLI, or logs. It is used to control and direct how
/// messages are processed and displayed in an application context.
///
/// # Examples
///
/// ```rust
/// use classic_message_core::MessageTarget;
///
/// let target = MessageTarget::All;
/// assert!(target.should_display_in_gui());
/// assert!(target.should_display_in_cli());
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
pub enum MessageTarget {
    /// Show in both GUI and CLI.
    #[default]
    All,
    /// Show only in GUI mode (legacy, prefer `Gui`).
    GuiOnly,
    /// Show only in CLI mode (legacy, prefer `Console`).
    CliOnly,
    /// Only write to log file, no display.
    LogOnly,
    /// Show only in GUI mode.
    Gui,
    /// Show only in CLI mode.
    Console,
}

impl MessageTarget {
    /// Determines if the message should be displayed in GUI mode.
    ///
    /// # Arguments
    ///
    /// * `is_gui_mode` - Whether the application is currently in GUI mode.
    ///
    /// # Returns
    ///
    /// `true` if the message should be displayed in GUI, `false` otherwise.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::MessageTarget;
    ///
    /// assert!(MessageTarget::All.should_display_in_gui());
    /// assert!(MessageTarget::Gui.should_display_in_gui());
    /// assert!(!MessageTarget::Console.should_display_in_gui());
    /// assert!(!MessageTarget::LogOnly.should_display_in_gui());
    /// ```
    #[must_use]
    pub const fn should_display_in_gui(&self) -> bool {
        matches!(self, Self::All | Self::GuiOnly | Self::Gui)
    }

    /// Determines if the message should be displayed in CLI mode.
    ///
    /// # Arguments
    ///
    /// * `is_gui_mode` - Whether the application is currently in GUI mode.
    ///
    /// # Returns
    ///
    /// `true` if the message should be displayed in CLI, `false` otherwise.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::MessageTarget;
    ///
    /// assert!(MessageTarget::All.should_display_in_cli());
    /// assert!(MessageTarget::Console.should_display_in_cli());
    /// assert!(!MessageTarget::Gui.should_display_in_cli());
    /// assert!(!MessageTarget::LogOnly.should_display_in_cli());
    /// ```
    #[must_use]
    pub const fn should_display_in_cli(&self) -> bool {
        matches!(self, Self::All | Self::CliOnly | Self::Console)
    }

    /// Determines if the message should be displayed at all (not log-only).
    ///
    /// # Returns
    ///
    /// `true` if the message should be displayed (not log-only), `false` otherwise.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::MessageTarget;
    ///
    /// assert!(MessageTarget::All.should_display());
    /// assert!(!MessageTarget::LogOnly.should_display());
    /// ```
    #[must_use]
    pub const fn should_display(&self) -> bool {
        !matches!(self, Self::LogOnly)
    }
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_message_type_to_log_level() {
        assert_eq!(MessageType::Debug.to_log_level(), log::Level::Debug);
        assert_eq!(MessageType::Info.to_log_level(), log::Level::Info);
        assert_eq!(MessageType::Warning.to_log_level(), log::Level::Warn);
        assert_eq!(MessageType::Error.to_log_level(), log::Level::Error);
        assert_eq!(MessageType::Success.to_log_level(), log::Level::Info);
        assert_eq!(MessageType::Progress.to_log_level(), log::Level::Debug);
        assert_eq!(MessageType::Critical.to_log_level(), log::Level::Error);
    }

    #[test]
    fn test_message_type_name() {
        assert_eq!(MessageType::Info.name(), "Info");
        assert_eq!(MessageType::Warning.name(), "Warning");
        assert_eq!(MessageType::Error.name(), "Error");
        assert_eq!(MessageType::Success.name(), "Success");
        assert_eq!(MessageType::Progress.name(), "Progress");
        assert_eq!(MessageType::Debug.name(), "Debug");
        assert_eq!(MessageType::Critical.name(), "Critical");
    }

    #[test]
    fn test_message_target_should_display_in_gui() {
        assert!(MessageTarget::All.should_display_in_gui());
        assert!(MessageTarget::GuiOnly.should_display_in_gui());
        assert!(MessageTarget::Gui.should_display_in_gui());
        assert!(!MessageTarget::CliOnly.should_display_in_gui());
        assert!(!MessageTarget::Console.should_display_in_gui());
        assert!(!MessageTarget::LogOnly.should_display_in_gui());
    }

    #[test]
    fn test_message_target_should_display_in_cli() {
        assert!(MessageTarget::All.should_display_in_cli());
        assert!(MessageTarget::CliOnly.should_display_in_cli());
        assert!(MessageTarget::Console.should_display_in_cli());
        assert!(!MessageTarget::GuiOnly.should_display_in_cli());
        assert!(!MessageTarget::Gui.should_display_in_cli());
        assert!(!MessageTarget::LogOnly.should_display_in_cli());
    }

    #[test]
    fn test_message_target_should_display() {
        assert!(MessageTarget::All.should_display());
        assert!(MessageTarget::GuiOnly.should_display());
        assert!(MessageTarget::CliOnly.should_display());
        assert!(MessageTarget::Gui.should_display());
        assert!(MessageTarget::Console.should_display());
        assert!(!MessageTarget::LogOnly.should_display());
    }

    #[test]
    fn test_message_target_default() {
        assert_eq!(MessageTarget::default(), MessageTarget::All);
    }
}
