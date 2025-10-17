// Clipboard handler for copy-to-clipboard functionality
//
// This module provides clipboard operations using the arboard crate,
// with proper error handling and success feedback.

use anyhow::{Context, Result};
use arboard::Clipboard;

/// Copy text to the system clipboard
///
/// Uses the arboard crate to access the system clipboard and copy the provided text.
///
/// # Arguments
/// * `text` - The text content to copy to clipboard
///
/// # Returns
/// * `Ok(())` - Text successfully copied to clipboard
/// * `Err(anyhow::Error)` - Failed to access clipboard or copy text
///
/// # Example
/// ```
/// use classic_gui_slint::handlers::clipboard;
///
/// match clipboard::copy_to_clipboard("Hello, world!") {
///     Ok(()) => println!("Copied to clipboard!"),
///     Err(e) => eprintln!("Failed to copy: {}", e),
/// }
/// ```
pub fn copy_to_clipboard(text: &str) -> Result<()> {
    tracing::debug!("Copying {} characters to clipboard", text.len());

    // Create clipboard context
    let mut clipboard = Clipboard::new()
        .context("Failed to access system clipboard")?;

    // Set clipboard text
    clipboard.set_text(text)
        .context("Failed to copy text to clipboard")?;

    tracing::info!("Successfully copied {} characters to clipboard", text.len());
    Ok(())
}

/// Clear the system clipboard
///
/// Clears the clipboard by setting it to an empty string.
///
/// # Returns
/// * `Ok(())` - Clipboard successfully cleared
/// * `Err(anyhow::Error)` - Failed to access or clear clipboard
#[allow(dead_code)]
pub fn clear_clipboard() -> Result<()> {
    tracing::debug!("Clearing clipboard");

    let mut clipboard = Clipboard::new()
        .context("Failed to access system clipboard")?;

    clipboard.set_text("")
        .context("Failed to clear clipboard")?;

    tracing::info!("Clipboard cleared");
    Ok(())
}

/// Get text from the system clipboard
///
/// Reads the current text content from the clipboard.
///
/// # Returns
/// * `Ok(String)` - Text content from clipboard
/// * `Err(anyhow::Error)` - Failed to access clipboard or read text
#[allow(dead_code)]
pub fn get_clipboard_text() -> Result<String> {
    tracing::debug!("Reading clipboard text");

    let mut clipboard = Clipboard::new()
        .context("Failed to access system clipboard")?;

    let text = clipboard.get_text()
        .context("Failed to read clipboard text")?;

    tracing::debug!("Read {} characters from clipboard", text.len());
    Ok(text)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_copy_and_read_clipboard() {
        // Note: This test may fail in CI environments without clipboard access
        let test_text = "Test clipboard content";

        // Try to copy text
        match copy_to_clipboard(test_text) {
            Ok(()) => {
                // Try to read it back
                match get_clipboard_text() {
                    Ok(clipboard_text) => {
                        assert_eq!(clipboard_text, test_text);
                    }
                    Err(e) => {
                        // Clipboard read may fail in CI
                        eprintln!("Note: Clipboard read test skipped (no clipboard access): {}", e);
                    }
                }
            }
            Err(e) => {
                // Clipboard write may fail in CI
                eprintln!("Note: Clipboard write test skipped (no clipboard access): {}", e);
            }
        }
    }

    #[test]
    fn test_clear_clipboard() {
        // Note: This test may fail in CI environments without clipboard access
        match clear_clipboard() {
            Ok(()) => {
                match get_clipboard_text() {
                    Ok(text) => assert_eq!(text, ""),
                    Err(e) => eprintln!("Note: Clipboard clear test skipped: {}", e),
                }
            }
            Err(e) => {
                eprintln!("Note: Clipboard clear test skipped (no clipboard access): {}", e);
            }
        }
    }
}
