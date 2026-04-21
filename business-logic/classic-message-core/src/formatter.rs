//! Message formatting utilities including emoji stripping.

/// Strips emojis and symbols from the given text.
///
/// This function removes all emojis and symbols within specified Unicode ranges from
/// the input text. Emojis and symbols are identified through Unicode character ranges.
/// This is particularly useful for logging to avoid encoding issues on Windows console.
///
/// # Arguments
///
/// * `text` - The input text string possibly containing emojis.
///
/// # Returns
///
/// A `String` with all emojis removed and whitespace trimmed.
///
/// # Examples
///
/// ```rust
/// use classic_message_core::strip_emoji;
///
/// let text = "Hello 👋 World 🌍!";
/// let clean = strip_emoji(text);
/// assert_eq!(clean, "Hello  World !");
/// ```
#[must_use]
pub fn strip_emoji(text: &str) -> String {
    text.chars()
        .filter(|&c| {
            let code = c as u32;
            // Emoji ranges to filter out
            !(
                (0x1F600..=0x1F64F).contains(&code) ||  // Emoticons
                (0x1F300..=0x1F5FF).contains(&code) ||  // Symbols & pictographs
                (0x1F680..=0x1F6FF).contains(&code) ||  // Transport & map symbols
                (0x1F1E0..=0x1F1FF).contains(&code) ||  // Flags (iOS)
                (0x2702..=0x27B0).contains(&code) ||    // Dingbats
                (0x24C2..=0x1F251).contains(&code) ||   // Extended range
                (0x1F900..=0x1F9FF).contains(&code) ||  // Supplemental symbols
                (0x2600..=0x26FF).contains(&code) ||    // Miscellaneous symbols
                (0x2700..=0x27BF).contains(&code)
                // Dingbats extended
            )
        })
        .collect::<String>()
        .trim()
        .to_string()
}

/// Formats a message for logging by stripping emojis from content and details.
///
/// This function prepares a message for logging by:
/// 1. Stripping emojis from the content
/// 2. Appending stripped details if present
/// 3. Returning a clean log-safe string
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
/// assert!(!formatted.contains('✅'));
/// assert!(!formatted.contains('🎉'));
/// ```
#[must_use]
pub fn format_log_message(content: &str, details: Option<&str>) -> String {
    let clean_content = strip_emoji(content);

    match details {
        Some(d) => {
            let clean_details = strip_emoji(d);
            format!("{clean_content}\nDetails: {clean_details}")
        }
        None => clean_content,
    }
}

#[cfg(test)]
#[path = "formatter_tests.rs"]
mod tests;
