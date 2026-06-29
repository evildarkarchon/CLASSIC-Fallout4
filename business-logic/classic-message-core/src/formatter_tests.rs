use super::*;

#[test]
fn test_format_log_message_preserves_emoji_in_content() {
    let formatted = format_log_message("Success! ✅", None);
    assert_eq!(formatted, "Success! ✅");
}

#[test]
fn test_format_log_message_appends_details_verbatim() {
    let formatted = format_log_message("Done", Some("All tests passed 🎉"));
    assert_eq!(formatted, "Done\nDetails: All tests passed 🎉");
}

#[test]
fn test_format_log_message_no_details_returns_content_only() {
    let formatted = format_log_message("Hello", None);
    assert_eq!(formatted, "Hello");
}

#[test]
fn test_format_log_message_preserves_symbols_and_whitespace() {
    let formatted = format_log_message("  ⚡ Ready  ", Some("Path => C:\\Temp\\CLASSIC ✅"));
    assert_eq!(
        formatted,
        "  ⚡ Ready  \nDetails: Path => C:\\Temp\\CLASSIC ✅"
    );
}
