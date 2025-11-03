///! Message data structure for managing messages and their associated metadata.
use crate::enums::{MessageTarget, MessageType};
use serde::{Deserialize, Serialize};

/// Represents a message with various attributes for content, type, target, and optional metadata.
///
/// This struct is used to structure message data, including its content, type, target audience,
/// and optional attributes such as title and additional details. It provides a standardized way
/// to handle messages across different components or systems.
///
/// # Examples
///
/// ```rust
/// use classic_message_core::{Message, MessageType, MessageTarget};
///
/// let msg = Message::new("Hello, world!", MessageType::Info);
/// assert_eq!(msg.content(), "Hello, world!");
/// assert_eq!(msg.msg_type(), MessageType::Info);
/// assert_eq!(msg.target(), MessageTarget::All);
/// ```
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Message {
    /// The core content or body of the message.
    content: String,
    /// The type or category of the message.
    msg_type: MessageType,
    /// The intended audience or target for the message.
    target: MessageTarget,
    /// An optional title for the message.
    title: Option<String>,
    /// Additional details or context related to the message.
    details: Option<String>,
}

impl Message {
    /// Creates a new message with the specified content and type.
    ///
    /// The target defaults to `MessageTarget::All`.
    ///
    /// # Arguments
    ///
    /// * `content` - The main content of the message.
    /// * `msg_type` - The type/severity of the message.
    ///
    /// # Returns
    ///
    /// A new `Message` instance.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::{Message, MessageType};
    ///
    /// let msg = Message::new("Operation completed", MessageType::Success);
    /// assert_eq!(msg.content(), "Operation completed");
    /// ```
    #[must_use]
    pub fn new(content: impl Into<String>, msg_type: MessageType) -> Self {
        Self {
            content: content.into(),
            msg_type,
            target: MessageTarget::default(),
            title: None,
            details: None,
        }
    }

    /// Creates a new message with the specified content, type, and target.
    ///
    /// # Arguments
    ///
    /// * `content` - The main content of the message.
    /// * `msg_type` - The type/severity of the message.
    /// * `target` - The target audience for the message.
    ///
    /// # Returns
    ///
    /// A new `Message` instance.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::{Message, MessageType, MessageTarget};
    ///
    /// let msg = Message::with_target(
    ///     "Debug info",
    ///     MessageType::Debug,
    ///     MessageTarget::LogOnly
    /// );
    /// assert_eq!(msg.target(), MessageTarget::LogOnly);
    /// ```
    #[must_use]
    pub fn with_target(
        content: impl Into<String>,
        msg_type: MessageType,
        target: MessageTarget,
    ) -> Self {
        Self {
            content: content.into(),
            msg_type,
            target,
            title: None,
            details: None,
        }
    }

    /// Builder method to set the message title.
    ///
    /// # Arguments
    ///
    /// * `title` - The title for the message.
    ///
    /// # Returns
    ///
    /// Self for method chaining.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::{Message, MessageType};
    ///
    /// let msg = Message::new("Content", MessageType::Info)
    ///     .with_title("Important");
    /// assert_eq!(msg.title(), Some("Important"));
    /// ```
    #[must_use]
    pub fn with_title(mut self, title: impl Into<String>) -> Self {
        self.title = Some(title.into());
        self
    }

    /// Builder method to set the message details.
    ///
    /// # Arguments
    ///
    /// * `details` - Additional details or context for the message.
    ///
    /// # Returns
    ///
    /// Self for method chaining.
    ///
    /// # Examples
    ///
    /// ```rust
    /// use classic_message_core::{Message, MessageType};
    ///
    /// let msg = Message::new("Error occurred", MessageType::Error)
    ///     .with_details("Stack trace: ...");
    /// assert_eq!(msg.details(), Some("Stack trace: ..."));
    /// ```
    #[must_use]
    pub fn with_details(mut self, details: impl Into<String>) -> Self {
        self.details = Some(details.into());
        self
    }

    /// Gets the message content.
    ///
    /// # Returns
    ///
    /// A string slice containing the message content.
    #[must_use]
    pub fn content(&self) -> &str {
        &self.content
    }

    /// Gets the message type.
    ///
    /// # Returns
    ///
    /// The `MessageType` of this message.
    #[must_use]
    pub const fn msg_type(&self) -> MessageType {
        self.msg_type
    }

