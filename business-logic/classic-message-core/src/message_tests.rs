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
