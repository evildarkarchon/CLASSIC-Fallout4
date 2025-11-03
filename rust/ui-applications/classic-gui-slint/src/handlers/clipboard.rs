// Clipboard handler for copy-to-clipboard functionality
//
// This module re-exports clipboard functionality from classic_ui_shared
// and provides GUI-specific convenience wrappers.

use anyhow::Result;

// Re-export shared clipboard functions
pub use classic_ui_shared::clipboard::copy_to_clipboard;

/// Copy formatted error information to clipboard (GUI-specific wrapper).
///
/// This is a convenience wrapper around [`classic_ui_shared::clipboard::copy_error_to_clipboard`]
/// that automatically sets the interface name to "GUI".
///
/// # Arguments
/// * `title` - Error title (e.g., "Scan Failed")
/// * `message` - Primary error message
/// * `details` - Optional detailed error information
///
/// # Returns
/// * `Ok(())` - Error report copied successfully
/// * `Err(anyhow::Error)` - Failed to copy to clipboard
#[allow(dead_code)]
pub fn copy_error_to_clipboard(title: &str, message: &str, details: Option<&str>) -> Result<()> {
    classic_ui_shared::clipboard::copy_error_to_clipboard(title, message, details, "GUI")
}

#[cfg(test)]
mod tests {
    use super::*;
    use classic_ui_shared::clipboard::{
        clear_clipboard, get_clipboard_text, is_clipboard_available,
    };

    #[test]
    fn test_clipboard_operations() {
        // These tests may fail in CI environments without clipboard access
        if !is_clipboard_available() {
            eprintln!("Skipping clipboard tests: clipboard not available");
            return;
        }

        // Test basic copy
        let test_text = "Test clipboard content";
        assert!(copy_to_clipboard(test_text).is_ok());

        // Test round-trip
        let read_text = get_clipboard_text().expect("Failed to read clipboard");
        assert_eq!(read_text, test_text);

        // Test clear
        assert!(clear_clipboard().is_ok());
        let cleared_text = get_clipboard_text().expect("Failed to read clipboard");
        assert_eq!(cleared_text, "");
    }

    #[test]
    fn test_copy_error_to_clipboard() {
        if !is_clipboard_available() {
            eprintln!("Skipping clipboard tests: clipboard not available");
            return;
        }

        let result = copy_error_to_clipboard(
            "Test Error",
            "This is a test error",
            Some("Error details here"),
        );
        assert!(result.is_ok());
    }
}
