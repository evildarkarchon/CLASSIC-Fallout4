//! Message formatting utilities preserving valid UTF-8.

/// Formats a message for logging while preserving valid UTF-8.
///
/// This function prepares a message for logging by:
/// 1. Returning content verbatim when no details are present
/// 2. Appending details verbatim as `"\nDetails: {details}"` when present
///
/// # Arguments
///
/// * `content` - The main message content.
/// * `details` - Optional additional details.
///
/// # Returns
///
/// A formatted string suitable for logging.
///
/// # Examples
///
/// ```rust
/// use classic_message_core::format_log_message;
///
/// let formatted = format_log_message("Success! ✅", Some("All tests passed 🎉"));
/// assert_eq!(formatted, "Success! ✅\nDetails: All tests passed 🎉");
/// ```
#[must_use]
pub fn format_log_message(content: &str, details: Option<&str>) -> String {
    match details {
        Some(d) => format!("{content}\nDetails: {d}"),
        None => content.to_string(),
    }
}

#[cfg(test)]
#[path = "formatter_tests.rs"]
mod tests;
