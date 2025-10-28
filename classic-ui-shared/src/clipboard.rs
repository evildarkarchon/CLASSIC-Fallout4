//! Clipboard operations for copying and reading system clipboard.
//!
//! This module provides cross-platform clipboard functionality using the
//! `arboard` crate for copying error messages, report content, and other
//! text to the system clipboard, as well as reading from the clipboard.
//!
//! # Examples
//!
//! ```no_run
//! use classic_ui_shared::clipboard::{copy_to_clipboard, get_clipboard_text, is_clipboard_available};
//!
//! // Check if clipboard is available
//! if is_clipboard_available() {
//!     // Copy text to clipboard
//!     copy_to_clipboard("Hello, world!").expect("Failed to copy to clipboard");
//!
//!     // Read text from clipboard
//!     let text = get_clipboard_text().expect("Failed to read from clipboard");
//!     println!("Clipboard content: {}", text);
//! }
//! ```

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
/// use classic_ui_shared::clipboard::copy_to_clipboard;
///
/// match copy_to_clipboard("Important data") {
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
    tracing::debug!("Copying {} characters to clipboard", text.len());

    let mut clipboard = Clipboard::new().context("Failed to access system clipboard")?;

    clipboard
        .set_text(text.to_string())
        .context("Failed to set clipboard text")?;

    tracing::info!("Successfully copied {} characters to clipboard", text.len());
    Ok(())
}

/// Clear the system clipboard.
///
/// Clears the clipboard by setting it to an empty string.
///
/// # Returns
///
/// Returns `Ok(())` on success, or an error if clipboard operation fails.
///
/// # Examples
///
/// ```no_run
/// use classic_ui_shared::clipboard::clear_clipboard;
///
/// clear_clipboard().expect("Failed to clear clipboard");
/// ```
///
/// # Errors
///
/// Returns an error if:
/// - Clipboard is not available
/// - Clipboard access is denied by the system
pub fn clear_clipboard() -> Result<()> {
    tracing::debug!("Clearing clipboard");

    let mut clipboard = Clipboard::new().context("Failed to access system clipboard")?;

    clipboard
        .set_text("")
        .context("Failed to clear clipboard")?;

    tracing::info!("Clipboard cleared");
    Ok(())
}

/// Get text from the system clipboard.
///
/// Reads the current text content from the clipboard.
///
/// # Returns
///
/// Returns `Ok(String)` with the clipboard content on success, or an error if operation fails.
///
/// # Examples
///
/// ```no_run
/// use classic_ui_shared::clipboard::get_clipboard_text;
///
/// match get_clipboard_text() {
///     Ok(text) => println!("Clipboard: {}", text),
///     Err(e) => eprintln!("Failed to read clipboard: {}", e),
/// }
/// ```
///
/// # Errors
///
/// Returns an error if:
/// - Clipboard is not available
/// - Clipboard access is denied by the system
/// - Clipboard contains non-text data
pub fn get_clipboard_text() -> Result<String> {
    tracing::debug!("Reading clipboard text");

    let mut clipboard = Clipboard::new().context("Failed to access system clipboard")?;

    let text = clipboard
        .get_text()
        .context("Failed to read clipboard text")?;

    tracing::debug!("Read {} characters from clipboard", text.len());
    Ok(text)
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
/// use classic_ui_shared::clipboard::is_clipboard_available;
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
/// * `interface_name` - Name of the interface (e.g., "TUI", "GUI", "CLI")
///
/// # Returns
///
/// Returns `Ok(())` on success, or an error if clipboard operation fails.
///
/// # Examples
///
/// ```no_run
/// use classic_ui_shared::clipboard::copy_error_to_clipboard;
///
/// copy_error_to_clipboard(
///     "Database Error",
///     "Failed to connect to database",
///     Some("Connection timeout after 30 seconds\nHost: localhost:5432"),
///     "GUI"
/// )?;
/// # Ok::<(), anyhow::Error>(())
/// ```
///
/// # Errors
///
/// Returns an error if:
/// - Clipboard is not available
/// - Clipboard access is denied by the system
pub fn copy_error_to_clipboard(
    title: &str,
    message: &str,
    details: Option<&str>,
    interface_name: &str,
) -> Result<()> {
    let timestamp = chrono::Local::now().format("%Y-%m-%d %H:%M:%S");

    let formatted = if let Some(details) = details {
        format!(
            "=== CLASSIC {} Error Report ===\n\
             Timestamp: {}\n\
             Error: {}\n\
             Message: {}\n\n\
             Details:\n{}\n\
             ================================",
            interface_name, timestamp, title, message, details
        )
    } else {
        format!(
            "=== CLASSIC {} Error Report ===\n\
             Timestamp: {}\n\
             Error: {}\n\
             Message: {}\n\
             ================================",
            interface_name, timestamp, title, message
        )
    };

    copy_to_clipboard(&formatted)
}

#[cfg(test)]
mod tests {
    // NOTE: Clipboard tests are disabled due to heap corruption issues with arboard
    // in test environments on Windows. The clipboard functionality is manually tested.
    //
    // See: https://github.com/1Password/arboard/issues/
    //
    // Tests can be run manually in a regular application context.
}