    /// Gets the message target.
    ///
    /// # Returns
    ///
    /// The `MessageTarget` of this message.
    #[must_use]
    pub const fn target(&self) -> MessageTarget {
        self.target
    }

    /// Gets the optional message title.
    ///
    /// # Returns
    ///
    /// An `Option` containing the title if set.
    #[must_use]
    pub fn title(&self) -> Option<&str> {
        self.title.as_deref()
    }

    /// Gets the optional message details.
    ///
    /// # Returns
    ///
    /// An `Option` containing the details if set.
    #[must_use]
    pub fn details(&self) -> Option<&str> {
        self.details.as_deref()
    }

    /// Sets the message content.
    ///
    /// # Arguments
    ///
    /// * `content` - The new content for the message.
    pub fn set_content(&mut self, content: impl Into<String>) {
        self.content = content.into();
    }

    /// Sets the message type.
    ///
    /// # Arguments
    ///
    /// * `msg_type` - The new type for the message.
    pub fn set_msg_type(&mut self, msg_type: MessageType) {
        self.msg_type = msg_type;
    }

    /// Sets the message target.
    ///
    /// # Arguments
    ///
    /// * `target` - The new target for the message.
    pub fn set_target(&mut self, target: MessageTarget) {
        self.target = target;
    }

    /// Sets the message title.
    ///
    /// # Arguments
    ///
    /// * `title` - The new title for the message, or `None` to clear it.
    pub fn set_title(&mut self, title: Option<impl Into<String>>) {
        self.title = title.map(Into::into);
    }

    /// Sets the message details.
    ///
    /// # Arguments
    ///
    /// * `details` - The new details for the message, or `None` to clear them.
    pub fn set_details(&mut self, details: Option<impl Into<String>>) {
        self.details = details.map(Into::into);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_message_new() {
        let msg = Message::new("Test content", MessageType::Info);
        assert_eq!(msg.content(), "Test content");
        assert_eq!(msg.msg_type(), MessageType::Info);
        assert_eq!(msg.target(), MessageTarget::All);
        assert_eq!(msg.title(), None);
        assert_eq!(msg.details(), None);
    }

    #[test]
    fn test_message_with_target() {
        let msg = Message::with_target("Debug msg", MessageType::Debug, MessageTarget::LogOnly);
        assert_eq!(msg.content(), "Debug msg");
        assert_eq!(msg.msg_type(), MessageType::Debug);
        assert_eq!(msg.target(), MessageTarget::LogOnly);
    }

    #[test]
    fn test_message_with_title() {
        let msg = Message::new("Content", MessageType::Warning).with_title("Warning Title");
        assert_eq!(msg.title(), Some("Warning Title"));
    }

    #[test]
    fn test_message_with_details() {
        let msg = Message::new("Error", MessageType::Error).with_details("Error details here");
        assert_eq!(msg.details(), Some("Error details here"));
    }

    #[test]
    fn test_message_builder_chain() {
        let msg = Message::new("Main content", MessageType::Success)
            .with_title("Success")
            .with_details("Operation completed successfully");

        assert_eq!(msg.content(), "Main content");
        assert_eq!(msg.msg_type(), MessageType::Success);
        assert_eq!(msg.title(), Some("Success"));
        assert_eq!(msg.details(), Some("Operation completed successfully"));
    }

    #[test]
    fn test_message_setters() {
        let mut msg = Message::new("Original", MessageType::Info);

        msg.set_content("Updated");
        assert_eq!(msg.content(), "Updated");

        msg.set_msg_type(MessageType::Warning);
        assert_eq!(msg.msg_type(), MessageType::Warning);

        msg.set_target(MessageTarget::Gui);
        assert_eq!(msg.target(), MessageTarget::Gui);

        msg.set_title(Some("New Title"));
        assert_eq!(msg.title(), Some("New Title"));

        msg.set_details(Some("New Details"));
        assert_eq!(msg.details(), Some("New Details"));

        msg.set_title(None::<String>);
        assert_eq!(msg.title(), None);

        msg.set_details(None::<String>);
        assert_eq!(msg.details(), None);
    }

    #[test]
    fn test_message_clone() {
        let msg1 = Message::new("Test", MessageType::Info).with_title("Title");
        let msg2 = msg1.clone();

        assert_eq!(msg1.content(), msg2.content());
        assert_eq!(msg1.msg_type(), msg2.msg_type());
        assert_eq!(msg1.target(), msg2.target());
        assert_eq!(msg1.title(), msg2.title());
    }
}
