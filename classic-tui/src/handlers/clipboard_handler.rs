///! Clipboard operations for copying text to system clipboard.
///!
///! This module provides cross-platform clipboard functionality using the
///! `arboard` crate for copying error messages, report content, and other
///! text to the system clipboard.

use anyhow::{Context, Result};
use arboard::Clipboard;

/// Copy text to the system clipboard.
///
/// This function creates a new clipboard instance and sets the text content.
/// On success, returns `Ok(())`. On failure, returns an error describing what went wrong.
///
/// # Arguments
///
/// * `text` - The text content to copy to clipboard
///
/// # Returns
///
/// Returns `Ok(())` on success, or an error if clipboard operation fails.
///
/// # Examples
///
/// ```no_run
/// use classic_tui::handlers::clipboard_handler::copy_to_clipboard;
///
/// let error_text = "Error: File not found\nDetails: /path/to/file.log";
/// match copy_to_clipboard(error_text) {
///     Ok(()) => println!("✓ Copied to clipboard"),
///     Err(e) => println!("✗ Failed to copy: {}", e),
/// }
/// ```
///
/// # Errors
///
/// Returns an error if:
/// - Clipboard is not available (e.g., headless environment)
/// - Clipboard access is denied by the system
/// - Text encoding fails
pub fn copy_to_clipboard(text: &str) -> Result<()> {
    let mut clipboard = Clipboard::new().context("Failed to access system clipboard")?;

    clipboard
        .set_text(text.to_string())
        .context("Failed to set clipboard text")?;

    Ok(())
}

/// Copy formatted error information to clipboard.
///
/// This function formats error information with a timestamp, title, message,
/// and optional details, then copies it to the clipboard. The format is
/// designed to be easily pasted into bug reports or support requests.
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
pub fn copy_error_to_clipboard(title: &str, message: &str, details: Option<&str>) -> Result<()> {
    let timestamp = chrono::Local::now().format("%Y-%m-%d %H:%M:%S");

    let formatted = if let Some(details) = details {
        format!(
            "=== CLASSIC TUI Error Report ===\n\
             Timestamp: {}\n\
             Error: {}\n\
             Message: {}\n\n\
             Details:\n{}\n\
             ================================",
            timestamp, title, message, details
        )
    } else {
        format!(
            "=== CLASSIC TUI Error Report ===\n\
             Timestamp: {}\n\
             Error: {}\n\
             Message: {}\n\
             ================================",
            timestamp, title, message
        )
    };

    copy_to_clipboard(&formatted)
}

/// Check if clipboard is available on the current system.
///
/// This function attempts to create a clipboard instance to verify
/// that clipboard functionality is available. Useful for disabling
/// clipboard-related UI elements in headless environments.
///
/// # Returns
///
/// Returns `true` if clipboard is available, `false` otherwise.
///
/// # Examples
///
/// ```no_run
/// use classic_tui::handlers::clipboard_handler::is_clipboard_available;
///
/// if is_clipboard_available() {
///     println!("Clipboard support enabled");
/// } else {
///     println!("Clipboard not available (headless environment?)");
/// }
/// ```
pub fn is_clipboard_available() -> bool {
    Clipboard::new().is_ok()
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

        assert!(result.is_ok(), "Failed to copy error to clipboard: {:?}", result);
    }

    #[test]
    fn test_copy_error_to_clipboard_without_details() {
        if !is_clipboard_available() {
            eprintln!("Skipping clipboard test: clipboard not available");
            return;
        }

        let result = copy_error_to_clipboard(
            "Simple Error",
            "This error has no details",
            None,
        );

        assert!(result.is_ok(), "Failed to copy error to clipboard: {:?}", result);
    }

    #[test]
    fn test_is_clipboard_available() {
        // This just checks that the function doesn't panic
        let _ = is_clipboard_available();
    }
}
