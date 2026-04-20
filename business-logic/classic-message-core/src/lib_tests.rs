use super::*;

#[test]
fn test_integration_message_with_formatting() {
    let msg =
        Message::new("Success! ✅", MessageType::Success).with_details("Operation completed 🎉");

    // Format for logging
    let log_text = format_log_message(msg.content(), msg.details());

    // Should not contain emojis
    assert!(!log_text.contains('✅'));
    assert!(!log_text.contains('🎉'));

    // Should contain actual text
    assert!(log_text.contains("Success"));
    assert!(log_text.contains("Operation completed"));
}

#[test]
fn test_integration_message_routing() {
    let gui_msg = Message::with_target("GUI message", MessageType::Info, MessageTarget::Gui);
    let cli_msg = Message::with_target("CLI message", MessageType::Info, MessageTarget::Console);
    let all_msg = Message::new("All message", MessageType::Info);

    assert!(gui_msg.target().should_display_in_gui());
    assert!(!gui_msg.target().should_display_in_cli());

    assert!(!cli_msg.target().should_display_in_gui());
    assert!(cli_msg.target().should_display_in_cli());

    assert!(all_msg.target().should_display_in_gui());
    assert!(all_msg.target().should_display_in_cli());
}

#[test]
fn test_integration_log_level_mapping() {
    assert_eq!(MessageType::Info.to_log_level(), log::Level::Info);
    assert_eq!(MessageType::Warning.to_log_level(), log::Level::Warn);
    assert_eq!(MessageType::Error.to_log_level(), log::Level::Error);
    assert_eq!(MessageType::Debug.to_log_level(), log::Level::Debug);
}

#[test]
fn test_integration_builder_pattern() {
    let msg = Message::new("Content", MessageType::Info)
        .with_title("Title")
        .with_details("Details");

    assert_eq!(msg.content(), "Content");
    assert_eq!(msg.title(), Some("Title"));
    assert_eq!(msg.details(), Some("Details"));
    assert_eq!(msg.msg_type(), MessageType::Info);
    assert_eq!(msg.target(), MessageTarget::All);
}
