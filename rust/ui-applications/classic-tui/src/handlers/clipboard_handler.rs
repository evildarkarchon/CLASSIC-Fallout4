//! Clipboard operations for copying text to system clipboard.
//!
//! This module re-exports clipboard functionality from [`classic_ui_shared::clipboard`]
//! and provides TUI-specific convenience wrappers.

use anyhow::Result;

// Re-export shared clipboard functions
pub use classic_ui_shared::clipboard::copy_to_clipboard;

#[cfg(test)]
use classic_ui_shared::clipboard::is_clipboard_available;

/// Copy formatted error information to clipboard (TUI-specific wrapper).
///
/// This is a convenience wrapper around [`classic_ui_shared::clipboard::copy_error_to_clipboard`]
/// that automatically sets the interface name to "TUI".
///
/// # Arguments
///
/// * `title` - Error title (e.g., "Scan Failed")
/// * `message` - Primary error message
/// * `details` - Optional detailed error information (stack trace, context, etc.)
///
/// # Returns
///
/// Returns `Ok(())` on success, or an error if clipboard operation fails.
///
/// # Examples
///
/// ```no_run
/// use classic_tui::handlers::clipboard_handler::copy_error_to_clipboard;
///
/// copy_error_to_clipboard(
///     "Database Error",
///     "Failed to connect to database",
///     Some("Connection timeout after 30 seconds\nHost: localhost:5432")
/// )?;
/// # Ok::<(), anyhow::Error>(())
/// ```
#[allow(dead_code)]
pub fn copy_error_to_clipboard(title: &str, message: &str, details: Option<&str>) -> Result<()> {
    classic_ui_shared::clipboard::copy_error_to_clipboard(title, message, details, "TUI")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_copy_to_clipboard_basic() {
        // This test may fail in headless CI environments
        if !is_clipboard_available() {
            eprintln!("Skipping clipboard test: clipboard not available");
            return;
        }

        let test_text = "Test clipboard content";
        let result = copy_to_clipboard(test_text);

        // Should succeed if clipboard is available
        assert!(result.is_ok(), "Failed to copy to clipboard: {:?}", result);
    }

    #[test]
    fn test_copy_error_to_clipboard_with_details() {
        if !is_clipboard_available() {
            eprintln!("Skipping clipboard test: clipboard not available");
            return;
        }

        let result = copy_error_to_clipboard(
            "Test Error",
            "This is a test error message",
            Some("Stack trace:\n  at function1()\n  at function2()"),
        );

        assert!(
            result.is_ok(),
            "Failed to copy error to clipboard: {:?}",
            result
        );
    }

    #[test]
    fn test_copy_error_to_clipboard_without_details() {
        if !is_clipboard_available() {
            eprintln!("Skipping clipboard test: clipboard not available");
            return;
        }

        let result = copy_error_to_clipboard("Simple Error", "This error has no details", None);

        assert!(
            result.is_ok(),
            "Failed to copy error to clipboard: {:?}",
            result
        );
    }

    #[test]
    fn test_is_clipboard_available() {
        // This just checks that the function doesn't panic
        let _ = is_clipboard_available();
    }
}
