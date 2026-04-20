use super::*;

#[test]
fn test_strip_emoji_no_emojis() {
    let text = "Hello, world!";
    assert_eq!(strip_emoji(text), "Hello, world!");
}

#[test]
fn test_strip_emoji_with_emojis() {
    let text = "Hello 👋 World 🌍!";
    let result = strip_emoji(text);
    assert!(!result.contains('👋'));
    assert!(!result.contains('🌍'));
    assert!(result.contains("Hello"));
    assert!(result.contains("World"));
}

#[test]
fn test_strip_emoji_only_emojis() {
    let text = "👋🌍🎉";
    let result = strip_emoji(text);
    assert!(result.is_empty());
}

#[test]
fn test_strip_emoji_mixed_content() {
    let text = "✅ Success! Operation completed 🎉";
    let result = strip_emoji(text);
    assert!(!result.contains('✅'));
    assert!(!result.contains('🎉'));
    assert!(result.contains("Success"));
    assert!(result.contains("Operation completed"));
}

#[test]
fn test_strip_emoji_unicode_ranges() {
    // Test various emoji ranges
    let text = "😀😎🚀🇺🇸✂️⚡🎨"; // Various emoji categories
    let result = strip_emoji(text);
    assert!(result.is_empty() || result.trim().is_empty());
}

#[test]
fn test_strip_emoji_preserves_text() {
    let text = "This is 😊 a test 🔥 message";
    let result = strip_emoji(text);
    assert!(result.contains("This is"));
    assert!(result.contains("a test"));
    assert!(result.contains("message"));
}

#[test]
fn test_format_log_message_no_details() {
    let formatted = format_log_message("Test message 🎉", None);
    assert!(!formatted.contains('🎉'));
    assert!(formatted.contains("Test message"));
    assert!(!formatted.contains("Details:"));
}

#[test]
fn test_format_log_message_with_details() {
    let formatted = format_log_message("Error occurred ❌", Some("Stack trace 🔍"));
    assert!(!formatted.contains('❌'));
    assert!(!formatted.contains('🔍'));
    assert!(formatted.contains("Error occurred"));
    assert!(formatted.contains("Details:"));
    assert!(formatted.contains("Stack trace"));
}

#[test]
fn test_format_log_message_clean_text() {
    let formatted = format_log_message("Clean message", Some("Clean details"));
    assert_eq!(formatted, "Clean message\nDetails: Clean details");
}

#[test]
fn test_strip_emoji_trims_whitespace() {
    let text = "  😊 Hello 🌍  ";
    let result = strip_emoji(text);
    // Should remove leading/trailing whitespace after emoji removal
    assert!(!result.starts_with(' '));
    assert!(!result.ends_with(' '));
}
