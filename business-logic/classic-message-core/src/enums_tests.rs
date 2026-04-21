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
